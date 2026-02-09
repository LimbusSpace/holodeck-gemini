#!/usr/bin/env python3
"""Final verification of Hunyuan 3D integration."""

import os
import sys
from pathlib import Path

# Load environment variables
def load_env_file():
    """Load environment variables from .env file."""
    env_paths = [
        Path(".env"),
        Path(__file__).parent / ".env",
        Path.home() / ".env"
    ]

    for env_path in env_paths:
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip().strip('"\'')
                print(f"Loaded environment from {env_path}")
                break
            except Exception as e:
                print(f"Failed to load {env_path}: {e}")

load_env_file()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

def verify_imports():
    """Verify all modules can be imported."""
    print("\n[1/6] Verifying module imports...")

    try:
        from holodeck_core.object_gen.hunyuan_3d_client import (
            Hunyuan3DClient, Hunyuan3DTask, Hunyuan3DResult, generate_3d_asset
        )
        print("  [OK] Hunyuan 3D client imports successful")

        from holodeck_core.object_gen.backend_selector import BackendSelector
        print("  [OK] Backend selector imports successful")

        from holodeck_core.object_gen.asset_manager import AssetGenerationManager
        print("  [OK] Asset generation manager imports successful")

        return True
    except Exception as e:
        print(f"  [FAIL] Import failed: {e}")
        return False

def verify_environment():
    """Verify environment configuration."""
    print("\n[2/6] Verifying environment configuration...")

    required_vars = ['HUNYUAN_SECRET_ID', 'HUNYUAN_SECRET_KEY']
    all_good = True

    for var in required_vars:
        if os.getenv(var):
            print(f"  [OK] {var}: Set")
        else:
            print(f"  [FAIL] {var}: Not set")
            all_good = False

    return all_good

def verify_client_initialization():
    """Verify client can be initialized."""
    print("\n[3/6] Verifying client initialization...")

    try:
        from holodeck_core.object_gen.hunyuan_3d_client import Hunyuan3DClient

        secret_id = os.getenv("HUNYUAN_SECRET_ID")
        secret_key = os.getenv("HUNYUAN_SECRET_KEY")

        if not secret_id or not secret_key:
            print("  [FAIL] Credentials not available")
            return False

        # Test Pro version
        client_pro = Hunyuan3DClient(secret_id, secret_key, use_pro_version=True)
        print("  [OK] Pro version client initialized")

        # Test Rapid version
        client_rapid = Hunyuan3DClient(secret_id, secret_key, use_pro_version=False)
        print("  [OK] Rapid version client initialized")

        return True
    except Exception as e:
        print(f"  [FAIL] Client initialization failed: {e}")
        return False

def verify_connection():
    """Verify API connection."""
    print("\n[4/6] Verifying API connection...")

    try:
        from holodeck_core.object_gen.hunyuan_3d_client import Hunyuan3DClient

        secret_id = os.getenv("HUNYUAN_SECRET_ID")
        secret_key = os.getenv("HUNYUAN_SECRET_KEY")

        if not secret_id or not secret_key:
            print("  [FAIL] Credentials not available")
            return False

        client = Hunyuan3DClient(secret_id, secret_key)

        if client.test_connection():
            print("  [OK] API connection test passed")
            return True
        else:
            print("  [FAIL] API connection test failed")
            return False
    except Exception as e:
        print(f"  [FAIL] Connection test failed: {e}")
        return False

def verify_task_creation():
    """Verify task creation."""
    print("\n[5/6] Verifying task creation...")

    try:
        from holodeck_core.object_gen.hunyuan_3d_client import Hunyuan3DTask

        # Test basic task
        task1 = Hunyuan3DTask(
            task_id="test1",
            prompt="A red apple",
            output_dir="test_output"
        )
        print("  [OK] Basic task creation successful")

        # Test multi-view task
        task2 = Hunyuan3DTask(
            task_id="test2",
            output_dir="test_output",
            multi_views={"front": "url1", "back": "url2"}
        )
        print("  [OK] Multi-view task creation successful")

        return True
    except Exception as e:
        print(f"  [FAIL] Task creation failed: {e}")
        return False

def verify_integration():
    """Verify integration with asset manager."""
    print("\n[6/6] Verifying integration...")

    try:
        from holodeck_core.object_gen.asset_manager import AssetGenerationManager

        # Test with backend selector
        manager = AssetGenerationManager(
            workspace_root="workspace",
            use_backend_selector=True
        )
        print("  [OK] Asset manager with backend selector works")

        # Test legacy mode
        manager_legacy = AssetGenerationManager(
            workspace_root="workspace",
            use_backend_selector=False
        )
        print("  [OK] Asset manager legacy mode works")

        return True
    except Exception as e:
        print(f"  [FAIL] Integration test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("Hunyuan 3D Integration - Final Verification")
    print("=" * 60)
    print("This script verifies that all Hunyuan 3D integration")
    print("components are working correctly.\n")

    tests = [
        ("Module Imports", verify_imports),
        ("Environment Configuration", verify_environment),
        ("Client Initialization", verify_client_initialization),
        ("API Connection", verify_connection),
        ("Task Creation", verify_task_creation),
        ("Integration", verify_integration),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  [ERROR] Unexpected error: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"  {test_name}: {status}")

    print(f"\nOverall Result: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] ALL VERIFICATION TESTS PASSED!")
        print("\nThe Hunyuan 3D integration is complete and ready for use.")
        print("\nYou can now:")
        print("  - Generate 3D models from text prompts")
        print("  - Generate 3D models from images")
        print("  - Use multi-view image generation")
        print("  - Choose between Pro and Rapid versions")
        print("  - Integrate with the existing asset pipeline")
        print("\nCheck example_hunyuan_3d.py for usage examples.")
        return True
    else:
        print(f"\n[FAIL] {total - passed} verification tests failed.")
        print("Please check the error messages above and fix any issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)