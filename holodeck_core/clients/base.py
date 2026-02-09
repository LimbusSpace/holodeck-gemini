#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Client Interfaces

Provides abstract base classes and interfaces for all client types
in the Holodeck system, ensuring consistent APIs and behavior patterns.
"""

import abc
import asyncio
from typing import Dict, Any, Optional, List, Union, Protocol
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from ..config.base import ConfigManager
from ..logging.standardized import StandardizedLogger, get_logger
from ..exceptions.framework import (
    HolodeckError, ValidationError, APIError, ImageGenerationError,
    ThreeDGenerationError, LLMError
)


class ServiceType(Enum):
    """Enumeration of supported service types"""
    IMAGE_GENERATION = "image_generation"
    THREED_GENERATION = "3d_generation"
    LLM = "llm"
    HYBRID = "hybrid"


@dataclass
class ClientConfig:
    """Standardized client configuration"""
    service_type: ServiceType
    timeout: int = 300
    max_retries: int = 3
    retry_delay: float = 1.0
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour


@dataclass
class GenerationResult:
    """Standardized result format for generation operations"""
    success: bool
    data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration: float = 0.0


class BaseClient(abc.ABC):
    """
    Abstract base class for all Holodeck clients.

    Provides common functionality for:
    - Configuration management
    - Logging
    - Error handling
    - Retry logic
    - Performance monitoring
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[StandardizedLogger] = None,
        client_config: Optional[ClientConfig] = None
    ):
        """
        Initialize base client.

        Args:
            config_manager: Configuration manager instance
            logger: Logger instance
            client_config: Client-specific configuration
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = logger or get_logger(self.__class__.__name__)
        self.client_config = client_config or ClientConfig(
            service_type=self.get_service_type()
        )

        # Initialize common attributes
        self._initialized = False
        self._cache = {}

    @abc.abstractmethod
    def get_service_type(self) -> ServiceType:
        """Get the service type for this client"""
        pass

    @abc.abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate client configuration.

        Returns:
            True if configuration is valid

        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass

    def initialize(self) -> None:
        """Initialize the client"""
        if self._initialized:
            return

        try:
            self.validate_configuration()
            self._setup_client()
            self._initialized = True
            self.logger.info(f"Client initialized: {self.__class__.__name__}")
        except Exception as e:
            self.logger.error(f"Client initialization failed: {e}")
            raise

    @abc.abstractmethod
    def _setup_client(self) -> None:
        """Setup client-specific configuration and connections"""
        pass

    def ensure_initialized(self) -> None:
        """Ensure client is initialized before use"""
        if not self._initialized:
            self.initialize()

    def _validate_inputs(self, **kwargs) -> None:
        """
        Validate input parameters.

        Override in subclasses for specific validation logic.
        """
        pass

    def _handle_error(self, error: Exception, operation: str, **context) -> None:
        """Handle errors with standardized logging"""
        if isinstance(error, HolodeckError):
            error.context.update(context)
            self.logger.error(f"{operation} failed: {error.message}", context=error.context)
        else:
            self.logger.error(f"{operation} failed with unexpected error: {error}", context=context)

    def _cache_result(self, key: str, result: Any, ttl: Optional[int] = None) -> None:
        """Cache a result with optional TTL"""
        if not self.client_config.enable_caching:
            return

        import time
        ttl = ttl or self.client_config.cache_ttl
        expiry = time.time() + ttl

        self._cache[key] = {
            "result": result,
            "expiry": expiry
        }

    def _get_cached_result(self, key: str) -> Optional[Any]:
        """Get cached result if available and not expired"""
        if not self.client_config.enable_caching or key not in self._cache:
            return None

        import time
        cached = self._cache[key]

        if time.time() > cached["expiry"]:
            del self._cache[key]
            return None

        return cached["result"]

    def clear_cache(self) -> None:
        """Clear the client cache"""
        self._cache.clear()
        self.logger.info("Client cache cleared")


class BaseImageClient(BaseClient):
    """
    Abstract base class for image generation clients.

    Provides common functionality for:
    - Text-to-image generation
    - Image validation
    - Resolution handling
    - Style management
    """

    def get_service_type(self) -> ServiceType:
        return ServiceType.IMAGE_GENERATION

    @abc.abstractmethod
    async def generate_image(
        self,
        prompt: str,
        resolution: str = "1024:1024",
        style: Optional[str] = None,
        model: str = "default",
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate image from text prompt.

        Args:
            prompt: Text description for image generation
            resolution: Image resolution (e.g., "1024:1024")
            style: Optional style parameter
            model: Model version to use
            output_path: Optional path to save generated image
            **kwargs: Additional model-specific parameters

        Returns:
            GenerationResult containing image data and metadata
        """
        pass

    @abc.abstractmethod
    async def validate_prompt(self, prompt: str) -> bool:
        """
        Validate if prompt is acceptable for generation.

        Args:
            prompt: Text prompt to validate

        Returns:
            True if prompt is valid

        Raises:
            ValidationError: If prompt is invalid
        """
        pass

    def _validate_inputs(self, prompt: str, resolution: str, **kwargs) -> None:
        """Validate image generation inputs"""
        super()._validate_inputs(**kwargs)

        if not prompt or not prompt.strip():
            raise ValidationError("Prompt cannot be empty", field_name="prompt")

        if len(prompt) > 1000:  # Reasonable limit
            raise ValidationError(
                "Prompt too long (max 1000 characters)",
                field_name="prompt",
                field_value=len(prompt)
            )

        # Validate resolution format
        if ':' not in resolution:
            raise ValidationError(
                "Resolution must be in format WIDTH:HEIGHT",
                field_name="resolution",
                field_value=resolution
            )

        try:
            width, height = resolution.split(':')
            width, height = int(width), int(height)

            if width <= 0 or height <= 0:
                raise ValueError("Dimensions must be positive")

            if width > 4096 or height > 4096:
                raise ValidationError(
                    "Resolution too large (max 4096x4096)",
                    field_name="resolution",
                    field_value=resolution
                )

        except ValueError as e:
            raise ValidationError(
                f"Invalid resolution format: {e}",
                field_name="resolution",
                field_value=resolution
            )

    async def test_connection(self) -> bool:
        """
        Test if the image generation service is accessible.

        Returns:
            True if connection successful
        """
        try:
            # Use a simple test prompt
            test_prompt = "test"
            result = await self.generate_image(
                prompt=test_prompt,
                resolution="256:256"  # Small resolution for quick test
            )
            return result.success
        except Exception as e:
            self.logger.warning(f"Connection test failed: {e}")
            return False


class Base3DClient(BaseClient):
    """
    Abstract base class for 3D generation clients.

    Provides common functionality for:
    - Image-to-3D generation
    - 3D model validation
    - Format handling
    - Workflow management
    """

    def get_service_type(self) -> ServiceType:
        return ServiceType.THREED_GENERATION

    @abc.abstractmethod
    async def generate_3d_from_image(
        self,
        image_path: Union[str, Path],
        output_format: str = "glb",
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate 3D model from input image.

        Args:
            image_path: Path to input image
            output_format: Output format (glb, obj, fbx, etc.)
            output_dir: Directory to save generated 3D model
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult containing 3D model data and metadata
        """
        pass

    @abc.abstractmethod
    async def generate_3d_from_prompt(
        self,
        prompt: str,
        output_format: str = "glb",
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate 3D model from text prompt.

        Args:
            prompt: Text description for 3D generation
            output_format: Output format
            output_dir: Directory to save generated 3D model
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult containing 3D model data and metadata
        """
        pass

    def _validate_inputs(self, image_path: Optional[Union[str, Path]] = None,
                        prompt: Optional[str] = None, **kwargs) -> None:
        """Validate 3D generation inputs"""
        super()._validate_inputs(**kwargs)

        if image_path is None and prompt is None:
            raise ValidationError(
                "Either image_path or prompt must be provided",
                field_name="inputs"
            )

        if image_path is not None:
            image_path = Path(image_path)
            if not image_path.exists():
                raise ValidationError(
                    "Input image not found",
                    field_name="image_path",
                    field_value=str(image_path)
                )

            if image_path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.webp']:
                raise ValidationError(
                    "Unsupported image format",
                    field_name="image_path",
                    field_value=image_path.suffix
                )

        if prompt is not None:
            if not prompt or not prompt.strip():
                raise ValidationError("Prompt cannot be empty", field_name="prompt")

            if len(prompt) > 500:  # Shorter limit for 3D
                raise ValidationError(
                    "Prompt too long (max 500 characters)",
                    field_name="prompt",
                    field_value=len(prompt)
                )

    async def test_connection(self) -> bool:
        """
        Test if the 3D generation service is accessible.

        Returns:
            True if connection successful
        """
        try:
            # Try a simple text-to-3D generation
            test_prompt = "cube"
            result = await self.generate_3d_from_prompt(
                prompt=test_prompt,
                output_format="glb"
            )
            return result.success
        except Exception as e:
            self.logger.warning(f"3D connection test failed: {e}")
            return False


class BaseLLMClient(BaseClient):
    """
    Abstract base class for LLM clients.

    Provides common functionality for:
    - Text generation
    - Chat completion
    - Prompt engineering
    - Response validation
    """

    def get_service_type(self) -> ServiceType:
        return ServiceType.LLM

    @abc.abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate chat completion response.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters

        Returns:
            GenerationResult containing response and metadata
        """
        pass

    @abc.abstractmethod
    async def text_generation(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model parameters

        Returns:
            GenerationResult containing generated text and metadata
        """
        pass

    def _validate_inputs(self, messages: Optional[List[Dict[str, str]]] = None,
                        prompt: Optional[str] = None, temperature: float = 0.7,
                        **kwargs) -> None:
        """Validate LLM inputs"""
        super()._validate_inputs(**kwargs)

        if messages is None and prompt is None:
            raise ValidationError(
                "Either messages or prompt must be provided",
                field_name="inputs"
            )

        if messages is not None:
            if not messages:
                raise ValidationError("Messages list cannot be empty", field_name="messages")

            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    raise ValidationError(
                        f"Message {i} must be a dictionary",
                        field_name="messages",
                        field_value=type(msg)
                    )

                if 'role' not in msg or 'content' not in msg:
                    raise ValidationError(
                        f"Message {i} must have 'role' and 'content' keys",
                        field_name="messages"
                    )

                if msg['role'] not in ['user', 'assistant', 'system']:
                    raise ValidationError(
                        f"Invalid role in message {i}: {msg['role']}",
                        field_name="messages"
                    )

        if prompt is not None:
            if not prompt or not prompt.strip():
                raise ValidationError("Prompt cannot be empty", field_name="prompt")

        if not 0.0 <= temperature <= 1.0:
            raise ValidationError(
                "Temperature must be between 0.0 and 1.0",
                field_name="temperature",
                field_value=temperature
            )

    async def test_connection(self) -> bool:
        """
        Test if the LLM service is accessible.

        Returns:
            True if connection successful
        """
        try:
            test_messages = [{"role": "user", "content": "test"}]
            result = await self.chat_completion(test_messages, max_tokens=10)
            return result.success
        except Exception as e:
            self.logger.warning(f"LLM connection test failed: {e}")
            return False


# Type aliases for convenience
ImageClient = BaseImageClient
ThreeDClient = Base3DClient
LLMClient = BaseLLMClient


# Example usage and testing
if __name__ == "__main__":
    # Example of implementing a concrete client
    class ExampleImageClient(BaseImageClient):
        def validate_configuration(self) -> bool:
            # Check if required API keys are available
            api_key = self.config_manager.get_config("EXAMPLE_API_KEY")
            return bool(api_key)

        def _setup_client(self) -> None:
            # Setup API client, connections, etc.
            pass

        async def generate_image(self, prompt: str, **kwargs) -> GenerationResult:
            # Implementation would go here
            return GenerationResult(success=True, data="example_image_data")

        async def validate_prompt(self, prompt: str) -> bool:
            return len(prompt) > 0

    # Test the example client
    async def test_client():
        client = ExampleImageClient()
        try:
            client.initialize()
            print("Client initialized successfully")
        except Exception as e:
            print(f"Client initialization failed: {e}")

    # Run test
    asyncio.run(test_client())