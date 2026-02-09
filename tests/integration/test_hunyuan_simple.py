#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("dotenv not available, skipping")

def test_environment():
    """测试环境配置"""
    print("检查环境变量配置:")

    secret_id = os.getenv('HUNYUAN_SECRET_ID')
    secret_key = os.getenv('HUNYUAN_SECRET_KEY')

    if secret_id and secret_key:
        print("HUNYUAN_SECRET_ID:", secret_id[:10] + "..." if len(secret_id) > 10 else secret_id)
        print("HUNYUAN_SECRET_KEY:", secret_key[:10] + "..." if len(secret_key) > 10 else secret_key)
        print("环境变量配置正确")
        return True
    else:
        print("环境变量未正确配置")
        print("请编辑.env文件，填入您的API密钥")
        return False

def test_import():
    """测试模块导入"""
    print("\n测试模块导入:")

    try:
        from holodeck_core.image_generation import HunyuanImageClient
        print("HunyuanImageClient 导入成功")
        return True
    except Exception as e:
        print("HunyuanImageClient 导入失败:", str(e))
        return False

def test_client_creation():
    """测试客户端创建"""
    print("\n测试客户端创建:")

    try:
        from holodeck_core.image_generation import HunyuanImageClient

        secret_id = os.getenv('HUNYUAN_SECRET_ID')
        secret_key = os.getenv('HUNYUAN_SECRET_KEY')

        client = HunyuanImageClient(
            secret_id=secret_id,
            secret_key=secret_key,
            region="ap-guangzhou"  # 指定广州地域
        )
        print("客户端创建成功")
        return client
    except Exception as e:
        print("客户端创建失败:", str(e))
        return None

def test_connection(client):
    """测试连接"""
    print("\n测试API连接:")

    try:
        if client.test_connection():
            print("API连接测试成功")
            return True
        else:
            print("API连接测试失败")
            return False
    except Exception as e:
        print("API连接测试异常:", str(e))
        return False

def test_image_generation(client):
    """测试图像生成"""
    print("\n测试图像生成:")

    try:
        prompt = "一只可爱的柯基犬在花园里玩耍，阳光明媚"
        output_path = "test_output.png"

        print("生成提示词:", prompt)
        print("输出路径:", output_path)

        result = client.generate_image(
            prompt=prompt,
            resolution="1024:1024",
            style=None,  # 使用默认风格
            model="hunyuan-pro",
            output_path=output_path
        )

        if result and 'local_path' in result:
            print("图像生成成功!")
            print("保存路径:", result['local_path'])
            print("生成时间:", result['metadata']['generation_time_sec'], "秒")
            print("Job ID:", result['job_id'])
            return True
        else:
            print("图像生成失败")
            return False

    except Exception as e:
        print("图像生成异常:", str(e))
        return False

def main():
    """主测试函数"""
    print("混元图像3.0测试开始")
    print("=" * 50)

    # 测试环境
    if not test_environment():
        return

    # 测试导入
    if not test_import():
        return

    # 测试客户端创建
    client = test_client_creation()
    if not client:
        return

    # 跳过连接测试，直接测试图像生成
    print("\n跳过API连接测试，直接测试图像生成:")
    test_image_generation(client)

    print("\n测试完成")

if __name__ == "__main__":
    main()