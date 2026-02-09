#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# 手动加载.env文件
dotenv_path = Path('.env')
if dotenv_path.exists():
    with open(dotenv_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

print('环境变量加载完成')
print('HUNYUAN_SECRET_ID:', '已设置' if os.getenv('HUNYUAN_SECRET_ID') else '未设置')
print('HUNYUAN_SECRET_KEY:', '已设置' if os.getenv('HUNYUAN_SECRET_KEY') else '未设置')

if os.getenv('HUNYUAN_SECRET_ID') and os.getenv('HUNYUAN_SECRET_KEY'):
    print('\n开始测试混元图像...')

    try:
        sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))
        from holodeck_core.image_generation import HunyuanImageClient

        client = HunyuanImageClient(
            secret_id=os.getenv('HUNYUAN_SECRET_ID'),
            secret_key=os.getenv('HUNYUAN_SECRET_KEY'),
            region='ap-guangzhou'
        )
        print('客户端创建成功')

        # 测试生成
        result = client.generate_image(
            prompt='一只可爱的小猫在花园里',
            resolution='1024:1024',
            style=None,
            model='hunyuan-pro',
            output_path='test_output.png'
        )

        print('生成成功!')
        print('结果:', result)

        if 'local_path' in result:
            print('文件保存到:', result['local_path'])
            if os.path.exists(result['local_path']):
                size = os.path.getsize(result['local_path'])
                print('文件大小:', size, '字节')
            else:
                print('文件不存在，可能只返回了URL')

        if 'image_url' in result:
            print('图像URL:', result['image_url'])

    except Exception as e:
        print('错误:', str(e))
        if 'RequestLimitExceeded' in str(e):
            print('达到并发限制，请等待几分钟后重试')
else:
    print('请先配置API密钥')