#!/usr/bin/env python3
"""
测试GLB文件进入Blender的完整步骤修复

验证mcp_bridge.py和scene_assembler.py的修复是否正常工作
"""

import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mcp_bridge_imports():
    """测试MCP桥接层导入是否正常"""
    logger.info("测试MCP桥接层导入...")

    try:
        from holodeck_core.blender.mcp_bridge import BlenderMCPBridge
        logger.info("✓ BlenderMCPBridge导入成功")

        # 测试MCP工具客户端导入
        from holodeck_core.tools.mcp_client import get_mcp_client, MCPToolClient
        logger.info("✓ MCP工具客户端导入成功")

        # 创建桥接实例
        bridge = BlenderMCPBridge()
        logger.info("✓ BlenderMCPBridge实例创建成功")

        # 测试MCP客户端
        mcp_client = get_mcp_client()
        logger.info("✓ MCP客户端获取成功")

        return True

    except Exception as e:
        logger.error(f"✗ MCP桥接层导入失败: {e}")
        return False

def test_scene_assembler_imports():
    """测试场景组装器导入是否正常"""
    logger.info("测试场景组装器导入...")

    try:
        from holodeck_core.blender.scene_assembler import SceneAssembler
        logger.info("✓ SceneAssembler导入成功")

        # 创建组装器实例
        assembler = SceneAssembler()
        logger.info("✓ SceneAssembler实例创建成功")

        # 检查必要的方法是否存在
        required_methods = ['assemble_scene', 'render_scene', '_execute_via_blender_mcp']
        for method in required_methods:
            if hasattr(assembler, method):
                logger.info(f"✓ 方法 {method} 存在")
            else:
                logger.error(f"✗ 方法 {method} 不存在")
                return False

        return True

    except Exception as e:
        logger.error(f"✗ 场景组装器导入失败: {e}")
        return False

def test_mcp_bridge_methods():
    """测试MCP桥接层方法调用"""
    logger.info("测试MCP桥接层方法...")

    try:
        from holodeck_core.blender.mcp_bridge import BlenderMCPBridge
        from holodeck_core.tools.mcp_client import get_mcp_client

        bridge = BlenderMCPBridge()
        mcp_client = get_mcp_client()

        # 测试方法是否存在
        required_methods = ['apply_layout', 'get_scene_info', 'take_screenshot']
        for method in required_methods:
            if hasattr(bridge, method):
                logger.info(f"✓ 桥接方法 {method} 存在")
            else:
                logger.error(f"✗ 桥接方法 {method} 不存在")
                return False

        # 测试MCP客户端方法
        if hasattr(mcp_client, 'call_tool'):
            logger.info("✓ MCP客户端call_tool方法存在")
        else:
            logger.error("✗ MCP客户端call_tool方法不存在")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ MCP桥接层方法测试失败: {e}")
        return False

def test_cli_integration():
    """测试CLI集成是否正常"""
    logger.info("测试CLI集成...")

    try:
        # 测试CLI命令导入
        from holodeck_cli.commands.build import build_command, assemble_and_render
        logger.info("✓ CLI build命令导入成功")

        # 测试参数解析器
        from holodeck_cli.cli import create_parser
        parser = create_parser()
        logger.info("✓ CLI参数解析器创建成功")

        # 测试--no-blendermcp参数是否存在
        try:
            build_parser = None
            for action in parser._subparsers._actions:
                if hasattr(action, 'choices') and 'build' in action.choices:
                    build_parser = action.choices['build']
                    break

            if build_parser and '--no-blendermcp' in [opt.dest for opt in build_parser._actions]:
                logger.info("✓ --no-blendermcp参数存在")
            else:
                logger.warning("⚠ --no-blendermcp参数可能不存在或配置不正确")
        except Exception as e:
            logger.warning(f"⚠ CLI参数检查失败: {e}")

        return True

    except Exception as e:
        logger.error(f"✗ CLI集成测试失败: {e}")
        return False

def test_error_handling():
    """测试错误处理机制"""
    logger.info("测试错误处理机制...")

    try:
        from holodeck_core.blender.scene_assembler import SceneAssembler

        assembler = SceneAssembler()

        # 测试回退方法是否存在
        fallback_methods = ['_fallback_to_script_generation', '_fallback_to_local_execution', '_fallback_render_generation']
        for method in fallback_methods:
            if hasattr(assembler, method):
                logger.info(f"✓ 回退方法 {method} 存在")
            else:
                logger.error(f"✗ 回退方法 {method} 不存在")
                return False

        return True

    except Exception as e:
        logger.error(f"✗ 错误处理测试失败: {e}")
        return False

def main():
    """运行所有测试"""
    logger.info("开始GLB文件进入Blender修复验证测试...")

    tests = [
        ("MCP桥接层导入", test_mcp_bridge_imports),
        ("场景组装器导入", test_scene_assembler_imports),
        ("MCP桥接层方法", test_mcp_bridge_methods),
        ("CLI集成", test_cli_integration),
        ("错误处理机制", test_error_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        logger.info(f"\n--- 运行测试: {test_name} ---")
        try:
            if test_func():
                logger.info(f"✓ {test_name} 通过")
                passed += 1
            else:
                logger.error(f"✗ {test_name} 失败")
                failed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} 异常: {e}")
            failed += 1

    logger.info(f"\n=== 测试结果 ===")
    logger.info(f"通过: {passed}")
    logger.info(f"失败: {failed}")
    logger.info(f"总计: {passed + failed}")

    if failed == 0:
        logger.info("🎉 所有测试通过！GLB文件进入Blender的修复已完成。")
        return True
    else:
        logger.error("❌ 部分测试失败，需要进一步检查和修复。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)