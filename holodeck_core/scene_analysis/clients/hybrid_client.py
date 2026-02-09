"""Hybrid client with VLM primary and ComfyUI fallback.

Implements session-level backend locking to ensure consistency.
"""

import asyncio
import logging
import os
import base64
from typing import Any, Dict, List, Optional, Tuple, Union
from pathlib import Path
from .unified_vlm import UnifiedVLMClient, VLMBackend
from ..prompts.templates import PromptManager

logger = logging.getLogger(__name__)

# Demo mode - use mock data when no backends are available
DEMO_MODE = os.getenv('HOLODECK_DEMO_MODE', '').lower() in ('true', '1', 'yes')

# Minimal 1x1 PNG for demo purposes
DEMO_PNG_DATA = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\xcc\xdb\xb4\x00\x00\x00\x00IEND\xaeB`\x82').decode()


class SessionBackendLock:
    """Ensures session-level consistency by locking backend choice."""

    def __init__(self):
        """Initialize session backend lock."""
        self.session_backends = {}  # session_id -> backend_type
        self.backend_types = ["hunyuan", "apiyi", "vlm", "comfyui"]

    async def get_backend_for_session(
        self,
        session_id: str,
        operation: str,
        vlm_available: bool = True,
        hunyuan_available: bool = True,
        apiyi_available: bool = True
    ) -> str:
        """Get or determine backend for a session.

        Args:
            session_id: Session identifier
            operation: Operation type (helps with fallback decisions)
            vlm_available: Whether VLM is currently available
            hunyuan_available: Whether Hunyuan Image is currently available

        Returns:
            Backend type (强制返回 "apiyi")
        """
        # If session already locked, use stored backend
        if session_id in self.session_backends:
            logger.info(f"Using locked backend for session {session_id}: {self.session_backends[session_id]}")
            return self.session_backends[session_id]

        # 强制只使用 APIYI，移除所有其他选项
        if DEMO_MODE:
            backend = "demo"
            logger.warning(f"Demo mode forced for session {session_id}")
        else:
            backend = "apiyi"
            logger.info(f"强制锁定 session {session_id} 到 APIYI 后端 (唯一可用选项)")

        self.session_backends[session_id] = backend
        return backend

    def release_session(self, session_id: str):
        """Release session backend lock."""
        if session_id in self.session_backends:
            del self.session_backends[session_id]
            logger.info(f"Released backend lock for session {session_id}")

    def get_session_backend(self, session_id: str) -> Optional[str]:
        """Get current backend for session without changing it."""
        return self.session_backends.get(session_id)


class HybridAnalysisClient:
    """Hybrid client with intelligent backend selection and fallback."""

    def __init__(
        self,
        vlm_client: UnifiedVLMClient,
        comfyui_client,
        prompt_manager: PromptManager,
        fallback_enabled: bool = True,
        hunyuan_client = None
    ):
        """Initialize hybrid client.

        Args:
            vlm_client: Unified VLM client instance
            comfyui_client: ComfyUI client instance
            prompt_manager: Prompt template manager
            fallback_enabled: Whether to enable fallback
            hunyuan_client: Hunyuan Image client instance (optional)
        """
        self.vlm = vlm_client
        self.comfyui = comfyui_client
        self.hunyuan = hunyuan_client
        self.prompts = prompt_manager
        self.fallback_enabled = fallback_enabled
        self.session_lock = SessionBackendLock()

    async def test_vlm_availability(self) -> bool:
        """Test if VLM is available - 强制返回 False。"""
        logger.info("VLM 已被强制禁用，只使用 APIYI")
        return False

    async def test_hunyuan_availability(self) -> bool:
        """Test if Hunyuan Image is available - 强制返回 False。"""
        logger.info("Hunyuan Image 已被强制禁用，只使用 APIYI")
        return False

    async def test_apiyi_availability(self) -> bool:
        """Test if APIAYI is available - 强制检查 APIYI。"""
        try:
            from ...image_generation.unified_image_client import UnifiedImageClient
            apiyi_client = UnifiedImageClient()

            # Validate configuration first
            apiyi_client.validate_configuration()
            result = await apiyi_client.test_connection()
            logger.info("APIAYI 可用性检查通过")
            return result
        except Exception as e:
            logger.error(f"APIAYI 不可用: {e}")
            # 强制只使用 APIYI，如果不可用直接报错
            raise Exception(f"APIAYI 不可用，系统强制只使用 APIYI: {e}")

    async def generate_scene_reference(
        self,
        session_id: str,
        scene_text: str,
        style: str
    ) -> Any:  # SceneRefImage
        """Generate scene reference image with intelligent backend selection.

        Args:
            session_id: Session ID for consistency
            scene_text: Scene description
            style: Artistic style

        Returns:
            SceneRefImage object
        """
        backend = await self.session_lock.get_backend_for_session(
            session_id, "scene_ref",
            False,  # 禁用 VLM
            False,  # 禁用 Hunyuan
            await self.test_apiyi_availability()  # 只检查 APIYI
        )

        prompt = self.prompts.get_prompt("scene_reference", {
            "text": scene_text,
            "style": style
        })

        if backend == "demo":
            return await self._generate_with_demo(
                session_id, "scene_ref", prompt, style
            )
        elif backend == "apiyi":
            return await self._generate_with_apiyi(
                session_id, "scene_ref", prompt, style
            )
        else:
            # 强制只使用 APIYI，其他后端不应该被调用
            raise Exception(f"不支持的后端: {backend}，系统强制只使用 APIYI")

    async def extract_objects(
        self,
        session_id: str,
        scene_text: str,
        ref_image_path: Optional[str] = None
    ) -> Any:  # SceneData
        """Extract objects with backend consistency.

        Args:
            session_id: Session ID for consistency
            scene_text: Scene description
            ref_image_path: Path to reference image

        Returns:
            SceneData object
        """
        backend = await self.session_lock.get_backend_for_session(
            session_id, "object_extract",
            False,  # 禁用 VLM
            False,  # 禁用 Hunyuan
            await self.test_apiyi_availability()  # 只检查 APIYI
        )

        prompt = self.prompts.get_prompt("object_extraction", {
            "scene_text": scene_text
        })

        if backend == "apiyi":
            # Use APIYi for object extraction with enhanced Chinese support
            logger.info("Using APIYi for object extraction")
            return await self._extract_with_apiyi(scene_text, ref_image_path)
        else:
            # 强制只使用 APIYI，其他后端不应该被调用
            raise Exception(f"不支持的后端: {backend}，系统强制只使用 APIYI")

    async def generate_object_cards(
        self,
        session_id: str,
        objects: List[Dict[str, Any]],
        ref_image_path: str
    ) -> List[Any]:  # List[ObjectCard]
        """Generate object cards with session consistency.

        Args:
            session_id: Session ID
            objects: List of object definitions
            ref_image_path: Path to reference image

        Returns:
            List of ObjectCard objects
        """
        backend = await self.session_lock.get_backend_for_session(
            session_id, "object_cards",
            False,  # 禁用 VLM
            False,  # 禁用 Hunyuan
            await self.test_apiyi_availability()  # 只检查 APIYI
        )

        cards = []

        # Generate cards based on backend - 强制只使用 APIYI
        if backend == "apiyi":
            # Generate cards using APIYi
            for obj in objects:
                try:
                    card = await self._generate_single_card_apiyi(obj, ref_image_path, session_id)
                    cards.append(card)
                except Exception as e:
                    logger.error(f"APIYi card generation failed: {e}")
                    # 强制只使用 APIYI，如果失败直接抛出异常
                    raise Exception(f"APIYi card generation failed and no fallback available: {e}")
        else:
            # 强制只使用 APIYI，其他后端不应该被调用
            raise Exception(f"不支持的后端: {backend}，系统强制只使用 APIYI")

        return cards

    async def generate_background_texture(
        self,
        session_id: str,
        ref_image_path: str
    ) -> Any:  # BackgroundImage
        """Generate background texture with consistency.

        Args:
            session_id: Session ID
            ref_image_path: Path to reference image

        Returns:
            BackgroundImage object
        """
        backend = await self.session_lock.get_backend_for_session(
            session_id, "background",
            False,  # 禁用 VLM
            False,  # 禁用 Hunyuan
            await self.test_apiyi_availability()  # 只检查 APIYI
        )

        if backend == "apiyi":
            # Use APIYi for background texture generation
            logger.info("Using APIYi for background texture generation")
            # 这里可以实现 APIYi 的背景纹理生成逻辑
            # 目前暂时使用 ComfyUI 作为占位符，但应该替换为 APIYi 实现
            return await self._extract_background_comfyui(ref_image_path, session_id)
        else:
            # 强制只使用 APIYI，其他后端不应该被调用
            raise Exception(f"不支持的后端: {backend}，系统强制只使用 APIYI")

    async def _generate_with_vlm(
        self,
        session_id: str,
        operation: str,
        prompt: str,
        style: Optional[str] = None
    ) -> Any:
        """Generate using VLM - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("VLM 已被强制禁用，系统只使用 APIYI")

    async def _generate_with_comfyui(
        self,
        session_id: str,
        operation: str,
        prompt: str,
        style: Optional[str] = None
    ) -> Any:
        """Generate using ComfyUI - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("ComfyUI 已被强制禁用，系统只使用 APIYI")

    async def _generate_with_apiyi(
        self,
        session_id: str,
        operation: str,
        prompt: str,
        style: Optional[str] = None
    ) -> Any:
        """Generate using APIAYI."""
        try:
            from pathlib import Path
            import tempfile
            from holodeck_core.schemas import SceneRefImage
            from ...image_generation.unified_image_client import UnifiedImageClient

            # Create APIAYI client
            apiyi_client = UnifiedImageClient()

            # Create output directory
            output_dir = Path(tempfile.gettempdir()) / "holodeck_apiyi"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate image using APIAYI
            generation_result = await apiyi_client.generate_image(
                prompt=prompt,
                resolution="1024:1024",
                style=style,
                output_path=output_dir / f"{session_id}_{operation}.png"
            )

            # Convert to SceneRefImage format
            scene_ref_image = SceneRefImage(
                image_path=str(generation_result.data),
                prompt_used=prompt,
                style=style or "realistic",
                generation_time=generation_result.metadata.get("generation_time", 0.0)
            )

            logger.info(f"APIAYI生成场景参考图: {scene_ref_image.image_path}")
            return scene_ref_image

        except Exception as e:
            logger.error(f"APIAYI生成失败: {e}")
            raise

    async def _generate_single_card_vlm(
        self,
        obj: Dict[str, Any],
        ref_image_path: str
    ) -> Any:
        """Generate single object card using VLM - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("VLM 已被强制禁用，系统只使用 APIYI")

    async def _generate_single_card_comfyui(
        self,
        obj: Dict[str, Any],
        ref_image_path: str
    ) -> Any:
        """Generate single object card using ComfyUI - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("ComfyUI 已被强制禁用，系统只使用 APIYI")

    async def _generate_with_hunyuan(
        self,
        session_id: str,
        operation: str,
        prompt: str,
        style: Optional[str] = None
    ) -> Any:
        """Generate using Hunyuan Image - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("Hunyuan Image 已被强制禁用，系统只使用 APIYI")

    async def _generate_single_card_hunyuan(
        self,
        obj: Dict[str, Any],
        ref_image_path: str
    ) -> Any:
        """Generate single object card using Hunyuan Image - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("Hunyuan Image 已被强制禁用，系统只使用 APIYI")

    async def _extract_with_comfyui(
        self,
        scene_text: str,
        ref_image_path: Optional[str]
    ) -> Any:
        """Extract objects using ComfyUI - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("ComfyUI 已被强制禁用，系统只使用 APIYI")

    async def _extract_with_apiyi(
        self,
        scene_text: str,
        ref_image_path: Optional[str]
    ) -> Any:
        """Extract objects using UnifiedVLMClient (GLM4.6V) for intelligent extraction."""
        from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient
        from pathlib import Path

        logger.info(f"Extracting objects: {scene_text[:50]}...")

        vlm_client = UnifiedVLMClient()

        image_bytes = None
        if ref_image_path and Path(ref_image_path).exists():
            image_bytes = Path(ref_image_path).read_bytes()

        scene_data = await vlm_client.extract_objects(scene_text, image_bytes)
        logger.info(f"Extracted {len(scene_data.objects)} objects")
        return scene_data

    async def _extract_background_comfyui(
        self,
        ref_image_path: str,
        session_id: str
    ) -> Any:
        """Extract background using ComfyUI - 此方法已被禁用，强制只使用 APIYI。"""
        raise Exception("ComfyUI 已被强制禁用，系统只使用 APIYI")

    async def _generate_with_demo(
        self,
        session_id: str,
        operation: str,
        prompt: str,
        style: Optional[str] = None
    ) -> Any:
        """Generate using demo mode (mock data)."""
        try:
            from pathlib import Path
            import tempfile
            from holodeck_core.schemas import SceneRefImage
            import time

            # Create demo output directory
            output_dir = Path(tempfile.gettempdir()) / "holodeck_demo"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create demo image file
            output_path = output_dir / f"{session_id}_{operation}.png"

            # Write demo PNG data to file
            with open(output_path, 'wb') as f:
                f.write(base64.b64decode(DEMO_PNG_DATA))

            # Create SceneRefImage object
            scene_ref_image = SceneRefImage(
                image_path=str(output_path),
                prompt_used=prompt,
                style=style or "modern",
                generation_time=0.001  # Mock generation time
            )

            logger.info(f"Demo mode: Generated scene reference image: {output_path}")
            return scene_ref_image

        except Exception as e:
            logger.error(f"Demo mode generation failed: {e}")
            raise

    async def _generate_single_card_apiyi(
        self,
        obj: Dict[str, Any],
        ref_image_path: str,
        session_id: str
    ) -> Any:  # ObjectCard
        """Generate single object card using APIYi."""
        from holodeck_core.schemas.object_cards import ObjectCard
        import time
        import os
        from pathlib import Path

        start_time = time.time()

        try:
            # Create prompt for object card generation (Paper Prompt 3 format)
            object_name = obj.get("name", "object")
            style = obj.get("style", "realistic")

            # Paper Prompt 3: isolated front-view with transparent background
            prompt = (
                f"Please generate ONE PNG image of an isolated front-view {object_name} "
                f"with a transparent background, in {style} style, "
                f"with shapes and style similar to the reference scene."
            )

            # Setup output path
            session_dir = Path(f"workspace/sessions/{session_id}")
            object_cards_dir = session_dir / "object_cards"
            object_cards_dir.mkdir(parents=True, exist_ok=True)
            card_image_path = object_cards_dir / f"{obj['object_id']}.png"

            # Import APIYi client
            from ...image_generation.unified_image_client import UnifiedImageClient
            apiyi_client = UnifiedImageClient()

            # Generate image using APIYi with reference image
            result = await apiyi_client.generate_image(
                prompt=prompt,
                resolution="1024:1024",
                style=style,
                reference_image=ref_image_path,
                output_path=str(card_image_path)
            )

            if not result.success:
                raise Exception(f"APIYi image generation failed: {result.error}")

            generation_time = time.time() - start_time
            card = ObjectCard(
                object_id=obj.get("object_id", "unknown"),
                object_name=object_name,
                card_image_path=str(card_image_path),
                prompt_used=prompt,
                generation_time=generation_time,
                qc_status="approved"
            )
            logger.info(f"Generated APIYi object card: {card_image_path}")
            return card

        except Exception as e:
            logger.error(f"APIYi object card generation failed for {obj.get('object_id', 'unknown')}: {e}")
            raise