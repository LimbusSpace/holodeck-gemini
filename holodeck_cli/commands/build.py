"""
Build 命令实现

完整的3D场景生成流程，使用新的统一客户端架构。
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from holodeck_cli.config import config
from holodeck_cli.logging_config import get_logger
from holodeck_cli.utils import ensure_dir, save_json
from holodeck_cli.performance import monitor_performance, performance_monitor

# 导入holodeck_core模块 - 向后兼容
try:
    from holodeck_cli.sync_session import SyncSessionManager
    from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer
    from holodeck_core.object_gen.asset_generator import AssetGenerator
    from holodeck_core.scene_gen.layout_solver import LayoutSolver
    from holodeck_core.blender.scene_assembler import SceneAssembler
except ImportError as e:
    print(f"错误: 无法导入holodeck_core模块: {e}", file=sys.stderr)
    print("请确保已安装holodeck_core包", file=sys.stderr)
    sys.exit(1)

# 导入新的统一客户端架构
try:
    from holodeck_core.clients.factory import (
        ImageClientFactory,
        LLMClientFactory,
        ThreeDClientFactory
    )
    from holodeck_core.integration.pipeline_orchestrator import PipelineOrchestrator
    from holodeck_core.exceptions.framework import HolodeckError
    NEW_ARCHITECTURE_AVAILABLE = False  # 临时使用传统架构来验证APIYi
except ImportError as e:
    print(f"警告: 无法导入新的统一客户端架构: {e}", file=sys.stderr)
    print("将使用旧架构", file=sys.stderr)
    NEW_ARCHITECTURE_AVAILABLE = False

# 导入解耦的Pipeline架构
try:
    from holodeck_core.pipeline import run_pipeline_sync
    DECOUPLED_PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入解耦Pipeline: {e}", file=sys.stderr)
    DECOUPLED_PIPELINE_AVAILABLE = False

logger = get_logger(__name__)


@monitor_performance("create_session")
def create_session(text: str, style: str, session_id: Optional[str] = None,
                  max_objects: int = 25, room_size: Optional[tuple] = None) -> str:
    """创建新的会话"""

    logger.info("创建新会话...")

    # 创建同步会话管理器
    workspace_path = config.get_workspace_path()
    session_manager = SyncSessionManager(workspace_path)

    # 准备请求数据
    request_data = {
        "text": text,
        "style": style,
        "constraints": {
            "max_objects": max_objects
        }
    }

    if room_size:
        request_data["constraints"]["room_size_hint"] = list(room_size)

    # 创建会话
    if session_id:
        session_id = session_manager.create_session(session_id, request_data)
        logger.info(f"使用指定会话ID: {session_id}")
    else:
        session_id = session_manager.create_session(None, request_data)
        logger.info(f"创建新会话: {session_id}")

    return session_id


@monitor_performance("generate_scene_ref")
def generate_scene_ref(session_id: str) -> Path:
    """生成场景参考图"""

    logger.info("生成场景参考图...")

    workspace_path = config.get_workspace_path()
    session_manager = SyncSessionManager(workspace_path)
    session = session_manager.load_session(session_id)

    # 使用工厂模式的SceneAnalyzer（推荐）
    if NEW_ARCHITECTURE_AVAILABLE:
        analyzer = SceneAnalyzer(use_factory=True)
    else:
        analyzer = SceneAnalyzer(api_key=None, use_comfyui=True)

    scene_ref_path = analyzer.generate_reference_image(session)

    logger.info(f"场景参考图已保存: {scene_ref_path}")
    return scene_ref_path


@monitor_performance("extract_objects")
def extract_objects(session_id: str) -> Dict[str, Any]:
    """提取场景对象"""

    logger.info("提取场景对象...")

    workspace_path = config.get_workspace_path()
    session_manager = SyncSessionManager(workspace_path)
    session = session_manager.load_session(session_id)

    # 使用工厂模式的SceneAnalyzer（推荐）
    if NEW_ARCHITECTURE_AVAILABLE:
        analyzer = SceneAnalyzer(use_factory=True)
    else:
        analyzer = SceneAnalyzer(api_key=None, use_comfyui=True)

    objects_data = analyzer.extract_objects(session)

    # 保存对象数据
    objects_path = session.get_objects_path()
    save_json(objects_data, objects_path)

    logger.info(f"提取了 {len(objects_data.get('objects', []))} 个对象")
    return objects_data


@monitor_performance("generate_object_cards")
def generate_object_cards(session_id: str) -> None:
    """生成对象卡片"""

    logger.info("生成对象卡片...")

    workspace_path = config.get_workspace_path()
    session_manager = SyncSessionManager(workspace_path)
    session = session_manager.load_session(session_id)

    # 使用工厂模式的SceneAnalyzer（推荐）
    if NEW_ARCHITECTURE_AVAILABLE:
        analyzer = SceneAnalyzer(use_factory=True)
    else:
        analyzer = SceneAnalyzer(api_key=None, use_comfyui=True)

    analyzer.generate_object_cards(session)

    logger.info("对象卡片生成完成")


@monitor_performance("generate_assets")
def generate_assets(session_id: str, skip_assets: bool = False,
                   backend: str = "auto", force_hunyuan: bool = False,
                   force_sf3d: bool = False) -> None:
    """生成3D资产"""

    if skip_assets:
        logger.info("跳过资产生成步骤")
        return

    logger.info("生成3D资产...")

    workspace_path = config.get_workspace_path()
    session_manager = SyncSessionManager(workspace_path)
    session = session_manager.load_session(session_id)

    # 处理后端选择
    if force_hunyuan and backend == "auto":
        backend = "hunyuan"
        logger.info("强制使用混元3D后端")
    elif force_sf3d and backend == "auto":
        backend = "sf3d"
        logger.info("强制使用SF3D后端")
    elif backend != "auto":
        logger.info(f"使用指定后端: {backend}")
    else:
        logger.info("使用自动后端选择")

    generator = AssetGenerator()

    # 如果指定了特定后端，临时修改后端选择器的配置
    if backend != "auto":
        # 保存原始配置
        original_selector = generator.backend_selector

        # 创建临时配置的后端选择器
        class TempBackendSelector:
            def __init__(self, preferred_backend):
                self.preferred_backend = preferred_backend

            def get_optimal_backend(self):
                return self.preferred_backend

        generator.backend_selector = TempBackendSelector(backend)


    # 获取对象列表
    objects_data = session.load_objects()
    objects = objects_data.get("objects", [])

    generated_count = 0
    failed_count = 0

    for obj in objects:
        object_id = obj.get("object_id")
        if not object_id:
            continue

        try:
            object_name = obj.get('name', object_id)
            logger.info(f"生成资产: {object_name} ({object_id})")

            # Check available backends before generation
            backend_info = generator.backend_selector.get_backend_info()
            logger.info(f"可用后端: {backend_info['available_backends']}, 最优后端: {backend_info['optimal_backend']}")

            asset_path = generator.generate_from_card(session, object_id)
            if asset_path:
                logger.info(f"资产生成成功: {object_name} -> {asset_path}")
                generated_count += 1
            else:
                logger.warning(f"资产生成失败: {object_name} ({object_id})")
                failed_count += 1

        except Exception as e:
            logger.error(f"生成资产 {object_name} ({object_id}) 时出错: {e}")
            # Try fallback to description-based generation
            try:
                logger.info(f"尝试使用描述生成作为回退: {object_id}")
                description = obj.get("visual_desc", obj.get("name", f"A 3D model of {object_id}"))
                style_context = {
                    "scene_style": objects_data.get("scene_style", "modern"),
                    "category": obj.get("category", "object")
                }
                asset_path = generator.generate_from_description(
                    session_id=session_id,
                    object_id=object_id,
                    description=description,
                    style_context=style_context
                )
                if asset_path:
                    logger.info(f"描述生成回退成功: {asset_path}")
                    generated_count += 1
                else:
                    logger.warning(f"描述生成回退也失败: {object_id}")
                    failed_count += 1
            except Exception as fallback_error:
                logger.error(f"描述生成回退也失败: {fallback_error}")
                failed_count += 1

    # 恢复原始后端选择器
    if backend != "auto":
        generator.backend_selector = original_selector

    logger.info(f"资产生成完成: 成功 {generated_count}, 失败 {failed_count}")


@monitor_performance("solve_layout")
def solve_layout(session_id: str) -> Dict[str, Any]:
    """求解布局"""

    logger.info("开始布局求解...")

    workspace_path = config.get_workspace_path()
    session_manager = SyncSessionManager(workspace_path)
    session = session_manager.load_session(session_id)

    solver = LayoutSolver()

    # 生成约束
    logger.info("生成布局约束...")
    constraints = solver.generate_constraints(session)

    # 保存约束
    constraints_path = session.get_constraints_path(version="v1")
    save_json(constraints, constraints_path)

    # DFS求解
    logger.info("执行DFS求解...")
    max_attempts = 3

    for attempt in range(max_attempts):
        logger.info(f"求解尝试 {attempt + 1}/{max_attempts}")

        try:
            solution = solver.solve_dfs(session, constraints_path)

            if solution and solution.get("success"):
                logger.info("布局求解成功")

                # 保存解决方案
                solution_path = session.get_layout_solution_path(version="v1")
                save_json(solution, solution_path)

                return solution
            else:
                logger.warning(f"布局求解失败 (尝试 {attempt + 1})")

                # 保存失败轨迹
                if solution:
                    trace_path = session.get_dfs_trace_path(version="v1")
                    save_json(solution.get("trace", {}), trace_path)

                if attempt < max_attempts - 1:
                    # 基于失败轨迹调整约束
                    logger.info("调整约束并重新尝试...")
                    constraints = solver.generate_constraints(
                        session,
                        hint_from_trace=solution.get("trace")
                    )
                    constraints_path = session.get_constraints_path(version=f"v{attempt+2}")
                    save_json(constraints, constraints_path)

        except Exception as e:
            logger.error(f"求解过程中出错 (尝试 {attempt + 1}): {e}")
            if attempt == max_attempts - 1:
                raise

    raise RuntimeError(f"布局求解失败，已尝试 {max_attempts} 次")


@monitor_performance("assemble_and_render")
def assemble_and_render(session_id: str, skip_render: bool = False, no_blendermcp: bool = False) -> None:
    """组装场景并渲染"""

    logger.info("组装3D场景...")

    workspace_path = config.get_workspace_path()
    session_manager = SyncSessionManager(workspace_path)
    session = session_manager.load_session(session_id)

    assembler = SceneAssembler()

    # 组装场景
    try:
        if no_blendermcp:
            logger.info("跳过Blender MCP操作，生成手动脚本...")
            # 生成手动脚本作为回退
            script_path = assembler._fallback_to_script_generation(session)
            logger.info(f"已生成手动组装脚本: {script_path}")
            blend_path = str(session.session_dir / "blender_scene.blend")
        else:
            blend_path = assembler.assemble_scene(session)
            logger.info(f"场景组装完成: {blend_path}")
    except Exception as e:
        logger.error(f"场景组装失败: {e}")
        if not no_blendermcp:
            logger.info("尝试使用回退方案...")
            try:
                script_path = assembler._fallback_to_script_generation(session)
                logger.info(f"已生成手动组装脚本: {script_path}")
                blend_path = str(session.session_dir / "blender_scene.blend")
            except Exception as fallback_error:
                logger.error(f"回退方案也失败: {fallback_error}")
                raise
        else:
            raise

    # 渲染
    if not skip_render:
        logger.info("开始渲染...")
        try:
            if no_blendermcp:
                logger.info("跳过Blender MCP渲染，生成手动脚本...")
                render_script_path = session.session_dir / "render_scene_manual.py"
                assembler._fallback_render_generation(session)
                logger.info(f"已生成手动渲染脚本: {render_script_path}")
            else:
                renders = assembler.render_scene(session, cameras="default")
                logger.info(f"渲染完成: {len(renders)} 张图片")
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            # 渲染失败不终止整个流程


def build_command(args) -> int:
    """Build命令主函数 - 支持新旧架构"""

    logger.info("开始构建3D场景...")
    start_time = time.time()

    try:
        # 优先使用解耦Pipeline架构
        use_decoupled = DECOUPLED_PIPELINE_AVAILABLE and getattr(args, 'use_decoupled', True)
        until_stage = getattr(args, 'until', None)

        if use_decoupled:
            logger.info("使用解耦Pipeline架构")
            result = _build_with_decoupled_pipeline(args, until_stage)
        elif NEW_ARCHITECTURE_AVAILABLE and getattr(args, 'use_new_arch', True):
            logger.info("使用新统一客户端架构")
            result = _build_with_new_architecture(args)
        else:
            logger.info("使用传统架构")
            result = _build_with_legacy_architecture(args)

        # 计算总耗时
        elapsed_time = time.time() - start_time

        if result == 0:
            logger.info(f"场景构建完成! 总耗时: {elapsed_time:.2f}秒")
            logger.info(f"工作目录: {config.get_workspace_path() / 'sessions'}")

            # 生成性能报告
            try:
                from holodeck_cli.performance import generate_performance_report
                report_path = generate_performance_report()
                logger.info(f"性能报告已生成: {report_path}")
            except Exception as e:
                logger.debug(f"生成性能报告失败: {e}")
        else:
            logger.error(f"场景构建失败，耗时: {elapsed_time:.2f}秒")

        return result

    except KeyboardInterrupt:
        logger.info("构建过程被用户中断")
        return 130
    except Exception as e:
        logger.exception(f"构建过程失败: {e}")
        return 1


def _build_with_decoupled_pipeline(args, until_stage: Optional[str] = None) -> int:
    """使用解耦Pipeline架构的构建流程"""
    try:
        workspace = str(config.get_workspace_path())
        data = run_pipeline_sync(
            text=args.text,
            style=args.style,
            workspace=workspace,
            until=until_stage,
            session_id=getattr(args, 'session_id', None)
        )

        json_mode = getattr(args, 'json', False)

        if not data.errors:
            if json_mode:
                from holodeck_core.schemas.holodeck_error import SuccessResponse
                response = SuccessResponse(
                    session_id=data.session_id,
                    workspace_path=str(data.session_dir),
                    artifacts={
                        "scene_ref": str(data.scene_ref_path) if data.scene_ref_path else None,
                        "objects": str(data.session_dir / "objects.json"),
                        "layout": str(data.session_dir / "layout_solution.json"),
                    },
                    stages_completed=list(data.metrics.keys()),
                    message=f"Pipeline完成! 耗时: {data.metrics.get('total_time', 0):.2f}秒"
                )
                print(response.to_json())
            else:
                logger.info(f"会话ID: {data.session_id}")
                logger.info(f"工作目录: {data.session_dir}")
            return 0
        else:
            if json_mode:
                from holodeck_core.schemas.holodeck_error import ErrorHandler, ErrorCode
                error_response = ErrorHandler.create_error_response(
                    error_code=ErrorCode.E_INTERNAL_ERROR,
                    session_id=data.session_id,
                    message=f"Pipeline失败: {data.errors}",
                    additional_actions=["检查日志"]
                )
                print(error_response.to_json())
            else:
                logger.error(f"Pipeline失败: {data.errors}")
            return 1

    except Exception as e:
        logger.error(f"解耦Pipeline执行失败: {e}")
        logger.info("回退到传统架构...")
        return _build_with_legacy_architecture(args)
    """使用新统一客户端架构的构建流程"""

    try:
        # 创建客户端工厂
        image_factory = ImageClientFactory()
        llm_factory = LLMClientFactory()
        threed_factory = ThreeDClientFactory()

        # 创建客户端实例
        image_client = image_factory.create_client()
        llm_client = llm_factory.create_client()
        threed_client = threed_factory.create_client()

        logger.info(f"选择的图像客户端: {image_client.get_service_type()}")
        logger.info(f"选择的LLM客户端: {llm_client.get_service_type()}")
        logger.info(f"选择的3D客户端: {threed_client.get_service_type()}")

        # 创建管道编排器配置
        from holodeck_core.integration.pipeline_orchestrator import PipelineConfig

        pipeline_config = PipelineConfig(
            workspace_root=str(config.get_workspace_path()),
            session_id=args.session_id,
            enable_naming=True,
            enable_image_generation=True,
            enable_3d_generation=not args.skip_assets
        )

        orchestrator = PipelineOrchestrator(config=pipeline_config)

        # 准备管道输入上下文
        input_context = {
            "object_description": args.text,
            "object_name": f"Scene object from: {args.text[:50]}",
            "generation_prompt": f"A {args.style} style scene: {args.text}",
            "style": args.style,
            "max_objects": args.max_objects
        }

        # 执行管道
        import asyncio
        result = asyncio.run(orchestrator.execute_pipeline(input_context))

        # 检查是否需要JSON输出
        json_mode = getattr(args, 'json', False)

        if result.success:
            if json_mode:
                # JSON输出模式
                from holodeck_core.schemas.holodeck_error import SuccessResponse

                # 收集产物文件
                artifacts = {}
                workspace_path = config.get_workspace_path()
                session_dir = workspace_path / "sessions" / result.session_id

                # 检查常见的产物文件
                artifact_files = [
                    "scene_ref.png",
                    "objects.json",
                    "constraints_v1.json",
                    "layout_solution_v1.json",
                    "asset_manifest.json",
                    "blender_object_map.json"
                ]

                for artifact_file in artifact_files:
                    artifact_path = session_dir / artifact_file
                    if artifact_path.exists():
                        artifacts[artifact_file] = str(artifact_path)

                # 创建成功响应
                response = SuccessResponse(
                    session_id=result.session_id,
                    workspace_path=str(session_dir),
                    artifacts=artifacts,
                    stages_completed=result.metadata.get('completed_stages', []),
                    message=f"新架构场景生成成功! 总耗时: {result.total_time:.2f}秒"
                )

                # 输出JSON
                print(response.to_json())
                return 0
            else:
                # 传统文本输出模式
                logger.info(f"新架构场景生成成功")
                logger.info(f"会话ID: {result.session_id}")
                logger.info(f"完成阶段: {result.metadata.get('completed_stages', [])}")
                logger.info(f"总耗时: {result.total_time:.2f}秒")
                return 0
        else:
            if json_mode:
                # JSON错误输出模式
                from holodeck_core.schemas.holodeck_error import ErrorHandler, ErrorCode

                error_response = ErrorHandler.create_error_response(
                    error_code=ErrorCode.E_INTERNAL_ERROR,
                    session_id=result.session_id if hasattr(result, 'session_id') else getattr(args, 'session_id', None),
                    message=f"新架构场景生成失败: {result.error}",
                    additional_actions=["重试操作", "回退到传统架构"]
                )
                print(error_response.to_json())
                return 1
            else:
                # 传统文本错误输出模式
                logger.error(f"新架构场景生成失败: {result.error}")
                # 回退到传统架构
                logger.info("回退到传统架构...")
                return _build_with_legacy_architecture(args)

    except Exception as e:
        # 检查是否需要JSON输出
        json_mode = getattr(args, 'json', False)

        if json_mode:
            # JSON错误输出模式
            from holodeck_core.schemas.holodeck_error import ErrorHandler, ErrorCode

            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INTERNAL_ERROR,
                session_id=getattr(args, 'session_id', None),
                message=f"新架构执行失败: {str(e)}",
                additional_actions=["重试操作", "回退到传统架构"]
            )
            print(error_response.to_json())
            return 1
        else:
            # 传统文本错误输出模式
            logger.error(f"新架构执行失败: {e}")
            logger.info("回退到传统架构...")
            return _build_with_legacy_architecture(args)


def _build_with_legacy_architecture(args) -> int:
    """使用传统架构的构建流程（向后兼容）"""

    try:
        # 1. 创建会话
        session_id = create_session(
            text=args.text,
            style=args.style,
            session_id=args.session_id,
            max_objects=args.max_objects,
            room_size=args.room_size
        )

        # 2. 生成场景参考图
        generate_scene_ref(session_id)

        # 3. 提取对象
        extract_objects(session_id)

        # 4. 生成对象卡片
        generate_object_cards(session_id)

        # 5. 生成资产
        generate_assets(session_id, skip_assets=args.skip_assets, backend=args.backend_3d,
                       force_hunyuan=getattr(args, 'force_hunyuan', False),
                       force_sf3d=getattr(args, 'force_sf3d', False))

        # 6. 求解布局
        solve_layout(session_id)

        # 7. 组装和渲染
        assemble_and_render(
            session_id,
            skip_render=args.skip_render,
            no_blendermcp=getattr(args, 'no_blendermcp', False)
        )

        # 检查是否需要JSON输出
        json_mode = getattr(args, 'json', False)

        if json_mode:
            # JSON输出模式
            from holodeck_core.schemas.holodeck_error import SuccessResponse

            # 收集产物文件
            artifacts = {}
            from holodeck_cli.config import config
            workspace_path = config.get_workspace_path()
            session_dir = workspace_path / "sessions" / session_id

            # 检查常见的产物文件
            artifact_files = [
                "scene_ref.png",
                "objects.json",
                "constraints_v1.json",
                "layout_solution_v1.json",
                "asset_manifest.json",
                "blender_object_map.json"
            ]

            for artifact_file in artifact_files:
                artifact_path = session_dir / artifact_file
                if artifact_path.exists():
                    artifacts[artifact_file] = str(artifact_path)

            # 传统架构的所有阶段
            completed_stages = [
                "session", "scene_ref", "objects", "cards",
                "assets", "constraints", "layout", "assembly"
            ]

            # 创建成功响应
            response = SuccessResponse(
                session_id=session_id,
                workspace_path=str(session_dir),
                artifacts=artifacts,
                stages_completed=completed_stages,
                message=f"传统架构构建完成! 会话ID: {session_id}"
            )

            # 输出JSON
            print(response.to_json())
            return 0
        else:
            # 传统文本输出模式
            logger.info(f"会话ID: {session_id}")
            return 0

    except Exception as e:
        # 检查是否需要JSON输出
        json_mode = getattr(args, 'json', False)

        if json_mode:
            # JSON错误输出模式
            from holodeck_core.schemas.holodeck_error import ErrorHandler, ErrorCode

            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INTERNAL_ERROR,
                session_id=getattr(args, 'session_id', None),
                message=f"传统架构执行失败: {str(e)}",
                additional_actions=["重试操作", "检查日志文件"]
            )
            print(error_response.to_json())
            return 1
        else:
            # 传统文本错误输出模式
            logger.exception(f"传统架构执行失败: {e}")
            return 1


def demonstrate_factory_usage() -> None:
    """演示新的工厂架构使用方法"""

    logger.info("=== 演示新的工厂架构 ===")

    try:
        # 1. 创建LLM工厂
        llm_factory = LLMClientFactory()

        # 2. 创建统一VLM客户端
        vlm_client = llm_factory.create_client(
            client_name="unified_vlm",
            features=["object_extraction", "vision"]
        )

        logger.info(f"创建的统一VLM客户端: {type(vlm_client).__name__}")

        # 3. 获取客户端信息
        if hasattr(vlm_client, 'get_backend_info'):
            backend_info = vlm_client.get_backend_info()
            logger.info(f"后端信息: {backend_info}")

        # 4. 测试连接
        import asyncio
        connection_ok = asyncio.run(vlm_client.test_connection())
        logger.info(f"连接测试: {'成功' if connection_ok else '失败'}")

        # 5. 检查特性支持
        if hasattr(vlm_client, 'supports_feature'):
            features_to_check = ["object_extraction", "vision", "scene_analysis"]
            for feature in features_to_check:
                supported = asyncio.run(vlm_client.supports_feature(feature))
                logger.info(f"特性 '{feature}': {'支持' if supported else '不支持'}")

        logger.info("=== 工厂架构演示完成 ===")

    except Exception as e:
        logger.error(f"工厂架构演示失败: {e}")
        logger.info("将使用传统架构")