"""
Integration tests for Custom VLM Model Support
"""

import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, AsyncMock

from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend, CustomVLMClient
from holodeck_core.clients.factory import LLMClientFactory


class TestCustomVLMIntegration(unittest.TestCase):
    """Test integration of custom VLM model support"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()

        # Sample custom configuration
        self.custom_config = {
            "base_url": "https://api.example.com/v1",
            "api_key": "test-api-key",
            "model_name": "custom-model-v1",
            "headers": {"X-Custom-Header": "test-value"}
        }

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_custom_vlm_client_initialization(self):
        """Test CustomVLMClient initialization"""

        client = CustomVLMClient(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model_name="test-model"
        )

        self.assertEqual(client.base_url, "https://api.example.com/v1")
        self.assertEqual(client.api_key, "test-key")
        self.assertEqual(client.model_name, "test-model")

        # Check headers are set correctly
        self.assertIn("Authorization", client.headers)
        self.assertIn("Content-Type", client.headers)
        self.assertEqual(client.headers["Authorization"], "Bearer test-key")

    def test_custom_vlm_client_with_headers(self):
        """Test CustomVLMClient with additional headers"""

        additional_headers = {"X-Custom-Header": "test-value", "X-API-Version": "2023-01-01"}

        client = CustomVLMClient(
            base_url="https://api.example.com/v1",
            api_key="test-key",
            model_name="test-model",
            headers=additional_headers
        )

        # Check that additional headers are preserved
        self.assertEqual(client.headers["X-Custom-Header"], "test-value")
        self.assertEqual(client.headers["X-API-Version"], "2023-01-01")

        # Check that auth headers are still present
        self.assertIn("Authorization", client.headers)

    @patch('aiohttp.ClientSession.post')
    def test_custom_vlm_connection_test(self, mock_post):
        """Test custom VLM connection testing"""

        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response

        async def run_test():
            client = CustomVLMClient(
                base_url="https://api.example.com/v1",
                api_key="test-key",
                model_name="test-model"
            )

            result = await client.test_connection()
            self.assertTrue(result)

        asyncio.run(run_test())

    def test_unified_vlm_custom_backend_selection(self):
        """Test UnifiedVLMClient custom backend selection"""

        # Test custom backend is selected when configured
        client = UnifiedVLMClient(
            backend=VLMBackend.CUSTOM,
            custom_config=self.custom_config
        )

        self.assertEqual(client.backend, VLMBackend.CUSTOM)
        self.assertEqual(client.custom_config, self.custom_config)

    def test_unified_vlm_custom_availability_check(self):
        """Test custom backend availability checking"""

        client = UnifiedVLMClient()

        # Test without custom config
        self.assertFalse(client._is_backend_available(VLMBackend.CUSTOM))

        # Test with incomplete custom config
        client.custom_config = {"base_url": "https://api.example.com"}
        self.assertFalse(client._is_backend_available(VLMBackend.CUSTOM))

        # Test with complete custom config
        client.custom_config = self.custom_config
        self.assertTrue(client._is_backend_available(VLMBackend.CUSTOM))

    def test_unified_vlm_auto_selection_with_custom(self):
        """Test auto backend selection prioritizes custom when available"""

        client = UnifiedVLMClient(
            backend=VLMBackend.AUTO,
            custom_config=self.custom_config
        )

        selected_backend = client._select_backend()
        self.assertEqual(selected_backend, VLMBackend.CUSTOM)

    @patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient')
    def test_unified_vlm_custom_initialization(self, mock_custom_client):
        """Test UnifiedVLMClient initialization with custom backend"""

        mock_instance = AsyncMock()
        mock_custom_client.return_value = mock_instance

        async def run_test():
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config=self.custom_config
            )

            # Initialize should create CustomVLMClient
            await client.initialize()

            # Verify CustomVLMClient was created with correct parameters
            mock_custom_client.assert_called_once_with(
                base_url=self.custom_config["base_url"],
                api_key=self.custom_config["api_key"],
                model_name=self.custom_config["model_name"],
                headers=self.custom_config.get("headers")
            )

        asyncio.run(run_test())

    def test_custom_config_validation(self):
        """Test custom configuration validation"""

        # Test missing required keys
        with self.assertRaises(ValueError):
            UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={"base_url": "https://api.example.com"}  # Missing api_key and model_name
            )

        # Test empty custom config
        with self.assertRaises(ValueError):
            UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config={}
            )

    @patch('aiohttp.ClientSession.post')
    def test_custom_vlm_object_extraction(self, mock_post):
        """Test custom VLM object extraction"""

        # Mock API response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "scene_style": "modern",
                        "objects": [{
                            "name": "test_object",
                            "category": "furniture",
                            "size": [1.0, 1.0, 1.0],
                            "visual_description": "A test object",
                            "position": [0.0, 0.0, 0.0],
                            "rotation": [0.0, 0.0, 0.0],
                            "must_exist": True
                        }]
                    })
                }
            }]
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        async def run_test():
            client = CustomVLMClient(
                base_url="https://api.example.com/v1",
                api_key="test-key",
                model_name="test-model"
            )

            scene_data = await client.extract_objects("A test scene")

            # Verify API was called
            mock_post.assert_called_once()

            # Verify response parsing
            self.assertEqual(len(scene_data.objects), 1)
            self.assertEqual(scene_data.objects[0].name, "test_object")
            self.assertEqual(scene_data.scene_style, "modern")

        asyncio.run(run_test())

    def test_factory_custom_support(self):
        """Test factory support for custom models"""

        # Set environment variable to indicate custom model is available
        with patch.dict(os.environ, {"CUSTOM_VLM_CONFIG": "enabled"}):
            factory = LLMClientFactory()

            # Check that unified_vlm is considered configured
            self.assertTrue(factory._is_client_configured("unified_vlm"))

    @patch('aiohttp.ClientSession.post')
    def test_custom_vlm_fallback_on_error(self, mock_post):
        """Test custom VLM fallback when API fails"""

        # Mock API error
        mock_post.side_effect = Exception("API Error")

        async def run_test():
            client = CustomVLMClient(
                base_url="https://api.example.com/v1",
                api_key="test-key",
                model_name="test-model"
            )

            scene_data = await client.extract_objects("A test scene")

            # Should return fallback data
            self.assertEqual(len(scene_data.objects), 1)
            self.assertEqual(scene_data.objects[0].name, "scene_object")
            self.assertEqual(scene_data.scene_style, "modern")

        asyncio.run(run_test())

    def test_custom_vlm_feature_support(self):
        """Test custom VLM feature support detection"""

        async def run_test():
            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config=self.custom_config
            )

            # Initialize client
            await client.initialize()

            # Test feature support
            self.assertTrue(await client.supports_feature("object_extraction"))
            self.assertTrue(await client.supports_feature("vision"))
            self.assertTrue(await client.supports_feature("scene_analysis"))
            self.assertTrue(await client.supports_feature("custom_model"))
            self.assertFalse(await client.supports_feature("unsupported_feature"))

        asyncio.run(run_test())


class TestCustomVLMEnvironmentConfig(unittest.TestCase):
    """Test environment variable configuration for custom VLM"""

    def setUp(self):
        """Set up environment patches"""
        self.env_patches = [
            patch.dict(os.environ, {}, clear=False),
        ]
        for p in self.env_patches:
            p.start()

    def tearDown(self):
        """Clean up environment patches"""
        for p in self.env_patches:
            p.stop()

    def test_environment_config_loading(self):
        """Test loading custom VLM config from environment variables"""

        # Set environment variables
        os.environ["CUSTOM_VLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["CUSTOM_VLM_API_KEY"] = "env-api-key"
        os.environ["CUSTOM_VLM_MODEL_NAME"] = "env-model"
        os.environ["CUSTOM_VLM_HEADERS"] = '{"X-Env-Header": "env-value"}'

        # Function to load config from environment (as used in demo)
        def load_config_from_env():
            base_url = os.getenv("CUSTOM_VLM_BASE_URL")
            api_key = os.getenv("CUSTOM_VLM_API_KEY")
            model_name = os.getenv("CUSTOM_VLM_MODEL_NAME")
            headers_str = os.getenv("CUSTOM_VLM_HEADERS", "{}")

            if not all([base_url, api_key, model_name]):
                return None

            try:
                headers = json.loads(headers_str)
            except json.JSONDecodeError:
                headers = {}

            return {
                "base_url": base_url,
                "api_key": api_key,
                "model_name": model_name,
                "headers": headers
            }

        config = load_config_from_env()

        self.assertIsNotNone(config)
        self.assertEqual(config["base_url"], "https://api.example.com/v1")
        self.assertEqual(config["api_key"], "env-api-key")
        self.assertEqual(config["model_name"], "env-model")
        self.assertEqual(config["headers"]["X-Env-Header"], "env-value")

    def test_environment_config_missing_values(self):
        """Test environment config loading with missing values"""

        # Set only some environment variables
        os.environ["CUSTOM_VLM_BASE_URL"] = "https://api.example.com/v1"
        # Missing API key and model name

        def load_config_from_env():
            base_url = os.getenv("CUSTOM_VLM_BASE_URL")
            api_key = os.getenv("CUSTOM_VLM_API_KEY")
            model_name = os.getenv("CUSTOM_VLM_MODEL_NAME")

            if not all([base_url, api_key, model_name]):
                return None

            return {"base_url": base_url, "api_key": api_key, "model_name": model_name}

        config = load_config_from_env()
        self.assertIsNone(config)


if __name__ == '__main__':
    unittest.main()