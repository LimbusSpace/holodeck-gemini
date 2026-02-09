"""Blender integration module for Holodeck 3D scene generation system.

Implements Blender-based scene assembly and rendering as specified in GEMINI.md:
- Scene assembly from 3D assets and layout solution
- Camera pose management and rendering
- Material and lighting setup
- Batch rendering capabilities
"""

from .scene_assembler import SceneAssembler
from .render_engine import RenderEngine
from .camera_manager import CameraManager
from .material_manager import MaterialManager

__all__ = [
    'SceneAssembler',
    'RenderEngine',
    'CameraManager',
    'MaterialManager'
]