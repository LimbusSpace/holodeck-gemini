"""Object Generation module for Holodeck 2.0.

This module handles 3D asset generation from object cards using multiple backends:
- ComfyUI Stable Fast 3D
- Tencent Hunyuan 3D API
"""

from .cache import ImageHashCache
from .sf3d_client import SF3DClient
from .hunyuan_3d_client import Hunyuan3DClient, Hunyuan3DTask, Hunyuan3DResult
from .asset_manager import AssetGenerationManager
from .normalizers import GLBNormalizer
from .asset_generator import AssetGenerator
from .backend_selector import BackendSelector, get_backend_selector, get_optimal_backend, is_backend_available, get_backend_info

__all__ = [
    "ImageHashCache",
    "SF3DClient",
    "Hunyuan3DClient",
    "Hunyuan3DTask",
    "Hunyuan3DResult",
    "AssetGenerationManager",
    "GLBNormalizer",
    "AssetGenerator",
    "BackendSelector",
    "get_backend_selector",
    "get_optimal_backend",
    "is_backend_available",
    "get_backend_info"
]