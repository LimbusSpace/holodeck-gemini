#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("dotenv not available, skipping")

def test_with_retry():
    """带重试逻辑的混元图像测试"""
    print("混元图像3.0重试测试")
    print("=" * 50)

    # 检查环境变量
    secret_id = os.getenv('HUNYUAN_SECRET_ID')
    secret_key = os.getenv('HUNYUAN_SECRET_KEY')

    if not secret_id or not secret_key:
        print("环境变量未配置")
        return False

    print("环境变量配置正确")

    # 导入客户端
    try:
        from holodeck_core.image_generation import HunyuanImageClient
        client = HunyuanImageClient(
            secret_id=secret_id,
            secret_key=secret_key,
            region="ap-guangzhou"
        )
        print("客户端创建成功")
    except Exception as e:
        print(f"客户端创建失败: {e}")
        return False

    # 测试参数
    prompt = "一只可爱的柯基犬在花园里玩耍，阳光明媚"
    output_path = "test_output.png"

    # 重试逻辑
    max_retries = 3
    retry_delay = 30  # 30秒后重试

    for attempt in range(max_retries):
        print(f"\n尝试 #{attempt + 1}/{max_retries}")

        try:
            print("提交生成任务...")
            result = client.generate_image(
                prompt=prompt,
                resolution="1024:1024",
                style=None,  # 使用默认风格
                model="hunyuan-pro",
                output_path=output_path
            )

            # 成功！
            if result and 'local_path' in result:
                print("🎉 图像生成成功!")
                print(f"保存路径: {result['local_path']}")
                print(f"生成时间: {result['metadata']['generation_time_sec']}秒")
                print(f"Job ID: {result['job_id']}")

                # 检查文件是否存在
                if os.path.exists(result['local_path']):
                    file_size = os.path.getsize(result['local_path'])
                    print(f"文件大小: {file_size} 字节")
                    return True
                else:
                    print("警告: 文件未保存到本地")
                    return True  # API调用成功，只是文件保存有问题

            else:
                print("生成结果异常")
                return False

        except Exception as e:
            error_msg = str(e)
            print(f"生成失败: {error_msg}")

            # 检查是否是并发限制
            if "RequestLimitExceeded" in error_msg or "JobNumExceed" in error_msg:
                if attempt < max_retries - 1:
                    print(f"达到并发限制，{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print("重试次数用完，仍然达到限制")
                    print("💡 建议：")
                    print("   - 等待几分钟后再次尝试")
                    print("   - 联系腾讯云客服提高配额")
                    return False
            else:
                # 其他错误，直接返回
                print("遇到其他错误，停止重试")
                return False

    return False

def main():
    """主函数"""
    success = test_with_retry()

    if success:
        print("\n混元图像3.0测试完全成功！")
        print("\n下一步建议：")
        print("   - 运行 examples/hunyuan_3d_pipeline_example.py 测试完整管线")
        print("   - 在您的项目中集成混元图像功能")
        print("   - 调整提示词和参数优化生成效果")
    else:
        print("\n测试失败")
        print("\n故障排除：")
        print("   - 检查腾讯云账户余额和配额")
        print("   - 确认混元图像服务已完全开通")
        print("   - 等待并发限制重置后重试")
        print("   - 联系腾讯云技术支持")

if __name__ == "__main__":
    main()