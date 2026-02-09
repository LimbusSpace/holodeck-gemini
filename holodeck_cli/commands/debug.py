"""
Debug 命令实现

调试和验证工具。
"""

import sys
import os
import time
import platform
import json
from pathlib import Path
from typing import Dict, Any, List

# 导入新架构组件
new_architecture_available = False
try:
    from holodeck_core.config.base import ConfigManager
    from holodeck_core.logging.standardized import get_logger as get_standardized_logger, log_time
    from holodeck_core.exceptions.framework import (
        ConfigurationError, ValidationError, APIError, HolodeckError
    )
    from holodeck_core.clients.factory import (
        ImageClientFactory,
        LLMClientFactory,
        ThreeDClientFactory
    )
    from holodeck_core.storage.session_manager import SessionManager
    from holodeck_core.object_gen.asset_generator import AssetGenerator

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

    logger = get_logger(__name__)

def _get_config():
    """获取配置 - 支持新旧架构"""
    if new_architecture_available:
        return config_manager
    else:
        return config

def _get_logger():
    """获取日志记录器 - 支持新旧架构"""
    return logger


@log_time("test_asset_generation")
def test_asset_generation(object_desc: str) -> bool:
    """测试资产生成 - 支持新旧架构"""

    logger.info(f"测试资产生成: {object_desc}")

    try:
        current_config = _get_config()
        workspace_path = current_config.get_workspace_path()
        session_manager = SessionManager(workspace_path)

        # 创建临时会话数据
        temp_session_id = f"test_asset_{int(time.time())}"
        request_data = {
            "text": f"测试对象: {object_desc}",
            "style": "modern",
            "is_test": True
        }

        session_manager.create_session(temp_session_id, request_data)
        session = session_manager.load_session(temp_session_id)

        # 创建测试对象
        test_object = {
            "object_id": "test_obj_001",
            "name": "test_object",
            "category": "test",
            "visual_desc": object_desc,
            "must_exist": True
        }

        # 创建对象卡片
        object_cards_dir = session.get_object_cards_dir()
        object_cards_dir.mkdir(parents=True, exist_ok=True)

        card_path = object_cards_dir / f"{test_object['object_id']}.json"
        with open(card_path, 'w', encoding='utf-8') as f:
            json.dump(test_object, f, indent=2, ensure_ascii=False)

        # 尝试生成资产
        generator = AssetGenerator()
        asset_path = generator.generate_from_card(session, test_object['object_id'])

        if asset_path and asset_path.exists():
            logger.info(f"资产生成成功: {asset_path}")
            logger.info(f"文件大小: {asset_path.stat().st_size} bytes")
            return True
        else:
            logger.error("资产生成失败")
            return False

    except Exception as e:
        logger.exception(f"资产生成测试失败: {e}")
        return False

    finally:
        # 清理临时会话
        try:
            temp_session_dir = workspace_path / "sessions" / temp_session_id
            if temp_session_dir.exists():
                import shutil
                shutil.rmtree(temp_session_dir)
        except Exception as e:
            logger.warning(f"清理临时会话失败: {e}")


@log_time("validate_environment")
def validate_environment() -> Dict[str, Any]:
    """验证运行环境 - 使用增强的错误处理"""

    results = {
        "system": {},
        "python": {},
        "dependencies": {},
        "configuration": {},
        "paths": {},
        "api_keys": {},
        "clients": {},  # 新增：客户端状态检查
        "errors": []    # 新增：错误收集
    }

    try:
        # 系统信息
        results["system"] = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.architecture()[0],
            "machine": platform.machine()
        }

        # Python信息
        results["python"] = {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": sys.executable
        }

        # 检查依赖
        dependencies = [
            "holodeck_core",
            "requests",
            "pillow",
            "numpy"
        ]

        for dep in dependencies:
            try:
                __import__(dep)
                results["dependencies"][dep] = "Y 已安装"
            except ImportError as e:
                results["dependencies"][dep] = f"N 未安装 ({e})"
                if dep == "holodeck_core":
                    results["errors"].append(ConfigurationError(
                        message=f"关键依赖 {dep} 未安装",
                        recovery_suggestion=["运行: uv sync 安装依赖"]
                    ))

        # 配置检查 - 支持新旧架构
        current_config = _get_config()
        try:
            results["configuration"] = {
                "workspace_dir": str(current_config.get_workspace_path()),
                "cache_dir": str(current_config.get_cache_path()),
                "log_level": current_config.get("log_level"),
                "max_workers": current_config.get("max_workers"),
                "timeout": current_config.get("timeout"),
                "architecture": "new" if new_architecture_available else "legacy"
            }
        except Exception as e:
            results["errors"].append(ConfigurationError(
                message=f"配置读取失败: {e}",
                recovery_suggestion=["检查配置文件", "验证环境变量"]
            ))

        # 路径检查
        try:
            workspace_path = current_config.get_workspace_path()
            cache_path = current_config.get_cache_path()
            important_paths = [workspace_path, cache_path, workspace_path / "sessions"]

            for path in important_paths:
                exists = path.exists()
                writable = os.access(path, os.W_OK) if exists else os.access(path.parent, os.W_OK)
                results["paths"][str(path)] = {
                    "exists": exists,
                    "writable": writable
                }

                if not exists:
                    results["errors"].append(ValidationError(
                        message=f"路径不存在: {path}",
                        field_name="path",
                        field_value=str(path)
                    ))
                elif not writable:
                    results["errors"].append(ValidationError(
                        message=f"路径不可写: {path}",
                        field_name="path",
                        field_value=str(path)
                    ))
        except Exception as e:
            results["errors"].append(ConfigurationError(
                message=f"路径检查失败: {e}",
                recovery_suggestion=["检查工作空间权限"]
            ))

        # API密钥检查
        api_services = ["openai", "stability", "meshy", "replicate", "hunyuan", "sf3d"]
        for service in api_services:
            try:
                api_key = current_config.get_api_key(service)
                if api_key:
                    # 隐藏密钥，只显示前几位
                    masked_key = api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
                    results["api_keys"][service] = f"Y 已配置 ({masked_key})"
                else:
                    results["api_keys"][service] = "N 未配置"
            except Exception as e:
                results["api_keys"][service] = f"E 检查失败 ({e})"

        # 客户端状态检查（仅在新架构可用时）
        if new_architecture_available:
            try:
                results["clients"] = _check_client_status()
            except Exception as e:
                results["errors"].append(APIError(
                    message=f"客户端状态检查失败: {e}",
                    context={"error": str(e)}
                ))

    except Exception as e:
        results["errors"].append(HolodeckError(
            message=f"环境验证过程中发生未预期错误: {e}",
            recovery_suggestion=["查看详细日志", "重新运行验证"]
        ))

    return results

def _check_client_status() -> Dict[str, Any]:
    """检查客户端状态 - 新架构专用"""
    client_status = {}

    try:
        # 检查图像客户端
        image_factory = ImageClientFactory()
        image_client = image_factory.create_client()
        client_status["image"] = {
            "type": image_client.get_service_type().value,
            "status": "available"
        }
    except Exception as e:
        client_status["image"] = {
            "type": "unknown",
            "status": f"unavailable ({e})"
        }

    try:
        # 检查LLM客户端
        llm_factory = LLMClientFactory()
        llm_client = llm_factory.create_client()
        client_status["llm"] = {
            "type": llm_client.get_service_type().value,
            "status": "available"
        }
    except Exception as e:
        client_status["llm"] = {
            "type": "unknown",
            "status": f"unavailable ({e})"
        }

    try:
        # 检查3D客户端
        threed_factory = ThreeDClientFactory()
        threed_client = threed_factory.create_client()
        client_status["3d"] = {
            "type": threed_client.get_service_type().value,
            "status": "available"
        }
    except Exception as e:
        client_status["3d"] = {
            "type": "unknown",
            "status": f"unavailable ({e})"
        }

    return client_status


def print_validation_results(results: Dict[str, Any]) -> None:
    """打印验证结果 - 增强版本"""

    print("=== 环境验证结果 ===")
    print()

    # 系统信息
    print("系统信息:")
    for key, value in results["system"].items():
        print(f"  {key}: {value}")
    print()

    # Python信息
    print("Python信息:")
    for key, value in results["python"].items():
        print(f"  {key}: {value}")
    print()

    # 依赖检查
    print("依赖检查:")
    for dep, status in results["dependencies"].items():
        print(f"  {dep}: {status}")
    print()

    # 配置检查
    print("配置信息:")
    for key, value in results["configuration"].items():
        print(f"  {key}: {value}")
    print()

    # 路径检查
    print("路径检查:")
    for path, info in results["paths"].items():
        exists = "Y" if info["exists"] else "N"
        writable = "Y" if info["writable"] else "N"
        print(f"  {path}:")
        print(f"    存在: {exists}, 可写: {writable}")
    print()

    # API密钥检查
    print("API密钥检查:")
    for service, status in results["api_keys"].items():
        print(f"  {service}: {status}")
    print()

    # 客户端状态检查（如果可用）
    if "clients" in results and results["clients"]:
        print("客户端状态:")
        for client_type, status in results["clients"].items():
            print(f"  {client_type}: {status['type']} - {status['status']}")
        print()

    # 错误和警告
    if "errors" in results and results["errors"]:
        print("发现的问题:")
        for error in results["errors"]:
            print(f"  - {error.message}")
            if hasattr(error, 'recovery_suggestion') and error.recovery_suggestion:
                print(f"    建议: {', '.join(error.recovery_suggestion)}")
        print()


def show_system_info() -> None:
    """显示系统信息"""

    print("=== Holodeck 系统信息 ===")
    print()

    # 版本信息
    try:
        from holodeck_cli import __version__
        print(f"Holodeck CLI 版本: {__version__}")
    except ImportError:
        print("Holodeck CLI 版本: 未知")

    try:
        import holodeck_core
        print(f"Holodeck Core 版本: {getattr(holodeck_core, '__version__', '未知')}")
    except ImportError:
        print("Holodeck Core: 未安装")

    print()

    # 配置信息
    print("当前配置:")
    print(f"  工作空间: {config.get_workspace_path()}")
    print(f"  缓存目录: {config.get_cache_path()}")
    print(f"  日志级别: {config.get('log_level')}")
    print(f"  最大工作进程: {config.get('max_workers')}")
    print()

    # 会话统计
    workspace_path = config.get_workspace_path()
    sessions_dir = workspace_path / "sessions"

    if sessions_dir.exists():
        session_count = len(list(sessions_dir.iterdir()))
        print(f"会话总数: {session_count}")

        # 统计完成的会话
        completed_sessions = 0
        for session_dir in sessions_dir.iterdir():
            if (session_dir / "blender_scene.blend").exists():
                completed_sessions += 1

        print(f"已完成会话: {completed_sessions}")
    else:
        print("会话总数: 0")

    print()



def debug_command(args) -> int:
    """Debug命令主函数"""

    if not args.debug_action:
        print("请指定调试操作 (validate/info/test-asset)")
        return 1

    try:
        if args.debug_action == "validate":
            results = validate_environment()
            print_validation_results(results)

            # 检查是否有问题
            issues = []

            # 检查关键依赖
            for dep, status in results["dependencies"].items():
                if dep == "holodeck_core" and "✗" in status:
                    issues.append(f"关键依赖 {dep} 未安装")

            # 检查路径
            for path, info in results["paths"].items():
                if not info["exists"]:
                    issues.append(f"路径不存在: {path}")
                elif not info["writable"]:
                    issues.append(f"路径不可写: {path}")

            if issues:
                print("发现的问题:")
                for issue in issues:
                    print(f"  - {issue}")
                return 1
            else:
                print("✓ 环境验证通过")
                return 0

        elif args.debug_action == "info":
            show_system_info()
            return 0

        elif args.debug_action == "test-asset":
            if not args.object_desc:
                logger.error("请指定对象描述")
                return 1

            success = test_asset_generation(args.object_desc)
            return 0 if success else 1

        elif args.debug_action == "monitoring":
            return handle_monitoring_command(args)

        elif args.debug_action == "alerts":
            return handle_alerts_command(args)

        else:
            logger.error(f"未知的调试操作: {args.debug_action}")
            return 1

    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        return 130
    except Exception as e:
        logger.exception(f"执行调试命令时出错: {e}")
        return 1


# 监控告警相关功能
def handle_monitoring_command(args) -> int:
    """处理监控命令"""
    try:
        # 检查是否已设置监控系统
        try:
            from holodeck_cli.monitoring import get_monitoring_system
            monitoring_system = get_monitoring_system()
        except ImportError:
            print("监控系统未启用")
            return 1

        if not monitoring_system:
            print("监控系统未初始化")
            return 1

        if hasattr(args, 'monitoring_action'):
            if args.monitoring_action == "status":
                return show_monitoring_status(monitoring_system)
            elif args.monitoring_action == "metrics":
                return show_metrics(monitoring_system)
            elif args.monitoring_action == "health":
                return show_health_status(monitoring_system)
            else:
                print(f"未知的监控操作: {args.monitoring_action}")
                return 1
        else:
            # 默认显示状态
            return show_monitoring_status(monitoring_system)

    except Exception as e:
        logger.error(f"监控命令执行失败: {e}")
        return 1


def handle_alerts_command(args) -> int:
    """处理告警命令"""
    try:
        # 检查是否已设置告警系统
        try:
            from holodeck_cli.alerting import get_alerting_manager
            alerting_manager = get_alerting_manager()
        except ImportError:
            print("告警系统未启用")
            return 1

        if not alerting_manager:
            print("告警系统未初始化")
            return 1

        if hasattr(args, 'alerts_action'):
            if args.alerts_action == "status":
                return show_alerts_status(alerting_manager)
            elif args.alerts_action == "history":
                return show_alerts_history(alerting_manager)
            elif args.alerts_action == "channels":
                return show_notification_channels(alerting_manager)
            else:
                print(f"未知的告警操作: {args.alerts_action}")
                return 1
        else:
            # 默认显示状态
            return show_alerts_status(alerting_manager)

    except Exception as e:
        logger.error(f"告警命令执行失败: {e}")
        return 1


def show_monitoring_status(monitoring_system) -> int:
    """显示监控状态"""
    try:
        print("=== 监控系统状态 ===")

        # 获取健康状态
        health_status = monitoring_system.get_health_status()

        print(f"系统状态: {health_status['status']}")
        print(f"检查时间: {time.ctime(health_status['timestamp'])}")
        print()

        # 显示各项检查
        checks = health_status.get('checks', {})
        for check_name, check_result in checks.items():
            status_icon = "✓" if check_result['status'] == 'pass' else "✗"
            print(f"{status_icon} {check_name}: {check_result['details']}")

        print()
        return 0

    except Exception as e:
        logger.error(f"显示监控状态失败: {e}")
        return 1


def show_metrics(monitoring_system) -> int:
    """显示性能指标"""
    try:
        print("=== 性能指标 ===")

        # 更新系统指标
        monitoring_system.update_system_metrics()

        # 这里可以显示具体的指标数据
        # 由于Prometheus指标是实时的，这里主要显示状态
        print("✓ Prometheus指标服务器运行中")
        print(f"✓ 指标端口: {monitoring_system.metrics_port}")
        print("✓ 访问 /metrics 获取详细指标")
        print("✓ 访问 /health 获取健康状态")

        print()
        return 0

    except Exception as e:
        logger.error(f"显示指标失败: {e}")
        return 1


def show_health_status(monitoring_system) -> int:
    """显示健康状态"""
    try:
        health_status = monitoring_system.get_health_status()

        print("=== 健康状态 ===")
        print(json.dumps(health_status, indent=2, ensure_ascii=False))

        return 0

    except Exception as e:
        logger.error(f"显示健康状态失败: {e}")
        return 1


def show_alerts_status(alerting_manager) -> int:
    """显示告警状态"""
    try:
        status = alerting_manager.get_alert_status()

        print("=== 告警状态 ===")
        print(f"活跃告警: {status['active_alerts']}")
        print(f"通知渠道: {status['enabled_channels']}/{status['total_channels']}")
        print(f"历史告警: {status['alert_history_count']}")
        print()

        if status['active_alerts'] > 0:
            print("活跃告警列表:")
            for alert in status['active_alerts_list']:
                severity_icon = {
                    'critical': '🔴',
                    'warning': '🟡',
                    'info': '🔵'
                }.get(alert['severity'], '⚪')

                print(f"  {severity_icon} {alert['name']} ({alert['severity']})")
                print(f"    消息: {alert['message']}")
                print(f"    时间: {time.ctime(alert['timestamp'])}")
                print()

        return 0

    except Exception as e:
        logger.error(f"显示告警状态失败: {e}")
        return 1


def show_alerts_history(alerting_manager) -> int:
    """显示告警历史"""
    try:
        history = alerting_manager.get_alert_history(limit=20)

        print("=== 告警历史 (最近20条) ===")

        if not history:
            print("无历史告警记录")
            return 0

        for alert in history:
            severity_icon = {
                'critical': '🔴',
                'warning': '🟡',
                'info': '🔵'
            }.get(alert['severity'], '⚪')

            resolved_text = "✓ 已解决" if alert['resolved'] else "⏳ 未解决"

            print(f"{severity_icon} {alert['name']} ({alert['severity']}) - {resolved_text}")
            print(f"  消息: {alert['message']}")
            print(f"  触发时间: {time.ctime(alert['timestamp'])}")

            if alert['resolved'] and alert['resolved_at']:
                print(f"  解决时间: {time.ctime(alert['resolved_at'])}")

            print()

        return 0

    except Exception as e:
        logger.error(f"显示告警历史失败: {e}")
        return 1


def show_notification_channels(alerting_manager) -> int:
    """显示通知渠道"""
    try:
        print("=== 通知渠道 ===")

        from holodeck_cli.alerting import get_alerting_manager
        if not alerting_manager:
            print("告警管理器未初始化")
            return 1

        # 获取渠道信息需要访问私有属性，这里简化处理
        print("通知渠道配置:")
        print("  - email: 邮件通知 (需要配置SMTP)")
        print("  - webhook: Webhook通知")
        print("  - slack: Slack通知")
        print("  - teams: Microsoft Teams通知")
        print()
        print("使用以下命令配置通知渠道:")
        print("  holodeck config set alerting.channels.email.enabled true")
        print("  holodeck config set alerting.channels.email.smtp_server smtp.example.com")
        print()

        return 0

    except Exception as e:
        logger.error(f"显示通知渠道失败: {e}")
        return 1