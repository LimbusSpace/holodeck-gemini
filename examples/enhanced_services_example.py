"""
增强服务使用示例

这些示例展示了如何使用新的增强服务，包括增强的LLM命名服务、
统一的客户端工厂等。
"""

import asyncio
from pathlib import Path

# 示例1: 使用增强的LLM命名服务
print("=== 示例1: 增强的LLM命名服务 ===")

async def demo_enhanced_naming():
    from holodeck_core.object_gen.enhanced_llm_naming_service import EnhancedLLMNamingService

    # 创建增强命名服务
    naming_service = EnhancedLLMNamingService(
        cache_ttl=3600,  # 缓存1小时
        enable_image_analysis=True
    )

    try:
        # 基本命名（无图像）
        result = await naming_service.generate_object_name(
            description="一个现代化的玻璃茶几，具有简约的设计",
            object_name="Modern Coffee Table"
        )
        print(f"生成的名称: {result}")

        # 带图像分析的命名（如果有测试图像）
        test_image = Path("test_image.png")
        if test_image.exists():
            result_with_image = await naming_service.generate_object_name(
                description="一个古典的木质餐桌，有精美的雕刻",
                object_name="Carved Dining Table",
                image_path=test_image
            )
            print(f"带图像分析的名称: {result_with_image}")
        else:
            print("测试图像不存在，跳过图像分析示例")

        # 获取服务统计信息
        stats = naming_service.get_statistics()
        print(f"服务统计: {stats}")

    except Exception as e:
        print(f"命名服务错误: {e}")

# 示例2: 使用统一的客户端工厂
print("\n=== 示例2: 统一的客户端工厂 ===")

def demo_client_factory():
    from holodeck_core.clients.factory import (
        ImageClientFactory,
        LLMClientFactory,
        ThreeDClientFactory
    )

    # 创建客户端工厂
    image_factory = ImageClientFactory()
    llm_factory = LLMClientFactory()
    threed_factory = ThreeDClientFactory()

    try:
        # 自动选择最佳可用的图像客户端
        image_client = image_factory.create_client()
        print(f"选择的图像客户端: {image_client.get_service_type()}")

        # 自动选择最佳可用的LLM客户端
        llm_client = llm_factory.create_client()
        print(f"选择的LLM客户端: {llm_client.get_service_type()}")

        # 创建3D客户端（自动选择）
        threed_client_auto = threed_factory.create_client()
        print(f"自动选择的3D客户端: {threed_client_auto.get_service_type()}")

        # 创建特定的3D客户端
        try:
            threed_client_hunyuan = threed_factory.create_client(backend="hunyuan")
            print(f"Hunyuan 3D客户端: {threed_client_hunyuan.get_service_type()}")
        except Exception as e:
            print(f"Hunyuan 3D客户端不可用: {e}")

        try:
            threed_client_sf3d = threed_factory.create_client(backend="sf3d")
            print(f"SF3D客户端: {threed_client_sf3d.get_service_type()}")
        except Exception as e:
            print(f"SF3D客户端不可用: {e}")

    except Exception as e:
        print(f"客户端工厂错误: {e}")

# 示例3: 使用管道编排器
print("\n=== 示例3: 管道编排器 ===")

async def demo_pipeline_orchestrator():
    from holodeck_core.integration.pipeline_orchestrator import PipelineOrchestrator
    from holodeck_core.clients.factory import (
        ImageClientFactory,
        LLMClientFactory,
        ThreeDClientFactory
    )

    try:
        # 创建客户端
        image_factory = ImageClientFactory()
        llm_factory = LLMClientFactory()
        threed_factory = ThreeDClientFactory()

        image_client = image_factory.create_client()
        llm_client = llm_factory.create_client()
        threed_client = threed_factory.create_client()

        # 创建管道编排器
        orchestrator = PipelineOrchestrator(
            image_client=image_client,
            llm_client=llm_client,
            threed_client=threed_client
        )

        # 生成场景（简化示例）
        result = await orchestrator.generate_scene(
            description="一个现代化的客厅，有沙发和茶几",
            style="modern",
            max_objects=10
        )

        print(f"场景生成结果: {result.success}")
        if result.success:
            print(f"生成的对象: {result.objects}")
            print(f"完成阶段: {result.completed_stages}")
        else:
            print(f"错误: {result.error_message}")

    except Exception as e:
        print(f"管道编排器错误: {e}")

# 示例4: 错误处理和日志
print("\n=== 示例4: 错误处理和日志 ===")

from holodeck_core.exceptions.framework import (
    ConfigurationError, ValidationError, APIError
)
from holodeck_core.logging.standardized import get_logger

def demo_error_handling():
    logger = get_logger(__name__)

    # 模拟配置错误
    try:
        raise ConfigurationError(
            message="缺少必需的API密钥",
            recovery_suggestion=["设置HUNYUAN_API_KEY环境变量", "检查配置文件"]
        )
    except ConfigurationError as e:
        logger.error(f"配置错误: {e.message}")
        if e.recovery_suggestion:
            logger.info("建议的解决方案:")
            for suggestion in e.recovery_suggestion:
                logger.info(f"  - {suggestion}")

    # 模拟验证错误
    try:
        raise ValidationError(
            message="输入参数无效",
            field_name="object_count",
            field_value="-1"
        )
    except ValidationError as e:
        logger.error(f"验证错误: {e.message}")
        logger.error(f"字段: {e.field_name}, 值: {e.field_value}")

    # 模拟API错误
    try:
        raise APIError(
            message="API请求失败",
            context={"status_code": 500, "response": "Internal Server Error"}
        )
    except APIError as e:
        logger.error(f"API错误: {e.message}")
        logger.debug(f"错误上下文: {e.context}")

# 示例5: 性能监控
print("\n=== 示例5: 性能监控 ===")

from holodeck_core.logging.standardized import log_time

@log_time("demo_function")
def demo_performance_monitoring():
    """演示性能监控装饰器"""
    import time
    time.sleep(0.1)  # 模拟一些工作
    return "完成"

def main():
    """运行所有示例"""
    print("开始运行增强服务示例...\n")

    # 运行同步示例
    demo_client_factory()
    demo_error_handling()

    # 运行性能监控示例
    result = demo_performance_monitoring()
    print(f"性能监控结果: {result}")

    # 运行异步示例
    asyncio.run(demo_enhanced_naming())
    asyncio.run(demo_pipeline_orchestrator())

    print("\n=== 所有示例完成 ===")
    print("新的增强服务提供了：")
    print("✅ 统一的客户端接口")
    print("✅ 自动客户端选择")
    print("✅ 增强的错误处理")
    print("✅ 性能监控")
    print("✅ 完整的管道编排")
    print("✅ 向后兼容性")

if __name__ == "__main__":
    main()