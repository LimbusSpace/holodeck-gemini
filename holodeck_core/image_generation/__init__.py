"""Image generation module using ComfyUI and Hunyuan Image.

This module provides integration with local ComfyUI instance and
Tencent Cloud Hunyuan Image 3.0 for text-to-image generation in the HOLODECK 2.0 pipeline.

Optimized Hunyuan Image client provides concurrency control and retry mechanisms
to handle API rate limits and improve reliability.
"""

from .comfyui_client import ComfyUIClient
from .workflows import SCENE_REF_WORKFLOW, OBJECT_CARD_WORKFLOW
from .image_manager import ImageManager
from .hunyuan_image_client import HunyuanImageClient, generate_scene_reference, generate_object_card
from .hunyuan_image_client_optimized import (
    HunyuanImageClientOptimized,
    GenerationTask,
    GenerationResult,
    create_optimized_client_from_env,
    generate_batch_images
)

__all__ = [
    "ComfyUIClient",
    "SCENE_REF_WORKFLOW",
    "OBJECT_CARD_WORKFLOW",
    "ImageManager",
    "HunyuanImageClient",  # Legacy client
    "generate_scene_reference",
    "generate_object_card",
    # Optimized client
    "HunyuanImageClientOptimized",
    "GenerationTask",
    "GenerationResult",
    "create_optimized_client_from_env",
    "generate_batch_images"
]