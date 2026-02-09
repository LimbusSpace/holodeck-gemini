"""
Tests for environment variable configuration support in UnifiedVLMClient.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend, CustomVLMClient


class TestEnvironmentVariableConfig:
    """Test environment variable configuration support."""

    def setup_method(self):
        """Clear relevant environment variables before each test."""
        env_vars = [
            "CUSTOM_VLM_BASE_URL",
            "CUSTOM_VLM_API_KEY",
            "CUSTOM_VLM_MODEL_NAME"
        ]
        for var in env_vars:
            if var in os.environ:
                del os.environ[var]

    def teardown_method(self):
        """Clean up environment variables after each test."""
        self.setup_method()

    def test_custom_backend_from_environment_variables(self):
        """Test custom backend configuration from environment variables."""
        # Set environment variables
        os.environ["CUSTOM_VLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["CUSTOM_VLM_API_KEY"] = "test_api_key"
        os.environ["CUSTOM_VLM_MODEL_NAME"] = "test_model"

        # Mock CustomVLMClient to avoid actual API calls
        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient') as mock_custom_client:
            mock_instance = MagicMock()
            mock_custom_client.return_value = mock_instance

            # Create client with custom backend
            client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)

            # Verify backend is available
            assert client._is_backend_available(VLMBackend.CUSTOM) == True

            # Initialize client (this should use environment variables)
            client.ensure_initialized()

            # Verify CustomVLMClient was called with environment variable values
            mock_custom_client.assert_called_once_with(
                base_url="https://api.example.com/v1",
                api_key="test_api_key",
                model_name="test_model",
                headers=None
            )

    def test_custom_backend_environment_variables_not_available(self):
        """Test custom backend when environment variables are not set."""
        # Don't set environment variables
        client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)

        # Verify backend is not available
        assert client._is_backend_available(VLMBackend.CUSTOM) == False

    def test_custom_backend_partial_environment_variables(self):
        """Test custom backend with only some environment variables set."""
        # Set only some environment variables
        os.environ["CUSTOM_VLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["CUSTOM_VLM_API_KEY"] = "test_api_key"
        # Missing CUSTOM_VLM_MODEL_NAME

        client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)

        # Verify backend is not available (all three are required)
        assert client._is_backend_available(VLMBackend.CUSTOM) == False

    def test_custom_backend_precedence_explicit_config_over_env(self):
        """Test that explicit custom_config takes precedence over environment variables."""
        # Set environment variables
        os.environ["CUSTOM_VLM_BASE_URL"] = "https://env.example.com/v1"
        os.environ["CUSTOM_VLM_API_KEY"] = "env_api_key"
        os.environ["CUSTOM_VLM_MODEL_NAME"] = "env_model"

        # Provide explicit custom_config
        explicit_config = {
            "base_url": "https://explicit.example.com/v1",
            "api_key": "explicit_api_key",
            "model_name": "explicit_model"
        }

        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient') as mock_custom_client:
            mock_instance = MagicMock()
            mock_custom_client.return_value = mock_instance

            client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config=explicit_config
            )

            # Initialize client
            client.ensure_initialized()

            # Verify CustomVLMClient was called with explicit config, not env vars
            mock_custom_client.assert_called_once_with(
                base_url="https://explicit.example.com/v1",
                api_key="explicit_api_key",
                model_name="explicit_model",
                headers=None
            )

    def test_custom_backend_missing_environment_variables_error(self):
        """Test error handling when custom backend is requested but no config is available."""
        # Don't set environment variables or provide custom_config
        client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)

        with pytest.raises(ValueError, match="Requested backend VLMBackend.CUSTOM is not available"):
            client.ensure_initialized()

    def test_auto_backend_selection_with_custom_env_vars(self):
        """Test auto backend selection when custom environment variables are available."""
        # Set custom environment variables
        os.environ["CUSTOM_VLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["CUSTOM_VLM_API_KEY"] = "test_api_key"
        os.environ["CUSTOM_VLM_MODEL_NAME"] = "test_model"

        with patch('holodeck_core.scene_analysis.clients.unified_vlm.CustomVLMClient') as mock_custom_client:
            mock_instance = MagicMock()
            mock_custom_client.return_value = mock_instance

            # Create client with auto backend selection
            client = UnifiedVLMClient(backend=VLMBackend.AUTO)

            # Initialize client
            client.ensure_initialized()

            # Verify custom backend was selected and used
            mock_custom_client.assert_called_once()
            call_args = mock_custom_client.call_args
            assert call_args[1]['base_url'] == "https://api.example.com/v1"
            assert call_args[1]['api_key'] == "test_api_key"
            assert call_args[1]['model_name'] == "test_model"

    def test_environment_variable_names(self):
        """Test that the expected environment variable names are used."""
        expected_vars = [
            "CUSTOM_VLM_BASE_URL",
            "CUSTOM_VLM_API_KEY",
            "CUSTOM_VLM_MODEL_NAME"
        ]

        # Verify these are the actual variable names used in the code
        # by setting them and checking if they're recognized
        for var in expected_vars:
            os.environ[var] = "test_value"

        # Set all required variables
        os.environ["CUSTOM_VLM_BASE_URL"] = "https://api.example.com/v1"
        os.environ["CUSTOM_VLM_API_KEY"] = "test_api_key"
        os.environ["CUSTOM_VLM_MODEL_NAME"] = "test_model"

        client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)
        assert client._is_backend_available(VLMBackend.CUSTOM) == True


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])