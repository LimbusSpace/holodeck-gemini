#!/usr/bin/env python3
"""Test script for the new GLB import functionality using MCP bridge."""

import sys
import os
from pathlib import Path

# Add holodeck_core to Python path
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

from blender.mcp_bridge import BlenderMCPBridge

def test_glb_import_mcp():
    """Test the new GLB import functionality via MCP bridge."""

    # Find existing GLB files
    workspace_dir = Path("C:/Users/Administrator/Desktop/holodeck-gemini/workspace/sessions")
    glb_files = list(workspace_dir.rglob("*.glb"))

    if not glb_files:
        print("No GLB files found for testing")
        return

    # Take up to 2 GLB files for testing
    test_files = glb_files[:2]
    print(f"Found {len(test_files)} GLB files for testing:")
    for f in test_files:
        print(f"  - {f}")

    # Create bridge and test import
    bridge = BlenderMCPBridge()

    # Test 1: Import with automatic naming
    print("\n=== Test 1: Import with automatic naming ===")
    glb_paths = [str(f) for f in test_files]

    result = bridge.import_glb_assets(glb_paths)
    print("Import result:", result)

    # Test 2: Import with custom naming
    print("\n=== Test 2: Import with custom naming ===")
    custom_names = ["test_object_1", "test_object_2"]

    result2 = bridge.import_glb_assets(glb_paths, custom_names)
    print("Import result:", result2)

    # Test 3: Generate import script for manual execution
    print("\n=== Test 3: Generate import script ===")
    script_content = bridge._generate_glb_import_script(glb_paths, custom_names)

    # Save script to file
    script_path = Path("test_import_script.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    print(f"Generated import script saved to: {script_path}")
    print(f"Script size: {len(script_content)} characters")

    # Show how to use it
    print("\n=== Usage Instructions ===")
    print("1. Via MCP bridge (programmatic):")
    print("   bridge = BlenderMCPBridge()")
    print("   result = bridge.import_glb_assets(['path/to/file.glb'], ['object_name'])")
    print()
    print("2. Via generated script (manual):")
    print(f"   blender --python {script_path}")
    print()
    print("3. Via mcp__blender__execute_blender_code:")
    print("   Use the generated script content with the MCP tool")

    return script_path

if __name__ == "__main__":
    test_glb_import_mcp()