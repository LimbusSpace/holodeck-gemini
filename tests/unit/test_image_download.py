#!/usr/bin/env python3

import requests
from pathlib import Path

def test_image_download():
    """测试图像下载功能"""
    # 使用之前debug中获得的图像URL
    image_url = "https://example.com/test-image.png"  # Replace with actual URL for testing

    output_path = "test_downloaded_image.png"

    try:
        print("开始下载图像...")
        response = requests.get(image_url, timeout=30)
        response.raise_for_status()

        output_path = Path(output_path)
        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"图像下载成功！保存到: {output_path}")
        print(f"文件大小: {len(response.content)} 字节")

        return True

    except Exception as e:
        print(f"下载失败: {e}")
        return False

if __name__ == "__main__":
    test_image_download()