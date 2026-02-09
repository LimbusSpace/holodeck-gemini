#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add holodeck_core to path
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

def load_environment_variables():
    """Load environment variables from .env file"""
    dotenv_path = Path('.env')
    if dotenv_path.exists():
        with open(dotenv_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def test_hunyuan_integration():
    """Test Hunyuan Image integration with 3D pipeline"""
    print("混元图像3.0集成测试")
    print("=" * 50)

    # Load environment variables
    load_environment_variables()

    print("环境检查:")
    print(f"   - HUNYUAN_SECRET_ID: {'已设置' if os.getenv('HUNYUAN_SECRET_ID') else '未设置'}")
    print(f"   - HUNYUAN_SECRET_KEY: {'已设置' if os.getenv('HUNYUAN_SECRET_KEY') else '未设置'}")

    if not os.getenv('HUNYUAN_SECRET_ID') or not os.getenv('HUNYUAN_SECRET_KEY'):
        print("\n错误: 未配置混元图像API密钥")
        return False

    # Test 1: Basic client creation
    print("\n测试1: 客户端创建")
    print("-" * 30)
    try:
        from holodeck_core.image_generation import HunyuanImageClient
        client = HunyuanImageClient(
            secret_id=os.getenv('HUNYUAN_SECRET_ID'),
            secret_key=os.getenv('HUNYUAN_SECRET_KEY'),
            region='ap-guangzhou'
        )
        print("客户端创建成功")
        test1_success = True
    except Exception as e:
        print(f"客户端创建失败: {e}")
        test1_success = False

    # Test 2: Connection test
    print("\n测试2: API连接测试")
    print("-" * 30)
    try:
        if 'client' in locals():
            connection_ok = client.test_connection()
            if connection_ok:
                print("API连接测试成功")
                test2_success = True
            else:
                print("API连接测试失败")
                test2_success = False
        else:
            print("客户端未创建，跳过连接测试")
            test2_success = False
    except Exception as e:
        print(f"API连接测试异常: {e}")
        test2_success = False

    # Test 3: Scene analysis integration
    print("\n测试3: 场景分析集成")
    print("-" * 30)
    try:
        from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer

        # Test scene analyzer with Hunyuan support
        analyzer = SceneAnalyzer(use_hunyuan=True)
        print("场景分析器创建成功 (启用混元图像)")

        # Test convenience functions
        from holodeck_core.image_generation import generate_scene_reference, generate_object_card
        print("便捷函数导入成功")

        test3_success = True
    except Exception as e:
        print(f"场景分析集成失败: {e}")
        test3_success = False

    # Summary
    print("\n测试总结")
    print("=" * 50)
    tests = [
        ("客户端创建", test1_success),
        ("API连接", test2_success),
        ("场景分析集成", test3_success)
    ]

    passed = sum(1 for _, success in tests if success)
    total = len(tests)

    for test_name, success in tests:
        status = "通过" if success else "失败"
        print(f"   {test_name}: {status}")

    print(f"\n总体: {passed}/{total} 测试通过")

    if passed == total:
        print("\n所有测试通过！混元图像3.0已准备好用于生产环境。")
        print("\n下一步建议:")
        print("   - 运行 examples/hunyuan_3d_pipeline_example.py 测试完整管线")
        print("   - 等待并发限制重置后测试图像生成功能")
        print("   - 在您的项目中集成混元图像功能")
        return True
    else:
        print("\n部分测试失败，请检查错误信息。")
        return False

if __name__ == "__main__":
    test_hunyuan_integration()