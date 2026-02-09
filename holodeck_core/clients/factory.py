#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Client Factory Pattern Implementation

Provides factory classes for creating different types of clients with
standardized interfaces, configuration management, and fallback mechanisms.
"""

import abc
import logging
import os
from typing import Dict, Any, Optional, Type, Union, List
from pathlib import Path

from ..config.base import ConfigManager, get_config, is_service_configured
from ..logging.standardized import StandardizedLogger, get_logger
from ..exceptions.framework import (
    ConfigurationError, APIError, HolodeckError
)
from .base import (
    BaseClient, BaseImageClient, Base3DClient, BaseLLMClient,
    ServiceType, ClientConfig
)


logger = get_logger(__name__)


class ClientFactory(abc.ABC):
    """
    Abstract base factory class for creating clients.

    Provides common functionality for:
    - Configuration validation
    - Client instantiation
    - Error handling
    - Fallback mechanisms
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize client factory.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(self.__class__.__name__)

        # Registry of available client classes
        self._client_registry: Dict[str, Type[BaseClient]] = {}

    def register_client(self, name: str, client_class: Type[BaseClient]) -> None:
        """
        Register a client class with the factory.

        Args:
            name: Unique name for the client
            client_class: Client class to register
        """
        if not issubclass(client_class, BaseClient):
            raise ConfigurationError(
                f"Client class must inherit from BaseClient: {client_class.__name__}"
            )

        self._client_registry[name] = client_class
        self.logger.info(f"Registered client: {name} -> {client_class.__name__}")

    def unregister_client(self, name: str) -> None:
        """Unregister a client class"""
        if name in self._client_registry:
            del self._client_registry[name]
            self.logger.info(f"Unregistered client: {name}")

    def get_available_clients(self) -> List[str]:
        """Get list of available client names"""
        return list(self._client_registry.keys())

    @abc.abstractmethod
    def create_client(self, client_name: str, **kwargs) -> BaseClient:
        """
        Create a client instance.

        Args:
            client_name: Name of the client to create
            **kwargs: Additional configuration parameters

        Returns:
            Configured client instance

        Raises:
            ConfigurationError: If client creation fails
        """
        pass

    def _validate_client_class(self, client_name: str) -> Type[BaseClient]:
        """Validate that client class exists and is properly configured"""
        if client_name not in self._client_registry:
            raise ConfigurationError(
                f"Unknown client: {client_name}. Available: {list(self._client_registry.keys())}"
            )

        client_class = self._client_registry[client_name]
        return client_class

    def _create_client_config(self, service_type: ServiceType, **kwargs) -> ClientConfig:
        """Create a client configuration"""
        return ClientConfig(
            service_type=service_type,
            timeout=kwargs.get('timeout', 300),
            max_retries=kwargs.get('max_retries', 3),
            retry_delay=kwargs.get('retry_delay', 1.0),
            enable_caching=kwargs.get('enable_caching', True),
            cache_ttl=kwargs.get('cache_ttl', 3600)
        )

    def _create_client_instance(
        self,
        client_class: Type[BaseClient],
        client_config: Optional[ClientConfig] = None,
        **kwargs
    ) -> BaseClient:
        """Create and initialize a client instance"""
        try:
            # Create client instance
            client = client_class(
                config_manager=self.config_manager,
                client_config=client_config
            )

            # Initialize client
            client.initialize()

            self.logger.info(f"Created client instance: {client_class.__name__}")
            return client

        except Exception as e:
            self.logger.error(f"Failed to create client {client_class.__name__}: {e}")
            raise ConfigurationError(
                f"Failed to create client {client_class.__name__}: {e}"
            )


class ImageClientFactory(ClientFactory):
    """
    Factory for creating image generation clients.

    Supports multiple backends with automatic fallback and
    priority-based selection.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__(config_manager)

        # Register default image clients
        self._register_default_clients()

        # Client priority order - 强制只使用 APIYI
        self._priority_order = [
            "apiyi"  # 唯一可用的图像生成后端
        ]

    def _register_default_clients(self) -> None:
        """Register default image generation clients - 强制只注册 APIYI"""
        # Import here to avoid circular imports
        try:
            from ..image_generation.unified_image_client import UnifiedImageClient
            self.register_client("apiyi", UnifiedImageClient)
            self.logger.info("已注册 UnifiedImageClient (唯一可用的图像生成后端)")
        except ImportError as e:
            self.logger.error(f"UnifiedImageClient 不可用: {e}")
            raise ConfigurationError("UnifiedImageClient 不可用，系统强制只使用 APIYI")

        # 强制禁用其他所有图像生成后端
        self.logger.info("已强制禁用 HunyuanImage, ComfyUI, OpenAI DALL-E, Stability API 等其他图像生成后端")

    def create_client(
        self,
        client_name: Optional[str] = None,
        fallback: bool = True,
        **kwargs
    ) -> BaseImageClient:
        """
        Create an image generation client.

        Args:
            client_name: Specific client to create (None for auto-selection)
            fallback: Whether to try fallback clients if primary fails
            **kwargs: Additional configuration parameters

        Returns:
            Configured image generation client

        Raises:
            ConfigurationError: If no suitable client can be created
        """
        if client_name:
            # Create specific client
            return self._create_specific_client(client_name, **kwargs)

        # Auto-select best available client
        return self._create_best_available_client(fallback, **kwargs)

    def _create_specific_client(self, client_name: str, **kwargs) -> BaseImageClient:
        """Create a specific named client"""
        client_class = self._validate_client_class(client_name)

        # Check if client is properly configured
        if not self._is_client_configured(client_name):
            raise ConfigurationError(
                f"Client {client_name} is not properly configured. "
                f"Please check required environment variables."
            )

        client_config = self._create_client_config(ServiceType.IMAGE_GENERATION, **kwargs)
        client = self._create_client_instance(client_class, client_config, **kwargs)

        # Verify client is functional
        if hasattr(client, 'test_connection'):
            import asyncio
            try:
                result = asyncio.run(client.test_connection())
                if not result:
                    raise ConfigurationError(f"Client {client_name} connection test failed")
            except Exception as e:
                raise ConfigurationError(f"Client {client_name} connection test failed: {e}")

        return client

    def _create_best_available_client(self, fallback: bool, **kwargs) -> BaseImageClient:
        """Create the best available client - 强制只使用 APIYI"""

        # 强制只使用 APIYI
        client_name = "apiyi"
        if client_name in self._client_registry and self._is_client_configured(client_name):
            try:
                self.logger.info(f"Creating APIYI client (强制唯一选项)")
                return self._create_specific_client(client_name, **kwargs)
            except ConfigurationError as e:
                # 强制只使用 APIYI，没有fallback选项
                self.logger.error(f"APIAYI 客户端创建失败，系统强制只使用 APIYI: {e}")
                raise ConfigurationError(
                    f"APIAYI 客户端创建失败: {e}。系统强制只使用 APIYI，没有备选方案。"
                )

        # APIYI 不可用
        raise ConfigurationError(
            "APIAYI 不可用。系统强制只使用 APIYI，请确保 APIAYI_API_KEY 环境变量已正确配置。"
        )

    def _is_client_configured(self, client_name: str) -> bool:
        """Check if a client is properly configured - 强制只检查 APIYI"""
        if client_name != "apiyi":
            self.logger.warning(f"客户端 {client_name} 已被强制禁用，系统只使用 APIYI")
            return False

        # 只检查 APIYI 配置
        is_configured = bool(get_config("APIAYI_API_KEY", None))
        if not is_configured:
            self.logger.error("APIAYI_API_KEY 未配置，系统强制只使用 APIYI")
        return is_configured

    def get_client_info(self) -> Dict[str, Any]:
        """Get information about available and configured clients - 强制只显示 APIYI"""
        info = {
            "available_clients": ["apiyi"],  # 强制只显示 APIYI
            "priority_order": self._priority_order,
            "configured_clients": [],
            "unconfigured_clients": [],
            "note": "系统强制只使用 APIYI，其他图像生成后端已被禁用"
        }

        # 只检查 APIYI
        if self._is_client_configured("apiyi"):
            info["configured_clients"].append("apiyi")
        else:
            info["unconfigured_clients"].append("apiyi")

        return info


class ThreeDClientFactory(ClientFactory):
    """
    Factory for creating 3D generation clients.

    Supports multiple backends with workflow management and
    automatic backend selection based on input type and requirements.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__(config_manager)

        # Register default 3D clients
        self._register_default_clients()

        # Client capabilities mapping
        self._client_capabilities = {
            "sf3d": {"image_to_3d": True, "text_to_3d": False, "formats": ["glb"]},
            "hunyuan_3d": {"image_to_3d": True, "text_to_3d": True, "formats": ["glb", "obj"]},
            "comfyui_3d": {"image_to_3d": True, "text_to_3d": False, "formats": ["glb", "obj", "fbx"]}
        }

    def _register_default_clients(self) -> None:
        """Register default 3D generation clients"""
        try:
            from ..object_gen.sf3d_client import SF3DClient
            self.register_client("sf3d", SF3DClient)
        except ImportError:
            self.logger.debug("SF3DClient not available")

        try:
            from ..object_gen.hunyuan_3d_client import Hunyuan3DClient
            self.register_client("hunyuan_3d", Hunyuan3DClient)
        except ImportError:
            self.logger.debug("Hunyuan3DClient not available")

    def create_client(
        self,
        client_name: Optional[str] = None,
        generation_type: Optional[str] = None,
        output_format: Optional[str] = None,
        **kwargs
    ) -> Base3DClient:
        """
        Create a 3D generation client.

        Args:
            client_name: Specific client to create (None for auto-selection)
            generation_type: Type of generation ('image_to_3d', 'text_to_3d')
            output_format: Desired output format ('glb', 'obj', 'fbx')
            **kwargs: Additional configuration parameters

        Returns:
            Configured 3D generation client
        """
        if client_name:
            return self._create_specific_client(client_name, **kwargs)

        # Auto-select based on requirements
        return self._create_optimal_client(generation_type, output_format, **kwargs)

    def _create_specific_client(self, client_name: str, **kwargs) -> Base3DClient:
        """Create a specific named 3D client"""
        client_class = self._validate_client_class(client_name)

        if not self._is_client_configured(client_name):
            raise ConfigurationError(
                f"Client {client_name} is not properly configured"
            )

        client_config = self._create_client_config(ServiceType.THREED_GENERATION, **kwargs)
        return self._create_client_instance(client_class, client_config, **kwargs)

    def _create_optimal_client(
        self,
        generation_type: Optional[str],
        output_format: Optional[str],
        **kwargs
    ) -> Base3DClient:
        """Create optimal client based on generation requirements"""

        # Find clients that support the required capabilities
        suitable_clients = []

        for client_name, capabilities in self._client_capabilities.items():
            if client_name not in self._client_registry:
                continue

            if not self._is_client_configured(client_name):
                continue

            # Check generation type support
            if generation_type:
                type_key = generation_type.replace('-', '_')
                if not capabilities.get(type_key, False):
                    continue

            # Check format support
            if output_format and output_format not in capabilities.get("formats", []):
                continue

            suitable_clients.append(client_name)

        if not suitable_clients:
            raise ConfigurationError(
                f"No 3D clients support the requested configuration: "
                f"type={generation_type}, format={output_format}. "
                f"Available clients: {list(self._client_registry.keys())}"
            )

        # Try to create the first suitable client
        for client_name in suitable_clients:
            try:
                self.logger.info(f"Creating optimal 3D client: {client_name}")
                return self._create_specific_client(client_name, **kwargs)
            except ConfigurationError as e:
                self.logger.warning(f"Failed to create {client_name}: {e}")
                continue

        raise ConfigurationError("Failed to create any suitable 3D client")

    def _is_client_configured(self, client_name: str) -> bool:
        """Check if a 3D client is properly configured"""
        config_checks = {
            "sf3d": lambda: bool(get_config("COMFYUI_SERVER_ADDRESS", None)),
            "hunyuan_3d": lambda: is_service_configured("HUNYUAN"),
            "comfyui_3d": lambda: bool(get_config("COMFYUI_SERVER_ADDRESS", None))
        }

        check = config_checks.get(client_name, lambda: False)
        return check()

    def get_capabilities(self, client_name: str) -> Dict[str, Any]:
        """Get capabilities of a specific client"""
        return self._client_capabilities.get(client_name, {})


class LLMClientFactory(ClientFactory):
    """
    Factory for creating LLM clients.

    Supports multiple LLM backends with automatic fallback and
    feature-based selection.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        super().__init__(config_manager)

        # Register default LLM clients
        self._register_default_clients()

        # Client priority order (VLM clients first for vision-language tasks)
        self._priority_order = [
            "unified_vlm",  # Unified VLM client (supports OpenAI and SiliconFlow)
            "openai",
            "claude",
            "hunyuan_llm",
            "local_llm"
        ]

    def _register_default_clients(self) -> None:
        """Register default LLM clients"""
        # Import here to avoid circular imports
        try:
            from ..scene_analysis.clients.unified_vlm import UnifiedVLMClient
            self.register_client("unified_vlm", UnifiedVLMClient)
        except ImportError:
            self.logger.debug("UnifiedVLMClient not available")

        # These would be implemented as concrete LLM clients
        # TODO: Add other LLM clients as they become available

    def create_client(
        self,
        client_name: Optional[str] = None,
        features: Optional[List[str]] = None,
        **kwargs
    ) -> BaseLLMClient:
        """
        Create an LLM client.

        Args:
            client_name: Specific client to create (None for auto-selection)
            features: Required features (e.g., ['chat', 'completion', 'vision'])
            **kwargs: Additional configuration parameters

        Returns:
            Configured LLM client
        """
        if client_name:
            return self._create_specific_client(client_name, **kwargs)

        return self._create_best_llm_client(features, **kwargs)

    def _create_specific_client(self, client_name: str, **kwargs) -> BaseLLMClient:
        """Create a specific named LLM client"""
        client_class = self._validate_client_class(client_name)

        if not self._is_client_configured(client_name):
            raise ConfigurationError(
                f"LLM client {client_name} is not properly configured"
            )

        client_config = self._create_client_config(ServiceType.LLM, **kwargs)
        return self._create_client_instance(client_class, client_config, **kwargs)

    def _create_best_llm_client(
        self,
        features: Optional[List[str]],
        **kwargs
    ) -> BaseLLMClient:
        """Create best LLM client based on priority and features"""

        for client_name in self._priority_order:
            if client_name in self._client_registry and self._is_client_configured(client_name):
                try:
                    if features and not self._supports_features(client_name, features):
                        continue

                    self.logger.info(f"Creating LLM client: {client_name}")
                    return self._create_specific_client(client_name, **kwargs)
                except ConfigurationError as e:
                    self.logger.warning(f"Failed to create {client_name}: {e}")
                    continue

        raise ConfigurationError("No suitable LLM client available")

    def _is_client_configured(self, client_name: str) -> bool:
        """Check if an LLM client is properly configured"""
        config_checks = {
            "unified_vlm": lambda: (is_service_configured("OPENAI") or
                                   bool(os.getenv("SILICONFLOW_API_KEY")) or
                                   bool(os.getenv("CUSTOM_VLM_CONFIG"))),
            "openai": lambda: is_service_configured("OPENAI"),
            "claude": lambda: is_service_configured("ANTHROPIC"),
            "hunyuan_llm": lambda: is_service_configured("HUNYUAN"),
            "local_llm": lambda: True  # Always available as fallback
        }

        check = config_checks.get(client_name, lambda: False)
        return check()

    def _supports_features(self, client_name: str, features: List[str]) -> bool:
        """Check if client supports required features"""
        # Define feature support for each client type
        feature_support = {
            "unified_vlm": [
                "object_extraction",
                "vision",
                "scene_analysis",
                "multi_backend"
            ],
            "openai": [
                "chat",
                "completion",
                "vision",
                "object_extraction"
            ],
            "claude": [
                "chat",
                "completion"
            ],
            "hunyuan_llm": [
                "chat",
                "completion"
            ],
            "local_llm": [
                "chat",
                "completion"
            ]
        }

        supported_features = feature_support.get(client_name, [])
        return all(feature in supported_features for feature in features) if features else True


# Convenience functions for easy client creation
def create_image_client(
    client_name: Optional[str] = None,
    **kwargs
) -> BaseImageClient:
    """Convenience function to create image generation client"""
    factory = ImageClientFactory()
    return factory.create_client(client_name, **kwargs)


def create_3d_client(
    client_name: Optional[str] = None,
    generation_type: Optional[str] = None,
    output_format: Optional[str] = None,
    **kwargs
) -> Base3DClient:
    """Convenience function to create 3D generation client"""
    factory = ThreeDClientFactory()
    return factory.create_client(client_name, generation_type, output_format, **kwargs)


def create_llm_client(
    client_name: Optional[str] = None,
    features: Optional[List[str]] = None,
    **kwargs
) -> BaseLLMClient:
    """Convenience function to create LLM client"""
    factory = LLMClientFactory()
    return factory.create_client(client_name, features, **kwargs)


# Example usage and testing
if __name__ == "__main__":
    # Test image client factory
    try:
        image_factory = ImageClientFactory()
        print("Available image clients:", image_factory.get_available_clients())
        print("Client info:", image_factory.get_client_info())

        # Try to create a client
        client = image_factory.create_client()
        print(f"Created client: {type(client).__name__}")

    except ConfigurationError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")