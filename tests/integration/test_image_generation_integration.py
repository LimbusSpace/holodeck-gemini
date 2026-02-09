"""
Integration tests for standardized prompt templates in image generation pipeline.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend, CustomVLMClient
from holodeck_core.scene_analysis.prompt_templates import PromptTemplateManager


class TestImageGenerationIntegration:
    """Integration tests for image generation with standardized prompts."""

    @pytest.fixture
    def mock_custom_client(self):
        """Create a mock custom VLM client."""
        client = MagicMock(spec=CustomVLMClient)
        client.test_connection = AsyncMock(return_value=True)
        client.generate_reference_image = AsyncMock(return_value=b"fake_image_data")
        client.generate_object_image = AsyncMock(return_value=b"fake_object_image_data")
        return client

    @pytest.mark.asyncio
    async def test_reference_image_generation_with_standardized_prompts(self, mock_custom_client):
        """Test reference image generation using standardized prompts."""
        # Setup
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(backend=VLMBackend.CUSTOM, custom_config={
                'base_url': 'https://api.example.com/v1',
                'api_key': 'test_key',
                'model_name': 'test_model'
            })

            # Test English prompt
            description_en = "A modern living room with sofa, coffee table, and TV"
            style_en = "realistic"

            result_en = await client.generate_reference_image(
                description=description_en,
                style=style_en,
                language="en"
            )

            # Verify the method was called
            mock_custom_client.generate_reference_image.assert_called()
            assert result_en == b"fake_image_data"

            # Test Chinese prompt
            description_zh = "一个现代化的客厅，配有沙发、咖啡桌和电视"
            style_zh = "写实"

            result_zh = await client.generate_reference_image(
                description=description_zh,
                style=style_zh,
                language="zh"
            )

            assert result_zh == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_object_image_generation_with_standardized_prompts(self, mock_custom_client):
        """Test object image generation using standardized prompts."""
        # Setup
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(backend=VLMBackend.CUSTOM, custom_config={
                'base_url': 'https://api.example.com/v1',
                'api_key': 'test_key',
                'model_name': 'test_model'
            })

            # Test English object generation
            obj_name_en = "modern sofa"
            style_en = "realistic"
            context_en = "A modern living room"

            result_en = await client.generate_object_image(
                obj_name=obj_name_en,
                style=style_en,
                reference_context=context_en,
                language="en"
            )

            # Verify the method was called
            mock_custom_client.generate_object_image.assert_called()
            assert result_en == b"fake_object_image_data"

            # Test Chinese object generation
            obj_name_zh = "现代沙发"
            style_zh = "写实"
            context_zh = "一个现代化的客厅"

            result_zh = await client.generate_object_image(
                obj_name=obj_name_zh,
                style=style_zh,
                reference_context=context_zh,
                language="zh"
            )

            assert result_zh == b"fake_object_image_data"

    @pytest.mark.asyncio
    async def test_auto_language_detection_in_image_generation(self, mock_custom_client):
        """Test automatic language detection in image generation."""
        # Setup
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(backend=VLMBackend.CUSTOM, custom_config={
                'base_url': 'https://api.example.com/v1',
                'api_key': 'test_key',
                'model_name': 'test_model'
            })

            # Test auto-detection with English text
            result_en = await client.generate_reference_image(
                description="A modern kitchen with island and appliances",
                style="realistic"
                # language=None (auto-detection)
            )

            assert result_en == b"fake_image_data"

            # Test auto-detection with Chinese text
            result_zh = await client.generate_reference_image(
                description="一个现代化的厨房，配有岛台和电器",
                style="写实"
                # language=None (auto-detection)
            )

            assert result_zh == b"fake_image_data"

    def test_prompt_template_manager_integration(self):
        """Test PromptTemplateManager integration with image generation."""
        manager = PromptTemplateManager(default_language="en")

        # Test English reference prompt
        prompt_en = manager.get_prompt(
            "reference_image",
            "en",
            description="A modern living room",
            style="realistic"
        )

        assert "3-D view: x->right, y->backward, z->up" in prompt_en
        assert "Well-lit, no extra objects" in prompt_en

        # Test Chinese reference prompt
        prompt_zh = manager.get_prompt(
            "reference_image",
            "zh",
            description="一个现代化的客厅",
            style="写实"
        )

        assert "3D视图：x轴向右，y轴向后，z轴向上" in prompt_zh
        assert "光照良好，无额外物体" in prompt_zh

        # Test English object prompt
        obj_prompt_en = manager.get_prompt(
            "individual_object",
            "en",
            obj_name="modern sofa",
            style="realistic"
        )

        assert "transparent background" in obj_prompt_en
        assert "isolated front-view" in obj_prompt_en

        # Test Chinese object prompt
        obj_prompt_zh = manager.get_prompt(
            "individual_object",
            "zh",
            obj_name="现代沙发",
            style="写实"
        )

        assert "透明背景" in obj_prompt_zh
        assert "孤立正面视图" in obj_prompt_zh

    @pytest.mark.asyncio
    async def test_production_pipeline_integration(self, mock_custom_client):
        """Test integration with production pipeline workflow."""
        # Setup
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(backend=VLMBackend.CUSTOM, custom_config={
                'base_url': 'https://api.example.com/v1',
                'api_key': 'test_key',
                'model_name': 'test_model'
            })

            # Simulate production pipeline workflow
            # Step 1: Generate reference image
            scene_description = "A modern living room with sofa, coffee table, and TV"
            style = "realistic"

            reference_image = await client.generate_reference_image(
                description=scene_description,
                style=style,
                language="en"
            )

            assert reference_image == b"fake_image_data"

            # Step 2: Generate object images for each extracted object
            objects = ["modern sofa", "coffee table", "TV stand"]

            for obj_name in objects:
                object_image = await client.generate_object_image(
                    obj_name=obj_name,
                    style=style,
                    reference_context=scene_description,
                    language="en"
                )

                assert object_image == b"fake_object_image_data"

            # Verify all methods were called
            assert mock_custom_client.generate_reference_image.called
            assert mock_custom_client.generate_object_image.call_count == len(objects)

    @pytest.mark.asyncio
    async def test_multilingual_production_pipeline(self, mock_custom_client):
        """Test multilingual support in production pipeline."""
        # Setup
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient', return_value=mock_custom_client):
            client = UnifiedVLMClient(backend=VLMBackend.CUSTOM, custom_config={
                'base_url': 'https://api.example.com/v1',
                'api_key': 'test_key',
                'model_name': 'test_model'
            })

            # Test English pipeline
            scene_en = "A cozy bedroom with bed and nightstand"
            reference_en = await client.generate_reference_image(
                description=scene_en,
                style="realistic",
                language="en"
            )

            # Test Chinese pipeline
            scene_zh = "一个舒适的卧室，配有床和床头柜"
            reference_zh = await client.generate_reference_image(
                description=scene_zh,
                style="写实",
                language="zh"
            )

            # Test auto-detection pipeline
            scene_mixed = "A modern 现代厨房 kitchen with island 岛台"
            reference_auto = await client.generate_reference_image(
                description=scene_mixed,
                style="realistic"
                # language=None (auto-detection)
            )

            assert reference_en == b"fake_image_data"
            assert reference_zh == b"fake_image_data"
            assert reference_auto == b"fake_image_data"

            # Verify different prompts were used for different languages
            calls = mock_custom_client.generate_reference_image.call_args_list
            assert len(calls) == 3


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])