"""Material management for Blender scene materials.

Implements material handling and optimization based on HOLODECK 2.0:
- Material assignment and consistency
- PBR material optimization
- Style-based material selection
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class MaterialDefinition:
    """Material definition for Blender materials."""
    name: str
    type: str  # "principled", "glossy", "diffuse", etc.
    parameters: Dict[str, Any]
    style_tags: List[str]


class MaterialManager:
    """Manages materials for Blender scene objects."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Define material library
        self.material_library = self._create_material_library()

        # Style-based material mappings
        self.style_materials = {
            "modern": ["modern_wood", "modern_metal", "modern_glass", "modern_fabric"],
            "rustic": ["rustic_wood", "rustic_stone", "rustic_metal", "rustic_fabric"],
            "minimalist": ["minimalist_white", "minimalist_gray", "minimalist_black"],
            "industrial": ["industrial_metal", "industrial_concrete", "industrial_wood"],
            "cyberpunk": ["cyber_metal", "cyber_glass", "neon_emission", "tech_plastic"]
        }

    def _create_material_library(self) -> Dict[str, MaterialDefinition]:
        """Create library of predefined materials."""
        return {
            # Modern materials
            "modern_wood": MaterialDefinition(
                name="Modern Wood",
                type="principled",
                parameters={
                    "Base Color": (0.6, 0.4, 0.2, 1.0),
                    "Roughness": 0.3,
                    "Metallic": 0.0,
                    "Specular": 0.2
                },
                style_tags=["modern", "wood", "natural"]
            ),
            "modern_metal": MaterialDefinition(
                name="Modern Metal",
                type="principled",
                parameters={
                    "Base Color": (0.8, 0.8, 0.8, 1.0),
                    "Roughness": 0.1,
                    "Metallic": 0.9,
                    "Specular": 0.5
                },
                style_tags=["modern", "metal", "reflective"]
            ),
            "modern_glass": MaterialDefinition(
                name="Modern Glass",
                type="principled",
                parameters={
                    "Base Color": (0.9, 0.95, 1.0, 1.0),
                    "Roughness": 0.0,
                    "Metallic": 0.0,
                    "Specular": 0.5,
                    "Transmission": 0.95,
                    "IOR": 1.45
                },
                style_tags=["modern", "glass", "transparent"]
            ),
            "modern_fabric": MaterialDefinition(
                name="Modern Fabric",
                type="principled",
                parameters={
                    "Base Color": (0.3, 0.3, 0.4, 1.0),
                    "Roughness": 0.8,
                    "Metallic": 0.0,
                    "Specular": 0.1
                },
                style_tags=["modern", "fabric", "soft"]
            ),

            # Rustic materials
            "rustic_wood": MaterialDefinition(
                name="Rustic Wood",
                type="principled",
                parameters={
                    "Base Color": (0.4, 0.3, 0.2, 1.0),
                    "Roughness": 0.7,
                    "Metallic": 0.0,
                    "Specular": 0.1
                },
                style_tags=["rustic", "wood", "natural", "rough"]
            ),
            "rustic_stone": MaterialDefinition(
                name="Rustic Stone",
                type="principled",
                parameters={
                    "Base Color": (0.5, 0.5, 0.45, 1.0),
                    "Roughness": 0.9,
                    "Metallic": 0.0,
                    "Specular": 0.2
                },
                style_tags=["rustic", "stone", "natural", "rough"]
            ),

            # Minimalist materials
            "minimalist_white": MaterialDefinition(
                name="Minimalist White",
                type="principled",
                parameters={
                    "Base Color": (0.95, 0.95, 0.95, 1.0),
                    "Roughness": 0.2,
                    "Metallic": 0.0,
                    "Specular": 0.3
                },
                style_tags=["minimalist", "white", "clean"]
            ),
            "minimalist_gray": MaterialDefinition(
                name="Minimalist Gray",
                type="principled",
                parameters={
                    "Base Color": (0.6, 0.6, 0.6, 1.0),
                    "Roughness": 0.3,
                    "Metallic": 0.0,
                    "Specular": 0.2
                },
                style_tags=["minimalist", "gray", "neutral"]
            ),

            # Cyberpunk materials
            "cyber_metal": MaterialDefinition(
                name="Cyber Metal",
                type="principled",
                parameters={
                    "Base Color": (0.2, 0.8, 1.0, 1.0),
                    "Roughness": 0.1,
                    "Metallic": 0.9,
                    "Specular": 0.8
                },
                style_tags=["cyberpunk", "metal", "neon", "tech"]
            ),
            "neon_emission": MaterialDefinition(
                name="Neon Emission",
                type="emission",
                parameters={
                    "Color": (0.0, 1.0, 0.5, 1.0),
                    "Strength": 5.0
                },
                style_tags=["cyberpunk", "emission", "neon", "glow"]
            )
        }

    def assign_materials_to_scene(self, objects_data: Dict[str, Any],
                                 scene_style: str = "modern") -> Dict[str, Any]:
        """Assign materials to scene objects based on style and object type.

        Args:
            objects_data: Scene objects data
            scene_style: Overall scene style

        Returns:
            Updated objects data with material assignments
        """
        try:
            self.logger.info(f"Assigning materials for {scene_style} style scene")

            updated_objects = objects_data.copy()

            for obj in updated_objects.get("objects", []):
                # Determine appropriate material
                material_name = self._select_material_for_object(obj, scene_style)

                if material_name:
                    # Add material assignment
                    if "materials" not in obj:
                        obj["materials"] = []

                    obj["materials"] = [material_name]

                    # Add material properties for rendering
                    material_def = self.material_library.get(material_name)
                    if material_def:
                        obj["material_properties"] = material_def.parameters

            self.logger.info(f"Assigned materials to {len(updated_objects.get('objects', []))} objects")
            return updated_objects

        except Exception as e:
            self.logger.error(f"Material assignment failed: {e}")
            return objects_data

    def _select_material_for_object(self, obj: Dict[str, Any], scene_style: str) -> Optional[str]:
        """Select appropriate material for an object."""
        try:
            obj_category = obj.get("category", "furniture")
            visual_desc = obj.get("visual_desc", "").lower()

            # Get style-appropriate materials
            style_materials = self.style_materials.get(scene_style, [])

            # Material selection logic based on object category and description
            material_candidates = []

            # Check visual description for material hints
            if "wood" in visual_desc or "wooden" in visual_desc:
                material_candidates.extend([m for m in style_materials if "wood" in m])
            elif "metal" in visual_desc or "steel" in visual_desc or "iron" in visual_desc:
                material_candidates.extend([m for m in style_materials if "metal" in m])
            elif "glass" in visual_desc or "transparent" in visual_desc:
                material_candidates.extend([m for m in style_materials if "glass" in m])
            elif "fabric" in visual_desc or "cloth" in visual_desc or "cushion" in visual_desc:
                material_candidates.extend([m for m in style_materials if "fabric" in m])
            elif "stone" in visual_desc or "concrete" in visual_desc or "marble" in visual_desc:
                material_candidates.extend([m for m in style_materials if "stone" in m])

            # Category-based selection
            if not material_candidates:
                if obj_category == "furniture":
                    material_candidates.extend([m for m in style_materials if "wood" in m or "fabric" in m])
                elif obj_category == "lighting":
                    material_candidates.extend([m for m in style_materials if "metal" in m or "glass" in m])
                elif obj_category == "electronics":
                    material_candidates.extend([m for m in style_materials if "metal" in m or "plastic" in m])

            # Fallback to first style material
            if not material_candidates and style_materials:
                material_candidates = [style_materials[0]]

            # Return best candidate
            if material_candidates:
                return material_candidates[0]

            return None

        except Exception as e:
            self.logger.warning(f"Material selection failed for object: {e}")
            return None

    def generate_material_script(self, objects_data: Dict[str, Any],
                               scene_style: str) -> str:
        """Generate Blender Python script for material assignment."""

        script_lines = [
            "# Blender material assignment script",
            "# Generated by Holodeck-Gemini",
            "",
            "import bpy",
            "import math",
            "",
            "def create_principled_material(name, params):",
            "    \"\"\"Create a Principled BSDF material.\"\"\"",
            "    mat = bpy.data.materials.new(name=name)",
            "    mat.use_nodes = True",
            "    nodes = mat.node_tree.nodes",
            "    links = mat.node_tree.links",
            "",
            "    # Clear default nodes",
            "    nodes.clear()",
            "",
            "    # Create Principled BSDF node",
            "    bsdf = nodes.new('ShaderNodeBsdfPrincipled')",
            "    output = nodes.new('ShaderNodeOutputMaterial')",
            "",
            "    # Connect nodes",
            "    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])",
            "",
            "    # Set parameters",
            "    for param_name, value in params.items():",
            "        if hasattr(bsdf.inputs.get(param_name, None), 'default_value'):",
            "            bsdf.inputs[param_name].default_value = value",
            "",
            "    return mat",
            "",
            "def create_emission_material(name, params):",
            "    \"\"\"Create an emission material.\"\"\"",
            "    mat = bpy.data.materials.new(name=name)",
            "    mat.use_nodes = True",
            "    nodes = mat.node_tree.nodes",
            "    links = mat.node_tree.links",
            "",
            "    # Clear default nodes",
            "    nodes.clear()",
            "",
            "    # Create emission nodes",
            "    emission = nodes.new('ShaderNodeEmission')",
            "    output = nodes.new('ShaderNodeOutputMaterial')",
            "",
            "    # Connect nodes",
            "    links.new(emission.outputs['Emission'], output.inputs['Surface'])",
            "",
            "    # Set parameters",
            "    emission.inputs['Color'].default_value = params.get('Color', (1, 1, 1, 1))",
            "    emission.inputs['Strength'].default_value = params.get('Strength', 1.0)",
            "",
            "    return mat",
            "",
            "def assign_material_to_object(obj_name, material):",
            "    \"\"\"Assign material to object.\"\"\"",
            "    obj = bpy.data.objects.get(obj_name)",
            "    if obj:",
            "        # Clear existing materials",
            "        obj.data.materials.clear()",
            "        # Assign new material",
            "        obj.data.materials.append(material)",
            "        print(f'Assigned material to {obj_name}')",
            "    else:",
            "        print(f'Object {obj_name} not found')",
            "",
            "def main():"
        ]

        # Add material creation and assignment
        objects = objects_data.get("objects", [])

        for obj in objects:
            obj_id = obj.get("object_id")
            materials = obj.get("materials", [])

            if materials:
                material_name = materials[0]
                material_def = self.material_library.get(material_name)

                if material_def:
                    script_lines.extend([
                        f"    # Create material: {material_name}",
                        f"    params = {material_def.parameters}",
                    ])

                    if material_def.type == "principled":
                        script_lines.append(f"    mat = create_principled_material('{material_name}', params)")
                    elif material_def.type == "emission":
                        script_lines.append(f"    mat = create_emission_material('{material_name}', params)")

                    script_lines.extend([
                        f"    assign_material_to_object('{obj_id}', mat)",
                        ""
                    ])

        script_lines.extend([
            "    print('Material assignment completed')",
            "",
            "if __name__ == '__main__':",
            "    main()"
        ])

        return "\n".join(script_lines)

    def optimize_materials_for_render(self, objects_data: Dict[str, Any],
                                    render_config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize materials for specific render settings."""
        try:
            self.logger.info("Optimizing materials for render settings")

            optimized_objects = objects_data.copy()

            # Get render quality settings
            samples = render_config.get("samples", 1024)
            use_gpu = render_config.get("use_gpu", True)

            for obj in optimized_objects.get("objects", []):
                # TODO: Implement material optimization for render settings
                pass

            return optimized_objects

        except Exception as e:
            self.logger.error(f"Error optimizing materials: {e}")
            return objects_data