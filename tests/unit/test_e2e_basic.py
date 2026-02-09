#!/usr/bin/env python3
"""
基础 E2E 测试验证脚本

这个脚本验证 E2E 测试的基本功能，不运行完整的 build 流程
"""

import json
import os
import sys
from pathlib import Path


def test_e2e_script_imports():
    """测试 E2E 脚本可以正常导入"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from tests.e2e_test import E2ETester
        print("成功 E2E 脚本导入成功")
        return True
    except Exception as e:
        print(f"失败 E2E 脚本导入失败: {e}")
        return False


def test_project_structure():
    """测试项目结构完整"""
    project_root = Path(__file__).parent.parent

    required_files = [
        "holodeck_cli/cli.py",
        "holodeck_core/__init__.py",
        "tests/e2e_test.py",
        "run_e2e_test.sh",
        "run_e2e_test.bat"
    ]

    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            print(f"失败 必需文件不存在: {file_path}")
            return False

    print("成功 项目结构完整")
    return True


def test_config_files():
    """测试配置文件完整"""
    project_root = Path(__file__).parent.parent

    # 检查 .mcp.json
    mcp_config = project_root / ".mcp.json"
    if not mcp_config.exists():
        print("失败 .mcp.json 不存在")
        return False

    try:
        with open(mcp_config, 'r') as f:
            config = json.load(f)

        if "mcpServers" not in config:
            print("失败 .mcp.json 格式错误")
            return False

        if "blender" not in config["mcpServers"]:
            print("失败 .mcp.json 缺少 blender 配置")
            return False

        print("成功 .mcp.json 配置正确")
        return True

    except Exception as e:
        print(f"失败 .mcp.json 解析失败: {e}")
        return False


def test_standard_formats():
    """测试标准格式文档存在"""
    project_root = Path(__file__).parent.parent
    formats_file = project_root / "STANDARD_FORMATS.md"

    if not formats_file.exists():
        print("失败 STANDARD_FORMATS.md 不存在")
        return False

    try:
        with open(formats_file, 'r', encoding='utf-8') as f:
            content = f.read()

        required_sections = [
            "layout_solution.json",
            "asset_manifest.json",
            "blender_object_map.json"
        ]

        for section in required_sections:
            if section not in content:
                print(f"失败 STANDARD_FORMATS.md 缺少章节: {section}")
                return False

        print("成功 标准格式文档完整")
        return True

    except Exception as e:
        print(f"失败 标准格式文档读取失败: {e}")
        return False


def main():
    """运行基础验证测试"""
    print("运行 E2E 基础验证测试")
    print("=" * 40)

    tests = [
        ("E2E 脚本导入", test_e2e_script_imports),
        ("项目结构", test_project_structure),
        ("配置文件", test_config_files),
        ("标准格式文档", test_standard_formats)
    ]

    all_passed = True
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"成功 {test_name} 测试通过")
            else:
                print(f"失败: {test_name} 测试失败")
                all_passed = False
        except Exception as e:
            print(f"异常: {test_name} 测试异常: {e}")
            all_passed = False

    print("=" * 40)
    if all_passed:
        print("完成 基础验证测试通过！")
        print("现在可以运行完整的 E2E 测试:")
        print("   python tests/e2e_test.py")
        return True
    else:
        print("基础验证测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)