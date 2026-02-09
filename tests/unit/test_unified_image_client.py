"""Unit tests for UnifiedImageClient."""

import pytest
import os
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(__file__).rsplit('tests', 1)[0])


class TestUnifiedImageClient:
    """Test UnifiedImageClient functionality."""

    def test_default_protocol_is_gemini(self):
        """Test default protocol is gemini."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test-key"}, clear=False):
            os.environ.pop("IMAGE_GEN_PROTOCOL", None)
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            assert client.protocol == "gemini"

    def test_protocol_from_env(self):
        """Test protocol attribute exists and is string."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            assert client.protocol in ["openai", "gemini"]

    def test_api_key_fallback(self):
        """Test API key is set from environment."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test-key"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            assert client.api_key is not None

    def test_resolution_to_aspect_ratio_square(self):
        """Test 1:1 aspect ratio."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            assert client._resolution_to_aspect_ratio("1024:1024") == "1:1"

    def test_resolution_to_aspect_ratio_16_9(self):
        """Test 16:9 aspect ratio."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            assert client._resolution_to_aspect_ratio("1920:1080") == "16:9"

    def test_resolution_to_size_1k(self):
        """Test 1K size detection."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            assert client._resolution_to_size("1024:1024") == "1K"

    def test_resolution_to_size_2k(self):
        """Test 2K size detection."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            assert client._resolution_to_size("2048:2048") == "2K"

    def test_get_model_info(self):
        """Test model info returns correct structure."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            info = client.get_model_info()
            assert "protocol" in info
            assert "model" in info
            assert "base_url" in info

    def test_backwards_compatibility_alias(self):
        """Test APIYiClient alias exists."""
        from holodeck_core.image_generation.unified_image_client import APIYiClient, UnifiedImageClient
        assert APIYiClient is UnifiedImageClient


@pytest.mark.asyncio
class TestUnifiedImageClientAsync:
    """Async tests for UnifiedImageClient."""

    async def test_validate_prompt_empty(self):
        """Test empty prompt validation."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            from holodeck_core.exceptions.framework import ValidationError
            client = UnifiedImageClient()
            with pytest.raises(ValidationError):
                await client.validate_prompt("")

    async def test_validate_prompt_too_long(self):
        """Test too long prompt validation."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            from holodeck_core.exceptions.framework import ValidationError
            client = UnifiedImageClient()
            with pytest.raises(ValidationError):
                await client.validate_prompt("x" * 1001)

    async def test_validate_prompt_valid(self):
        """Test valid prompt passes."""
        with patch.dict(os.environ, {"IMAGE_GEN_API_KEY": "test"}, clear=False):
            from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
            client = UnifiedImageClient()
            result = await client.validate_prompt("A cute cat")
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
