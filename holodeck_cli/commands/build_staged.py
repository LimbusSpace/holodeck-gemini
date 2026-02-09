"""
阶段化Build命令实现

支持--target, --until, --from, --only等阶段化执行参数。
"""

import sys
import time
from typing import List, Optional

from holodeck_cli.config import config
from holodeck_cli.logging_config import get_logger
from holodeck_cli.stages import BuildStage, stage_config
from holodeck_cli.stage_executor import StageExecutor
from holodeck_cli.utils import ensure_dir

try:
    from holodeck_core.storage.workspace_manager import WorkspaceManager
except ImportError as e:
    print(f"错误ck_core: 无法导入holode模块: {e}", file=sys.stderr)
    sys.exit(1)

logger = get_logger(__name__)


def parse_stage_args(args) -> tuple[Optional[BuildStage], Optional[BuildStage]]:
    """解析阶段参数，返回(from_stage, until_stage)"""

    # 检查参数冲突 - 允许--from和--until组合
    stage_args = [args.target, args.only]
    range_args = [args.from_stage, args.until]

    if sum(1 for arg in stage_args if arg is not None) > 1:
        logger.error("参数冲突: --target 和 --only 不能同时使用")
        return None, None

    if sum(1 for arg in stage_args if arg is not None) > 0 and sum(1 for arg in range_args if arg is not None) > 0:
        logger.error("参数冲突: --target/--only 不能与 --from/--until 同时使用")
        return None, None

    # 解析--only参数
    if args.only:
        try:
            stage = BuildStage.from_string(args.only)
            return stage, stage
        except ValueError as e:
            logger.error(str(e))
            return None, None

    # 解析--target参数 (等同于--until)
    if args.target:
        try:
            target_stage = BuildStage.from_string(args.target)
            return BuildStage.SESSION, target_stage
        except ValueError as e:
            logger.error(str(e))
            return None, None

    # 解析--from和--until参数
    if args.from_stage:
        try:
            from_stage = BuildStage.from_string(args.from_stage)
        except ValueError as e:
            logger.error(str(e))
            return None, None
    else:
        from_stage = BuildStage.SESSION

    if args.until:
        try:
            until_stage = BuildStage.from_string(args.until)
        except ValueError as e:
            logger.error(str(e))
            return None, None
    else:
        until_stage = BuildStage.LAYOUT

    return from_stage, until_stage


def validate_session_and_text(args) -> tuple[str, bool]:
    """验证会话和文本参数"""

    # 验证参数
    if not args.text and not args.session_id:
        logger.error("必须提供文本描述或会话ID")
        return "", False

    if args.text and args.session_id:
        logger.error("不能同时提供文本描述和会话ID")
        return "", False

    # 创建或验证会话
    workspace_manager = WorkspaceManager()

    if args.session_id:
        session_id = args.session_id
        if not workspace_manager.session_exists(session_id):
            logger.error(f"会话 {session_id} 不存在")
            return "", False
    else:
        # 创建新会话
        session_id = workspace_manager.create_session(args.text, args.style)
        logger.info(f"创建新会话: {session_id}")

    return session_id, True


def execute_staged_build(args) -> int:
    """执行阶段化build流程"""

    # 检查是否需要JSON输出，如果是则重定向日志到stderr
    json_mode = getattr(args, 'json', False)
    original_handlers = []

    if json_mode:
        import sys
        import logging

        # 保存原始的stdout处理器
        root_logger = logging.getLogger()
        original_handlers = [h for h in root_logger.handlers[:]]

        # 移除所有现有处理器
        for handler in original_handlers:
            root_logger.removeHandler(handler)

        # 为所有现有的logger移除stdout处理器并添加stderr处理器
        for logger_name in list(logging.Logger.manager.loggerDict.keys()):
            logger = logging.getLogger(logger_name)
            # 移除所有处理器
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            # 添加stderr处理器
            stderr_handler = logging.StreamHandler(sys.stderr)
            stderr_handler.setLevel(logging.INFO)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            stderr_handler.setFormatter(formatter)
            logger.addHandler(stderr_handler)

        # 添加根logger的stderr处理器
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        stderr_handler.setFormatter(formatter)
        root_logger.addHandler(stderr_handler)

    try:
        logger.info("开始阶段化构建流程...")
        start_time = time.time()

        # 1. 解析阶段参数
        from_stage, until_stage = parse_stage_args(args)
        if from_stage is None or until_stage is None:
            return 1

        logger.info(f"解析结果: from_stage={from_stage.value}, until_stage={until_stage.value}")
        logger.info(f"执行阶段范围: {from_stage.value} -> {until_stage.value}")

        # 2. 验证会话和文本参数
        session_id, success = validate_session_and_text(args)
        if not success:
            return 1

        # 3. 创建阶段执行器
        executor = StageExecutor(session_id)

        # 4. 获取要执行的阶段列表
        stages_to_execute = BuildStage.get_stages_between(from_stage, until_stage)

        logger.info(f"将执行以下阶段: {[s.value for s in stages_to_execute]}")

        # 5. 执行阶段
        stage_kwargs = {
            "text": args.text,
            "style": args.style,
            "max_objects": args.max_objects,
            "room_size": args.room_size,
            "skip_render": args.skip_render,
            "skip_assets": args.skip_assets,
            "no_blendermcp": args.no_blendermcp
        }

        # 如果指定了--from参数，跳过依赖检查
        skip_dependencies = args.from_stage is not None
        success = executor.execute_stages(stages_to_execute, skip_dependencies=skip_dependencies, **stage_kwargs)

        # 6. 输出执行结果
        elapsed_time = time.time() - start_time
        summary = executor.get_execution_summary()

        if json_mode:
            # JSON输出模式
            from holodeck_core.schemas.holodeck_error import SuccessResponse, ErrorResponse, ErrorCode, ErrorHandler

            # 收集产物文件
            artifacts = {}
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

            # 收集完成的阶段
            completed_stages = []
            for stage in stages_to_execute:
                result = executor.get_stage_result(stage)
                if result and result.get("success"):
                    completed_stages.append(stage.value)

            # 根据执行结果创建响应
            if success:
                # 创建成功响应
                response = SuccessResponse(
                    session_id=session_id,
                    workspace_path=str(session_dir),
                    artifacts=artifacts,
                    stages_completed=completed_stages,
                    message=f"阶段化构建完成! 总耗时: {elapsed_time:.2f}秒, {summary['successful_stages']}/{summary['total_stages']} 阶段成功"
                )
                return response
            else:
                # 创建错误响应
                error_response = ErrorHandler.create_error_response(
                    error_code=ErrorCode.E_INTERNAL_ERROR,
                    session_id=session_id,
                    message=f"阶段化构建失败! 总耗时: {elapsed_time:.2f}秒, {summary['successful_stages']}/{summary['total_stages']} 阶段成功",
                    additional_actions=["重试操作", "检查日志文件"]
                )
                return error_response
        else:
            # 传统文本输出模式
            logger.info(f"阶段化构建完成! 总耗时: {elapsed_time:.2f}秒")
            logger.info(f"会话ID: {session_id}")
            logger.info(f"执行摘要: {summary['successful_stages']}/{summary['total_stages']} 阶段成功")
            logger.info(f"工作目录: {config.get_workspace_path() / 'sessions' / session_id}")

            # 输出各阶段结果
            for stage in stages_to_execute:
                result = executor.get_stage_result(stage)
                if result:
                    status = "✓" if result.get("success") else "✗"
                    duration = result.get("duration", 0)
                    logger.info(f"  {status} {stage.value}: {duration:.2f}秒")

            return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("构建过程被用户中断")
        return 130
    except Exception as e:
        logger.exception(f"阶段化构建过程失败: {e}")
        return 1
    finally:
        # 恢复原始的日志处理器
        if json_mode and original_handlers:
            import logging
            root_logger = logging.getLogger()
            root_logger.handlers.clear()
            for handler in original_handlers:
                root_logger.addHandler(handler)


def build_command(args) -> int:
    """Build命令主函数（阶段化版本）"""

    # 如果没有指定任何阶段参数，使用传统build流程
    stage_args = [args.target, args.until, args.from_stage, args.only]
    if all(arg is None for arg in stage_args):
        # 导入传统build实现
        from holodeck_cli.commands.build import build_command as legacy_build_command
        return legacy_build_command(args)
    else:
        # 使用阶段化build实现
        return execute_staged_build(args)