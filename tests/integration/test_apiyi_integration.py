#!/usr/bin/env python3
"""
APIAyi integration tests.

Tests the integration of APIYi client with the Holodeck pipeline.
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from holodeck_core.image_generation.apiyi_client import APIYiClient
from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
from holodeck_core.clients.factory import ImageClientFactory
from holodeck_core.clients.base import GenerationResult


@pytest.fixture
def mock_api_key():
    """Mock API key for testing."""
    return "sk-test-api-key-12345"


@pytest.fixture
def apiyi_client(mock_api_key):
    """Create APIYi client for testing."""
    with patch.dict('os.environ', {'APIAYI_API_KEY': mock_api_key}):
        client = APIYiClient()
        return client


@pytest.fixture
def mock_successful_response():
    """Mock successful API response."""
    import base64
    # Create a minimal 1x1 PNG image for testing
    png_data = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xdd\xcc\xdb\xb4\x00\x00\x00\x00IEND\xaeB`\x82').decode()

    return {
        "candidates": [{
            "content": {
                "parts": [{
                    "inlineData": {
                        "data": png_data,
                        "mimeType": "image/png"
                    }
                }]
            }
        }]
    }


class TestAPIYiClient:
    """Test APIYi client functionality."""

    def test_validate_configuration_success(self, apiyi_client, mock_api_key):
        """Test successful configuration validation."""
        with patch.dict('os.environ', {'APIAYI_API_KEY': mock_api_key}):
            result = apiyi_client.validate_configuration()
            assert result is True

    def test_validate_configuration_missing_key(self, apiyi_client):
        """Test configuration validation with missing API key."""
        with patch.dict('os.environ', {'APIAYI_API_KEY': ''}):
            with pytest.raises(Exception) as exc_info:
                apiyi_client.validate_configuration()
            assert "APIAYI_API_KEY" in str(exc_info.value)

    def test_validate_configuration_placeholder_key(self, apiyi_client):
        """Test configuration validation with placeholder API key."""
        with patch.dict('os.environ', {'APIAYI_API_KEY': 'sk-your-api-key'}):
            with pytest.raises(Exception) as exc_info:
                apiyi_client.validate_configuration()
            assert "placeholder" in str(exc_info.value).lower()

    def test_resolution_to_aspect_ratio(self, apiyi_client):
        """Test resolution to aspect ratio conversion."""
        test_cases = [
            ("1024:1024", "1:1"),
            ("1920:1080", "16:9"),
            ("1024:768", "4:3"),
            ("1536:1024", "3:2"),
            ("800:600", "16:9"),  # Should default to 16:9
            ("invalid", "16:9")  # Should handle invalid input
        ]

        for resolution, expected_ratio in test_cases:
            ratio = apiyi_client._resolution_to_aspect_ratio(resolution)
            assert ratio == expected_ratio, f"Failed for {resolution}: got {ratio}, expected {expected_ratio}"

    def test_resolution_to_size(self, apiyi_client):
        """Test resolution to image size conversion."""
        test_cases = [
            ("2048:2048", "2K"),
            ("1920:1080", "1080p"),
            ("1280:720", "720p"),
            ("800:600", "480p"),
            ("512:512", "480p"),
            ("invalid", "1080p")  # Default
        ]

        for resolution, expected_size in test_cases:
            size = apiyi_client._resolution_to_size(resolution)
            assert size == expected_size, f"Failed for {resolution}: got {size}, expected {expected_size}"

    def test_build_enhanced_prompt(self, apiyi_client):
        """Test enhanced prompt building."""
        test_cases = [
            ("a cat", None, "a cat, high quality, detailed"),
            ("a cat", "oil_painting", "a cat, oil painting style, painted with oil brushes, textured brushstrokes, high quality, detailed"),
            ("a cat", "watercolor", "a cat, watercolor painting style, soft and flowing colors, high quality, detailed"),
            ("a cat", "unknown_style", "a cat, unknown_style style, high quality, detailed")
        ]

        for prompt, style, expected in test_cases:
            enhanced = apiyi_client._build_enhanced_prompt(prompt, style)
            assert enhanced == expected, f"Failed for {prompt} + {style}: got {enhanced}, expected {expected}"

    @pytest.mark.asyncio
    async def test_validate_prompt(self, apiyi_client):
        """Test prompt validation."""
        # Valid prompts
        valid_prompts = [
            "a beautiful landscape",
            "a cat in a garden",
            "x" * 500  # Under limit
        ]

        for prompt in valid_prompts:
            result = await apiyi_client.validate_prompt(prompt)
            assert result is True

        # Invalid prompts
        invalid_prompts = [
            "",  # Empty
            "   ",  # Whitespace only
            "x" * 1001,  # Over limit
            "violent content",  # Inappropriate
            "nudity in art"  # Inappropriate
        ]

        for prompt in invalid_prompts:
            with pytest.raises(Exception):
                await apiyi_client.validate_prompt(prompt)

    @pytest.mark.asyncio
    async def test_generate_image_success(self, apiyi_client, mock_successful_response):
        """Test successful image generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_output.png"

            with patch('aiohttp.ClientSession.post') as mock_post:
                # Mock the API response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=mock_successful_response)
                mock_post.return_value.__aenter__.return_value = mock_response

                result = await apiyi_client.generate_image(
                    prompt="a test image",
                    resolution="1024:1024",
                    output_path=output_path
                )

                assert result.success is True
                assert result.data == str(output_path)
                assert Path(result.data).exists()
                assert result.metadata["backend"] == "apiyi"
                assert "generation_time" in result.metadata

    @pytest.mark.asyncio
    async def test_generate_image_api_error(self, apiyi_client):
        """Test image generation with API error."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock API error response
            mock_response = AsyncMock()
            mock_response.status = 401
            mock_response.text = AsyncMock(return_value="Invalid API key")
            mock_post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(Exception) as exc_info:
                await apiyi_client.generate_image(
                    prompt="a test image",
                    resolution="1024:1024"
                )

            assert "401" in str(exc_info.value) or "Invalid API key" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_image_timeout(self, apiyi_client):
        """Test image generation timeout handling."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock timeout
            mock_post.side_effect = asyncio.TimeoutError()

            with pytest.raises(Exception) as exc_info:
                await apiyi_client.generate_image(
                    prompt="a test image",
                    resolution="1024:1024",
                    timeout=1  # Short timeout for testing
                )

            assert "timeout" in str(exc_info.value).lower()


class TestAPIYiFactoryIntegration:
    """Test APIYi integration with client factory."""

    def test_factory_registration(self):
        """Test that APIYi client is registered in factory."""
        factory = ImageClientFactory()
        available_clients = factory.get_available_clients()
        assert "apiyi" in available_clients

    @pytest.mark.asyncio
    async def test_factory_create_client(self, mock_api_key):
        """Test creating APIYi client through factory."""
        with patch.dict('os.environ', {'APIAYI_API_KEY': mock_api_key}):
            factory = ImageClientFactory()

            # Test specific client creation
            client = factory.create_client("apiyi")
            assert isinstance(client, APIYiClient)

    def test_factory_configuration_check(self, mock_api_key):
        """Test factory configuration checking."""
        with patch.dict('os.environ', {'APIAYI_API_KEY': mock_api_key}):
            factory = ImageClientFactory()
            client_info = factory.get_client_info()
            assert "apiyi" in client_info["configured_clients"]

        # Test without API key
        with patch.dict('os.environ', {'APIAYI_API_KEY': ''}):
            factory = ImageClientFactory()
            client_info = factory.get_client_info()
            assert "apiyi" not in client_info["configured_clients"]


class TestAPIYiUnifiedClient:
    """Test APIYi integration with unified client."""

    @pytest.mark.asyncio
    async def test_unified_client_with_apiyi(self, mock_api_key, mock_successful_response):
        """Test unified client using APIYi backend."""
        with patch.dict('os.environ', {'APIAYI_API_KEY': mock_api_key}):
            with patch('aiohttp.ClientSession.post') as mock_post:
                # Mock the API response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=mock_successful_response)
                mock_post.return_value.__aenter__.return_value = mock_response

                unified_client = UnifiedImageClient()
                unified_client.initialize()

                result = await unified_client.generate_image(
                    prompt="a test image",
                    resolution="1024:1024",
                    backend="apiyi"
                )

                assert result.success is True
                assert result.metadata["backend"] == "apiyi"

    @pytest.mark.asyncio
    async def test_unified_client_auto_selection(self, mock_api_key, mock_successful_response):
        """Test unified client auto-selecting APIYi."""
        with patch.dict('os.environ', {'APIAYI_API_KEY': mock_api_key}):
            with patch('aiohttp.ClientSession.post') as mock_post:
                # Mock the API response
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value=mock_successful_response)
                mock_post.return_value.__aenter__.return_value = mock_response

                unified_client = UnifiedImageClient()
                unified_client.initialize()

                result = await unified_client.generate_image(
                    prompt="a test image",
                    resolution="1024:1024"
                    # No backend specified - should auto-select APIYi
                )

                assert result.success is True
                # Should select APIYi as it's in priority order and configured
                assert result.metadata["backend"] == "apiyi"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])