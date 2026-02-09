#!/usr/bin/env python3
"""Demonstration of optimized Hunyuan Image client with concurrency control."""

import os
import sys
import asyncio
from pathlib import Path

# Add holodeck_core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "holodeck_core"))

def load_environment_variables():
    """Load environment variables from .env file"""
    dotenv_path = Path(__file__).parent.parent / '.env'
    if dotenv_path.exists():
        with open(dotenv_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value


def demo_basic_usage():
    """Demonstrate basic usage of optimized client."""
    print("🎯 基础使用演示")
    print("=" * 50)

    load_environment_variables()

    try:
        from holodeck_core.image_generation.hunyuan_image_client_optimized import (
            HunyuanImageClientOptimized
        )

        # Create client with custom concurrency settings
        client = HunyuanImageClientOptimized(
            secret_id=os.getenv('HUNYUAN_SECRET_ID'),
            secret_key=os.getenv('HUNYUAN_SECRET_KEY'),
            region='ap-guangzhou',
            max_concurrent_jobs=2,
            max_retries=3
        )

        print("✅ 客户端创建成功")
        print(f"   - 最大并发数: {client.max_concurrent_jobs}")
        print(f"   - 最大重试次数: {client.max_retries}")

        # Test single image generation (backward compatible)
        print("\n📸 生成单个图像...")
        result = client.generate_image(
            prompt="一只优雅的白猫在月光下，背景是星空，艺术风格",
            resolution="1024:1024",
            model="hunyuan-pro",
            output_path="demo_single_cat.png"
        )

        if result["status"] == "success":
            print("✅ 图像生成成功！")
            print(f"   - 生成时间: {result['metadata']['generation_time_sec']}秒")
            print(f"   - 任务ID: {result['metadata']['task_id']}")
            if result.get("local_path"):
                print(f"   - 保存路径: {result['local_path']}")
        else:
            print(f"❌ 图像生成失败: {result.get('error', 'Unknown error')}")

        return True

    except Exception as e:
        print(f"❌ 基础使用演示失败: {e}")
        return False


def demo_batch_processing():
    """Demonstrate batch processing with concurrency control."""
    print("\n🔄 批量处理演示")
    print("=" * 50)

    load_environment_variables()

    try:
        from holodeck_core.image_generation.hunyuan_image_client_optimized import (
            HunyuanImageClientOptimized, GenerationTask
        )

        # Create client
        client = HunyuanImageClientOptimized(
            secret_id=os.getenv('HUNYUAN_SECRET_ID'),
            secret_key=os.getenv('HUNYUAN_SECRET_KEY'),
            region='ap-guangzhou',
            max_concurrent_jobs=2
        )

        # Create multiple tasks
        prompts = [
            "一只橘猫在屋顶上看风景，温暖的阳光",
            "一只黑猫在夜晚的城市街道上，霓虹灯效果",
            "一只花猫在花园里追逐蝴蝶，春天风格",
            "一只波斯猫在豪华客厅里，优雅氛围"
        ]

        tasks = []
        for i, prompt in enumerate(prompts):
            task = GenerationTask(
                prompt=prompt,
                resolution="1024:1024",
                model="hunyuan-pro",
                output_path=f"demo_batch_cat_{i+1}.png"
            )
            tasks.append(task)

        print(f"📋 创建 {len(tasks)} 个生成任务")
        print(f"⚡ 并发控制: 最多同时运行 {client.max_concurrent_jobs} 个任务")

        # Process batch synchronously
        print("\n开始批量处理...")
        results = client.generate_batch_sync(tasks)

        # Show results
        print(f"\n📊 批量处理结果:")
        success_count = 0
        for i, result in enumerate(results):
            status = "✅" if result.success else "❌"
            print(f"   任务 {i+1} {status}: {prompts[i][:30]}...")
            if result.success:
                success_count += 1
                print(f"      - 耗时: {result.generation_time:.2f}秒")
                if result.local_path:
                    print(f"      - 保存: {result.local_path}")

        print(f"\n📈 成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

        return success_count > 0

    except Exception as e:
        print(f"❌ 批量处理演示失败: {e}")
        return False


async def demo_async_processing():
    """Demonstrate asynchronous batch processing."""
    print("\n⚡ 异步处理演示")
    print("=" * 50)

    load_environment_variables()

    try:
        from holodeck_core.image_generation.hunyuan_image_client_optimized import (
            HunyuanImageClientOptimized, GenerationTask
        )

        # Create client
        client = HunyuanImageClientOptimized(
            secret_id=os.getenv('HUNYUAN_SECRET_ID'),
            secret_key=os.getenv('HUNYUAN_SECRET_KEY'),
            region='ap-guangzhou',
            max_concurrent_jobs=2
        )

        # Create tasks
        prompts = [
            "一只暹罗猫在图书馆里看书，温馨氛围",
            "一只缅因猫在雪地里，冬季风格"
        ]

        tasks = []
        for i, prompt in enumerate(prompts):
            task = GenerationTask(
                prompt=prompt,
                resolution="1024:1024",
                model="hunyuan-pro",
                output_path=f"demo_async_cat_{i+1}.png"
            )
            tasks.append(task)

        print(f"🔄 开始异步处理 {len(tasks)} 个任务...")

        # Process batch asynchronously
        results = await client.generate_batch_async(tasks)

        # Show results
        print(f"\n📊 异步处理结果:")
        success_count = 0
        for i, result in enumerate(results):
            status = "✅" if result.success else "❌"
            print(f"   任务 {i+1} {status}: {prompts[i][:30]}...")
            if result.success:
                success_count += 1

        print(f"\n📈 成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

        return success_count > 0

    except Exception as e:
        print(f"❌ 异步处理演示失败: {e}")
        return False


def demo_convenience_functions():
    """Demonstrate convenience functions."""
    print("\n🛠️  便捷函数演示")
    print("=" * 50)

    load_environment_variables()

    try:
        from holodeck_core.image_generation.hunyuan_image_client_optimized import (
            generate_batch_images
        )

        # Use convenience function for batch generation
        prompts = [
            "一只小猫在草地上玩耍，可爱风格",
            "一只成年猫在窗台上晒太阳，写实风格"
        ]

        print(f"📦 使用便捷函数处理 {len(prompts)} 个任务...")

        results = generate_batch_images(
            prompts=prompts,
            output_dir=".",
            resolution="1024:1024",
            model="hunyuan-pro"
        )

        print(f"\n📊 便捷函数处理结果:")
        success_count = 0
        for i, result in enumerate(results):
            status = "✅" if result["success"] else "❌"
            print(f"   任务 {i+1} {status}: {prompts[i][:30]}...")
            if result["success"]:
                success_count += 1
                if result.get("local_path"):
                    print(f"      - 保存: {result['local_path']}")

        print(f"\n📈 成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

        return success_count > 0

    except Exception as e:
        print(f"❌ 便捷函数演示失败: {e}")
        return False


def main():
    """Main demonstration function."""
    print("🚀 混元图像3.0优化客户端演示")
    print("=" * 60)
    print("本演示展示优化后的混元图像客户端功能:")
    print("   • 信号量并发控制")
    print("   • 自动重试机制")
    print("   • 批量任务处理")
    print("   • 异步支持")
    print("   • 便捷函数")
    print("=" * 60)

    # Run demonstrations
    demo1_success = demo_basic_usage()
    demo2_success = demo_batch_processing()
    demo3_success = demo_convenience_functions()

    # Run async demo
    try:
        demo4_success = asyncio.run(demo_async_processing())
    except Exception as e:
        print(f"❌ 异步演示运行失败: {e}")
        demo4_success = False

    # Summary
    print("\n🎯 演示总结")
    print("=" * 60)

    demos = [
        ("基础使用", demo1_success),
        ("批量处理", demo2_success),
        ("便捷函数", demo3_success),
        ("异步处理", demo4_success)
    ]

    passed = sum(1 for _, success in demos if success)
    total = len(demos)

    for demo_name, success in demos:
        status = "通过" if success else "失败"
        print(f"   {demo_name}: {status}")

    print(f"\n总体: {passed}/{total} 演示通过")

    if passed == total:
        print("\n🎉 所有演示成功完成！")
        print("\n优化客户端特性总结:")
        print("   ✅ 智能并发控制 - 避免API限流")
        print("   ✅ 自动重试机制 - 提高成功率")
        print("   ✅ 批量任务处理 - 提升效率")
        print("   ✅ 异步支持 - 非阻塞操作")
        print("   ✅ 向后兼容 - 现有代码无需修改")
        print("   ✅ 便捷函数 - 简化常用操作")
    else:
        print("\n⚠️  部分演示失败，请检查配置和错误信息。")


if __name__ == "__main__":
    main()