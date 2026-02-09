#!/usr/bin/env python3
"""
基础验证测试 - 验证项目结构和配置
"""

import json
import os
import sys
from pathlib import Path


def test_project_structure():
    """测试项目结构"""
    print("测试项目结构...")

    project_root = Path(__file__).parent.parent

    # 检查必需文件和目录
    required_paths = [
        "holodeck_cli/cli.py",
        "holodeck_core/__init__.py",
".mcp.json",
        "STANDARD_FORMATS.md",
        "workspace/sessions"
    ]

    for path_str in required_paths:
        path = project_root / path_str
        if not path.exists():
            print(f"失败: {path_str} 不存在")
            return False
        print(f"成功: {path_str} 存在")

    return True


def test_mcp_config():
    """测试 MCP 配置"""
    print("测试 MCP 配置...")

    config_file = Path(__file__).parent.parent / ".mcp.json"

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        if "mcpServers" not in config:
            print("失败: .mcp.json 缺少 mcpServers")
            return False

        if "blender" not in config["mcpServers"]:
            print("失败: .mcp.json 缺少 blender 配置")
            return False

        blender_config = config["mcpServers"]["blender"]
        if "command" not in blender_config:
            print("失败: blender 配置缺少 command")
            return False

        print("成功: MCP 配置正确")
        print(f"  - server key: blender")
        print(f"  - command: {blender_config['command']}")
        print(f"  - args: {blender_config.get('args', [])}")
        return True

    except Exception as e:
        print(f"失败: 解析 .mcp.json 失败: {e}")
        return False


def test_standard_formats():
    """测试标准格式文档"""
    print("测试标准格式文档...")

    formats_file = Path(__file__).parent.parent / "STANDARD_FORMATS.md"

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
                print(f"失败: 缺少章节 {section}")
                return False

        print("成功: 标准格式文档完整")
        return True

    except Exception as e:
        print(f"失败: 读取标准格式文档失败: {e}")
        return False


def test_cli_structure():
    """测试 CLI 结构"""
    print("测试 CLI 结构...")

    cli_dir = Path(__file__).parent.parent / "holodeck_cli"

    required_files = [
        "cli.py",
        "__main__.py",
        "config.py"
    ]

    for file_name in required_files:
        file_path = cli_dir / file_name
        if not file_path.exists():
            print(f"失败: {file_name} 不存在")
            return False

    print("成功: CLI 结构完整")
    return True


def main():
    """主函数"""
    print("Holodeck 基础验证测试")
    print("=" * 40)

    tests = [
        ("项目结构", test_project_structure),
        ("MCP 配置", test_mcp_config),
        ("标准格式", test_standard_formats),
        ("CLI 结构", test_cli_structure)
    ]

    all_passed = True
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"成功: {test_name} 测试通过")
            else:
                print(f"失败: {test_name} 测试失败")
                all_passed = False
        except Exception as e:
            print(f"异常: {test_name} 测试异常: {e}")
            all_passed = False
        print()

    print("=" * 40)
    if all_passed:
        print("基础验证测试通过！")
        print("项目结构完整，配置正确。")
        return True
    else:
        print("基础验证测试失败")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)