"""Scene Analysis module for Holodeck 2.0.

This module implements Scene Analysis pipeline from HOLODECK 2.0 paper:
- Scene reference image generation (GPT-Image-1)
- Object extraction from text and scene reference (GPT-o1/o3)
- Object card generation with quality control
- Background extraction for floor texture
"""

from .clients.unified_vlm import UnifiedVLMClient, VLMBackend, CustomVLMClient
from .scene_analyzer import SceneAnalyzer
from .prompt_templates import (
    PromptTemplateManager,
    get_reference_image_prompt,
    get_object_image_prompt
)

__all__ = [
    "UnifiedVLMClient",
    "VLMBackend",
    "CustomVLMClient",
    "SceneAnalyzer",
    "PromptTemplateManager",
    "get_reference_image_prompt",
    "get_object_image_prompt"
]