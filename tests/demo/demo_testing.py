#!/usr/bin/env python3
"""
Holodeck 测试体系演示脚本

演示我们创建的端到端验收测试体系
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_step(step, description):
    """打印步骤"""
    print(f"\n[{step}] {description}")


def demo_project_structure():
    """演示项目结构"""
    print_header("项目结构验证")

    print_step("1", "验证项目目录结构")
    project_root = Path(__file__).parent

    key_files = [
        "holodeck_cli/cli.py",
        "holodeck_core/__init__.py",
".mcp.json",
        "STANDARD_FORMATS.md",
        "workspace/sessions"
    ]

    for file_path in key_files:
        full_path = project_root / file_path
        status = "✓" if full_path.exists() else "✗"
        print(f"  {status} {file_path}")

    print_step("2", "验证 MCP 配置")
    mcp_config = project_root / ".mcp.json"
    if mcp_config.exists():
        with open(mcp_config) as f:
            config = json.load(f)
        server_name = list(config["mcpServers"].keys())[0]
        print(f"  ✓ 服务器名称: {server_name}")
        print(f"  ✓ 工具前缀: mcp__{server_name}__")


def demo_standard_formats():
    """演示标准格式"""
    print_header("标准格式规范")

    print_step("1", "layout_solution_v1.json 格式")
    print("""
{
  "success": true,
  "object_placements": {
    "obj_001": {
      "pos": [x, y, z],
      "rot_euler": [rx, ry, rz],
      "scale": [sx, sy, sz]
    }
  },
  "version": "v1"
}
""")

    print_step("2", "asset_manifest.json 格式")
    print("""
{
  "version": "v1",
  "assets": {
    "obj_001": {
      "asset_path": "assets/table.glb",
      "format": "glb",
      "size_bytes": 12345,
      "checksum": "sha256:...",
      "metadata": {...}
    }
  },
  "total_assets": 1,
  "total_size_mb": 0.012
}
""")

    print_step("3", "blender_object_map.json 格式")
    print("""
{
  "naming_convention": "object_name_equals_id",
  "description": "Blender中对象名称直接使用object_id",
  "mapping": {
    "obj_001": "obj_001"
  }
}
""")


def demo_testing_framework():
    """演示测试框架"""
    print_header("测试框架演示")

    print_step("1", "基础验证测试")
    print("  功能: 验证项目结构和配置")
    print("  文件: tests/basic_validation.py")
    print("  命令: python tests/basic_validation.py")

    print_step("2", "端到端验收测试")
    print("  功能: 验证完整 build 流程")
    print("  文件: tests/e2e_test_simple.py")
    print("  场景: '一个空房间，里面有一个立方体桌子'")
    print("  验证: CLI执行、文件生成、格式正确性")

    print_step("3", "测试运行器")
    print("  功能: 统一管理测试执行")
    print("  文件: test_runner_simple.py")
    print("  模式: quick(快速验证), full(完整E2E), all(全部)")


def demo_mcp_tools():
    """演示 MCP 工具"""
    print_header("MCP 工具清单")

    print_step("1", "基础工具")
    tools = [
        "mcp__blender__get_scene_info",
        "mcp__blender__get_viewport_screenshot",
        "mcp__blender__execute_blender_code"
    ]
    for tool in tools:
        print(f"  ✓ {tool}")

    print_step("2", "资产生成工具")
    asset_tools = [
        "mcp__blender__generate_hunyuan3d_model",
        "mcp__blender__generate_hyper3d_model_via_text",
        "mcp__blender__download_sketchfab_model",
        "mcp__blender__download_polyhaven_asset"
    ]
    for tool in asset_tools:
        print(f"  ✓ {tool}")


def demo_workflow():
    """演示工作流程"""
    print_header("工作流程演示")

    print_step("1", "CLI 生成阶段")
    print("""
holodeck build "一个空房间，里面有一个立方体桌子"
  --until layout
  --no-blendermcp
""")
    print("  输出:")
    print("    - layout_solution_v1.json")
    print("    - asset_manifest.json")
    print("    - blender_object_map.json")

    print_step("2", "Blender 应用阶段")
    print("""
# Blender apply 脚本示例
import bpy
import json

# 读取标准文件
with open('layout_solution_v1.json') as f:
    layout = json.load(f)

# 导入资产并应用布局
for object_id, placement in layout["object_placements"].items():
    # 导入资产
    # 设置对象名称
    # 应用位置、旋转、缩放
""")

    print_step("3", "验证和截图")
    print("""
mcp__blender__get_viewport_screenshot
  -> 返回 viewport 截图作为验收证据
""")


def run_demo():
    """运行演示"""
    print("Holodeck Holodeck 端到端验收测试体系演示")
    print("演示我们创建的完整测试和质量保证体系\n")

    demo_project_structure()
    demo_standard_formats()
    demo_testing_framework()
    demo_mcp_tools()
    demo_workflow()

    print_header("演示总结")
    print("\n成功 已完成演示:")
    print("  1. 项目结构验证体系")
    print("  2. 标准文件格式规范")
    print("  3. 端到端测试框架")
    print("  4. MCP 工具清单")
    print("  5. 完整工作流程")

    print("\n文件 生成的文件:")
    print("  - tests/basic_validation.py (基础验证)")
    print("  - tests/e2e_test_simple.py (端到端测试)")
    print("  - test_runner_simple.py (测试运行器)")
    print("  - TEST_CASE.md (测试用例文档)")
    print("  - QUALITY_ASSURANCE.md (质量保证文档)")

    print("\n目标 验收标准:")
    print("  ✓ CLI 能生成标准格式文件")
    print("  ✓ 文件格式符合规范")
    print("  ✓ Blender 能使用通用脚本应用场景")
    print("  ✓ 测试体系可重复验证")

    print("\n完成 端到端验收测试体系创建完成！")


if __name__ == "__main__":
    run_demo()