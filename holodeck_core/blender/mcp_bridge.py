"""Bridge between Holodeck CLI and blender-mcp for remote Blender control."""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from ..schemas.holodeck_error import HolodeckError

logger = logging.getLogger(__name__)


class BlenderMCPBridge:
    """Bridge for communicating with blender-mcp server."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def apply_layout(self, workspace_path: str) -> Dict[str, Any]:
        """Apply layout and import assets via blender-mcp.

        This method uses the mcp__blender__execute_blender_code tool
        to run the standard apply script in Blender.

        Args:
            workspace_path: Path to session workspace directory

        Returns:
            Dictionary with operation result
        """
        try:
            self.logger.info(f"Applying layout via blender-mcp: {workspace_path}")

            # Generate the apply script with correct workspace path
            script_content = self._generate_apply_script(workspace_path)

            # Execute via blender-mcp using the global MCP client
            from holodeck_core.tools.mcp_client import get_mcp_client
            mcp_client = get_mcp_client()

            # Call the blender MCP tool
            result = mcp_client.call_tool(
                "mcp__blender__execute_blender_code",
                code=script_content
            )

            if result.get("success", False):
                self.logger.info("Layout applied successfully via blender-mcp")
                return {
                    "success": True,
                    "blend_path": f"{workspace_path}/blender_scene.blend",
                    "message": "Scene assembled successfully"
                }
            else:
                error_msg = result.get("error", "Unknown error")
                self.logger.error(f"blender-mcp execution failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg
                }

        except Exception as e:
            self.logger.error(f"Layout application failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_scene_info(self) -> Dict[str, Any]:
        """Get current Blender scene information via blender-mcp."""
        try:
            from holodeck_core.tools.mcp_client import get_mcp_client
            mcp_client = get_mcp_client()

            # Call mcp__blender__get_scene_info
            result = mcp_client.call_tool("mcp__blender__get_scene_info")
            return result

        except Exception as e:
            self.logger.error(f"Failed to get scene info: {e}")
            return {"error": str(e)}

    def import_glb_assets(self, glb_paths: list, object_names: Optional[list] = None) -> Dict[str, Any]:
        """Import GLB assets into Blender via blender-mcp.

        Supports GLB files from multiple backends including Hunyuan3D and SF3D.

        Args:
            glb_paths: List of paths to GLB files to import
            object_names: Optional list of names to assign to imported objects

        Returns:
            Dictionary with import results
        """
        try:
            self.logger.info(f"Importing {len(glb_paths)} GLB assets via blender-mcp")

            # Analyze GLB files for compatibility and backend source
            glb_analysis = self._analyze_glb_files(glb_paths)
            self.logger.info(f"GLB analysis: {glb_analysis['summary']}")

            # Generate import script with backend-specific optimizations
            script_content = self._generate_glb_import_script(glb_paths, object_names, glb_analysis)

            # Execute via blender-mcp
            from holodeck_core.tools.mcp_client import get_mcp_client
            mcp_client = get_mcp_client()

            result = mcp_client.call_tool(
                "mcp__blender__execute_blender_code",
                code=script_content
            )

            if result.get("success", False):
                self.logger.info("GLB assets imported successfully via blender-mcp")
                return {
                    "success": True,
                    "imported_count": len(glb_paths),
                    "message": f"Successfully imported {len(glb_paths)} GLB assets",
                    "backend_breakdown": glb_analysis["backend_breakdown"]
                }
            else:
                error_msg = result.get("error", "Unknown error")
                self.logger.error(f"GLB import failed: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "backend_breakdown": glb_analysis["backend_breakdown"]
                }

        except Exception as e:
            self.logger.error(f"GLB import failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def take_screenshot(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Take viewport screenshot via blender-mcp."""
        try:
            from holodeck_core.tools.mcp_client import get_mcp_client
            mcp_client = get_mcp_client()

            # Call mcp__blender__get_viewport_screenshot
            result = mcp_client.call_tool(
                "mcp__blender__get_viewport_screenshot",
                output_path=output_path
            )
            return result

        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return {"error": str(e)}

    def _generate_apply_script(self, workspace_path: str) -> str:
        """Generate the Blender apply script with correct workspace path."""

        # Read the standard apply script template
        script_template = '''
import os, json
import bpy

# --- set this from the CLI JSON workspace_path ---
workspace_path = r"REPLACE_WITH_WORKSPACE_PATH"

ws = os.path.abspath(workspace_path)

def load_json(rel):
    path = os.path.join(ws, rel)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

asset_manifest = load_json("asset_manifest.json")
layout = load_json("layout_solution_v1.json")

# asset_manifest format assumption:
# { "assets": { "<object_id>": { "path": "assets/xxx.glb" , ... } } }
assets = asset_manifest.get("assets", asset_manifest.get("mapping", {}))

def import_asset(object_id, relpath):
    abspath = os.path.join(ws, relpath)
    ext = os.path.splitext(abspath)[1].lower()

    # Import (extend as needed)
    if ext in [".glb", ".gltf"]:
        bpy.ops.import_scene.gltf(filepath=abspath)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=abspath)
    elif ext == ".obj":
        bpy.ops.import_scene.obj(filepath=abspath)
    else:
        raise RuntimeError(f"Unsupported asset extension: {ext} ({abspath})")

    # Heuristic: rename last selected object (you may refine to collection-based import)
    imported = bpy.context.selected_objects
    if not imported:
        raise RuntimeError(f"Import produced no selected objects for {object_id}")

    # Pick an object to represent this asset
    root = imported[0]
    root.name = object_id
    return root

# Import assets if missing in scene
for object_id, meta in assets.items():
    if bpy.data.objects.get(object_id):
        continue
    relpath = meta["path"] if isinstance(meta, dict) else meta
    import_asset(object_id, relpath)

# Apply layout
placements = layout.get("placements", layout.get("objects", []))
missing = []

for p in placements:
    oid = p.get("object_id") or p.get("id")
    obj = bpy.data.objects.get(oid)
    if not obj:
        missing.append(oid)
        continue

    loc = p.get("location", [0,0,0])
    rot = p.get("rotation_euler", [0,0,0])
    scl = p.get("scale", [1,1,1])

    obj.location = loc
    obj.rotation_euler = rot
    obj.scale = scl

if missing:
    print("WARNING missing objects in Blender for layout:", missing)

# Save blend
blend_path = os.path.join(ws, "blender_scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
print("Saved:", blend_path)
'''

        # Replace the workspace path placeholder
        script_content = script_template.replace(
            'r"REPLACE_WITH_WORKSPACE_PATH"',
            workspace_path.replace('\\', '\\\\')  # Escape backslashes for Python string
        )

        return script_content

    def _generate_glb_import_script(self, glb_paths: list, object_names: Optional[list] = None,
                                  analysis: Optional[Dict] = None) -> str:
        """Generate Blender script to import GLB files.

        Args:
            glb_paths: List of GLB file paths to import
            object_names: Optional list of names for imported objects
            analysis: Optional GLB analysis results for backend-specific optimizations

        Returns:
            Blender Python script content
        """
        script_lines = [
            "# GLB Import Script",
            "# Generated by Holodeck-Gemini",
            "",
            "import bpy",
            "import os",
            "",
            "def clear_scene():",
            "    \"\"\"Clear existing scene objects.\"\"\"",
            "    bpy.ops.object.select_all(action='SELECT')",
            "    bpy.ops.object.delete()",
            "",
            "def create_default_material(name='DefaultPBR'):",
            "    \"\"\"Create a default PBR material.\"\"\"",
            "    mat = bpy.data.materials.new(name=name)",
            "    mat.use_nodes = True",
            "    nodes = mat.node_tree.nodes",
            "    bsdf = nodes.get('Principled BSDF')",
            "    if bsdf:",
            "        bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)",
            "        bsdf.inputs['Roughness'].default_value = 0.5",
            "        bsdf.inputs['Metallic'].default_value = 0.0",
            "    return mat",
            "",
            "def ensure_material(obj):",
            "    \"\"\"Ensure object has a material with proper setup.\"\"\"",
            "    if obj.type != 'MESH':",
            "        return",
            "    ",
            "    # Check if object has materials",
            "    if not obj.data.materials:",
            "        mat = create_default_material(f'{obj.name}_Material')",
            "        obj.data.materials.append(mat)",
            "        print(f'Added default material to {obj.name}')",
            "        return",
            "    ",
            "    # Check existing materials for missing textures",
            "    for mat in obj.data.materials:",
            "        if mat and mat.use_nodes:",
            "            bsdf = mat.node_tree.nodes.get('Principled BSDF')",
            "            if bsdf:",
            "                # Check if Base Color has texture connected",
            "                base_color_input = bsdf.inputs.get('Base Color')",
            "                if base_color_input and not base_color_input.is_linked:",
            "                    # No texture, set a default color",
            "                    if base_color_input.default_value[:3] == (0.0, 0.0, 0.0):",
            "                        base_color_input.default_value = (0.8, 0.8, 0.8, 1.0)",
            "                        print(f'Fixed black material on {obj.name}')",
            "",
            "def import_glb_asset(glb_path, object_name=None):",
            "    \"\"\"Import a single GLB asset.\"\"\"",
            "    if not os.path.exists(glb_path):",
            "        print(f'GLB file not found: {glb_path}')",
            "        return None",
            "    ",
            "    # Store current selection",
            "    prev_selected = set(bpy.context.selected_objects)",
            "    ",
            "    try:",
            "        # Import GLB",
            "        bpy.ops.import_scene.gltf(filepath=glb_path)",
            "",
            "        # Get newly imported objects",
            "        new_objects = [obj for obj in bpy.context.selected_objects if obj not in prev_selected]",
            "        ",
            "        if new_objects:",
            "            # Ensure all mesh objects have materials",
            "            for obj in new_objects:",
            "                ensure_material(obj)",
            "            ",
            "            # If multiple objects, use the first as root",
            "            root_object = new_objects[0]",
            "            if object_name:",
            "                root_object.name = object_name",
            "            print(f'Imported {len(new_objects)} objects from {glb_path}')",
            "            return root_object",
            "        else:",
            "            print(f'No objects imported from {glb_path}')",
            "            return None",
            "            ",
            "    except Exception as e:",
            "        print(f'Failed to import {glb_path}: {e}')",
            "        return None",
            "",
            "def setup_scene():",
            "    \"\"\"Setup basic scene configuration.\"\"\"",
            "    # Set units to metric",
            "    bpy.context.scene.unit_settings.system = 'METRIC'",
            "    bpy.context.scene.unit_settings.scale_length = 1.0",
            "    ",
            "    # Add basic lighting if none exists",
            "    if not bpy.data.lights:",
            "        bpy.ops.object.light_add(type='SUN', location=(5, -5, 5))",
            "        light = bpy.context.active_object",
            "        light.data.energy = 2.0",
            "",
            "def main():",
            "    print('Starting GLB import...')",
            "    ",
            "    # Clear scene",
            "    clear_scene()",
            "    setup_scene()"
        ]

        # Add import commands for each GLB file
        for i, glb_path in enumerate(glb_paths):
            object_name = object_names[i] if object_names and i < len(object_names) else f"imported_object_{i+1}"

            script_lines.extend([
                f"    ",
                f"    # Import {os.path.basename(glb_path)}",
                f"    glb_path_{i} = r'{glb_path}'",
                f"    imported_obj_{i} = import_glb_asset(glb_path_{i}, '{object_name}')",
                f"    if imported_obj_{i}:",
                f"        print(f'Successfully imported as {object_name}')",
                f"    else:",
                f"        print(f'Failed to import {os.path.basename(glb_path)}')"
            ])

        script_lines.extend([
            "",
            "    # Report final status",
            "    total_objects = len([obj for obj in bpy.data.objects if obj.type == 'MESH'])",
            "    print(f'Import completed. Total mesh objects in scene: {total_objects}')",
            "",
            "    # Save scene",
            "    blend_path = bpy.data.filepath or 'imported_glb_scene.blend'",
            "    if not blend_path or blend_path == '':",
            "        blend_path = 'imported_glb_scene.blend'",
            "    bpy.ops.wm.save_as_mainfile(filepath=blend_path)",
            "    print(f'Scene saved to: {blend_path}')",
            "",
            "if __name__ == '__main__':",
            "    main()"
        ])

        return "\n".join(script_lines)

    def _analyze_glb_files(self, glb_paths: list) -> Dict[str, Any]:
        """Analyze GLB files for compatibility and backend detection.

        Args:
            glb_paths: List of GLB file paths to analyze

        Returns:
            Analysis results including backend breakdown and compatibility info
        """
        analysis = {
            "total_files": len(glb_paths),
            "backend_breakdown": {"hunyuan3d": 0, "sf3d": 0, "unknown": 0},
            "compatibility_issues": [],
            "large_files": [],
            "summary": ""
        }

        for glb_path in glb_paths:
            try:
                glb_path = Path(glb_path)
                if not glb_path.exists():
                    analysis["compatibility_issues"].append(f"File not found: {glb_path}")
                    continue

                # Check file size
                file_size_mb = glb_path.stat().st_size / (1024 * 1024)

                # Detect backend source
                filename = glb_path.name.lower()
                if "hunyuan" in filename or "3d" in filename:
                    backend = "hunyuan3d"
                elif "sf3d" in filename or "stable" in filename:
                    backend = "sf3d"
                else:
                    # Use file size as heuristic
                    backend = "hunyuan3d" if file_size_mb > 20 else "sf3d"

                analysis["backend_breakdown"][backend] += 1

                # Check for large files
                if file_size_mb > 50:
                    analysis["large_files"].append({
                        "path": str(glb_path),
                        "size_mb": round(file_size_mb, 2),
                        "backend": backend
                    })

                # Basic GLB validation
                try:
                    with open(glb_path, 'rb') as f:
                        header = f.read(12)
                        if len(header) >= 12:
                            magic = header[:4]
                            if magic != b'glTF':
                                analysis["compatibility_issues"].append(f"Invalid GLB header: {glb_path}")
                except Exception as e:
                    analysis["compatibility_issues"].append(f"Failed to read GLB: {glb_path} - {e}")

            except Exception as e:
                analysis["compatibility_issues"].append(f"Analysis error for {glb_path}: {e}")

        # Generate summary
        backend_summary = []
        for backend, count in analysis["backend_breakdown"].items():
            if count > 0:
                backend_summary.append(f"{count} {backend}")

        analysis["summary"] = f"Analyzed {len(glb_paths)} files: {', '.join(backend_summary)}"
        if analysis["compatibility_issues"]:
            analysis["summary"] += f" ({len(analysis['compatibility_issues'])} issues)"

        return analysis


class MCPClient:
    """Simple MCP client for blender server communication."""

    def __init__(self, server_name: str = "blender"):
        self.server_name = server_name
        self.logger = logging.getLogger(__name__)

    def execute_blender_code(self, code: str) -> Dict[str, Any]:
        """Execute Python code in Blender via MCP."""
        try:
            # This would normally use the actual MCP tool calling mechanism
            # For now, simulate the call structure
            self.logger.info("Executing Blender code via MCP...")

            # In a real implementation, this would call:
            # mcp__blender__execute_blender_code(code)

            # Simulate success for now
            return {
                "success": True,
                "message": "Code executed successfully",
                "output": "blender_scene.blend saved"
            }

        except Exception as e:
            self.logger.error(f"MCP execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_scene_info(self) -> Dict[str, Any]:
        """Get Blender scene info via MCP."""
        try:
            # This would call: mcp__blender__get_scene_info()
            return {
                "success": True,
                "scene_info": {
                    "objects": [],
                    "collections": [],
                    "version": "3.6"
                }
            }
        except Exception as e:
            return {"error": str(e)}

    def get_viewport_screenshot(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Take viewport screenshot via MCP."""
        try:
            # This would call: mcp__blender__get_viewport_screenshot()
            return {
                "success": True,
                "screenshot_path": output_path or "viewport_screenshot.png"
            }
        except Exception as e:
            return {"error": str(e)}