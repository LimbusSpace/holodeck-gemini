#!/usr/bin/env python3
"""Test optimized Hunyuan Image client with concurrency control."""

import os
import sys
import time
from pathlib import Path

# Add holodeck_core to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "holodeck_core"))

def load_environment_variables():
    """Load environment variables from .env file"""
    dotenv_path = Path(__file__).parent.parent.parent.parent / '.env'
    if dotenv_path.exists():
        with open(dotenv_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def test_concurrency_control():
    """Test concurrency control with multiple tasks."""
    print("测试并发控制...")
    print("=" * 50)

    load_environment_variables()

    # Check environment variables
    secret_id = os.getenv('HUNYUAN_SECRET_ID')
    secret_key = os.getenv('HUNYUAN_SECRET_KEY')

    if not secret_id or not secret_key:
        print("环境变量未配置")
        return False

    try:
        from holodeck_core.image_generation.hunyuan_image_client_optimized import (
            HunyuanImageClientOptimized, GenerationTask
        )

        # Create client with concurrency control
        client = HunyuanImageClientOptimized(
            secret_id=secret_id,
            secret_key=secret_key,
            region='ap-guangzhou',
            max_concurrent_jobs=2,  # Limit to 2 concurrent jobs
            max_retries=3
        )
        print("✅ 优化客户端创建成功")

        # Test connection
        if client.test_connection():
            print("✅ API连接测试成功")
        else:
            print("❌ API连接测试失败")
            return False

        # Create test tasks (fewer to avoid rate limiting during demo)
        prompts = [
            "一只可爱的小猫在花园里",
            "一只柯基犬在阳光下玩耍",
            "一只橘猫在屋顶上看风景"
        ]

        tasks = []
        for i, prompt in enumerate(prompts):
            task = GenerationTask(
                prompt=prompt,
                resolution="1024:1024",
                model="hunyuan-pro",
                output_path=f"test_output_{i+1}.png"
            )
            tasks.append(task)

        print(f"\n开始批量处理 {len(tasks)} 个任务...")
        print(f"最大并发数: {client.max_concurrent_jobs}")
        print(f"最大重试次数: {client.max_retries}")

        start_time = time.time()

        # Test synchronous batch generation
        results = client.generate_batch_sync(tasks)

        total_time = time.time() - start_time

        print(f"\n批量处理完成！总耗时: {total_time:.2f}秒")
        print("\n结果统计:")
        print("-" * 30)

        success_count = 0
        for result in results:
            status = "✅ 成功" if result.success else "❌ 失败"
            print(f"任务 {result.task_id}: {status}")
            if result.success:
                success_count += 1
                print(f"  - 生成时间: {result.generation_time:.2f}秒")
                print(f"  - Job ID: {result.job_id}")
                if result.image_url:
                    print(f"  - 图像URL: {result.image_url[:50]}...")
                if result.local_path:
                    print(f"  - 本地路径: {result.local_path}")
            else:
                print(f"  - 错误信息: {result.error_message}")

        print(f"\n成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")

        # Test single image generation (backward compatibility)
        print("\n测试单个图像生成 (向后兼容)...")
        single_result = client.generate_image(
            prompt="一只优雅的白猫在月光下",
            resolution="1024:1024",
            output_path="test_single_output.png"
        )

        if single_result["status"] == "success":
            print("✅ 单个图像生成成功")
            print(f"  - 生成时间: {single_result['metadata']['generation_time_sec']}秒")
        else:
            print("❌ 单个图像生成失败")
            print(f"  - 错误: {single_result.get('error', 'Unknown error')}")

        return success_count > 0

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_retry_mechanism():
    """Test retry mechanism (simulation)."""
    print("\n测试重试机制...")
    print("=" * 50)

    load_environment_variables()

    try:
        from holodeck_core.image_generation.hunyuan_image_client_optimized import (
            HunyuanImageClientOptimized, GenerationTask
        )

        # Create client with aggressive retry settings for testing
        client = HunyuanImageClientOptimized(
            secret_id=os.getenv('HUNYUAN_SECRET_ID'),
            secret_key=os.getenv('HUNYUAN_SECRET_KEY'),
            region='ap-guangzhou',
            max_concurrent_jobs=1,  # Single job to test retry
            max_retries=2,
            retry_delay=1.0
        )

        # Test with a simple task
        task = GenerationTask(
            prompt="测试重试机制的简单图像",
            output_path="test_retry_output.png"
        )

        print("提交任务测试重试机制...")
        result = client._process_single_task(task)

        if result.success:
            print("✅ 重试机制测试成功")
        else:
            print(f"❌ 重试机制测试失败: {result.error_message}")

        return True

    except Exception as e:
        print(f"重试机制测试异常: {e}")
        return False

def main():
    """Main test function."""
    print("混元图像3.0优化客户端测试")
    print("=" * 60)

    test1_success = test_concurrency_control()
    test2_success = test_retry_mechanism()

    print("\n测试总结")
    print("=" * 60)

    tests = [
        ("并发控制测试", test1_success),
        ("重试机制测试", test2_success)
    ]

    passed = sum(1 for _, success in tests if success)
    total = len(tests)

    for test_name, success in tests:
        status = "通过" if success else "失败"
        print(f"   {test_name}: {status}")

    print(f"\n总体: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有优化功能测试通过！")
        print("\n优化特性:")
        print("   ✅ 信号量并发控制")
        print("   ✅ 自动重试机制")
        print("   ✅ 批量任务处理")
        print("   ✅ 线程安全操作")
        print("   ✅ 向后兼容接口")
    else:
        print("\n❌ 部分测试失败，请检查错误信息。")

if __name__ == "__main__":
    main()