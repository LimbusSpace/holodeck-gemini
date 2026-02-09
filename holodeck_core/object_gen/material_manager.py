"""
Material Manager for Holodeck 3D Asset Generation

This module provides comprehensive material management for 3D assets including:
- PBR material creation and management
- Texture processing and optimization
- Material assignment and validation
- Blender integration for material handling
"""

import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np
from PIL import Image

# Import available schemas - MaterialSchema and TextureSchema will be defined locally if needed
from holodeck_core.storage import WorkspaceManager


class TextureType(Enum):
    """PBR texture types"""
    ALBEDO = "albedo"
    METALLIC = "metallic"
    ROUGHNESS = "roughness"
    NORMAL = "normal"
    HEIGHT = "height"
    AO = "ao"
    EMISSION = "emission"


class MaterialQuality(Enum):
    """Material quality levels"""
    LOW = "low"      # 512x512
    MEDIUM = "medium" # 1024x1024
    HIGH = "high"    # 2048x2048
    ULTRA = "ultra"  # 4096x4096


@dataclass
class TextureInfo:
    """Information about a texture map"""
    path: Path
    type: TextureType
    size: Tuple[int, int]
    channels: int
    format: str
    is_srgb: bool = False
    compression: Optional[str] = None


@dataclass
class MaterialInfo:
    """Information about a material"""
    id: str
    name: str
    textures: Dict[TextureType, TextureInfo] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    quality: MaterialQuality = MaterialQuality.MEDIUM
    created_at: str = ""
    modified_at: str = ""


class MaterialManager:
    """
    Manages PBR materials and textures for 3D assets
    """

    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace = workspace_manager
        self.logger = logging.getLogger(__name__)
        self.materials_dir = self.workspace.workspace_root / "materials"
        self.textures_dir = self.workspace.workspace_root / "textures"
        self.cache_dir = self.workspace.workspace_root / "cache" / "materials"

        # Create directories
        self.materials_dir.mkdir(parents=True, exist_ok=True)
        self.textures_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Material registry
        self.materials: Dict[str, MaterialInfo] = {}
        self._load_material_registry()

    def create_material(self, name: str, quality: MaterialQuality = MaterialQuality.MEDIUM) -> str:
        """
        Create a new material

        Args:
            name: Material name
            quality: Material quality level

        Returns:
            Material ID
        """
        material_id = str(uuid.uuid4())
        material = MaterialInfo(
            id=material_id,
            name=name,
            quality=quality,
            created_at=self._get_timestamp(),
            modified_at=self._get_timestamp()
        )

        self.materials[material_id] = material
        self._save_material_registry()

        self.logger.info(f"Created material: {name} (ID: {material_id})")
        return material_id

    def add_texture(self, material_id: str, texture_path: Path, texture_type: TextureType) -> bool:
        """
        Add a texture to a material

        Args:
            material_id: Material ID
            texture_path: Path to texture file
            texture_type: Type of texture

        Returns:
            Success status
        """
        if material_id not in self.materials:
            self.logger.error(f"Material {material_id} not found")
            return False

        if not texture_path.exists():
            self.logger.error(f"Texture file not found: {texture_path}")
            return False

        try:
            # Process and optimize texture
            processed_path = self._process_texture(texture_path, texture_type)

            # Get texture info
            with Image.open(processed_path) as img:
                texture_info = TextureInfo(
                    path=processed_path,
                    type=texture_type,
                    size=img.size,
                    channels=len(img.getbands()),
                    format=img.format or "UNKNOWN",
                    is_srgb=texture_type in [TextureType.ALBEDO, TextureType.EMISSION]
                )

            # Add to material
            self.materials[material_id].textures[texture_type] = texture_info
            self.materials[material_id].modified_at = self._get_timestamp()

            self._save_material_registry()
            self.logger.info(f"Added {texture_type.value} texture to material {material_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to add texture: {e}")
            return False

    def set_material_property(self, material_id: str, property_name: str, value: Any) -> bool:
        """
        Set a material property

        Args:
            material_id: Material ID
            property_name: Property name
            value: Property value

        Returns:
            Success status
        """
        if material_id not in self.materials:
            self.logger.error(f"Material {material_id} not found")
            return False

        self.materials[material_id].properties[property_name] = value
        self.materials[material_id].modified_at = self._get_timestamp()

        self._save_material_registry()
        return True

    def get_material(self, material_id: str) -> Optional[MaterialInfo]:
        """
        Get material information

        Args:
            material_id: Material ID

        Returns:
            MaterialInfo or None if not found
        """
        return self.materials.get(material_id)

    def list_materials(self) -> List[MaterialInfo]:
        """
        List all materials

        Returns:
            List of materials
        """
        return list(self.materials.values())

    def delete_material(self, material_id: str) -> bool:
        """
        Delete a material and its textures

        Args:
            material_id: Material ID

        Returns:
            Success status
        """
        if material_id not in self.materials:
            return False

        # Delete texture files
        material = self.materials[material_id]
        for texture_info in material.textures.values():
            try:
                if texture_info.path.exists():
                    texture_info.path.unlink()
            except Exception as e:
                self.logger.warning(f"Failed to delete texture {texture_info.path}: {e}")

        # Remove from registry
        del self.materials[material_id]
        self._save_material_registry()

        self.logger.info(f"Deleted material {material_id}")
        return True

    def optimize_textures(self, material_id: str, target_quality: MaterialQuality) -> bool:
        """
        Optimize all textures for a material to target quality

        Args:
            material_id: Material ID
            target_quality: Target quality level

        Returns:
            Success status
        """
        if material_id not in self.materials:
            return False

        material = self.materials[material_id]
        target_size = self._get_texture_size(target_quality)

        for texture_type, texture_info in material.textures.items():
            try:
                # Resize texture if needed
                if texture_info.size != target_size:
                    resized_path = self._resize_texture(texture_info.path, target_size)

                    # Update texture info
                    with Image.open(resized_path) as img:
                        material.textures[texture_type] = TextureInfo(
                            path=resized_path,
                            type=texture_type,
                            size=img.size,
                            channels=len(img.getbands()),
                            format=img.format or "UNKNOWN",
                            is_srgb=texture_info.is_srgb
                        )

            except Exception as e:
                self.logger.error(f"Failed to optimize texture {texture_type.value}: {e}")
                return False

        material.quality = target_quality
        material.modified_at = self._get_timestamp()
        self._save_material_registry()

        self.logger.info(f"Optimized textures for material {material_id} to {target_quality.value}")
        return True

    def generate_missing_textures(self, material_id: str) -> bool:
        """
        Generate missing PBR textures for a material

        Args:
            material_id: Material ID

        Returns:
            Success status
        """
        if material_id not in self.materials:
            return False

        material = self.materials[material_id]
        base_size = self._get_texture_size(material.quality)

        # Define default textures for missing types
        defaults = {
            TextureType.METALLIC: (128, 128, 128),  # Gray for non-metallic
            TextureType.ROUGHNESS: (192, 192, 192),  # Medium roughness
            TextureType.AO: (255, 255, 255),        # No occlusion
            TextureType.EMISSION: (0, 0, 0),         # No emission
        }

        for texture_type, default_color in defaults.items():
            if texture_type not in material.textures:
                try:
                    texture_path = self._generate_default_texture(
                        texture_type, base_size, default_color
                    )
                    self.add_texture(material_id, texture_path, texture_type)
                except Exception as e:
                    self.logger.error(f"Failed to generate {texture_type.value}: {e}")
                    return False

        # Generate normal map if missing (flat normal)
        if TextureType.NORMAL not in material.textures:
            try:
                normal_path = self._generate_default_texture(
                    TextureType.NORMAL, base_size, (128, 128, 255)
                )
                self.add_texture(material_id, normal_path, TextureType.NORMAL)
            except Exception as e:
                self.logger.error(f"Failed to generate normal map: {e}")
                return False

        self.logger.info(f"Generated missing textures for material {material_id}")
        return True

    def export_material(self, material_id: str, output_dir: Path) -> Optional[Path]:
        """
        Export material with all textures to a directory

        Args:
            material_id: Material ID
            output_dir: Output directory

        Returns:
            Path to exported material directory or None on failure
        """
        if material_id not in self.materials:
            return None

        material = self.materials[material_id]
        export_dir = output_dir / f"material_{material_id}"
        export_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy all textures
            exported_textures = {}
            for texture_type, texture_info in material.textures.items():
                if texture_info.path.exists():
                    dest_path = export_dir / f"{texture_type.value}{texture_info.path.suffix}"
                    shutil.copy2(texture_info.path, dest_path)
                    exported_textures[texture_type.value] = dest_path.name

            # Create material JSON
            material_data = {
                "id": material.id,
                "name": material.name,
                "quality": material.quality.value,
                "textures": exported_textures,
                "properties": material.properties,
                "created_at": material.created_at,
                "modified_at": material.modified_at
            }

            with open(export_dir / "material.json", "w") as f:
                json.dump(material_data, f, indent=2)

            self.logger.info(f"Exported material {material_id} to {export_dir}")
            return export_dir

        except Exception as e:
            self.logger.error(f"Failed to export material: {e}")
            return None

    def create_material_from_images(self, name: str, texture_paths: Dict[TextureType, Path],
                                  quality: MaterialQuality = MaterialQuality.MEDIUM) -> Optional[str]:
        """
        Create a material from a set of texture images

        Args:
            name: Material name
            texture_paths: Dictionary of texture type to file path
            quality: Material quality

        Returns:
            Material ID or None on failure
        """
        material_id = self.create_material(name, quality)

        for texture_type, texture_path in texture_paths.items():
            if not self.add_texture(material_id, texture_path, texture_type):
                self.logger.error(f"Failed to add {texture_type.value} texture")
                self.delete_material(material_id)
                return None

        self.logger.info(f"Created material from images: {name}")
        return material_id

    def _process_texture(self, texture_path: Path, texture_type: TextureType) -> Path:
        """
        Process and optimize a texture

        Args:
            texture_path: Input texture path
            texture_type: Type of texture

        Returns:
            Path to processed texture
        """
        # Create processed texture directory
        processed_dir = self.textures_dir / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        # Generate output path
        output_path = processed_dir / f"{texture_path.stem}_{texture_type.value}{texture_path.suffix}"

        try:
            with Image.open(texture_path) as img:
                # Convert to appropriate mode
                if texture_type in [TextureType.ALBEDO, TextureType.EMISSION]:
                    # sRGB textures
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                else:
                    # Linear textures (normal, roughness, metallic, etc.)
                    if img.mode == "RGBA":
                        # For normal maps with alpha, keep RGBA
                        pass
                    elif img.mode != "RGB":
                        img = img.convert("RGB")

                # Save optimized texture
                img.save(output_path, optimize=True, quality=95)

            return output_path

        except Exception as e:
            self.logger.error(f"Failed to process texture {texture_path}: {e}")
            raise

    def _resize_texture(self, texture_path: Path, target_size: Tuple[int, int]) -> Path:
        """
        Resize a texture to target size

        Args:
            texture_path: Input texture path
            target_size: Target (width, height)

        Returns:
            Path to resized texture
        """
        resized_dir = self.textures_dir / "resized"
        resized_dir.mkdir(parents=True, exist_ok=True)

        output_path = resized_dir / f"{texture_path.stem}_{target_size[0]}x{target_size[1]}{texture_path.suffix}"

        try:
            with Image.open(texture_path) as img:
                # Use LANCZOS for high-quality downsampling
                resized_img = img.resize(target_size, Image.Resampling.LANCZOS)
                resized_img.save(output_path, optimize=True, quality=95)

            return output_path

        except Exception as e:
            self.logger.error(f"Failed to resize texture: {e}")
            raise

    def _generate_default_texture(self, texture_type: TextureType, size: Tuple[int, int],
                                color: Tuple[int, int, int]) -> Path:
        """
        Generate a default texture

        Args:
            texture_type: Type of texture
            size: Texture size (width, height)
            color: RGB color tuple

        Returns:
            Path to generated texture
        """
        default_dir = self.textures_dir / "defaults"
        default_dir.mkdir(parents=True, exist_ok=True)

        output_path = default_dir / f"default_{texture_type.value}_{size[0]}x{size[1]}.png"

        try:
            # Create solid color image
            img = Image.new("RGB", size, color)
            img.save(output_path, optimize=True)

            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate default texture: {e}")
            raise

    def _get_texture_size(self, quality: MaterialQuality) -> Tuple[int, int]:
        """
        Get texture size for quality level

        Args:
            quality: Material quality

        Returns:
            (width, height) tuple
        """
        sizes = {
            MaterialQuality.LOW: (512, 512),
            MaterialQuality.MEDIUM: (1024, 1024),
            MaterialQuality.HIGH: (2048, 2048),
            MaterialQuality.ULTRA: (4096, 4096)
        }
        return sizes.get(quality, (1024, 1024))

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()

    def _load_material_registry(self):
        """Load material registry from disk"""
        registry_path = self.materials_dir / "registry.json"
        if not registry_path.exists():
            return

        try:
            with open(registry_path, "r") as f:
                data = json.load(f)

            for material_data in data.get("materials", []):
                material = MaterialInfo(
                    id=material_data["id"],
                    name=material_data["name"],
                    quality=MaterialQuality(material_data["quality"]),
                    properties=material_data.get("properties", {}),
                    created_at=material_data["created_at"],
                    modified_at=material_data["modified_at"]
                )

                # Load texture info
                for texture_type_str, texture_data in material_data.get("textures", {}).items():
                    texture_type = TextureType(texture_type_str)
                    texture_info = TextureInfo(
                        path=Path(texture_data["path"]),
                        type=texture_type,
                        size=tuple(texture_data["size"]),
                        channels=texture_data["channels"],
                        format=texture_data["format"],
                        is_srgb=texture_data.get("is_srgb", False)
                    )
                    material.textures[texture_type] = texture_info

                self.materials[material.id] = material

            self.logger.info(f"Loaded {len(self.materials)} materials from registry")

        except Exception as e:
            self.logger.error(f"Failed to load material registry: {e}")

    def _save_material_registry(self):
        """Save material registry to disk"""
        registry_path = self.materials_dir / "registry.json"

        try:
            data = {
                "materials": []
            }

            for material in self.materials.values():
                material_data = {
                    "id": material.id,
                    "name": material.name,
                    "quality": material.quality.value,
                    "properties": material.properties,
                    "created_at": material.created_at,
                    "modified_at": material.modified_at,
                    "textures": {}
                }

                for texture_type, texture_info in material.textures.items():
                    material_data["textures"][texture_type.value] = {
                        "path": str(texture_info.path),
                        "size": list(texture_info.size),
                        "channels": texture_info.channels,
                        "format": texture_info.format,
                        "is_srgb": texture_info.is_srgb
                    }

                data["materials"].append(material_data)

            with open(registry_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to save material registry: {e}")


# Blender integration functions
class BlenderMaterialManager:
    """
    Blender-specific material management
    """

    def __init__(self, material_manager: MaterialManager):
        self.material_manager = material_manager
        self.logger = logging.getLogger(__name__)

    def create_blender_material(self, material_id: str) -> Optional[str]:
        """
        Create a Blender material from material manager data

        Args:
            material_id: Material ID

        Returns:
            Blender material name or None on failure
        """
        try:
            import bpy
        except ImportError:
            self.logger.error("Blender Python module not available")
            return None

        material_info = self.material_manager.get_material(material_id)
        if not material_info:
            return None

        try:
            # Create new material
            blender_material = bpy.data.materials.new(name=material_info.name)
            blender_material.use_nodes = True
            nodes = blender_material.node_tree.nodes
            links = blender_material.node_tree.links

            # Clear default nodes
            nodes.clear()

            # Create principled BSDF
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
            bsdf.location = (0, 0)

            # Create output node
            output = nodes.new("ShaderNodeOutputMaterial")
            output.location = (400, 0)

            # Connect BSDF to output
            links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

            # Add texture nodes
            self._add_texture_nodes(blender_material, material_info, nodes, links, bsdf)

            self.logger.info(f"Created Blender material: {material_info.name}")
            return blender_material.name

        except Exception as e:
            self.logger.error(f"Failed to create Blender material: {e}")
            return None

    def _add_texture_nodes(self, blender_material, material_info: MaterialInfo,
                         nodes, links, bsdf):
        """Add texture nodes to Blender material"""

        # Starting position for texture nodes
        x_pos = -800
        y_pos = 300

        # Texture node mapping
        texture_inputs = {
            TextureType.ALBEDO: ("Base Color", False),
            TextureType.METALLIC: ("Metallic", False),
            TextureType.ROUGHNESS: ("Roughness", False),
            TextureType.NORMAL: ("Normal", False),
            TextureType.AO: ("Ambient Occlusion", False),
            TextureType.EMISSION: ("Emission", False),
        }

        for texture_type, texture_info in material_info.textures.items():
            if texture_type not in texture_inputs:
                continue

            if not texture_info.path.exists():
                continue

            try:
                # Create texture node
                tex_node = nodes.new("ShaderNodeTexImage")
                tex_node.location = (x_pos, y_pos)
                tex_node.image = bpy.data.images.load(str(texture_info.path))

                # Set color space
                if texture_info.is_srgb:
                    tex_node.image.colorspace_settings.name = "sRGB"
                else:
                    tex_node.image.colorspace_settings.name = "Non-Color"

                input_name, is_vector = texture_inputs[texture_type]

                if texture_type == TextureType.NORMAL:
                    # Add normal map node
                    normal_node = nodes.new("ShaderNodeNormalMap")
                    normal_node.location = (x_pos + 300, y_pos)
                    links.new(tex_node.outputs["Color"], normal_node.inputs["Color"])
                    links.new(normal_node.outputs["Normal"], bsdf.inputs["Normal"])
                elif texture_type == TextureType.AO:
                    # Mix AO with albedo using multiply
                    if TextureType.ALBEDO in material_info.textures:
                        mix_node = nodes.new("ShaderNodeMixRGB")
                        mix_node.blend_type = "MULTIPLY"
                        mix_node.inputs[0].default_value = 1.0
                        mix_node.location = (x_pos + 300, y_pos)

                        # Find albedo node and connect
                        for node in nodes:
                            if (node.type == "TEX_IMAGE" and
                                node.image and
                                node.image.filepath.endswith(str(TextureType.ALBEDO.value))):
                                links.new(node.outputs["Color"], mix_node.inputs[1])
                                break

                        links.new(tex_node.outputs["Color"], mix_node.inputs[2])
                        links.new(mix_node.outputs["Color"], bsdf.inputs["Base Color"])
                else:
                    # Direct connection
                    links.new(tex_node.outputs["Color"], bsdf.inputs[input_name])

                y_pos -= 300

            except Exception as e:
                self.logger.error(f"Failed to add {texture_type.value} texture node: {e}")

    def assign_material_to_object(self, object_name: str, material_id: str) -> bool:
        """
        Assign a material to a Blender object

        Args:
            object_name: Blender object name
            material_id: Material ID

        Returns:
            Success status
        """
        try:
            import bpy
        except ImportError:
            self.logger.error("Blender Python module not available")
            return False

        # Create or get Blender material
        blender_material_name = self.create_blender_material(material_id)
        if not blender_material_name:
            return False

        try:
            # Get object
            obj = bpy.data.objects.get(object_name)
            if not obj:
                self.logger.error(f"Object {object_name} not found")
                return False

            # Assign material
            if obj.data.materials:
                obj.data.materials[0] = bpy.data.materials[blender_material_name]
            else:
                obj.data.materials.append(bpy.data.materials[blender_material_name])

            self.logger.info(f"Assigned material {material_id} to object {object_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to assign material: {e}")
            return False


# Utility functions
def validate_material_textures(material_info: MaterialInfo) -> Dict[str, List[str]]:
    """
    Validate material textures and return issues

    Args:
        material_info: Material to validate

    Returns:
        Dictionary of texture types to list of issues
    """
    issues = {}

    # Required textures for PBR
    required_textures = [TextureType.ALBEDO, TextureType.METALLIC, TextureType.ROUGHNESS]

    for texture_type in required_textures:
        type_issues = []

        if texture_type not in material_info.textures:
            type_issues.append("Missing required texture")
        else:
            texture_info = material_info.textures[texture_type]

            # Check if file exists
            if not texture_info.path.exists():
                type_issues.append("Texture file not found")

            # Check dimensions
            if texture_info.size[0] != texture_info.size[1]:
                type_issues.append("Texture is not square")

            # Check power of 2
            if not (texture_info.size[0] & (texture_info.size[0] - 1) == 0):
                type_issues.append("Texture dimensions are not power of 2")

        if type_issues:
            issues[texture_type.value] = type_issues

    return issues


def create_procedural_material(material_manager: MaterialManager, name: str,
                             base_color: Tuple[float, float, float] = (0.8, 0.8, 0.8),
                             metallic: float = 0.0,
                             roughness: float = 0.5) -> str:
    """
    Create a simple procedural material without textures

    Args:
        material_manager: Material manager instance
        name: Material name
        base_color: RGB color (0-1 range)
        metallic: Metallic value (0-1)
        roughness: Roughness value (0-1)

    Returns:
        Material ID
    """
    material_id = material_manager.create_material(name)

    # Set properties
    material_manager.set_material_property(material_id, "base_color", base_color)
    material_manager.set_material_property(material_id, "metallic", metallic)
    material_manager.set_material_property(material_id, "roughness", roughness)

    # Generate default textures
    material_manager.generate_missing_textures(material_id)

    return material_id