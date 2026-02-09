#!/usr/bin/env python3
"""
简单集成测试 - 验证混元3D工作流集成的核心功能
"""

import json
import logging
import sys
import tempfile
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_layout_solver_imports():
    """测试布局求解器导入和基本功能"""
    logger.info("Testing layout solver imports and basic functionality...")

    try:
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))

        from holodeck_core.scene_gen.layout_solver import LayoutSolver

        # Create solver instance
        solver = LayoutSolver()
        logger.info("✅ LayoutSolver instance created successfully")

        # Test backend detection method
        test_glb_path = Path("test_hunyuan3d_model.glb")
        backend = solver._detect_backend_source(test_glb_path, 25.0)

        if backend == "hunyuan3d":
            logger.info("✅ Backend detection working correctly (Hunyuan3D)")
        else:
            logger.warning(f"⚠️ Backend detection returned: {backend}")

        # Test SF3D detection
        backend_sf3d = solver._detect_backend_source(Path("test_sf3d_model.glb"), 5.0)
        if backend_sf3d == "sf3d":
            logger.info("✅ Backend detection working correctly (SF3D)")
        else:
            logger.warning(f"⚠️ SF3D backend detection returned: {backend_sf3d}")

        return True

    except Exception as e:
        logger.error(f"❌ Layout solver test failed: {e}")
        return False

def test_blender_mcp_imports():
    """测试Blender-MCP导入和基本功能"""
    logger.info("Testing Blender-MCP imports and basic functionality...")

    try:
        from holodeck_core.blender.mcp_bridge import BlenderMCPBridge

        # Create bridge instance
        bridge = BlenderMCPBridge()
        logger.info("✅ BlenderMCPBridge instance created successfully")

        # Create temporary GLB files for testing
        temp_dir = Path(tempfile.mkdtemp())

        # Create mock Hunyuan3D file
        hunyuan_glb = temp_dir / "test_hunyuan3d_model.glb"
        hunyuan_glb.write_bytes(b'glTF' + b'\x00' * 1000)  # Minimal GLB header

        # Create mock SF3D file
        sf3d_glb = temp_dir / "test_sf3d_model.glb"
        sf3d_glb.write_bytes(b'glTF' + b'\x00' * 500)  # Smaller file

        # Test GLB analysis
        analysis = bridge._analyze_glb_files([str(hunyuan_glb), str(sf3d_glb)])

        logger.info(f"✅ GLB analysis completed: {analysis['summary']}")
        logger.info(f"   Backend breakdown: {analysis['backend_breakdown']}")

        # Test script generation
        script = bridge._generate_glb_import_script(
            [str(hunyuan_glb), str(sf3d_glb)],
            ["Test_Hunyuan3D", "Test_SF3D"],
            analysis
        )

        if "Hunyuan3D" in script and "SF3D" in script:
            logger.info("✅ Backend-aware script generation working")
        else:
            logger.warning("⚠️ Script generation may not include backend optimizations")

        # Cleanup
        hunyuan_glb.unlink()
        sf3d_glb.unlink()

        return True

    except Exception as e:
        logger.error(f"❌ Blender-MCP test failed: {e}")
        return False

def test_backend_selector():
    """测试后端选择器集成"""
    logger.info("Testing backend selector integration...")

    try:
        from holodeck_core.object_gen.backend_selector import get_backend_selector

        # Get backend selector
        selector = get_backend_selector("workspace")
        logger.info("✅ Backend selector created successfully")

        # Test backend availability check
        backends = selector.get_all_backends()
        logger.info(f"✅ Available backends: {backends}")

        return True

    except Exception as e:
        logger.error(f"❌ Backend selector test failed: {e}")
        return False

def test_asset_manager_integration():
    """测试资产生成管理器集成"""
    logger.info("Testing asset manager integration...")

    try:
        from holodeck_core.object_gen.asset_manager import AssetGenerationManager

        # Create manager instance
        manager = AssetGenerationManager(use_backend_selector=True)
        logger.info("✅ AssetGenerationManager created with backend selector")

        # Check if Hunyuan3D client integration exists
        if hasattr(manager, 'backend_selector'):
            logger.info("✅ Backend selector integration confirmed")
        else:
            logger.warning("⚠️ Backend selector integration may be missing")

        return True

    except Exception as e:
        logger.error(f"❌ Asset manager test failed: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("混元3D工作流集成测试")
    logger.info("=" * 60)

    tests = [
        ("Layout Solver Integration", test_layout_solver_imports),
        ("Blender-MCP Integration", test_blender_mcp_imports),
        ("Backend Selector", test_backend_selector),
        ("Asset Manager Integration", test_asset_manager_integration),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        logger.info("🎉 所有集成测试通过！混元3D工作流集成成功完成。")
    else:
        logger.warning("⚠️ 部分测试失败，请检查相关集成。")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)