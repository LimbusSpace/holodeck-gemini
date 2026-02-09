#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VLM Client Adapters for Factory Architecture

Provides adapter classes to integrate existing VLM clients into the new
factory pattern architecture while maintaining backward compatibility.
"""

import abc
from typing import Dict, Any, Optional, List
from pathlib import Path

from holodeck_core.clients.base import BaseClient, GenerationResult, ServiceType
from holodeck_core.schemas.scene_objects import SceneData
from holodeck_core.config.base import ConfigManager
from holodeck_core.logging.standardized import get_logger

# Import existing VLM clients
# Legacy clients have been removed, these adapters are no longer needed
# All functionality is now provided through UnifiedVLMClient


class BaseVLMAdapter(BaseClient):
    """
    Base adapter class for VLM clients to integrate with factory architecture.

    This adapter provides the standard BaseClient interface while wrapping
    the existing VLM client implementations.
    """

    def __init__(
        self,
        legacy_client,
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Any] = None
    ):
        """
        Initialize VLM adapter.

        Args:
            legacy_client: Existing VLM client instance
            config_manager: Configuration manager
            logger: Logger instance
        """
        super().__init__(config_manager, logger)
        self.legacy_client = legacy_client

    def get_service_type(self) -> ServiceType:
        return ServiceType.HYBRID

    def validate_configuration(self) -> bool:
        """Validate adapter configuration."""
        if not self.legacy_client:
            raise Exception("Legacy client is required")
        return True

    async def extract_objects(
        self,
        scene_text: str,
        reference_image: Optional[bytes] = None
    ) -> SceneData:
        """
        Extract objects using the wrapped legacy client.

        Args:
            scene_text: Scene description text
            reference_image: Optional reference image bytes

        Returns:
            SceneData object with extracted objects
        """
        return await self.legacy_client.extract_objects(scene_text, reference_image)

    async def generate_scene_image(
        self,
        prompt: str,
        style: str = "realistic",
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> GenerationResult:
        """
        Generate scene image using the wrapped legacy client.

        Args:
            prompt: Scene description prompt
            style: Artistic style
            size: Image size
            quality: Image quality

        Returns:
            GenerationResult with image data
        """
        image_bytes, metadata = await self.legacy_client.generate_scene_image(
            prompt, style, size, quality
        )

        return GenerationResult(
            success=True,
            data=image_bytes,
            metadata=metadata
        )


class OpenAIVLMAdapter(BaseVLMAdapter):
    """
    Adapter for OpenAI VLM client to work with factory architecture.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Any] = None
    ):
        """
        Initialize OpenAI VLM adapter.

        Args:
            api_key: OpenAI API key
            config_manager: Configuration manager
            logger: Logger instance
        """
        legacy_client = LegacyOpenAIClient(api_key) if api_key else None
        super().__init__(legacy_client, config_manager, logger)
        self.api_key = api_key

    def validate_configuration(self) -> bool:
        """Validate OpenAI configuration."""
        if not self.api_key:
            raise Exception("OpenAI API key is required")

        if not self.legacy_client:
            raise Exception("Failed to initialize OpenAI client")

        return True

    async def test_connection(self) -> bool:
        """Test OpenAI connection."""
        if not self.legacy_client:
            return False
        return await self.legacy_client.test_connection()


class SiliconFlowVLMAdapter(BaseVLMAdapter):
    """
    Adapter for SiliconFlow VLM client to work with factory architecture.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Any] = None
    ):
        """
        Initialize SiliconFlow VLM adapter.

        Args:
            api_key: SiliconFlow API key
            config_manager: Configuration manager
            logger: Logger instance
        """
        legacy_client = LegacySiliconFlowClient(api_key) if api_key else None
        super().__init__(legacy_client, config_manager, logger)
        self.api_key = api_key

    def validate_configuration(self) -> bool:
        """Validate SiliconFlow configuration."""
        if not self.api_key:
            raise Exception("SiliconFlow API key is required")

        if not self.legacy_client:
            raise Exception("Failed to initialize SiliconFlow client")

        return True

    async def test_connection(self) -> bool:
        """Test SiliconFlow connection."""
        if not self.legacy_client:
            return False
        return await self.legacy_client.test_connection()


class HunyuanVLMAdapter(BaseVLMAdapter):
    """
    Adapter for Hunyuan VLM client.

    Note: Hunyuan doesn't support object extraction, so this adapter
    provides limited functionality with appropriate fallbacks.
    """

    def __init__(
        self,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[Any] = None
    ):
        """
        Initialize Hunyuan VLM adapter.

        Args:
            secret_id: Hunyuan Secret ID
            secret_key: Hunyuan Secret Key
            config_manager: Configuration manager
            logger: Logger instance
        """
        # Import here to avoid circular imports
        try:
            from holodeck_core.image_generation.hunyuan_image_client import HunyuanImageClient
            legacy_client = HunyuanImageClient(
                secret_id=secret_id,
                secret_key=secret_key
            ) if secret_id and secret_key else None
        except ImportError:
            legacy_client = None

        super().__init__(legacy_client, config_manager, logger)
        self.secret_id = secret_id
        self.secret_key = secret_key

    def validate_configuration(self) -> bool:
        """Validate Hunyuan configuration."""
        if not self.secret_id or not self.secret_key:
            raise Exception("Hunyuan Secret ID and Secret Key are required")

        if not self.legacy_client:
            raise Exception("Failed to initialize Hunyuan client")

        return True

    async def extract_objects(
        self,
        scene_text: str,
        reference_image: Optional[bytes] = None
    ) -> SceneData:
        """
        Hunyuan doesn't support object extraction.
        Raise appropriate error to trigger fallback.
        """
        raise Exception("Hunyuan does not support object extraction. Use fallback client.")

    async def test_connection(self) -> bool:
        """Test Hunyuan connection."""
        if not self.legacy_client:
            return False
        return self.legacy_client.test_connection()


# Factory functions for easy integration
def create_openai_vlm_adapter(api_key: Optional[str] = None) -> OpenAIVLMAdapter:
    """Create OpenAI VLM adapter."""
    import os
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    return OpenAIVLMAdapter(api_key=api_key)


def create_siliconflow_vlm_adapter(api_key: Optional[str] = None) -> SiliconFlowVLMAdapter:
    """Create SiliconFlow VLM adapter."""
    import os
    api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
    return SiliconFlowVLMAdapter(api_key=api_key)


def create_hunyuan_vlm_adapter(
    secret_id: Optional[str] = None,
    secret_key: Optional[str] = None
) -> HunyuanVLMAdapter:
    """Create Hunyuan VLM adapter."""
    import os
    secret_id = secret_id or os.getenv("HUNYUAN_SECRET_ID")
    secret_key = secret_key or os.getenv("HUNYUAN_SECRET_KEY")
    return HunyuanVLMAdapter(secret_id=secret_id, secret_key=secret_key)