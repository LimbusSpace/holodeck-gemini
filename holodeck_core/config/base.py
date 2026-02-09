#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Configuration Management System

Provides centralized configuration management with environment variable handling,
caching, and standardized loading patterns for all Holodeck components.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union
from functools import lru_cache


logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading fails"""
    pass


class ConfigManager:
    """
    Unified configuration management with environment variable handling and caching.

    Features:
    - Automatic .env file loading from multiple locations
    - Configuration value caching for performance
    - Type conversion and validation
    - Fallback value support
    - Standardized error handling
    """

    _instance = None
    _config_cache = {}
    _env_loaded = False

    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize configuration manager"""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._env_paths = [
                '.env',
                '../.env',
                '../../.env',
                '../../../.env',
                Path.home() / '.holodeck' / '.env'
            ]

    def ensure_env_loaded(self) -> bool:
        """
        Ensure environment variables are loaded from .env files.

        Returns:
            True if environment was loaded successfully
        """
        if self._env_loaded:
            return True

        loaded = False

        # Try to load with python-dotenv first
        try:
            from dotenv import load_dotenv
            for env_path in self._env_paths:
                env_path = Path(env_path)
                if env_path.exists():
                    load_dotenv(env_path)
                    # 检查是否在JSON模式下，避免污染输出
                    json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
                    if not json_mode:
                        logger.info(f"Loaded environment variables from {env_path}")
                    loaded = True
                    break
        except ImportError:
            logger.debug("python-dotenv not available, using manual loading")
        except Exception as e:
            # 检查是否在JSON模式下，避免污染输出
            json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
            if not json_mode:
                logger.warning(f"Failed to load with dotenv: {e}, trying manual loading")

        # Manual loading as fallback
        if not loaded:
            loaded = self._manual_env_loading()

        self._env_loaded = loaded
        return loaded

    def _manual_env_loading(self) -> bool:
        """Manual environment variable loading from .env files"""
        for env_path in self._env_paths:
            env_path = Path(env_path)
            if env_path.exists():
                try:
                    self._load_env_file(env_path)
                    # 检查是否在JSON模式下，避免污染输出
                    json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
                    if not json_mode:
                        logger.info(f"Manually loaded environment variables from {env_path}")
                    return True
                except Exception as e:
                    # 检查是否在JSON模式下，避免污染输出
                    json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
                    if not json_mode:
                        logger.warning(f"Failed to manually load {env_path}: {e}")

        # 检查是否在JSON模式下，避免污染输出
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
        if not json_mode:
            logger.warning("No .env file found in standard locations")
        return False

    def _load_env_file(self, env_path: Path) -> None:
        """Load environment variables from a specific .env file"""
        with open(env_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse key=value pairs
                if '=' in line:
                    try:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove surrounding quotes if present
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]

                        # Set environment variable if not already set
                        if key and not os.getenv(key):
                            os.environ[key] = value
                            # 检查是否在JSON模式下，避免污染输出
                            json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
                            if not json_mode:
                                logger.debug(f"Set environment variable: {key}")

                    except Exception as e:
                        # 检查是否在JSON模式下，避免污染输出
                        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
                        if not json_mode:
                            logger.warning(f"Failed to parse line {line_num} in {env_path}: {e}")

    @lru_cache(maxsize=128)
    def get_config(self, key: str, default: Any = None,
                   value_type: type = str, required: bool = False) -> Any:
        """
        Get configuration value with caching and type conversion.

        Args:
            key: Configuration key
            default: Default value if key not found
            value_type: Expected type for the value
            required: Whether the configuration key is required

        Returns:
            Configuration value converted to specified type

        Raises:
            ConfigurationError: If required key is missing or type conversion fails
        """
        # Ensure environment is loaded
        self.ensure_env_loaded()

        # Check cache first
        cache_key = f"{key}:{value_type.__name__}"
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # Get value from environment
        value = os.getenv(key)

        if value is None:
            if required:
                raise ConfigurationError(f"Required configuration key '{key}' not found")
            value = default

        # Convert type if needed
        if value is not None:
            try:
                if value_type == bool:
                    value = self._convert_to_bool(value)
                elif value_type in (int, float):
                    value = value_type(value)
                elif value_type == list:
                    value = self._convert_to_list(value)
                elif value_type == dict:
                    value = self._convert_to_dict(value)
            except (ValueError, TypeError) as e:
                raise ConfigurationError(
                    f"Failed to convert configuration key '{key}' to {value_type.__name__}: {e}"
                )

        # Cache the result
        self._config_cache[cache_key] = value
        return value

    def _convert_to_bool(self, value: str) -> bool:
        """Convert string value to boolean"""
        value = value.lower().strip()
        if value in ('true', '1', 'yes', 'on', 'enabled'):
            return True
        elif value in ('false', '0', 'no', 'off', 'disabled'):
            return False
        else:
            raise ValueError(f"Cannot convert '{value}' to boolean")

    def _convert_to_list(self, value: str) -> list:
        """Convert string value to list"""
        import json
        try:
            # Try JSON parsing first
            return json.loads(value)
        except json.JSONDecodeError:
            # Fall back to comma-separated values
            return [item.strip() for item in value.split(',') if item.strip()]

    def _convert_to_dict(self, value: str) -> dict:
        """Convert string value to dictionary"""
        import json
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            raise ValueError(f"Cannot convert '{value}' to dictionary: {e}")

    def get_api_credentials(self, service_name: str) -> Dict[str, str]:
        """
        Get API credentials for a specific service.

        Args:
            service_name: Name of the service (e.g., 'HUNYUAN', 'OPENAI')

        Returns:
            Dictionary containing API credentials
        """
        service_upper = service_name.upper()

        credentials = {
            'api_key': self.get_config(f'{service_upper}_API_KEY'),
            'secret_id': self.get_config(f'{service_upper}_SECRET_ID'),
            'secret_key': self.get_config(f'{service_upper}_SECRET_KEY'),
            'region': self.get_config(f'{service_upper}_REGION', 'ap-guangzhou'),
            'endpoint': self.get_config(f'{service_upper}_ENDPOINT')
        }

        # Remove None values
        return {k: v for k, v in credentials.items() if v is not None}

    def is_service_configured(self, service_name: str) -> bool:
        """
        Check if a service has the required configuration.

        Args:
            service_name: Name of the service to check

        Returns:
            True if service appears to be configured
        """
        credentials = self.get_api_credentials(service_name)

        # Check for common credential patterns
        has_api_key = bool(credentials.get('api_key'))
        has_secret_pair = bool(credentials.get('secret_id') and credentials.get('secret_key'))

        return has_api_key or has_secret_pair

    def clear_cache(self) -> None:
        """Clear the configuration cache"""
        self._config_cache.clear()
        self.get_config.cache_clear()
        # 检查是否在JSON模式下，避免污染输出
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
        if not json_mode:
            logger.info("Configuration cache cleared")

    def reload(self) -> None:
        """Reload configuration from environment files"""
        self.clear_cache()
        self._env_loaded = False
        self.ensure_env_loaded()
        # 检查是否在JSON模式下，避免污染输出
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
        if not json_mode:
            logger.info("Configuration reloaded")


# Convenience functions for easy access
def get_config(key: str, default: Any = None, value_type: type = str,
              required: bool = False) -> Any:
    """Convenience function to get configuration value"""
    return ConfigManager().get_config(key, default, value_type, required)


def get_api_credentials(service_name: str) -> Dict[str, str]:
    """Convenience function to get API credentials"""
    return ConfigManager().get_api_credentials(service_name)


def is_service_configured(service_name: str) -> bool:
    """Convenience function to check if service is configured"""
    return ConfigManager().is_service_configured(service_name)


# Example usage and testing
if __name__ == "__main__":
    # Initialize configuration manager
    config = ConfigManager()

    # Test basic functionality
    print("Testing Configuration Manager:")
    print(f"Environment loaded: {config.ensure_env_loaded()}")

    # Test API credentials loading
    hunyuan_creds = get_api_credentials('HUNYUAN')
    print(f"Hunyuan credentials: {hunyuan_creds}")

    # Test service configuration check
    print(f"Hunyuan configured: {is_service_configured('HUNYUAN')}")
    print(f"OpenAI configured: {is_service_configured('OPENAI')}")