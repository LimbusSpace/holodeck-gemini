"""
命令行接口主模块

使用argparse定义命令行接口，解析参数并分发到对应命令。
"""

import argparse
import sys
import os
import json
from pathlib import Path

from holodeck_cli.config import config
from holodeck_cli.logging_config import setup_logging, get_logger
from holodeck_cli.commands import build_command, session_command, debug_command
from holodeck_cli.error_handler import CLIErrorMiddleware
from holodeck_core.config.base import ConfigManager


def create_parser() -> argparse.ArgumentParser:
    """创建命令行解析器"""

    parser = argparse.ArgumentParser(
        prog="holodeck",
        description="Holodeck 3D场景生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  holodeck build "一个现代化的客厅，有沙发和茶几"
  holodeck build --style cyberpunk "一个卧室"
  holodeck session list
  holodeck debug validate
        """
    )

    # 全局选项
    parser.add_argument(
        "--version",
        action="version",
        version="holodeck-cli 0.1.0"
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="配置文件路径"
    )

    parser.add_argument(
        "--workspace",
        type=Path,
        help="工作空间目录"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别"
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="日志文件路径"
    )

    # 子命令
    subparsers = parser.add_subparsers(
        dest="command",
        help="可用命令",
        metavar="COMMAND"
    )

    # build 命令
    build_parser = subparsers.add_parser(
        "build",
        help="生成3D场景",
        description="根据文本描述生成3D场景，支持阶段化执行"
    )

    build_parser.add_argument(
        "text",
        type=str,
        nargs="?",
        help="场景描述文本 (如果不指定则需要有--session-id)"
    )

    build_parser.add_argument(
        "--style",
        type=str,
        default="modern",
        help="场景风格 (如: modern, cyberpunk, minimalist)"
    )

    build_parser.add_argument(
        "--session-id",
        type=str,
        help="会话ID (如果不指定则自动生成)"
    )

    build_parser.add_argument(
        "--output",
        type=Path,
        help="输出目录 (默认使用workspace/sessions/<session_id>)"
    )

    build_parser.add_argument(
        "--max-objects",
        type=int,
        default=25,
        help="最大对象数量"
    )

    build_parser.add_argument(
        "--room-size",
        type=float,
        nargs=3,
        metavar=("LENGTH", "WIDTH", "HEIGHT"),
        help="房间尺寸提示 (长 宽 高)"
    )

    build_parser.add_argument(
        "--skip-render",
        action="store_true",
        help="跳过渲染步骤"
    )

    build_parser.add_argument(
        "--skip-assets",
        action="store_true",
        help="跳过资产生成步骤"
    )

    build_parser.add_argument(
        "--no-blendermcp",
        action="store_true",
        help="跳过Blender MCP相关操作"
    )

    build_parser.add_argument(
        "--3d-backend",
        dest="backend_3d",
        choices=["auto", "hunyuan", "sf3d"],
        default="auto",
        help="3D生成后端选择 (auto: 自动选择, hunyuan: 混元3D, sf3d: SF3D)"
    )

    build_parser.add_argument(
        "--force-hunyuan",
        action="store_true",
        help="强制使用混元3D后端（如果可用）"
    )

    build_parser.add_argument(
        "--force-sf3d",
        action="store_true",
        help="强制使用SF3D后端"
    )

    # JSON输出选项
    build_parser.add_argument(
        "--json",
        action="store_true",
        help="输出JSON格式的结果"
    )

    # 阶段化执行参数
    stage_group = build_parser.add_argument_group("阶段化执行")

    stage_group.add_argument(
        "--target",
        type=str,
        help="运行到指定阶段 (如: objects, layout, render)"
    )

    stage_group.add_argument(
        "--until",
        type=str,
        help="运行到指定阶段（包含）"
    )

    stage_group.add_argument(
        "--from",
        dest="from_stage",
        type=str,
        help="从指定阶段开始"
    )

    stage_group.add_argument(
        "--only",
        type=str,
        help="只运行指定阶段"
    )

    # session 命令
    session_parser = subparsers.add_parser(
        "session",
        help="会话管理",
        description="管理生成会话"
    )

    session_subparsers = session_parser.add_subparsers(
        dest="session_action",
        help="会话操作",
        metavar="ACTION"
    )

    # session list
    list_parser = session_subparsers.add_parser(
        "list",
        help="列出所有会话"
    )

    list_parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="显示最近N个会话"
    )

    # session show
    show_parser = session_subparsers.add_parser(
        "show",
        help="显示会话详情"
    )

    show_parser.add_argument(
        "session_id",
        type=str,
        help="会话ID"
    )

    show_parser.add_argument(
        "--verbose",
        action="store_true",
        help="显示详细信息"
    )

    # session delete
    delete_parser = session_subparsers.add_parser(
        "delete",
        help="删除会话"
    )

    delete_parser.add_argument(
        "session_id",
        type=str,
        help="会话ID"
    )

    delete_parser.add_argument(
        "--force",
        action="store_true",
        help="强制删除，不确认"
    )

    # session status
    status_parser = session_subparsers.add_parser(
        "status",
        help="查看会话阶段状态"
    )

    status_parser.add_argument(
        "session_id",
        type=str,
        help="会话ID"
    )

    # debug 命令
    debug_parser = subparsers.add_parser(
        "debug",
        help="调试工具",
        description="调试和验证工具"
    )

    debug_subparsers = debug_parser.add_subparsers(
        dest="debug_action",
        help="调试操作",
        metavar="ACTION"
    )

    # debug validate
    validate_parser = debug_subparsers.add_parser(
        "validate",
        help="验证配置和环境"
    )

    # debug info
    info_parser = debug_subparsers.add_parser(
        "info",
        help="显示系统信息"
    )

    # debug test-asset
    test_asset_parser = debug_subparsers.add_parser(
        "test-asset",
        help="测试资产生成"
    )

    test_asset_parser.add_argument(
        "object_desc",
        type=str,
        help="对象描述"
    )

    # debug monitoring
    monitoring_parser = debug_subparsers.add_parser(
        "monitoring",
        help="监控和性能分析"
    )

    monitoring_subparsers = monitoring_parser.add_subparsers(
        dest="monitoring_action",
        help="监控操作",
        metavar="ACTION"
    )

    # debug monitoring status
    monitoring_status_parser = monitoring_subparsers.add_parser(
        "status",
        help="显示监控状态"
    )

    # debug monitoring metrics
    monitoring_metrics_parser = monitoring_subparsers.add_parser(
        "metrics",
        help="显示性能指标"
    )

    # debug monitoring health
    monitoring_health_parser = monitoring_subparsers.add_parser(
        "health",
        help="显示健康状态"
    )

    # debug alerts
    alerts_parser = debug_subparsers.add_parser(
        "alerts",
        help="告警管理"
    )

    alerts_subparsers = alerts_parser.add_subparsers(
        dest="alerts_action",
        help="告警操作",
        metavar="ACTION"
    )

    # debug alerts status
    alerts_status_parser = alerts_subparsers.add_parser(
        "status",
        help="显示告警状态"
    )

    # debug alerts history
    alerts_history_parser = alerts_subparsers.add_parser(
        "history",
        help="显示告警历史"
    )

    # debug alerts channels
    alerts_channels_parser = alerts_subparsers.add_parser(
        "channels",
        help="显示通知渠道"
    )

    return parser


def main():
    """主函数"""

    parser = create_parser()
    args = parser.parse_args()

    # 分发命令
    if not args.command:
        parser.print_help()
        return 1

    # 检查是否为JSON模式并尽早设置环境变量
    # 必须在任何日志配置之前设置，确保所有日志都输出到正确的流
    json_mode = hasattr(args, 'json') and args.json
    if json_mode:
        os.environ['HOLODECK_JSON_MODE'] = 'true'
    else:
        os.environ.pop('HOLODECK_JSON_MODE', None)

    # 设置日志 - 在配置系统初始化之前，确保日志重定向正确
    setup_logging(args.log_level, str(args.log_file) if args.log_file else None)

    # 初始化新的配置系统
    try:
        config_manager = ConfigManager()
        config_manager.ensure_env_loaded()
    except Exception as e:
        if json_mode:
            # JSON模式下输出结构化错误到stdout
            error_response = {
                "error": "ConfigurationError",
                "message": f"无法初始化新的配置系统: {e}",
                "session_id": None
            }
            print(json.dumps(error_response))
            return 1
        else:
            print(f"警告: 无法初始化新的配置系统: {e}", file=sys.stderr)

    # 处理全局选项
    if args.workspace:
        config.set("workspace_dir", str(args.workspace))

    # 重新获取logger以确保它已正确配置
    logger = get_logger(__name__)

    # 创建错误处理中间件
    error_middleware = CLIErrorMiddleware(json_mode=json_mode)

    try:
        # 包装命令函数
        if args.command == "build":
            wrapped_command = error_middleware.wrap_command(build_command)
            result = wrapped_command(args)
        elif args.command == "session":
            wrapped_command = error_middleware.wrap_command(session_command)
            result = wrapped_command(args)
        elif args.command == "debug":
            wrapped_command = error_middleware.wrap_command(debug_command)
            result = wrapped_command(args)
        else:
            logger.error(f"未知命令: {args.command}")
            return 1

        # 处理命令结果
        error_middleware.handle_command_result(result)
        return 0

    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        return 130
    except SystemExit:
        # 允许 SystemExit 正常传播
        raise
    except Exception as e:
        logger.exception(f"执行命令时发生错误: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())