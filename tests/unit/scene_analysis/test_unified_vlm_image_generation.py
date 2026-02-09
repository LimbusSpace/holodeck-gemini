"""
Unit tests for image generation functionality in UnifiedVLMClient.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend, CustomVLMClient


class TestUnifiedVLMImageGeneration:
    """Test image generation methods in UnifiedVLMClient."""

    @pytest.fixture
    def mock_custom_client(self):
        """Create a mock custom VLM client with image generation methods."""
        client = MagicMock(spec=CustomVLMClient)
        client.test_connection = AsyncMock(return_value=True)
        client.generate_reference_image = AsyncMock(return_value=b"fake_reference_image")
        client.generate_object_image = AsyncMock(return_value=b"fake_object_image")
        return client

    @pytest.mark.asyncio
    async def test_generate_reference_image_success(self, mock_custom_client):
        """Test successful reference image generation."""
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={
                    'base_url': 'https://api.example.com/v1',
                    'api_key': 'test_key',
                    'model_name': 'test_model'
                }
            )

            result = await client.generate_reference_image(
                description="A modern living room",
                style="realistic",
                language="en"
            )

            # Verify the result
            assert result == b"fake_reference_image"

            # Verify the method was called with correct parameters
            mock_custom_client.generate_reference_image.assert_called_once_with(
                "A modern living room", "realistic", "en"
            )

    @pytest.mark.asyncio
    async def test_generate_object_image_success(self, mock_custom_client):
        """Test successful object image generation."""
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={
                    'base_url': 'https://api.example.com/v1',
                    'api_key': 'test_key',
                    'model_name': 'test_model'
                }
            )

            result = await client.generate_object_image(
                obj_name="modern sofa",
                style="realistic",
                reference_context="A modern living room",
                language="en"
            )

            # Verify the result
            assert result == b"fake_object_image"

            # Verify the method was called with correct parameters
            mock_custom_client.generate_object_image.assert_called_once_with(
                "modern sofa", "realistic", "A modern living room", "en"
            )

    @pytest.mark.asyncio
    async def test_generate_reference_image_no_client(self):
        """Test reference image generation when no client is available."""
        client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)  # No custom config

        with pytest.raises(ValueError, match="Requested backend VLMBackend.CUSTOM is not available"):
            await client.generate_reference_image(
                description="A modern living room",
                style="realistic"
            )

    @pytest.mark.asyncio
    async def test_generate_object_image_no_client(self):
        """Test object image generation when no client is available."""
        client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)  # No custom config

        with pytest.raises(ValueError, match="Requested backend VLMBackend.CUSTOM is not available"):
            await client.generate_object_image(
                obj_name="modern sofa",
                style="realistic"
            )

    @pytest.mark.asyncio
    async def test_generate_reference_image_unsupported_backend(self, mock_custom_client):
        """Test reference image generation with backend that doesn't support it."""
        # Remove the generate_reference_image method to simulate unsupported backend
        del mock_custom_client.generate_reference_image

        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={
                    'base_url': 'https://api.example.com/v1',
                    'api_key': 'test_key',
                    'model_name': 'test_model'
                }
            )

            with pytest.raises(NotImplementedError, match="does not support reference image generation"):
                await client.generate_reference_image(
                    description="A modern living room",
                    style="realistic"
                )

    @pytest.mark.asyncio
    async def test_generate_object_image_unsupported_backend(self, mock_custom_client):
        """Test object image generation with backend that doesn't support it."""
        # Remove the generate_object_image method to simulate unsupported backend
        del mock_custom_client.generate_object_image

        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={
                    'base_url': 'https://api.example.com/v1',
                    'api_key': 'test_key',
                    'model_name': 'test_model'
                }
            )

            with pytest.raises(NotImplementedError, match="does not support object image generation"):
                await client.generate_object_image(
                    obj_name="modern sofa",
                    style="realistic"
                )

    @pytest.mark.asyncio
    async def test_generate_reference_image_backend_error(self, mock_custom_client):
        """Test reference image generation when backend raises an error."""
        # Make the method raise an exception
        mock_custom_client.generate_reference_image.side_effect = Exception("API error")

        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={
                    'base_url': 'https://api.example.com/v1',
                    'api_key': 'test_key',
                    'model_name': 'test_model'
                }
            )

            with pytest.raises(Exception, match="API error"):
                await client.generate_reference_image(
                    description="A modern living room",
                    style="realistic"
                )

    @pytest.mark.asyncio
    async def test_generate_object_image_backend_error(self, mock_custom_client):
        """Test object image generation when backend raises an error."""
        # Make the method raise an exception
        mock_custom_client.generate_object_image.side_effect = Exception("API error")

        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={
                    'base_url': 'https://api.example.com/v1',
                    'api_key': 'test_key',
                    'model_name': 'test_model'
                }
            )

            with pytest.raises(Exception, match="API error"):
                await client.generate_object_image(
                    obj_name="modern sofa",
                    style="realistic"
                )

    @pytest.mark.asyncio
    async def test_multilingual_image_generation(self, mock_custom_client):
        """Test image generation with different languages."""
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={
                    'base_url': 'https://api.example.com/v1',
                    'api_key': 'test_key',
                    'model_name': 'test_model'
                }
            )

            # Test English
            result_en = await client.generate_reference_image(
                description="A modern living room",
                style="realistic",
                language="en"
            )
            assert result_en == b"fake_reference_image"

            # Test Chinese
            result_zh = await client.generate_reference_image(
                description="一个现代化的客厅",
                style="写实",
                language="zh"
            )
            assert result_zh == b"fake_reference_image"

            # Test auto-detection (None language)
            result_auto = await client.generate_reference_image(
                description="A modern living room",
                style="realistic",
                language=None
            )
            assert result_auto == b"fake_reference_image"

            # Verify all three calls were made
            assert mock_custom_client.generate_reference_image.call_count == 3


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])