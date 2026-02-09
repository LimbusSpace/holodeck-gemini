"""
Unified VLM Client for Scene Analysis

Provides a unified interface for Vision-Language Model clients with support for
multiple backends (OpenAI, SiliconFlow) and automatic backend selection.
"""

import asyncio
import logging
import os
import json
import base64
from typing import Any, Dict, List, Optional, Union
from enum import Enum

import aiohttp
from holodeck_core.schemas.scene_objects import SceneData, SceneObject, Vec3
from holodeck_core.config.base import is_service_configured
from holodeck_core.clients.base import BaseLLMClient, ServiceType, GenerationResult
from holodeck_core.config.base import ConfigManager
from holodeck_core.logging.standardized import get_logger
from ..prompt_templates import get_reference_image_prompt, get_object_image_prompt

logger = logging.getLogger(__name__)


class VLMBackend(str, Enum):
    """Supported VLM backends"""
    AUTO = "auto"
    OPENAI = "openai"
    SILICONFLOW = "siliconflow"
    CUSTOM = "custom"


class CustomVLMClient:
    """Custom VLM client for user-defined models"""

    def __init__(self, base_url: str, api_key: str, model_name: str, headers: Optional[Dict[str, str]] = None):
        """Initialize custom VLM client

        Args:
            base_url: Base URL of the API endpoint
            api_key: API key for authentication
            model_name: Name of the model to use
            headers: Additional headers (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.headers = headers or {}
        self.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    async def test_connection(self) -> bool:
        """Test if the custom API is accessible"""
        try:
            test_payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 10
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=test_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f"Custom VLM connection test failed: {e}")
            return False

    async def extract_objects(self, scene_text: str, image: Optional[bytes] = None) -> SceneData:
        """Extract objects using custom VLM API"""
        try:
            # Prepare messages for object extraction
            system_prompt = """You are a professional 3D scene analysis assistant. Extract 3D objects from scene descriptions.

Requirements:
1. Identify all important 3D objects in the scene
2. Provide accurate names and descriptions
3. Determine reasonable sizes in meters
4. Classify objects (furniture, equipment, decoration, etc.)

Output format:
Return JSON with the following structure:
{
  "scene_style": "string",
  "objects": [
    {
      "name": "object_name",
      "category": "category_name",
      "size": [length, width, height],
      "visual_description": "detailed description",
      "position": [x, y, z],
      "rotation": [x, y, z],
      "must_exist": true
    }
  ]
}"""

            user_content = f"""Please analyze the following scene description and extract 3D objects:

Scene description: {scene_text}

Please return the analysis in JSON format."""

            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            # Add image if provided (if API supports vision)
            if image:
                import base64
                image_b64 = base64.b64encode(image).decode('utf-8')
                messages[1]["content"] = [
                    {"type": "text", "text": user_content},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        }
                    }
                ]

            # Make API request
            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.1
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API request failed: {response.status} - {error_text}")

                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]

                    # Parse JSON response (handle markdown code blocks)
                    try:
                        # Extract JSON from markdown code blocks if present
                        import re
                        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
                        if json_match:
                            json_str = json_match.group(1).strip()
                        else:
                            # Try to find JSON object directly
                            json_match = re.search(r'\{[\s\S]*\}', content)
                            json_str = json_match.group(0) if json_match else content.strip()
                        analysis_result = json.loads(json_str)
                        return self._parse_scene_data(analysis_result)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response: {e}, content: {content[:200]}")
                        return self._create_fallback_scene_data(scene_text)

        except Exception as e:
            logger.error(f"Error extracting objects with custom VLM: {e}")
            return self._create_fallback_scene_data(scene_text)

    def _parse_scene_data(self, analysis_result: Dict[str, Any]) -> SceneData:
        """Parse custom VLM analysis result into SceneData"""
        objects = []

        for i, obj_data in enumerate(analysis_result.get("objects", [])):
            try:
                obj = SceneObject(
                    object_id=f"obj_{i+1:03d}",
                    name=obj_data.get("name", f"object_{i+1}"),
                    category=obj_data.get("category", "furniture"),
                    size=Vec3(
                        x=float(obj_data.get("size", [1.0, 1.0, 1.0])[0]),
                        y=float(obj_data.get("size", [1.0, 1.0, 1.0])[1]),
                        z=float(obj_data.get("size", [1.0, 1.0, 1.0])[2])
                    ),
                    position=Vec3(
                        x=float(obj_data.get("position", [0.0, 0.0, 0.0])[0]),
                        y=float(obj_data.get("position", [0.0, 0.0, 0.0])[1]),
                        z=float(obj_data.get("position", [0.0, 0.0, 0.0])[2])
                    ),
                    rotation=Vec3(
                        x=float(obj_data.get("rotation", [0.0, 0.0, 0.0])[0]),
                        y=float(obj_data.get("rotation", [0.0, 0.0, 0.0])[1]),
                        z=float(obj_data.get("rotation", [0.0, 0.0, 0.0])[2])
                    ),
                    visual_description=obj_data.get("visual_description", ""),
                    must_exist=obj_data.get("must_exist", True)
                )
                objects.append(obj)
            except (ValueError, TypeError, IndexError) as e:
                logger.warning(f"Failed to parse object {i+1}: {e}")
                continue

        scene_data = SceneData(
            scene_style=analysis_result.get("scene_style", "modern"),
            objects=objects
        )

        logger.info(f"Parsed {len(objects)} objects from custom VLM response")
        return scene_data

    def _create_fallback_scene_data(self, scene_text: str) -> SceneData:
        """Create fallback scene data when custom API fails"""
        logger.warning("Using fallback scene data due to custom API failure")

        # Create a simple fallback object
        fallback_object = SceneObject(
            object_id="obj_001",
            name="scene_object",
            category="furniture",
            size=Vec3(x=1.0, y=1.0, z=1.0),
            position=Vec3(x=0.0, y=0.0, z=0.0),
            rotation=Vec3(x=0.0, y=0.0, z=0.0),
            visual_description=f"Object from scene: {scene_text[:50]}",
            must_exist=True
        )

        return SceneData(
            scene_style="modern",
            objects=[fallback_object]
        )

    async def generate_reference_image(
        self,
        description: str,
        style: str = "realistic",
        language: Optional[str] = None
    ) -> bytes:
        """Generate panoramic reference image using standardized template.

        Args:
            description: Scene description
            style: Artistic style for rendering
            language: Language for prompts ('en', 'zh', or None for auto-detection)

        Returns:
            Image data as bytes
        """
        try:
            # Use standardized prompt template for reference image generation
            prompt = get_reference_image_prompt(
                description=description,
                style=style,
                language=language
            )

            # Call image generation API
            return await self._call_image_generation_api(prompt)

        except Exception as e:
            logger.error(f"Error generating reference image: {e}")
            raise

    async def generate_object_image(
        self,
        obj_name: str,
        style: str = "realistic",
        reference_context: Optional[str] = None,
        language: Optional[str] = None
    ) -> bytes:
        """Generate isolated object image with transparent background.

        Args:
            obj_name: Name of the object to generate
            style: Artistic style for rendering
            reference_context: Optional reference context from scene
            language: Language for prompts ('en', 'zh', or None for auto-detection)

        Returns:
            Image data as bytes (PNG with transparent background)
        """
        try:
            # Use standardized prompt template for individual object generation
            prompt = get_object_image_prompt(
                obj_name=obj_name,
                style=style,
                language=language,
                reference_context=reference_context or ""
            )

            # Call image generation API with PNG format requirement
            return await self._call_image_generation_api(prompt, format="PNG")

        except Exception as e:
            logger.error(f"Error generating object image: {e}")
            raise

    async def _call_image_generation_api(
        self,
        prompt: str,
        format: str = "PNG",
        size: str = "1024x1024"
    ) -> bytes:
        """Call the image generation API with the provided prompt.

        Args:
            prompt: Image generation prompt
            format: Image format (PNG, JPEG, etc.)
            size: Image size specification

        Returns:
            Generated image data as bytes
        """
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "n": 1,
                "size": size,
                "response_format": "b64_json"
            }

            if format == "PNG":
                payload["response_format"] = "b64_json"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/images/generations",
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Image generation failed: {response.status} - {error_text}")

                    result = await response.json()
                    image_data = result["data"][0]["b64_json"]
                    return base64.b64decode(image_data)

        except Exception as e:
            logger.error(f"Error calling image generation API: {e}")
            raise


class UnifiedVLMClient(BaseLLMClient):
    """Unified Vision-Language Model client for scene analysis.

    Provides a single interface for object extraction using multiple VLM backends
    with automatic backend selection and fallback mechanisms.
    Supports custom models via URL + API Key + model name.
    """

    def __init__(self, backend: Union[str, VLMBackend] = VLMBackend.AUTO, api_key: Optional[str] = None,
                 config_manager: Optional[ConfigManager] = None, logger: Optional[get_logger] = None,
                 client_config: Optional[ClientConfig] = None, custom_config: Optional[Dict[str, Any]] = None):
        """Initialize unified VLM client.

        Args:
            backend: Backend to use ('auto', 'openai', 'siliconflow', 'custom')
            api_key: Optional API key (if not provided, will use environment variables)
            config_manager: Configuration manager instance
            logger: Logger instance
            client_config: Client-specific configuration
            custom_config: Custom model configuration dict with keys:
                - base_url: API endpoint URL
                - api_key: API key for custom model
                - model_name: Name of the model
                - headers: Optional additional headers
        """
        super().__init__(config_manager=config_manager, logger=logger, client_config=client_config)

        self.backend = VLMBackend(backend)
        self.api_key = api_key
        self.custom_config = custom_config or {}
        self._client = None

        self.logger.info(f"Initialized UnifiedVLMClient with backend: {self.backend}")

    def get_service_type(self) -> ServiceType:
        """Get the service type for this client"""
        return ServiceType.LLM

    def validate_configuration(self) -> bool:
        """Validate client configuration"""
        # Check if CUSTOM_VLM is configured
        return (bool(os.getenv("CUSTOM_VLM_BASE_URL")) and
                bool(os.getenv("CUSTOM_VLM_API_KEY")) and
                bool(os.getenv("CUSTOM_VLM_MODEL_NAME")))

    def _setup_client(self) -> None:
        """Setup client-specific configuration and connections"""
        # This will be called by the base class initialize() method
        pass

    def ensure_initialized(self) -> None:
        """Ensure client is initialized and backend is selected"""
        super().ensure_initialized()

        if not self._client:
            # Select backend based on configuration and language preferences
            selected_backend = self._select_backend()

            if selected_backend == VLMBackend.OPENAI:
                # OpenAI backend now uses custom VLM with OpenAI configuration
                if not self.custom_config:
                    # Create default OpenAI configuration
                    api_key = self.api_key or os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise ValueError("OpenAI API key required but not provided")
                    self.custom_config = {
                        "base_url": "https://api.openai.com/v1",
                        "api_key": api_key,
                        "model_name": "gpt-4-vision-preview"
                    }
                self._client = CustomVLMClient(**self.custom_config)

            elif selected_backend == VLMBackend.SILICONFLOW:
                # SiliconFlow backend now uses custom VLM with SiliconFlow configuration
                if not self.custom_config:
                    # Create default SiliconFlow configuration
                    api_key = self.api_key or os.getenv("SILICONFLOW_API_KEY")
                    if not api_key:
                        raise ValueError("SiliconFlow API key required but not provided")
                    self.custom_config = {
                        "base_url": "https://api.siliconflow.cn/v1",
                        "api_key": api_key,
                        "model_name": "zai-org/GLM-4.6V"
                    }
                self._client = CustomVLMClient(**self.custom_config)

            elif selected_backend == VLMBackend.CUSTOM:
                if not self.custom_config:
                    # Try to read from environment variables
                    base_url = os.getenv("CUSTOM_VLM_BASE_URL")
                    api_key = os.getenv("CUSTOM_VLM_API_KEY")
                    model_name = os.getenv("CUSTOM_VLM_MODEL_NAME")

                    if base_url and api_key and model_name:
                        self.custom_config = {
                            "base_url": base_url,
                            "api_key": api_key,
                            "model_name": model_name
                        }
                    else:
                        raise ValueError(
                            "Custom configuration required for custom backend. "
                            "Provide custom_config parameter or set environment variables: "
                            "CUSTOM_VLM_BASE_URL, CUSTOM_VLM_API_KEY, CUSTOM_VLM_MODEL_NAME"
                        )

                required_keys = ['base_url', 'api_key', 'model_name']
                for key in required_keys:
                    if key not in self.custom_config:
                        raise ValueError(f"Custom configuration missing required key: {key}")

                self._client = CustomVLMClient(
                    base_url=self.custom_config['base_url'],
                    api_key=self.custom_config['api_key'],
                    model_name=self.custom_config['model_name'],
                    headers=self.custom_config.get('headers')
                )

            else:
                raise ValueError(f"Unsupported backend: {selected_backend}")

            self.logger.info(f"UnifiedVLMClient initialized with backend: {selected_backend}")

    def _select_backend(self) -> VLMBackend:
        """Select the best backend based on configuration and preferences."""
        # If specific backend requested, use it if available
        if self.backend != VLMBackend.AUTO:
            if self._is_backend_available(self.backend):
                return self.backend
            else:
                raise ValueError(f"Requested backend {self.backend} is not available")

        # Auto-selection logic
        # Priority: Custom > SiliconFlow (for Chinese) > OpenAI (for English/International)

        # Check if custom backend is available
        if self._is_backend_available(VLMBackend.CUSTOM):
            return VLMBackend.CUSTOM

        # Check if SiliconFlow is available
        if self._is_backend_available(VLMBackend.SILICONFLOW):
            return VLMBackend.SILICONFLOW

        # Check if OpenAI is available
        if self._is_backend_available(VLMBackend.OPENAI):
            return VLMBackend.OPENAI

        # No backends available
        available_backends = []
        for backend in VLMBackend:
            if backend != VLMBackend.AUTO and self._is_backend_available(backend):
                available_backends.append(backend)

        if not available_backends:
            raise ValueError(
                "No VLM backends are available. Please configure: "
                "CUSTOM_VLM_BASE_URL, CUSTOM_VLM_API_KEY, and CUSTOM_VLM_MODEL_NAME"
            )

        # Return first available backend
        return available_backends[0]

    def _is_backend_available(self, backend: VLMBackend) -> bool:
        """Check if a backend is available and configured."""
        if backend == VLMBackend.OPENAI:
            return False  # OpenAI disabled, use CUSTOM instead
        elif backend == VLMBackend.SILICONFLOW:
            return False  # SiliconFlow disabled, use CUSTOM instead
        elif backend == VLMBackend.CUSTOM:
            # Check if custom configuration is provided and valid
            if self.custom_config:
                required_keys = ['base_url', 'api_key', 'model_name']
                return all(key in self.custom_config for key in required_keys)

            # Check if environment variables are set
            base_url = os.getenv("CUSTOM_VLM_BASE_URL")
            api_key = os.getenv("CUSTOM_VLM_API_KEY")
            model_name = os.getenv("CUSTOM_VLM_MODEL_NAME")
            return bool(base_url and api_key and model_name)
        return False

    async def test_connection(self) -> bool:
        """Test if the selected backend is accessible."""
        self.ensure_initialized()

        try:
            if hasattr(self._client, 'test_connection'):
                return await self._client.test_connection()
            else:
                self.logger.warning("Client does not support connection testing")
                return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    async def extract_objects(self, scene_text: str, image: Optional[bytes] = None) -> SceneData:
        """Extract objects from scene description using the selected backend.

        Args:
            scene_text: Scene description text
            image: Optional reference image bytes

        Returns:
            SceneData with extracted objects

        Raises:
            ValueError: If no backend is available
            RuntimeError: If object extraction fails
        """
        self.ensure_initialized()

        if not self._client:
            raise ValueError("No VLM client available")

        try:
            # Use the selected backend's extract_objects method
            scene_data = await self._client.extract_objects(scene_text, image)

            self.logger.info(f"Successfully extracted {len(scene_data.objects)} objects using {type(self._client).__name__}")
            return scene_data

        except Exception as e:
            self.logger.error(f"Object extraction failed with {type(self._client).__name__}: {e}")

            # Try fallback backend if available
            fallback_result = await self._try_fallback_backends(scene_text, image)
            if fallback_result:
                return fallback_result

            # If all backends fail, return minimal SceneData
            self.logger.warning("All backends failed, returning empty scene data")
            return SceneData(
                scene_style="unknown",
                objects=[]
            )

    async def generate_reference_image(
        self,
        description: str,
        style: str = "realistic",
        language: Optional[str] = None
    ) -> bytes:
        """Generate panoramic reference image using standardized template.

        Args:
            description: Scene description
            style: Artistic style for rendering
            language: Language for prompts ('en', 'zh', or None for auto-detection)

        Returns:
            Image data as bytes
        """
        self.ensure_initialized()

        if not self._client:
            raise ValueError("No VLM client available")

        try:
            if hasattr(self._client, 'generate_reference_image'):
                image_data = await self._client.generate_reference_image(description, style, language)
                self.logger.info(f"Successfully generated reference image using {type(self._client).__name__}")
                return image_data
            else:
                raise NotImplementedError(f"Backend {type(self._client).__name__} does not support reference image generation")

        except Exception as e:
            self.logger.error(f"Reference image generation failed with {type(self._client).__name__}: {e}")
            raise

    async def generate_object_image(
        self,
        obj_name: str,
        style: str = "realistic",
        reference_context: Optional[str] = None,
        language: Optional[str] = None
    ) -> bytes:
        """Generate isolated object image with transparent background.

        Args:
            obj_name: Name of the object to generate
            style: Artistic style for rendering
            reference_context: Optional reference context from scene
            language: Language for prompts ('en', 'zh', or None for auto-detection)

        Returns:
            Image data as bytes (PNG with transparent background)
        """
        self.ensure_initialized()

        if not self._client:
            raise ValueError("No VLM client available")

        try:
            if hasattr(self._client, 'generate_object_image'):
                image_data = await self._client.generate_object_image(obj_name, style, reference_context, language)
                self.logger.info(f"Successfully generated object image for '{obj_name}' using {type(self._client).__name__}")
                return image_data
            else:
                raise NotImplementedError(f"Backend {type(self._client).__name__} does not support object image generation")

        except Exception as e:
            self.logger.error(f"Object image generation failed with {type(self._client).__name__}: {e}")
            raise

        except Exception as e:
            self.logger.error(f"Object extraction failed with {type(self._client).__name__}: {e}")

            # Try fallback backend if available
            fallback_result = await self._try_fallback_backends(scene_text, image)
            if fallback_result:
                return fallback_result

            # If all backends fail, return minimal SceneData
            self.logger.warning("All backends failed, returning empty scene data")
            return SceneData(
                scene_style="unknown",
                objects=[]
            )

    async def _try_fallback_backends(self, scene_text: str, image: Optional[bytes] = None) -> Optional[SceneData]:
        """Try fallback backends if primary backend fails."""
        current_backend = self._get_current_backend()

        # Try other available backends
        for backend in VLMBackend:
            if backend == VLMBackend.AUTO or backend == current_backend:
                continue

            if self._is_backend_available(backend):
                try:
                    logger.info(f"Trying fallback backend: {backend}")

                    # Create temporary client with fallback backend
                    temp_client = UnifiedVLMClient(backend=backend, api_key=self.api_key)
                    await temp_client.initialize()

                    # Try extraction
                    scene_data = await temp_client.extract_objects(scene_text, image)

                    logger.info(f"Fallback to {backend} succeeded")
                    return scene_data

                except Exception as e:
                    logger.warning(f"Fallback to {backend} failed: {e}")
                    continue

        return None

    def _get_current_backend(self) -> Optional[VLMBackend]:
        """Get the current backend being used."""
        if not self._client:
            return None

        client_type = type(self._client).__name__
        if client_type == "OpenAIClient":
            return VLMBackend.OPENAI
        elif client_type == "SiliconFlowClient":
            return VLMBackend.SILICONFLOW

        return None

    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about available and configured backends."""
        info = {
            "current_backend": self._get_current_backend(),
            "requested_backend": self.backend,
            "available_backends": [],
            "configured_backends": [],
            "client_type": type(self._client).__name__ if self._client else None
        }

        for backend in VLMBackend:
            if backend != VLMBackend.AUTO:
                info["available_backends"].append(backend)
                if self._is_backend_available(backend):
                    info["configured_backends"].append(backend)

        return info

    async def supports_feature(self, feature: str) -> bool:
        """Check if the current backend supports a specific feature."""
        self.ensure_initialized()

        # Define feature support for each backend
        feature_support = {
            "openai": [
                "object_extraction",
                "vision",
                "scene_analysis",
                "image_generation",
                "reference_image_generation",
                "object_image_generation",
                "quality_evaluation"
            ],
            "siliconflow": [
                "object_extraction",
                "vision",
                "scene_analysis",
                "image_generation",
                "reference_image_generation",
                "object_image_generation",
                "chinese_optimized"
            ],
            "custom": [
                "object_extraction",
                "vision",
                "scene_analysis",
                "image_generation",
                "reference_image_generation",
                "object_image_generation",
                "custom_model"
            ]
        }

        current_backend = self._get_current_backend()
        if not current_backend or current_backend == VLMBackend.AUTO:
            return False

        backend_name = current_backend.value
        supported_features = feature_support.get(backend_name, [])

        return feature in supported_features

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate chat completion response."""
        self.ensure_initialized()

        try:
            # Forward to the underlying client if it supports chat completion
            if hasattr(self._client, 'chat_completion'):
                return await self._client.chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                raise NotImplementedError("Current backend does not support chat completion")

        except Exception as e:
            self.logger.error(f"Chat completion failed: {e}")
            return GenerationResult(success=False, error=str(e))

    async def text_generation(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate text from prompt."""
        self.ensure_initialized()

        try:
            # Forward to the underlying client if it supports text generation
            if hasattr(self._client, 'text_generation'):
                return await self._client.text_generation(
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            else:
                raise NotImplementedError("Current backend does not support text generation")

        except Exception as e:
            self.logger.error(f"Text generation failed: {e}")
            return GenerationResult(success=False, error=str(e))

    def __str__(self) -> str:
        """String representation of the client."""
        backend_info = self.get_backend_info()
        return f"UnifiedVLMClient(backend={backend_info['current_backend']}, client={backend_info['client_type']})"

    def __repr__(self) -> str:
        """Detailed representation of the client."""
        return f"UnifiedVLMClient(backend={self.backend}, initialized={self._initialized})"