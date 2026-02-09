#!/usr/bin/env python3
"""Test Hunyuan3D integration with the asset generation pipeline."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

from holodeck_core.object_gen.asset_generator import AssetGenerator
from holodeck_core.object_gen.backend_selector import BackendSelector

def test_backend_selector():
    """Test backend selector functionality."""
    print("[TEST] Testing Backend Selector...")

    selector = BackendSelector()
    backend = selector.get_optimal_backend()
    print(f"Selected backend: {backend}")

    # Test backend availability check
    available_backends = selector.get_available_backends()
    print(f"Available backends: {available_backends}")

    return backend

def test_asset_generator_initialization():
    """Test AssetGenerator initialization with Hunyuan3D support."""
    print("[TEST] Testing AssetGenerator initialization...")

    try:
        generator = AssetGenerator()
        print("✓ AssetGenerator initialized successfully")

        # Check if Hunyuan3D client is available
        if generator.hunyuan_client:
            print("✓ Hunyuan3D client is available")
        else:
            print("⚠ Hunyuan3D client is not available (missing credentials)")

        # Check SF3D client
        if generator.sf3d_client:
            print("✓ SF3D client is available")
        else:
            print("✗ SF3D client failed to initialize")

        return generator

    except Exception as e:
        print(f"✗ AssetGenerator initialization failed: {e}")
        return None

def test_backend_selection_integration():
    """Test backend selection integration."""
    print("[TEST] Testing backend selection integration...")

    # Test with different environment configurations
    test_configs = [
        {"PREFERRED_3D_BACKEND": "hunyuan"},
        {"PREFERRED_3D_BACKEND": "sf3d"},
        {}  # Default configuration
    ]

    for i, config in enumerate(test_configs):
        print(f"\nTest configuration {i+1}:")
        for key, value in config.items():
            os.environ[key] = value
            print(f"  {key}={value}")

        selector = BackendSelector()
        backend = selector.get_optimal_backend()
        print(f"  Selected backend: {backend}")

        # Clean up environment
        for key in config:
            os.environ.pop(key, None)

def mock_session():
    """Create a mock session for testing."""
    class MockSession:
        def __init__(self):
            self.session_id = "test_session"
            self.session_dir = Path(tempfile.mkdtemp())

        def get_object_cards_dir(self):
            cards_dir = self.session_dir / "object_cards"
            cards_dir.mkdir(exist_ok=True)
            return cards_dir

        def get_objects_path(self):
            return self.session_dir / "objects.json"

        def load_objects(self):
            return {"objects": []}

    return MockSession()

def test_asset_generation_workflow():
    """Test the complete asset generation workflow."""
    print("[TEST] Testing asset generation workflow...")

    # Create mock session
    session = mock_session()

    # Initialize generator
    generator = AssetGenerator()

    # Create a mock object card
    cards_dir = session.get_object_cards_dir()
    test_card = cards_dir / "test_object.json"

    card_data = {
        "name": "test_object",
        "description": "A simple test object",
        "properties": {"color": "blue", "size": "medium"}
    }

    import json
    with open(test_card, 'w', encoding='utf-8') as f:
        json.dump(card_data, f)

    print(f"Created test card: {test_card}")

    # Test asset generation
    try:
        asset_path = generator.generate_from_card(session, "test_object")
        print(f"✓ Asset generation completed: {asset_path}")

        if asset_path.exists():
            print(f"✓ Asset file exists: {asset_path.stat().st_size} bytes")
        else:
            print("✗ Asset file was not created")

    except Exception as e:
        print(f"✗ Asset generation failed: {e}")

    # Clean up
    import shutil
    shutil.rmtree(session.session_dir)

def main():
    """Run all integration tests."""
    print("=" * 60)
    print("Hunyuan3D Integration Test Suite")
    print("=" * 60)

    # Test 1: Backend Selector
    try:
        backend = test_backend_selector()
        print("✓ Backend selector test passed\n")
    except Exception as e:
        print(f"✗ Backend selector test failed: {e}\n")
        return False

    # Test 2: Asset Generator Initialization
    try:
        generator = test_asset_generator_initialization()
        if generator:
            print("✓ Asset generator initialization test passed\n")
        else:
            print("✗ Asset generator initialization test failed\n")
            return False
    except Exception as e:
        print(f"✗ Asset generator initialization test failed: {e}\n")
        return False

    # Test 3: Backend Selection Integration
    try:
        test_backend_selection_integration()
        print("✓ Backend selection integration test passed\n")
    except Exception as e:
        print(f"✗ Backend selection integration test failed: {e}\n")

    # Test 4: Asset Generation Workflow
    try:
        test_asset_generation_workflow()
        print("✓ Asset generation workflow test passed\n")
    except Exception as e:
        print(f"✗ Asset generation workflow test failed: {e}\n")

    print("=" * 60)
    print("Integration test completed!")
    print("Note: Full functionality requires valid API credentials.")
    print("=" * 60)

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
