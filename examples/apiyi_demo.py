#!/usr/bin/env python3
"""
APIAyi (Gemini-3-Pro-Image) 演示脚本

演示如何在Holodeck中使用APIAyi进行图像生成。
"""

import asyncio
import os
from pathlib import Path

# 设置环境变量（仅用于演示，实际使用中建议通过.env文件配置）
os.environ["APIAYI_API_KEY"] = "sk-your-api-key"  # 请替换为你的实际API密钥

from holodeck_core.image_generation.unified_image_client import UnifiedImageClient

async def demo_direct_client():
    """直接使用UnifiedImageClient演示"""
    print("=== UnifiedImageClient 直接客户端演示 ===\n")

    try:
        # 创建客户端
        client = UnifiedImageClient()
        client.initialize()

        print("✅ UnifiedImageClient 初始化成功")
        print(f"📋 模型信息: {client.get_model_info()}\n")

        # 演示不同的生成参数
        test_cases = [
            {
                "prompt": "一只可爱的小猫坐在花园里",
                "resolution": "1024:1024",
                "style": "oil_painting",
                "description": "油画风格小猫"
            },
            {
                "prompt": "未来城市天际线",
                "resolution": "1920:1080",
                "style": "digital_art",
                "description": "数字艺术未来城市"
            },
            {
                "prompt": "宁静的湖面倒映着雪山",
                "resolution": "1536:1536",
                "style": "watercolor",
                "description": "水彩风格湖景"
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"{i}. 生成 {test_case['description']}...")

            try:
                result = await client.generate_image(
                    prompt=test_case["prompt"],
                    resolution=test_case["resolution"],
                    style=test_case["style"],
                    output_path=f"demo_output_{i}.png"
                )

                if result.success:
                    print(f"   ✅ 成功: {result.data}")
                    print(f"   ⏱️  耗时: {result.duration:.2f}秒")
                    print(f"   📐 分辨率: {test_case['resolution']}")
                    print(f"   🎨 风格: {test_case['style']}")
                    print(f"   🔍 增强提示词: {result.metadata.get('enhanced_prompt', 'N/A')}")
                else:
                    print(f"   ❌ 失败: {result.error}")

            except Exception as e:
                print(f"   ❌ 错误: {e}")

            print()

    except Exception as e:
        print(f"❌ 演示失败: {e}")

async def demo_unified_client():
    """通过统一客户端演示"""
    print("=== 统一客户端演示 (使用APIAyi后端) ===\n")

    try:
        # 创建统一客户端
        unified_client = UnifiedImageClient()
        unified_client.initialize()

        print("✅ 统一客户端初始化成功")
        print(f"📋 可用后端: {list(unified_client.backend_stats.keys())}\n")

        # 指定使用APIAyi后端
        prompt = "一只可爱的熊猫在竹林中吃竹子"
        print(f"🎯 生成: {prompt}")

        result = await unified_client.generate_image(
            prompt=prompt,
            resolution="1024:1024",
            style="realistic",
            backend="apiyi",  # 指定使用APIAyi后端
            output_path="unified_demo_output.png"
        )

        if result.success:
            print(f"✅ 成功: {result.data}")
            print(f"⏱️  耗时: {result.duration:.2f}秒")
            print(f"🏭 后端: {result.metadata.get('backend', 'N/A')}")
            print(f"📊 后端统计: {unified_client.get_backend_statistics()}")
        else:
            print(f"❌ 失败: {result.error}")

    except Exception as e:
        print(f"❌ 演示失败: {e}")

async def demo_auto_selection():
    """演示自动后端选择"""
    print("\n=== 自动后端选择演示 ===\n")

    try:
        unified_client = UnifiedImageClient()
        unified_client.initialize()

        prompt = "抽象艺术风格的几何图形"
        print(f"🎯 生成 (自动选择后端): {prompt}")

        # 不指定后端，让系统自动选择
        result = await unified_client.generate_image(
            prompt=prompt,
            resolution="1024:1024",
            output_path="auto_demo_output.png"
        )

        if result.success:
            print(f"✅ 成功: {result.data}")
            print(f"🏭 自动选择的后端: {result.metadata.get('backend', 'N/A')}")
            print(f"⏱️  耗时: {result.duration:.2f}秒")
        else:
            print(f"❌ 失败: {result.error}")

    except Exception as e:
        print(f"❌ 演示失败: {e}")

def demo_configuration():
    """演示配置检查"""
    print("\n=== 配置检查演示 ===\n")

    try:
        from holodeck_core.config.base import get_config, ConfigManager

        config_manager = ConfigManager()

        # 检查APIAyi配置
        api_key = get_config("APIAYI_API_KEY")
        base_url = get_config("APIAYI_BASE_URL", "https://api.apiyi.com/v1beta/models")

        print(f"🔑 API密钥: {'已设置' if api_key else '未设置'}")
        print(f"🌐 基础URL: {base_url}")
        print(f"📱 模型: {get_config('APIAYI_MODEL', 'gemini-3-pro-image-preview')}")
        print(f"⏱️  超时: {get_config('APIAYI_TIMEOUT', 300)}秒")

        if api_key and api_key != "sk-your-api-key":
            print("✅ APIYi 配置正确")
        else:
            print("⚠️  请设置有效的APIAyi API密钥")

    except Exception as e:
        print(f"❌ 配置检查失败: {e}")

async def main():
    """主演示函数"""
    print("🚀 APIYi (Gemini-3-Pro-Image) 集成演示")
    print("=" * 50)

    # 检查配置
    demo_configuration()

    # 等待用户确认
    print("\n💡 提示: 请确保已设置正确的APIAyi API密钥")
    print("按 Enter 继续演示...")
    input()

    # 运行演示
    await demo_direct_client()
    await asyncio.sleep(1)

    await demo_unified_client()
    await asyncio.sleep(1)

    await demo_auto_selection()

    print("\n🎉 演示完成!")
    print("\n📝 总结:")
    print("- APIYi客户端已成功集成到Holodeck")
    print("- 支持直接使用和通过统一客户端使用")
    print("- 自动后端选择和性能统计")
    print("- 完整的错误处理和配置验证")

if __name__ == "__main__":
    # 创建输出目录
    Path("demo_outputs").mkdir(exist_ok=True)

    # 运行演示
    asyncio.run(main())