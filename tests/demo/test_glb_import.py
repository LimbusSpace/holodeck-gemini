#!/usr/bin/env python3
"""Test script for GLB import functionality in Holodeck."""

import os
import json
from pathlib import Path

def test_glb_import():
    """Test importing GLB files into Blender using existing Holodeck infrastructure."""

    # Find an existing GLB file
    workspace_dir = Path("C:/Users/Administrator/Desktop/holodeck-gemini/workspace/sessions")
    glb_files = list(workspace_dir.rglob("*.glb"))

    if not glb_files:
        print("No GLB files found for testing")
        return

    sample_glb = glb_files[0]
    print(f"Found sample GLB file: {sample_glb}")

    # Generate Blender script to import this GLB
    blender_script = f'''
import bpy
import os

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import GLB file
glb_path = r"{sample_glb}"
print(f"Importing GLB: {{glb_path}}")

if os.path.exists(glb_path):
    try:
        bpy.ops.import_scene.gltf(filepath=glb_path)
        print("GLB imported successfully!")

        # List imported objects
        imported_objects = [obj.name for obj in bpy.context.selected_objects]
        print(f"Imported objects: {{imported_objects}}")

        # Save the scene
        blend_path = r"{sample_glb.parent}/test_import.blend"
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"Scene saved to: {{blend_path}}")

    except Exception as e:
        print(f"Import failed: {{e}}")
else:
    print(f"GLB file not found: {{glb_path}}")
'''

    # Save script to file
    script_path = sample_glb.parent / "test_import.py"
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(blender_script)

    print(f"Generated Blender import script: {script_path}")

    # Show how to execute via MCP
    print("\nTo execute this via blender-mcp:")
    print(f"1. Use mcp__blender__execute_blender_code with the script content")
    print(f"2. Or run directly in Blender: blender --python {script_path}")

    return str(script_path)

if __name__ == "__main__":
    test_glb_import()