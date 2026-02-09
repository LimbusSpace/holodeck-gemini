"""
Integration tests for Unified VLM Client and Factory Architecture

Tests the integration between UnifiedVLMClient, LLMClientFactory, and SceneAnalyzer.
"""

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from holodeck_core.clients.factory import LLMClientFactory
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend
from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer
from holodeck_core.schemas.scene_objects import SceneData, SceneObject, Vec3


class TestUnifiedVLMIntegration(unittest.TestCase):
    """Test integration between UnifiedVLMClient and factory architecture"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # Mock environment variables
        self.env_patches = [
            patch.dict(os.environ, {}, clear=False),
        ]
        for p in self.env_patches:
            p.start()

    def tearDown(self):
        """Clean up test fixtures"""
        # Stop environment patches
        for p in self.env_patches:
            p.stop()

        # Clean up temporary directory
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_unified_vlm_client_initialization(self):
        """Test UnifiedVLMClient initialization with different backends"""

        # Test auto backend selection
        client = UnifiedVLMClient()
        self.assertEqual(client.backend, VLMBackend.AUTO)
        self.assertIsNone(client._client)
        self.assertFalse(client._initialized)

        # Test specific backend
        client = UnifiedVLMClient(backend=VLMBackend.OPENAI)
        self.assertEqual(client.backend, VLMBackend.OPENAI)

    @patch('holodeck_core.scene_analysis.clients.unified_vlm.is_service_configured')
    @patch.dict(os.environ, {'SILICONFLOW_API_KEY': 'test_key'})
    def test_backend_selection_logic(self, mock_is_configured):
        """Test backend selection logic"""

        mock_is_configured.return_value = False

        # Test SiliconFlow preference when available
        client = UnifiedVLMClient(backend=VLMBackend.AUTO)
        selected_backend = client._select_backend()
        self.assertEqual(selected_backend, VLMBackend.SILICONFLOW)

        # Test OpenAI when SiliconFlow not available
        with patch.dict(os.environ, {}, clear=True):
            mock_is_configured.return_value = True
            client = UnifiedVLMClient(backend=VLMBackend.AUTO)
            selected_backend = client._select_backend()
            self.assertEqual(selected_backend, VLMBackend.OPENAI)

    @patch('holodeck_core.scene_analysis.clients.unified_vlm.is_service_configured')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    def test_unified_vlm_initialization_with_openai(self, mock_is_configured):
        """Test UnifiedVLMClient initialization with OpenAI backend"""

        mock_is_configured.return_value = True

        async def run_test():
            client = UnifiedVLMClient(backend=VLMBackend.OPENAI)
            await client.initialize()

            self.assertTrue(client._initialized)
            self.assertIsNotNone(client._client)

            # Check that the client is properly initialized
            backend_info = client.get_backend_info()
            self.assertEqual(backend_info['current_backend'], VLMBackend.OPENAI)

        asyncio.run(run_test())

    @patch.dict(os.environ, {'SILICONFLOW_API_KEY': 'test_key'})
    def test_unified_vlm_initialization_with_siliconflow(self):
        """Test UnifiedVLMClient initialization with SiliconFlow backend"""

        async def run_test():
            client = UnifiedVLMClient(backend=VLMBackend.SILICONFLOW)
            await client.initialize()

            self.assertTrue(client._initialized)
            self.assertIsNotNone(client._client)

            # Check that the client is properly initialized
            backend_info = client.get_backend_info()
            self.assertEqual(backend_info['current_backend'], VLMBackend.SILICONFLOW)

        asyncio.run(run_test())

    def test_backend_availability_check(self):
        """Test backend availability checking"""

        client = UnifiedVLMClient()

        # Test with no configuration
        self.assertFalse(client._is_backend_available(VLMBackend.OPENAI))
        self.assertFalse(client._is_backend_available(VLMBackend.SILICONFLOW))

        # Test with OpenAI configured
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.is_service_configured', return_value=True):
            self.assertTrue(client._is_backend_available(VLMBackend.OPENAI))

        # Test with SiliconFlow configured
        with patch.dict(os.environ, {'SILICONFLOW_API_KEY': 'test_key'}):
            self.assertTrue(client._is_backend_available(VLMBackend.SILICONFLOW))

    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'})
    @patch('holodeck_core.scene_analysis.clients.openai_client.OpenAIClient.test_connection')
    def test_connection_testing(self, mock_test_connection):
        """Test connection testing functionality"""

        mock_test_connection.return_value = True

        async def run_test():
            client = UnifiedVLMClient(backend=VLMBackend.OPENAI)
            connection_ok = await client.test_connection()
            self.assertTrue(connection_ok)

        asyncio.run(run_test())

    def test_factory_registration(self):
        """Test that UnifiedVLMClient is properly registered in LLMClientFactory"""

        factory = LLMClientFactory()
        available_clients = factory.get_available_clients()

        # Check that unified_vlm is in the available clients
        self.assertIn('unified_vlm', available_clients)

    def test_factory_client_creation(self):
        """Test creating UnifiedVLMClient through factory"""

        factory = LLMClientFactory()

        # Test specific client creation
        try:
            client = factory.create_client(
                client_name="unified_vlm",
                features=["object_extraction", "vision"]
            )
            self.assertIsInstance(client, UnifiedVLMClient)
        except Exception as e:
            # This might fail due to missing API keys, which is expected
            self.assertIn("API key", str(e))

    def test_factory_feature_support(self):
        """Test factory feature support detection"""

        factory = LLMClientFactory()

        # Test VLM features
        vlm_supported = factory._supports_features("unified_vlm", ["object_extraction", "vision"])
        self.assertTrue(vlm_supported)

        # Test unsupported features
        unsupported = factory._supports_features("unified_vlm", ["unsupported_feature"])
        self.assertFalse(unsupported)

    def test_factory_configuration_check(self):
        """Test factory configuration checking"""

        factory = LLMClientFactory()

        # Test without any configuration
        self.assertFalse(factory._is_client_configured("unified_vlm"))

        # Test with OpenAI configured
        with patch('holodeck_core.clients.factory.is_service_configured', return_value=True):
            self.assertTrue(factory._is_client_configured("unified_vlm"))

        # Test with SiliconFlow configured
        with patch.dict(os.environ, {'SILICONFLOW_API_KEY': 'test_key'}):
            self.assertTrue(factory._is_client_configured("unified_vlm"))


class TestSceneAnalyzerFactoryIntegration(unittest.TestCase):
    """Test SceneAnalyzer integration with factory pattern"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scene_analyzer_factory_mode_initialization(self):
        """Test SceneAnalyzer initialization with factory mode"""

        # Test factory mode initialization
        analyzer = SceneAnalyzer(use_factory=True)
        self.assertTrue(analyzer.use_factory)
        self.assertIsNone(analyzer.llm_factory)
        self.assertIsNone(analyzer.vlm_client)

        # Test backward compatibility
        analyzer = SceneAnalyzer(api_key="test_key", use_factory=False)
        self.assertFalse(analyzer.use_factory)
        self.assertEqual(analyzer.api_key, "test_key")

    @patch('holodeck_core.scene_analysis.scene_analyzer.LLMClientFactory')
    def test_scene_analyzer_factory_client_creation(self, mock_factory_class):
        """Test SceneAnalyzer creating clients through factory"""

        # Mock the factory
        mock_factory = Mock()
        mock_factory_class.return_value = mock_factory

        # Mock VLM client creation
        mock_vlm_client = Mock()
        mock_factory.create_client.return_value = mock_vlm_client

        async def run_test():
            analyzer = SceneAnalyzer(use_factory=True)

            # This should trigger factory client creation
            with patch.object(analyzer, '_get_client') as mock_get_client:
                mock_get_client.return_value = mock_vlm_client
                client = analyzer._get_client()

            # Verify factory was called
            mock_factory_class.assert_called_once()
            mock_factory.create_client.assert_called_once_with(
                client_name="unified_vlm",
                features=["object_extraction", "vision"]
            )

        asyncio.run(run_test())

    def test_scene_analyzer_backward_compatibility(self):
        """Test that SceneAnalyzer maintains backward compatibility"""

        # Test traditional initialization still works
        analyzer = SceneAnalyzer(api_key="test_key", use_comfyui=True, use_hunyuan=True)

        self.assertEqual(analyzer.api_key, "test_key")
        self.assertTrue(analyzer.use_comfyui)
        self.assertTrue(analyzer.use_hunyuan)
        self.assertFalse(analyzer.use_factory)  # Should default to False for compatibility


class TestUnifiedVLMFeatureSupport(unittest.TestCase):
    """Test UnifiedVLMClient feature support detection"""

    def test_feature_support_detection(self):
        """Test feature support detection"""

        async def run_test():
            client = UnifiedVLMClient()

            # Test OpenAI features
            with patch('holodeck_core.scene_analysis.clients.unified_vlm.is_service_configured', return_value=True):
                with patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key'}):
                    await client.initialize()

                    # Test supported features
                    self.assertTrue(await client.supports_feature("object_extraction"))
                    self.assertTrue(await client.supports_feature("vision"))
                    self.assertTrue(await client.supports_feature("scene_analysis"))

                    # Test unsupported features
                    self.assertFalse(await client.supports_feature("unsupported_feature"))

        asyncio.run(run_test())

    def test_backend_info(self):
        """Test backend information retrieval"""

        client = UnifiedVLMClient()
        backend_info = client.get_backend_info()

        # Check basic structure
        self.assertIn('current_backend', backend_info)
        self.assertIn('requested_backend', backend_info)
        self.assertIn('available_backends', backend_info)
        self.assertIn('configured_backends', backend_info)
        self.assertIn('client_type', backend_info)

        # Check that available backends include expected options
        expected_backends = [VLMBackend.OPENAI, VLMBackend.SILICONFLOW]
        for backend in expected_backends:
            self.assertIn(backend, backend_info['available_backends'])


class TestErrorHandling(unittest.TestCase):
    """Test error handling in unified VLM architecture"""

    def test_no_backend_available_error(self):
        """Test error when no backends are available"""

        async def run_test():
            # No API keys configured
            with patch.dict(os.environ, {}, clear=True):
                with patch('holodeck_core.scene_analysis.clients.unified_vlm.is_service_configured', return_value=False):
                    client = UnifiedVLMClient(backend=VLMBackend.AUTO)

                    with self.assertRaises(ValueError) as context:
                        await client.initialize()

                    self.assertIn("No VLM backends are available", str(context.exception))

        asyncio.run(run_test())

    def test_unsupported_backend_error(self):
        """Test error when requested backend is not available"""

        async def run_test():
            # No API keys configured
            with patch.dict(os.environ, {}, clear=True):
                with patch('holodeck_core.scene_analysis.clients.unified_vlm.is_service_configured', return_value=False):
                    client = UnifiedVLMClient(backend=VLMBackend.OPENAI)

                    with self.assertRaises(ValueError) as context:
                        await client.initialize()

                    self.assertIn("Requested backend", str(context.exception))

        asyncio.run(run_test())

    def test_object_extraction_fallback(self):
        """Test fallback mechanism when primary backend fails"""

        async def run_test():
            # Mock a failing primary backend
            with patch('holodeck_core.scene_analysis.clients.openai_client.OpenAIClient') as mock_openai:
                mock_openai.return_value.extract_objects.side_effect = Exception("API Error")

                with patch('holodeck_core.scene_analysis.clients.siliconflow_client.SiliconFlowClient') as mock_siliconflow:
                    mock_siliconflow.return_value.extract_objects.return_value = SceneData(
                        scene_style="modern",
                        objects=[]
                    )

                    with patch.dict(os.environ, {
                        'OPENAI_API_KEY': 'test_key',
                        'SILICONFLOW_API_KEY': 'test_key'
                    }):
                        client = UnifiedVLMClient(backend=VLMBackend.OPENAI)
                        await client.initialize()

                        # This should trigger fallback to SiliconFlow
                        scene_data = await client.extract_objects("test scene")

                        # Should return empty scene data due to fallback
                        self.assertIsInstance(scene_data, SceneData)

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()