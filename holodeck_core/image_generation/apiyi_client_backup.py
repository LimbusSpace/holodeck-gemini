#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
APIAyi (Gemini-3-Pro-Image) client for image generation.

Provides interface to APIAyi's Gemini-3-Pro-Image API for high-quality image generation.
Based on the provided API example with proper error handling and integration.
"""

import asyncio
import aiohttp
import base64
import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from ..clients.base import BaseImageClient, GenerationResult
from ..config.base import get_config
from ..logging.standardized import get_logger
from ..exceptions.framework import ImageGenerationError, APIError, ValidationError

logger = get_logger(__name__)

class APIYiClient(BaseImageClient):
    """
    APIAyi client for generating images using Gemini-3-Pro-Image model.

    Features:
    - High-quality 2K image generation
    - Multiple aspect ratios support
    - Async API calls with proper timeout handling
    - Comprehensive error handling and validation
    """

    def __init__(self, config_manager=None, client_config=None):
        super().__init__(config_manager, None, client_config)
        self.api_key = get_config("APIAYI_API_KEY")
        self.base_url = get_config("APIAYI_BASE_URL", "https://api.apiyi.com/v1beta/models")
        self.model = get_config("APIAYI_MODEL", "gemini-3-pro-image-preview")
        self.default_timeout = get_config("APIAYI_TIMEOUT", 300, value_type=int)  # 5 minutes for 2K

    def validate_configuration(self) -> bool:
        """Validate APIAyi configuration."""
        if not self.api_key:
            raise ValidationError(
                "APIAYI_API_KEY environment variable is required",
                field_name="api_key"
            )

        if self.api_key.startswith("sk-your") or self.api_key == "your-api-key":
            raise ValidationError(
                "Please replace the placeholder API key with your actual APIAyi API key",
                field_name="api_key"
            )

        return True

    def _setup_client(self) -> None:
        """Setup APIAyi client."""
        # Test connection during setup
        try:
            asyncio.run(self.test_connection())
            logger.info("APIAyi client initialized successfully")
        except Exception as e:
            logger.warning(f"APIAyi connection test failed during setup: {e}")

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
        Generate image using APIAyi's Gemini-3-Pro-Image API.

        Args:
            prompt: Text description for image generation
            resolution: Image resolution (maps to aspect ratio)
            style: Style parameter (incorporated into prompt)
            model: Model version (uses configured model)
            output_path: Optional path to save generated image
            **kwargs: Additional parameters (quality, timeout, etc.)

        Returns:
            GenerationResult containing image data and metadata
        """
        start_time = time.time()

        try:
            # Input validation
            self._validate_inputs(prompt, resolution, **kwargs)

            # Map resolution to aspect ratio
            aspect_ratio = self._resolution_to_aspect_ratio(resolution)

            # Determine image size based on resolution
            image_size = self._resolution_to_size(resolution)

            # Build enhanced prompt with style
            enhanced_prompt = self._build_enhanced_prompt(prompt, style)

            # Prepare API request
            api_model = model if model != "default" else self.model
            timeout = kwargs.get("timeout", self.default_timeout)

            # Make API call
            result = await self._call_apiyi_api(
                prompt=enhanced_prompt,
                model=api_model,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                timeout=timeout
            )

            # Extract and save image
            image_path = await self._save_image_result(result, output_path, prompt)

            duration = time.time() - start_time

            return GenerationResult(
                success=True,
                data=str(image_path),
                metadata={
                    "backend": "apiyi",
                    "model": api_model,
                    "prompt": prompt,
                    "enhanced_prompt": enhanced_prompt,
                    "resolution": resolution,
                    "aspect_ratio": aspect_ratio,
                    "image_size": image_size,
                    "style": style,
                    "generation_time": duration,
                    "api_response_id": result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("inlineData", {}).get("fileData", {}).get("fileUri", "unknown")
                },
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"APIAyi generation failed: {e}")

            if isinstance(e, (ValidationError, ImageGenerationError)):
                raise
            else:
                raise ImageGenerationError(
                    f"APIAyi API error: {e}",
                    prompt=prompt[:50]
                )

    async def _call_apiyi_api(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str,
        image_size: str,
        timeout: int
    ) -> Dict[str, Any]:
        """Call APIAyi API with proper error handling."""
        # APIYi endpoint format includes the model name
        url = f"{self.base_url}/{model}:generateContent"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": image_size
                }
            }
        }

        logger.info(f"Calling APIAyi API: {model} with {aspect_ratio} aspect ratio")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:

                    if response.status == 200:
                        result = await response.json()

                        # Validate response structure
                        if not self._validate_api_response(result):
                            raise APIError("Invalid API response structure")

                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"APIAyi API error {response.status}: {error_text}")

                        if response.status == 401:
                            raise APIError("Invalid API key - please check your APIAyi API key")
                        elif response.status == 429:
                            raise APIError("Rate limit exceeded - please try again later")
                        elif response.status == 500:
                            raise APIError("APIAyi server error - please try again later")
                        else:
                            raise APIError(f"APIAyi API error {response.status}: {error_text}")

        except asyncio.TimeoutError:
            raise APIError(f"APIAyi API timeout after {timeout} seconds")
        except aiohttp.ClientError as e:
            raise APIError(f"Network error calling APIAyi API: {e}")

    def _validate_api_response(self, response: Dict[str, Any]) -> bool:
        """Validate API response structure."""
        try:
            candidates = response.get("candidates", [])
            if not candidates:
                logger.error("No candidates in API response")
                return False

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if not parts:
                logger.error("No parts in API response content")
                return False

            inline_data = parts[0].get("inlineData", {})
            if not inline_data.get("data"):
                logger.error("No image data in API response")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating API response: {e}")
            return False

    async def _save_image_result(
        self,
        result: Dict[str, Any],
        output_path: Optional[Union[str, Path]],
        prompt: str
    ) -> Path:
        """Extract and save image from API result."""
        # Extract image data
        candidates = result["candidates"]
        content = candidates[0]["content"]
        parts = content["parts"][0]
        inline_data = parts["inlineData"]
        img_data = inline_data["data"]

        # Determine output path
        if output_path:
            image_path = Path(output_path)
            image_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            # Create descriptive filename
            import hashlib
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
            image_path = Path(f"generated_image_{prompt_hash}.png")

        # Save image
        with open(image_path, 'wb') as f:
            f.write(base64.b64decode(img_data))

        logger.info(f"Image saved to: {image_path}")
        return image_path

    def _resolution_to_aspect_ratio(self, resolution: str) -> str:
        """Convert resolution to aspect ratio."""
        try:
            width, height = map(int, resolution.split(':'))

            # Common aspect ratios
            if width == height:
                return "1:1"
            elif width / height == 16 / 9:
                return "16:9"
            elif width / height == 4 / 3:
                return "4:3"
            elif width / height == 3 / 2:
                return "3:2"
            else:
                # Default to 16:9 for other ratios
                logger.warning(f"Unusual aspect ratio {width}:{height}, using 16:9")
                return "16:9"

        except Exception:
            logger.warning(f"Invalid resolution format: {resolution}, using 16:9")
            return "16:9"

    def _resolution_to_size(self, resolution: str) -> str:
        """Convert resolution to APIYi size parameter."""
        try:
            width, height = map(int, resolution.split(':'))

            # Determine size based on total pixels
            total_pixels = width * height

            if total_pixels >= 2048 * 2048:
                return "2K"
            elif total_pixels >= 1024 * 1024:
                return "1080p"
            elif total_pixels >= 512 * 512:
                return "720p"
            else:
                return "480p"

        except Exception:
            return "1080p"  # Default

    def _build_enhanced_prompt(self, prompt: str, style: Optional[str]) -> str:
        """Build enhanced prompt with style information."""
        if style:
            # Map common styles to descriptive terms
            style_mappings = {
                "oil_painting": "oil painting style, painted with oil brushes, textured brushstrokes",
                "watercolor": "watercolor painting style, soft and flowing colors",
                "digital_art": "digital art style, crisp and clean lines",
                "realistic": "photorealistic style, highly detailed and lifelike",
                "cartoon": "cartoon style, vibrant colors and simplified forms",
                "anime": "anime style, Japanese animation aesthetic",
                "sketch": "pencil sketch style, hand-drawn with pencil",
                "abstract": "abstract art style, non-representational forms"
            }

            style_desc = style_mappings.get(style.lower(), f"{style} style")
            enhanced_prompt = f"{prompt}, {style_desc}, high quality, detailed"
        else:
            enhanced_prompt = f"{prompt}, high quality, detailed"

        return enhanced_prompt

    async def validate_prompt(self, prompt: str) -> bool:
        """Validate prompt for APIYi API."""
        if not prompt or not prompt.strip():
            raise ValidationError("Prompt cannot be empty", field_name="prompt")

        # APIYi may have different length limits
        if len(prompt) > 1000:
            raise ValidationError(
                "Prompt too long for APIYi (max 1000 characters)",
                field_name="prompt",
                field_value=len(prompt)
            )

        # Check for inappropriate content (basic filtering)
        inappropriate_words = ["violence", "nudity", "hate", "explicit"]
        prompt_lower = prompt.lower()
        for word in inappropriate_words:
            if word in prompt_lower:
                raise ValidationError(
                    f"Prompt contains inappropriate content: {word}",
                    field_name="prompt"
                )

        return True

    async def test_connection(self) -> bool:
        """Test APIYi API connection."""
        try:
            # Use a simple test prompt
            test_prompt = "a simple geometric shape"

            result = await self._call_apiyi_api(
                prompt=test_prompt,
                model=self.model,
                aspect_ratio="1:1",
                image_size="480p",
                timeout=30  # Shorter timeout for test
            )

            return result.get("candidates") is not None

        except Exception as e:
            logger.warning(f"APIAyi connection test failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the configured model."""
        return {
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.default_timeout,
            "supported_aspect_ratios": ["1:1", "16:9", "4:3", "3:2"],
            "supported_sizes": ["480p", "720p", "1080p", "2K"]
        }