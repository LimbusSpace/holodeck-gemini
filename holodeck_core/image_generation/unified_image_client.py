"""Unified image generation client supporting OpenAI and Gemini protocols."""

import asyncio
import aiohttp
import base64
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Union

from ..clients.base import BaseImageClient, GenerationResult
from ..config.base import get_config
from ..logging.standardized import get_logger
from ..exceptions.framework import ImageGenerationError, APIError, ValidationError

logger = get_logger(__name__)


class UnifiedImageClient(BaseImageClient):
    """Unified client supporting OpenAI and Gemini protocols via env config."""

    def __init__(self, config_manager=None, client_config=None):
        super().__init__(config_manager, None, client_config)
        self.protocol = get_config("IMAGE_GEN_PROTOCOL", "gemini")
        self.base_url = get_config("IMAGE_GEN_BASE_URL", "https://api.apiyi.com/v1beta/models")
        self.api_key = get_config("IMAGE_GEN_API_KEY")
        self.model = get_config("IMAGE_GEN_MODEL", "gemini-3-pro-image-preview")
        self.default_timeout = 300

    def validate_configuration(self) -> bool:
        if not self.api_key:
            raise ValidationError("IMAGE_GEN_API_KEY is required", field_name="api_key")
        if self.api_key.startswith("sk-your") or self.api_key == "your-api-key":
            raise ValidationError("Replace placeholder API key with actual key", field_name="api_key")
        return True

    def _setup_client(self) -> None:
        logger.info(f"UnifiedImageClient initialized: protocol={self.protocol}, model={self.model}")

    async def generate_image(
        self,
        prompt: str,
        resolution: str = "1024:1024",
        style: Optional[str] = None,
        model: str = "default",
        output_path: Optional[Union[str, Path]] = None,
        reference_image: Optional[str] = None,
        **kwargs
    ) -> GenerationResult:
        start_time = time.time()
        try:
            self._validate_inputs(prompt, resolution, **kwargs)
            api_model = model if model != "default" else self.model
            timeout = kwargs.get("timeout", self.default_timeout)

            if self.protocol == "openai":
                result = await self._call_openai_api(prompt, api_model, resolution, timeout)
            else:
                result = await self._call_gemini_api(prompt, api_model, resolution, timeout, reference_image)

            image_path = await self._save_image_result(result, output_path, prompt)
            duration = time.time() - start_time

            return GenerationResult(
                success=True,
                data=str(image_path),
                metadata={
                    "backend": "unified",
                    "protocol": self.protocol,
                    "model": api_model,
                    "prompt": prompt,
                    "resolution": resolution,
                    "style": style,
                    "generation_time": duration
                },
                duration=duration
            )
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            if isinstance(e, (ValidationError, ImageGenerationError)):
                raise
            raise ImageGenerationError(f"API error: {e}", prompt=prompt[:50])

    async def _call_gemini_api(self, prompt: str, model: str, resolution: str, timeout: int, reference_image: Optional[str] = None) -> Dict[str, Any]:
        """Call Gemini-style API."""
        url = f"{self.base_url}/{model}:generateContent"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        aspect_ratio = self._resolution_to_aspect_ratio(resolution)

        parts = [{"text": prompt}]
        if reference_image and Path(reference_image).exists():
            with open(reference_image, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            parts.insert(0, {"inlineData": {"mimeType": "image/png", "data": img_b64}})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": aspect_ratio, "imageSize": self._resolution_to_size(resolution)}
            }
        }

        logger.info(f"Calling Gemini API: {model}")
        return await self._make_request(url, headers, payload, timeout)

    async def _call_openai_api(self, prompt: str, model: str, resolution: str, timeout: int) -> Dict[str, Any]:
        """Call OpenAI-style API."""
        url = f"{self.base_url}/images/generations"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        width, height = resolution.split(":")
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": f"{width}x{height}",
            "response_format": "b64_json"
        }

        logger.info(f"Calling OpenAI API: {model}")
        return await self._make_request(url, headers, payload, timeout)

    async def _make_request(self, url: str, headers: Dict, payload: Dict, timeout: int) -> Dict[str, Any]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers,
                                        timeout=aiohttp.ClientTimeout(total=timeout)) as response:
                    if response.status == 200:
                        return await response.json()
                    error_text = await response.text()
                    raise APIError(f"API error {response.status}: {error_text}")
        except asyncio.TimeoutError:
            raise APIError(f"API timeout after {timeout}s")
        except aiohttp.ClientError as e:
            raise APIError(f"Network error: {e}")

    async def _save_image_result(self, result: Dict[str, Any], output_path: Optional[Union[str, Path]], prompt: str) -> Path:
        if self.protocol == "openai":
            image_base64 = result["data"][0]["b64_json"]
        else:
            image_base64 = result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]

        if output_path:
            image_path = Path(output_path)
            image_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
            image_path = Path(f"generated_image_{prompt_hash}.png")

        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image_base64))

        logger.info(f"Image saved: {image_path}")
        return image_path

    def _resolution_to_aspect_ratio(self, resolution: str) -> str:
        try:
            w, h = map(int, resolution.split(':'))
            if w == h: return "1:1"
            if w / h == 16 / 9: return "16:9"
            if w / h == 4 / 3: return "4:3"
            return "1:1"
        except Exception:
            return "1:1"

    def _resolution_to_size(self, resolution: str) -> str:
        try:
            w, h = map(int, resolution.split(':'))
            total = w * h
            if total >= 2048 * 2048: return "2K"
            if total >= 1024 * 1024: return "1K"
            return "720p"
        except Exception:
            return "1K"

    async def validate_prompt(self, prompt: str) -> bool:
        if not prompt or not prompt.strip():
            raise ValidationError("Prompt cannot be empty", field_name="prompt")
        if len(prompt) > 1000:
            raise ValidationError("Prompt too long (max 1000)", field_name="prompt")
        return True

    async def test_connection(self) -> bool:
        try:
            if self.protocol == "openai":
                return bool(self.api_key)
            result = await self._call_gemini_api("test", self.model, "1:1", 30)
            return result.get("candidates") is not None
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol,
            "model": self.model,
            "base_url": self.base_url,
            "timeout": self.default_timeout
        }


# Backwards compatibility alias
APIYiClient = UnifiedImageClient
