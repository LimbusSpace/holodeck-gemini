"""
Session 管理命令实现
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# 导入新架构组件
new_architecture_available = False
try:
    from holodeck_core.config.base import ConfigManager
    from holodeck_core.logging.standardized import get_logger as get_standardized_logger
    from holodeck_core.exceptions.framework import ConfigurationError
    from holodeck_core.storage.session_manager import SessionManager

    # 使用新的配置管理和日志系统
    config_manager = ConfigManager()
    logger = get_standardized_logger(__name__)
    new_architecture_available = True
except ImportError as e:
    print(f"警告: 无法导入新的统一架构: {e}")
    print("将使用传统架构")

    # 向后兼容 - 使用旧系统
    from holodeck_cli.config import config
    from holodeck_cli.logging_config import get_logger
    from holodeck_cli.utils import ensure_dir, load_json, save_json
    from holodeck_cli.stages import BuildStage, stage_config

    logger = get_logger(__name__)

# 会话状态缓存 - 用于提高性能
_session_cache = {}
_cache_ttl = 300  # 5分钟缓存

def _get_cached_session_info(session_id: str) -> Optional[Dict[str, Any]]:
    """获取缓存的会话信息"""
    cache_key = f"session_{session_id}"
    cached_data = _session_cache.get(cache_key)

    if cached_data:
        timestamp, data = cached_data
        if time.time() - timestamp < _cache_ttl:
            return data
        else:
            # 缓存过期，删除
            del _session_cache[cache_key]

    return None

def _cache_session_info(session_id: str, data: Dict[str, Any]) -> None:
    """缓存会话信息"""
    cache_key = f"session_{session_id}"
    _session_cache[cache_key] = (time.time(), data)

def _invalidate_session_cache(session_id: str) -> None:
    """使会话缓存失效"""
    cache_key = f"session_{session_id}"
    if cache_key in _session_cache:
        del _session_cache[cache_key]

def clear_session_cache() -> None:
    """清除所有会话缓存"""
    _session_cache.clear()
    logger.info("会话缓存已清除")

def _get_workspace_path():
    """获取工作空间路径 - 支持新旧架构"""
    if new_architecture_available:
        return config_manager.get_workspace_path()
    else:
        return config.get_workspace_path()

def _get_logger():
    """获取日志记录器 - 支持新旧架构"""
    return logger


def list_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """列出所有会话 - 支持新旧架构和缓存"""

    workspace_path = _get_workspace_path()
    sessions_dir = workspace_path / "sessions"

    if not sessions_dir.exists():
        logger.info("没有找到任何会话")
        return []

    sessions = []

    # 获取所有会话目录
    for session_dir in sessions_dir.iterdir():
        if session_dir.is_dir():
            session_id = session_dir.name

            # 检查缓存
            cached_info = _get_cached_session_info(session_id)
            if cached_info:
                sessions.append(cached_info)
                continue

            request_path = session_dir / "request.json"

            session_info = {
                "session_id": session_id,
                "path": session_dir,
                "exists": True
            }

            # 尝试读取请求信息
            if request_path.exists():
                try:
                    if new_architecture_available:
                        # 使用新架构的JSON加载
                        from holodeck_cli.utils import load_json
                    request_data = load_json(request_path)
                    session_info["text"] = request_data.get("text", "未知")
                    session_info["style"] = request_data.get("style", "未知")
                    session_info["created"] = request_data.get("created")
                except Exception as e:
                    session_info["error"] = f"读取失败: {e}"
            else:
                session_info["text"] = "无描述"

            # 检查关键文件
            session_info["has_objects"] = (session_dir / "objects.json").exists()
            session_info["has_layout"] = (session_dir / "layout_solution_v1.json").exists()
            session_info["has_blend"] = (session_dir / "blender_scene.blend").exists()
            session_info["has_renders"] = (session_dir / "renders").exists()

            # 缓存会话信息
            _cache_session_info(session_id, session_info)
            sessions.append(session_info)

    # 按创建时间排序（如果有）
    sessions.sort(
        key=lambda s: s.get("created") or "",
        reverse=True
    )

    return sessions[:limit]


def show_session_details(session_id: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """显示会话详情 - 支持新旧架构"""

    workspace_path = _get_workspace_path()
    session_dir = workspace_path / "sessions" / session_id

    if not session_dir.exists():
        logger.error(f"会话不存在: {session_id}")
        return None

    # 读取基本信息
    request_path = session_dir / "request.json"
    if request_path.exists():
        try:
            request_data = load_json(request_path)
        except Exception as e:
            logger.error(f"无法读取请求文件: {e}")
            request_data = {}
    else:
        request_data = {}

    # 读取对象信息
    objects_data = None
    objects_path = session_dir / "objects.json"
    if objects_path.exists():
        try:
            objects_data = load_json(objects_path)
        except Exception as e:
            logger.warning(f"无法读取对象文件: {e}")

    # 读取布局信息
    layout_data = None
    layout_path = session_dir / "layout_solution_v1.json"
    if layout_path.exists():
        try:
            layout_data = load_json(layout_path)
        except Exception as e:
            logger.warning(f"无法读取布局文件: {e}")

    # 构建会话详情
    details = {
        "session_id": session_id,
        "path": session_dir,
        "request": request_data,
        "objects": objects_data,
        "layout": layout_data,
        "files": {}
    }

    # 检查文件状态
    important_files = [
        "request.json",
        "scene_ref.png",
        "objects.json",
        "constraints_v1.json",
        "layout_solution_v1.json",
        "dfs_trace_v1.json",
        "blender_scene.blend"
    ]

    for filename in important_files:
        file_path = session_dir / filename
        details["files"][filename] = {
            "exists": file_path.exists(),
            "size": file_path.stat().st_size if file_path.exists() else 0
        }

    # 检查渲染目录
    renders_dir = session_dir / "renders"
    if renders_dir.exists():
        render_files = list(renders_dir.glob("*.png")) + list(renders_dir.glob("*.jpg"))
        details["renders"] = {
            "count": len(render_files),
            "files": [f.name for f in render_files]
        }

    return details


def delete_session(session_id: str, force: bool = False) -> bool:
    """删除会话 - 支持新旧架构"""

    workspace_path = _get_workspace_path()
    session_dir = workspace_path / "sessions" / session_id

    if not session_dir.exists():
        logger.error(f"会话不存在: {session_id}")
        return False

    if not force:
        # 确认删除
        confirm = input(f"确定要删除会话 {session_id} 吗? (y/N): ")
        if confirm.lower() != 'y':
            logger.info("删除操作已取消")
            return False

    try:
        import shutil
        shutil.rmtree(session_dir)
        # 清除缓存
        _invalidate_session_cache(session_id)
        logger.info(f"会话 {session_id} 已删除")
        return True
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return False


def check_session_stage_status(session_id: str) -> Dict[str, Any]:
    """检查会话的阶段状态 - 支持新旧架构"""

    workspace_path = _get_workspace_path()
    session_dir = workspace_path / "sessions" / session_id

    if not session_dir.exists():
        logger.error(f"会话不存在: {session_id}")
        return {}

    # 模拟StageExecutor的状态检查逻辑
    stage_status = {}

    for stage in BuildStage.get_execution_order():
        if stage == BuildStage.ALL:
            continue

        output_files = stage_config.get_output_files(stage)
        stage_completed = True

        for output_file in output_files:
            file_path = session_dir / output_file

            if output_file.endswith('/'):
                # 目录检查
                if not file_path.exists() or not file_path.is_dir():
                    stage_completed = False
                    break
                # 检查目录是否为空
                if not any(file_path.iterdir()):
                    stage_completed = False
                    break
            else:
                # 文件检查
                if not file_path.exists():
                    stage_completed = False
                    break

        stage_status[stage.value] = {
            "completed": stage_completed,
            "description": stage_config.get_description(stage),
            "output_files": output_files
        }

    return stage_status


def print_session_status(session_id: str, stage_status: Dict[str, Any]) -> None:
    """打印会话阶段状态"""

    print(f"会话阶段状态: {session_id}")
    print("=" * 50)

    order = BuildStage.get_execution_order()
    for stage in order:
        if stage == BuildStage.ALL:
            continue

        status = stage_status.get(stage.value, {})
        completed = status.get("completed", False)
        description = status.get("description", "")

        status_symbol = "Y" if completed else "N"
        print(f"{status_symbol} {stage.value:<12} - {description}")

        # 显示输出文件状态
        output_files = status.get("output_files", [])
        for output_file in output_files:
            file_path = _get_workspace_path() / "sessions" / session_id / output_file

            if output_file.endswith('/'):
                # 目录
                exists = file_path.exists() and file_path.is_dir()
                file_status = "存在" if exists else "缺失"
                file_count = len(list(file_path.iterdir())) if exists else 0
                print(f"  [DIR] {output_file} ({file_status}, {file_count} files)")
            else:
                # 文件
                exists = file_path.exists()
                file_status = "存在" if exists else "缺失"
                file_size = f" ({file_path.stat().st_size} bytes)" if exists else ""
                print(f"  [FILE] {output_file} ({file_status}{file_size})")

    print()

    # 计算进度
    total_stages = len([s for s in order if s != BuildStage.ALL])
    completed_stages = sum(1 for status in stage_status.values() if status.get("completed", False))
    progress = (completed_stages / total_stages * 100) if total_stages > 0 else 0

    print(f"进度: {completed_stages}/{total_stages} 阶段完成 ({progress:.1f}%)")

    # 显示建议的下一个阶段
    for stage in order:
        if stage == BuildStage.ALL:
            continue
        if not stage_status.get(stage.value, {}).get("completed", False):
            print(f"建议下一步: holodeck build --session {session_id} --from {stage.value}")
            break


def print_session_list(sessions: List[Dict[str, Any]]) -> None:
    """打印会话列表"""

    if not sessions:
        print("没有找到会话")
        return

    print(f"{'会话ID':<20} {'描述':<30} {'对象':<8} {'布局':<8} {'Blender':<8} {'渲染':<8}")
    print("-" * 80)

    for session in sessions:
        session_id = session["session_id"]
        text = session.get("text", "无描述")[:28]

        has_objects = "Y" if session.get("has_objects") else "N"
        has_layout = "Y" if session.get("has_layout") else "N"
        has_blend = "Y" if session.get("has_blend") else "N"
        has_renders = "Y" if session.get("has_renders") else "N"

        print(f"{session_id:<20} {text:<30} {has_objects:<8} {has_layout:<8} {has_blend:<8} {has_renders:<8}")


def print_session_details(details: Dict[str, Any], verbose: bool = False) -> None:
    """打印会话详情"""

    session_id = details["session_id"]
    request = details.get("request", {})

    print(f"会话: {session_id}")
    print(f"路径: {details['path']}")
    print()

    print("请求信息:")
    print(f"  描述: {request.get('text', '未知')}")
    print(f"  风格: {request.get('style', '未知')}")
    print(f"  创建时间: {request.get('created', '未知')}")
    print()

    # 对象信息
    objects_data = details.get("objects")
    if objects_data:
        objects = objects_data.get("objects", [])
        print(f"对象 ({len(objects)} 个):")
        for obj in objects[:5]:  # 最多显示5个
            print(f"  - {obj.get('name', '未知')} ({obj.get('object_id', '未知')})")
        if len(objects) > 5:
            print(f"  ... 还有 {len(objects) - 5} 个对象")
        print()

    # 文件状态
    print("文件状态:")
    files = details.get("files", {})
    for filename, info in files.items():
        status = "✓" if info["exists"] else "✗"
        size_str = f" ({info['size']} bytes)" if info["exists"] else ""
        print(f"  {filename}: {status}{size_str}")

    # 渲染信息
    renders = details.get("renders")
    if renders:
        print(f"  渲染图片: {renders['count']} 张")
        if verbose and renders.get("files"):
            for filename in renders["files"]:
                print(f"    - {filename}")
    print()

    # 详细信息
    if verbose:
        layout = details.get("layout")
        if layout:
            print("布局信息:")
            print(f"  成功: {layout.get('success', False)}")
            print(f"  对象数量: {len(layout.get('objects', []))}")
            print()


def session_command(args) -> int:
    """Session命令主函数"""

    if not args.session_action:
        print("请指定会话操作 (list/show/delete)")
        return 1

    try:
        if args.session_action == "list":
            sessions = list_sessions(args.limit)
            print_session_list(sessions)
            return 0

        elif args.session_action == "show":
            if not args.session_id:
                logger.error("请指定会话ID")
                return 1

            details = show_session_details(args.session_id, args.verbose)
            if details:
                print_session_details(details, args.verbose)
                return 0
            else:
                return 1

        elif args.session_action == "delete":
            if not args.session_id:
                logger.error("请指定会话ID")
                return 1

            success = delete_session(args.session_id, args.force)
            return 0 if success else 1

        elif args.session_action == "status":
            if not args.session_id:
                logger.error("请指定会话ID")
                return 1

            stage_status = check_session_stage_status(args.session_id)
            if stage_status:
                print_session_status(args.session_id, stage_status)
                return 0
            else:
                return 1

        elif args.session_action == "cache-clear":
            clear_session_cache()
            print("会话缓存已清除")
            return 0

        elif args.session_action == "cache-stats":
            cache_size = len(_session_cache)
            print(f"会话缓存统计:")
            print(f"  缓存会话数: {cache_size}")
            print(f"  缓存TTL: {_cache_ttl}秒")
            if cache_size > 0:
                print("  缓存的会话:")
                for cache_key in _session_cache.keys():
                    session_id = cache_key.replace("session_", "")
                    print(f"    - {session_id}")
            return 0

        else:
            logger.error(f"未知的会话操作: {args.session_action}")
            return 1

    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        return 130
    except Exception as e:
        logger.exception(f"执行会话命令时出错: {e}")
        return 1