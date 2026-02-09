"""
Blender integration tests using pytest framework
"""

import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pytest
from PIL import Image

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from holodeck_core.object_gen.material_manager import (
    MaterialManager, BlenderMaterialManager, TextureType, MaterialQuality,
    create_procedural_material, validate_material_textures
)
from holodeck_core.storage import WorkspaceManager


@pytest.fixture
def material_manager():
    """Create a MaterialManager for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)
        workspace = WorkspaceManager(workspace_path)
        manager = MaterialManager(workspace)
        yield manager


@pytest.fixture
def test_textures():
    """Create test texture files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        texture_dir = Path(temp_dir) / "test_textures"
        texture_dir.mkdir(exist_ok=True)
        
        textures = {}

        # Create albedo texture (red color)
        albedo = Image.new("RGB", (512, 512), (200, 50, 50))
        albedo_path = texture_dir / "test_albedo.png"
        albedo.save(albedo_path)
        textures[TextureType.ALBEDO] = albedo_path
        
        # Create metallic texture (gray)
        metallic = Image.new("RGB", (512, 512), (128, 128, 128))
        metallic_path = texture_dir / "test_metallic.png"
        metallic.save(metallic_path)
        textures[TextureType.METALLIC] = metallic_path
        
        # Create roughness texture (medium gray)
        roughness = Image.new("RGB", (512, 512), (150, 150, 150))
        roughness_path = texture_dir / "test_roughness.png"
        roughness.save(roughness_path)
        textures[TextureType.ROUGHNESS] = roughness_path

        # Create normal map (flat blue)
        normal = Image.new("RGB", (512, 512), (128, 128, 255))
        normal_path = texture_dir / "test_normal.png"
        normal.save(normal_path)
        textures[TextureType.NORMAL] = normal_path

        yield textures


@pytest.mark.e2e
@pytest.mark.blender
@pytest.mark.slow
class TestBlenderIntegration:
    """Test Blender integration functionality"""
    
    def test_material_manager_creation(self, material_manager):
        """Test MaterialManager creation"""
        assert material_manager is not None

    def test_material_creation(self, material_manager):
        """Test material creation"""
        material_id = material_manager.create_material("Test Material", MaterialQuality.HIGH)
        assert material_id is not None

    def test_texture_addition(self, material_manager, test_textures):
        """Test adding textures to material"""
        material_id = material_manager.create_material("Test Material", MaterialQuality.HIGH)

        for texture_type, texture_path in test_textures.items():
            success = material_manager.add_texture(material_id, texture_path, texture_type)
            assert success, f"Failed to add {texture_type.value} texture"
            
    def test_material_retrieval(self, material_manager, test_textures):
        """Test material retrieval"""
        material_id = material_manager.create_material("Test Material", MaterialQuality.HIGH)

        # Add textures
        for texture_type, texture_path in test_textures.items():
            material_manager.add_texture(material_id, texture_path, texture_type)
            
        # Retrieve material
        material_info = material_manager.get_material(material_id)
        assert material_info is not None
        assert material_info.name == "Test Material"
        assert len(material_info.textures) == 4
        
    def test_blender_material_manager(self, material_manager):
        """Test BlenderMaterialManager"""
        blender_manager = BlenderMaterialManager(material_manager)
        assert blender_manager is not None

        # Test Blender availability
        try:
            import bpy
            blender_available = True
        except ImportError:
            blender_available = False
            pytest.skip("Blender Python module not available")
