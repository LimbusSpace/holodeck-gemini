#!/usr/bin/env python3
"""
监控告警系统演示脚本

演示Holodeck监控告警系统的功能。
"""

import time
import asyncio
from pathlib import Path

from holodeck_cli.monitoring import setup_monitoring, monitor_execution, AlertRule
from holodeck_cli.alerting import setup_alerting, start_alert_processor, NotificationChannel
from holodeck_cli.performance import performance_monitor, CacheOptimizer, MemoryOptimizer


@monitor_execution("demo_operation")
def demo_operation(duration: float = 1.0):
    """演示操作"""
    time.sleep(duration)
    return f"操作完成，耗时 {duration}秒"


@monitor_execution("demo_async_operation")
async def demo_async_operation(duration: float = 1.0):
    """演示异步操作"""
    await asyncio.sleep(duration)
    return f"异步操作完成，耗时 {duration}秒"


def demo_monitoring_system():
    """演示监控系统"""
    print("=== Holodeck 监控告警系统演示 ===\n")

    # 设置监控系统
    print("1. 设置监控系统...")
    monitoring_system = setup_monitoring(
        enable_prometheus=True,
        metrics_port=8080
    )
    print("✓ 监控系统已启动")
    print("✓ Prometheus指标服务器运行在端口 8080")
    print("✓ 访问 http://localhost:8080/metrics 查看指标")
    print("✓ 访问 http://localhost:8080/health 查看健康状态")
    print()

    # 设置告警系统
    print("2. 设置告警系统...")
    alerting_manager = setup_alerting(monitoring_system)
    print("✓ 告警系统已启动")
    print()

    # 启动告警处理器
    print("3. 启动告警处理器...")
    start_alert_processor(interval=30)
    print("✓ 告警处理器已启动 (每30秒检查一次)")
    print()

    # 演示操作执行
    print("4. 执行演示操作...")

    # 同步操作
    for i in range(3):
        result = demo_operation(0.5)
        print(f"   {result}")

        # 记录场景生成
        monitoring_system.record_scene_generation(
            quality="high",
            backend="hunyuan"
        )

    # 异步操作
    async def run_async_operations():
        tasks = []
        for i in range(3):
            task = demo_async_operation(0.3)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        for result in results:
            print(f"   {result}")

            # 记录场景生成
            monitoring_system.record_scene_generation(
                quality="standard",
                backend="comfyui"
            )

    # 运行异步操作
    asyncio.run(run_async_operations())

    print()

    # 演示缓存操作
    print("5. 演示缓存操作...")
    cache = CacheOptimizer(max_size_mb=10, ttl_seconds=60)

    # 设置缓存
    cache.set("key1", "value1")
    cache.set("key2", "value2")

    # 获取缓存
    value1 = cache.get("key1")
    print(f"   缓存获取 key1: {value1}")

    # 缓存统计
    stats = cache.get_stats()
    print(f"   缓存统计: {stats}")
    print()

    # 演示内存监控
    print("6. 演示内存监控...")
    memory_optimizer = MemoryOptimizer()

    # 内存使用
    memory_usage = memory_optimizer.get_memory_usage()
    print(f"   当前内存使用: {memory_usage['rss_mb']:.1f}MB")

    # 优化建议
    suggestions = memory_optimizer.suggest_optimizations()
    print(f"   优化建议: {suggestions}")

    # 清理内存
    memory_optimizer.cleanup_memory()
    print("   ✓ 内存清理完成")
    print()

    # 显示监控状态
    print("7. 显示监控状态...")
    health_status = monitoring_system.get_health_status()
    print(f"   系统状态: {health_status['status']}")

    for check_name, check_result in health_status['checks'].items():
        status_icon = "✓" if check_result['status'] == 'pass' else "✗"
        print(f"   {status_icon} {check_name}: {check_result['details']}")
    print()

    # 显示告警状态
    print("8. 显示告警状态...")
    alert_status = alerting_manager.get_alert_status()
    print(f"   活跃告警: {alert_status['active_alerts']}")
    print(f"   通知渠道: {alert_status['enabled_channels']}/{alert_status['total_channels']}")
    print(f"   历史告警: {alert_status['alert_history_count']}")
    print()

    # 添加自定义告警规则
    print("9. 添加自定义告警规则...")
    custom_alert = AlertRule(
        name="demo_custom_alert",
        condition="memory_usage > 100",
        threshold=100.0,
        severity="warning",
        description="演示自定义告警规则",
        enabled=True
    )
    monitoring_system.add_alert_rule(custom_alert)
    print("   ✓ 自定义告警规则已添加")
    print()

    # 触发一些API错误用于演示
    print("10. 演示API错误记录...")
    monitoring_system.record_api_error("openai", "timeout")
    monitoring_system.record_api_error("comfyui", "connection_failed")
    print("   ✓ API错误已记录")
    print()

    # 性能报告
    print("11. 生成性能报告...")
    # 记录一些性能指标
    performance_monitor.record_metric(
        operation="demo_operation",
        duration=0.5,
        success=True,
        metadata={"type": "demo"}
    )

    # 获取性能统计
    stats = performance_monitor.get_statistics("demo_operation")
    if stats:
        print(f"   操作统计: {stats['total_operations']} 次操作")
        print(f"   成功率: {stats['success_rate']:.1%}")
    print()

    print("=== 演示完成 ===")
    print("\n下一步操作:")
    print("1. 查看实时指标: curl http://localhost:8080/metrics")
    print("2. 查看健康状态: curl http://localhost:8080/health")
    print("3. 使用CLI命令:")
    print("   holodeck debug monitoring status")
    print("   holodeck debug alerts status")
    print("   holodeck debug performance")
    print()


def demo_alert_channels():
    """演示告警通知渠道"""
    print("=== 告警通知渠道演示 ===\n")

    # 创建监控系统
    monitoring_system = setup_monitoring(enable_prometheus=False)
    alerting_manager = setup_alerting(monitoring_system)

    # 演示添加通知渠道
    print("1. 添加邮件通知渠道...")
    email_channel = NotificationChannel(
        name="email_admin",
        type="email",
        config={
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "demo@gmail.com",
            "password": "demo-password",
            "from_email": "holodeck@demo.com",
            "to_emails": ["admin@demo.com"]
        },
        enabled=True
    )
    alerting_manager.add_notification_channel(email_channel)
    print("   ✓ 邮件通知渠道已添加")

    print("2. 添加Webhook通知渠道...")
    webhook_channel = NotificationChannel(
        name="webhook_api",
        type="webhook",
        config={
            "url": "https://demo.com/holodeck-alerts",
            "headers": {
                "Authorization": "Bearer demo-token"
            }
        },
        enabled=True
    )
    alerting_manager.add_notification_channel(webhook_channel)
    print("   ✓ Webhook通知渠道已添加")

    print("3. 添加Slack通知渠道...")
    slack_channel = NotificationChannel(
        name="slack_alerts",
        type="slack",
        config={
            "webhook_url": "https://hooks.slack.com/services/DEMO/SLACK/WEBHOOK"
        },
        enabled=True
    )
    alerting_manager.add_notification_channel(slack_channel)
    print("   ✓ Slack通知渠道已添加")

    print("4. 测试通知渠道...")
    channels_to_test = ["email_admin", "webhook_api", "slack_alerts"]

    for channel_name in channels_to_test:
        try:
            success = alerting_manager.test_notification_channel(channel_name)
            status = "✓ 成功" if success else "✗ 失败"
            print(f"   {channel_name}: {status}")
        except Exception as e:
            print(f"   {channel_name}: ✗ 错误 ({e})")

    print("\n=== 渠道演示完成 ===")
    print()


async def demo_async_monitoring():
    """演示异步监控"""
    print("=== 异步监控演示 ===\n")

    monitoring_system = setup_monitoring(enable_prometheus=False)

    # 异步操作监控
    @monitor_execution("async_demo")
    async def monitored_async_operation():
        await asyncio.sleep(1.0)
        return "异步操作完成"

    print("1. 执行异步监控操作...")
    result = await monitored_async_operation()
    print(f"   {result}")

    # 并发操作监控
    print("2. 执行并发监控操作...")
    tasks = []
    for i in range(5):
        task = monitored_async_operation()
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    for result in results:
        print(f"   {result}")

    print("\n=== 异步监控演示完成 ===")
    print()


def main():
    """主演示函数"""
    try:
        # 基本监控演示
        demo_monitoring_system()

        # 等待一下让用户查看结果
        print("等待5秒...")
        time.sleep(5)

        # 告警渠道演示
        demo_alert_channels()

        # 异步监控演示
        asyncio.run(demo_async_monitoring())

        print("🎉 所有演示完成!")
        print("\n提示: 监控系统仍在后台运行，您可以继续访问:")
        print("- http://localhost:8080/metrics")
        print("- http://localhost:8080/health")

    except KeyboardInterrupt:
        print("\n演示被用户中断")
    except Exception as e:
        print(f"\n演示过程中发生错误: {e}")


if __name__ == "__main__":
    main()