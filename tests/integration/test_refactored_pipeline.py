#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration Tests for Refactored Visual LLM and 3D Pipeline

Tests the complete refactored pipeline including:
- Configuration management
- Enhanced LLM naming service
- Unified image generation client
- Unified 3D generation client
- Pipeline orchestrator
"""

import asyncio
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from holodeck_core.config.base import ConfigManager, ConfigurationError
from holodeck_core.logging.standardized import StandardizedLogger, setup_logging
from holodeck_core.exceptions.framework import (
    ValidationError, APIError, ImageGenerationError, ThreeDGenerationError, LLMError
)
from holodeck_core.clients.base import GenerationResult, ServiceType
from holodeck_core.clients.factory import ImageClientFactory, ThreeDClientFactory, LLMClientFactory
from holodeck_core.object_gen.enhanced_llm_naming_service import (
    EnhancedLLMNamingService, ImageAnalyzer, CacheManager, NamingResult
)
from holodeck_core.image_generation.unified_image_client import UnifiedImageClient
from holodeck_core.object_gen.unified_3d_client import Unified3DClient
from holodeck_core.integration.pipeline_orchestrator import (
    PipelineOrchestrator, PipelineConfig, PipelineResult
)


class TestConfigurationManagement(unittest.TestCase):
    """Test configuration management system"""

    def setUp(self):
        """Setup test configuration"""
        # Create temporary .env file for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.env_file = self.temp_dir /".env"
        self.env_file.write_text("""
TEST_API_KEY=test_key_123
TEST_SECRET_ID=test_secret_id
TEST_SECRET_KEY=test_secret_key
TEST_REGION=ap-test
""")

    def tearDown(self):
        """Cleanup test files"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_manager_singleton(self):
        """Test ConfigManager singleton pattern"""
        config1 = ConfigManager()
        config2 = ConfigManager()
        self.assertIs(config1, config2)

    def test_env_loading(self):
        """Test environment variable loading"""
        import os

        # Clear any existing env vars
        for key in ['TEST_API_KEY', 'TEST_SECRET_ID', 'TEST_SECRET_KEY']:
            if key in os.environ:
                del os.environ[key]

        config = ConfigManager()
        config._env_paths = [str(self.env_file)]  # Override paths for testing

        # Test loading
        loaded = config.ensure_env_loaded()
        self.assertTrue(loaded)

        # Verify values are loaded
        self.assertEqual(config.get_config('TEST_API_KEY'), 'test_key_123')
        self.assertEqual(config.get_config('TEST_SECRET_ID'), 'test_secret_id')

    def test_config_caching(self):
        """Test configuration value caching"""
        config = ConfigManager()

        # Mock environment variable
        import os
        os.environ['TEST_CACHE_KEY'] = 'cached_value'

        # First access should load from environment
        value1 = config.get_config('TEST_CACHE_KEY')

        # Change environment variable
        os.environ['TEST_CACHE_KEY'] = 'changed_value'

        # Second access should return cached value
        value2 = config.get_config('TEST_CACHE_KEY')

        self.assertEqual(value1, 'cached_value')
        self.assertEqual(value2, 'cached_value')

    def test_type_conversion(self):
        """Test configuration value type conversion"""
        import os
        os.environ['TEST_BOOL_TRUE'] = 'true'
        os.environ['TEST_BOOL_FALSE'] = 'false'
        os.environ['TEST_INT'] = '42'
        os.environ['TEST_FLOAT'] = '3.14'

        config = ConfigManager()

        self.assertTrue(config.get_config('TEST_BOOL_TRUE', value_type=bool))
        self.assertFalse(config.get_config('TEST_BOOL_FALSE', value_type=bool))
        self.assertEqual(config.get_config('TEST_INT', value_type=int), 42)
        self.assertEqual(config.get_config('TEST_FLOAT', value_type=float), 3.14)

    def test_api_credentials(self):
        """Test API credentials retrieval"""
        import os
        os.environ['TEST_API_KEY'] = 'test_api_key'
        os.environ['TEST_REGION'] = 'test_region'

        config = ConfigManager()
        credentials = config.get_api_credentials('TEST')

        self.assertEqual(credentials['api_key'], 'test_api_key')
        self.assertEqual(credentials['region'], 'test_region')


class TestEnhancedLLMNamingService(unittest.IsolatedAsyncioTestCase):
    """Test enhanced LLM naming service"""

    def setUp(self):
        """Setup test naming service"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config_manager = ConfigManager()
        self.naming_service = EnhancedLLMNamingService(
            config_manager=self.config_manager,
            cache_ttl=300,  # 5 minutes for testing
            enable_image_analysis=True
        )

    def tearDown(self):
        """Cleanup test files"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_input_validation(self):
        """Test input validation"""
        with self.assertRaises(ValidationError):
            asyncio.run(self.naming_service.generate_object_name("", "test"))

        with self.assertRaises(ValidationError):
            asyncio.run(self.naming_service.generate_object_name("description", ""))

    @patch('holodeck_core.clients.factory.LLMClientFactory.create_client')
    async def test_naming_generation(self, mock_create_client):
        """Test naming generation with mocked LLM"""
        # Mock LLM client
        mock_client = AsyncMock()
        mock_client.chat_completion.return_value = GenerationResult(
            success=True,
            data={"content": "蒸汽朋克金属机械椅"},
            metadata={}
        )
        mock_create_client.return_value = mock_client

        result = await self.naming_service.generate_object_name(
            description="A futuristic chair with metallic frame",
            object_name="Cyber Chair"
        )

        self.assertIsNotNone(result)
        self.assertEqual(result, "蒸汽朋克金属机械椅")

    def test_cache_functionality(self):
        """Test caching functionality"""
        cache = CacheManager(cache_ttl=1)  # 1 second TTL

        # Create test result
        result = NamingResult(
            original_name="test",
            generated_name="测试",
            style="modern",
            material="metal",
            confidence=0.9,
            analysis_used=False,
            processing_time=0.5
        )

        # Test cache set/get
        cache_key = "test_key"
        cache.set(cache_key, result)
        cached_result = cache.get(cache_key)

        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result.generated_name, "测试")

        # Test cache expiration
        import time
        time.sleep(1.1)  # Wait for expiration
        expired_result = cache.get(cache_key)
        self.assertIsNone(expired_result)

    def test_image_analyzer(self):
        """Test image analyzer"""
        analyzer = ImageAnalyzer(self.config_manager)

        # Create test image
        test_image = self.temp_dir / "test.png"
        test_image.write_bytes(b"fake image data")

        # Test with non-existent image
        with self.assertRaises(ValidationError):
            analyzer.analyze_image(self.temp_dir / "nonexistent.png")

        # Test with unsupported format
        unsupported_image = self.temp_dir / "test.txt"
        unsupported_image.write_text("not an image")
        with self.assertRaises(ValidationError):
            analyzer.analyze_image(unsupported_image)


class TestUnifiedImageClient(unittest.IsolatedAsyncioTestCase):
    """Test unified image generation client"""

    def setUp(self):
        """Setup test image client"""
        self.config_manager = ConfigManager()
        self.image_client = UnifiedImageClient(self.config_manager)

    @patch('holodeck_core.clients.factory.ImageClientFactory.create_client')
    async def test_image_generation(self, mock_create_client):
        """Test image generation with mocked backend"""
        # Mock backend client
        mock_backend = AsyncMock()
        mock_backend.generate_image.return_value = GenerationResult(
            success=True,
            data="test_image.png",
            metadata={"backend": "mock"}
        )
        mock_create_client.return_value = mock_backend

        result = await self.image_client.generate_image(
            prompt="A test image",
            resolution="512:512"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data, "test_image.png")

    def test_input_validation(self):
        """Test input validation"""
        with self.assertRaises(ValidationError):
            self.image_client._validate_inputs("", "512:512")

        with self.assertRaises(ValidationError):
            self.image_client._validate_inputs("test", "invalid")

        with self.assertRaises(ValidationError):
            self.image_client._validate_inputs("test", "99999:99999")  # Too large

    def test_rate_limiter(self):
        """Test rate limiting functionality"""
        from holodeck_core.image_generation.unified_image_client import RateLimiter

        limiter = RateLimiter(requests_per_minute=60, burst_size=2)

        async def test_rate_limiting():
            # First two requests should be immediate
            start = asyncio.get_event_loop().time()
            await limiter.acquire()
            await limiter.acquire()
            immediate_time = asyncio.get_event_loop().time() - start

            # Third request should be delayed
            start = asyncio.get_event_loop().time()
            await limiter.acquire()
            delayed_time = asyncio.get_event_loop().time() - start

            return immediate_time, delayed_time

        immediate, delayed = asyncio.run(test_rate_limiting())
        self.assertLess(immediate, 0.1)  # Should be immediate
        self.assertGreater(delayed, 0.9)  # Should be delayed (~1 second)


class TestUnified3DClient(unittest.IsolatedAsyncioTestCase):
    """Test unified 3D generation client"""

    def setUp(self):
        """Setup test 3D client"""
        self.config_manager = ConfigManager()
        self.threed_client = Unified3DClient(self.config_manager)

    @patch('holodeck_core.clients.factory.ThreeDClientFactory.create_client')
    async def test_3d_generation_from_prompt(self, mock_create_client):
        """Test 3D generation from prompt with mocked backend"""
        # Mock backend client
        mock_backend = AsyncMock()
        mock_backend.generate_3d_from_prompt.return_value = GenerationResult(
            success=True,
            data="test_model.glb",
            metadata={"backend": "mock"}
        )
        mock_create_client.return_value = mock_backend

        result = await self.threed_client.generate_3d_from_prompt(
            prompt="A simple cube",
            output_format="glb"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.data, "test_model.glb")

    def test_input_validation(self):
        """Test input validation"""
        with self.assertRaises(ValidationError):
            self.threed_client._validate_inputs()

        with self.assertRaises(ValidationError):
            self.threed_client._validate_inputs(prompt="")

        with self.assertRaises(ValidationError):
            self.threed_client._validate_inputs(image_path=Path("nonexistent.png"))

    def test_resource_manager(self):
        """Test resource management"""
        from holodeck_core.object_gen.unified_3d_client import ResourceManager

        manager = ResourceManager(cleanup_enabled=True)

        # Create temporary file
        temp_file = manager.create_temp_file(suffix=".glb")
        self.assertTrue(temp_file.exists())
        self.assertIn(temp_file, manager.active_files)

        # Cleanup
        manager.cleanup_file(temp_file)
        self.assertNotIn(temp_file, manager.active_files)


class TestPipelineOrchestrator(unittest.IsolatedAsyncioTestCase):
    """Test pipeline orchestrator"""

    def setUp(self):
        """Setup test pipeline"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.config = PipelineConfig(
            workspace_root=str(self.temp_dir),
            enable_naming=True,
            enable_image_generation=True,
            enable_3d_generation=True
        )
        self.orchestrator = PipelineOrchestrator(self.config)

    def tearDown(self):
        """Cleanup test files"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.object(EnhancedLLMNamingService, 'generate_object_name')
    @patch.object(UnifiedImageClient, 'generate_image')
    @patch.object(Unified3DClient, 'generate_3d_from_image')
    async def test_complete_pipeline(self, mock_3d, mock_image, mock_naming):
        """Test complete pipeline execution with mocked services"""
        # Setup mocks
        mock_naming.return_value = "蒸汽朋克金属机械椅"

        mock_image.return_value = GenerationResult(
            success=True,
            data="generated_image.png",
            metadata={"backend": "mock"}
        )

        mock_3d.return_value = GenerationResult(
            success=True,
            data="generated_model.glb",
            metadata={"backend": "mock"}
        )

        # Execute pipeline
        context = {
            "object_description": "A futuristic cyberpunk chair",
            "object_name": "Cyber Chair",
            "generation_prompt": "A futuristic cyberpunk chair with neon lights"
        }

        result = await self.orchestrator.execute_pipeline(context)

        self.assertTrue(result.success)
        self.assertEqual(len(result.stages), 3)
        self.assertIn("naming", result.stages)
        self.assertIn("image_generation", result.stages)
        self.assertIn("3d_generation", result.stages)

    def test_input_validation(self):
        """Test pipeline input validation"""
        # Missing required fields
        with self.assertRaises(ConfigurationError):
            asyncio.run(self.orchestrator.execute_pipeline({}))

        # Missing object description
        with self.assertRaises(ConfigurationError):
            asyncio.run(self.orchestrator.execute_pipeline({"object_name": "test"}))

    def test_stage_failure_handling(self):
        """Test stage failure handling"""
        # Test that pipeline can handle individual stage failures
        # This would require more complex mocking setup
        pass


class TestIntegrationScenarios(unittest.IsolatedAsyncioTestCase):
    """Test complete integration scenarios"""

    def setUp(self):
        """Setup integration test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        """Cleanup integration test files"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def test_end_to_end_workflow(self):
        """Test end-to-end workflow with real components"""
        # This test would use real components with test configurations
        # For now, we'll test the component integration

        config_manager = ConfigManager()

        # Initialize services
        naming_service = EnhancedLLMNamingService(config_manager)
        image_client = UnifiedImageClient(config_manager)
        threed_client = Unified3DClient(config_manager)

        # Test service initialization
        self.assertIsNotNone(naming_service)
        self.assertIsNotNone(image_client)
        self.assertIsNotNone(threed_client)

    def test_configuration_integration(self):
        """Test configuration integration across components"""
        config_manager = ConfigManager()

        # Test that all components can use the same config manager
        naming_service = EnhancedLLMNamingService(config_manager)
        image_client = UnifiedImageClient(config_manager)
        threed_client = Unified3DClient(config_manager)

        # Verify they all use the same config instance
        self.assertIs(naming_service.config_manager, config_manager)
        self.assertIs(image_client.config_manager, config_manager)
        self.assertIs(threed_client.config_manager, config_manager)

    def test_error_propagation(self):
        """Test error propagation across components"""
        # Test that errors are properly propagated and handled
        # This would test the exception framework integration

        try:
            raise ValidationError("Test validation error", field_name="test")
        except ValidationError as e:
            # Test error conversion
            from holodeck_core.exceptions.framework import ErrorHandler
            error_response = ErrorHandler.create_error_response(e)

            self.assertFalse(error_response["success"])
            self.assertIn("error", error_response)
            self.assertEqual(error_response["error"]["error_code_name"], "VALIDATION_INVALID_FORMAT")


if __name__ == "__main__":
    # Setup logging for tests
    setup_logging(log_level="DEBUG")

    # Run tests
    unittest.main(verbosity=2)