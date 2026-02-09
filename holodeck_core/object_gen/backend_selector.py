"""Backend selection manager for 3D generation.

Automatically selects the best backend based on environment configuration
and availability. Reads from .env file and system environment variables.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from .hunyuan_3d_client import Hunyuan3DClient
from .sf3d_client import SF3DClient

logger = logging.getLogger(__name__)


@dataclass
class BackendConfig:
    """Configuration for a 3D generation backend."""
    name: str
    priority: int  # Higher number = higher priority
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


class BackendSelector:
    """Intelligent backend selector for 3D generation.

    Automatically detects available backends and selects the optimal one
    based on configuration, environment variables, and availability.
    """

    def __init__(self, workspace_root: str = "workspace"):
        """Initialize backend selector.

        Args:
            workspace_root: Root workspace directory
        """
        self.workspace_root = Path(workspace_root)
        self.available_backends = {}
        self.backend_configs = {}
        self._load_environment_config()
        self._detect_available_backends()

    def _load_environment_config(self):
        """Load configuration from .env file and environment variables."""
        # Default backend priorities
        self.backend_configs = {
            "hunyuan": BackendConfig(
                name="hunyuan",
                priority=100,  # Highest priority
                config={}
            ),
            "sf3d": BackendConfig(
                name="sf3d",
                priority=50,   # Lower priority
                config={}
            )
        }

        # Try to load from .env file
        self._load_dotenv()

        # Override with environment variables
        self._load_env_vars()

        logger.info("Loaded backend configurations")

    def _load_dotenv(self):
        """Load configuration from .env file."""
        env_paths = [
            Path(".env"),
            self.workspace_root / ".env",
            Path.home() / ".env"
        ]

        for env_path in env_paths:
            if env_path.exists():
                try:
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"\'')

                                # Parse backend-specific configurations
                                if key.startswith('HUNYUAN_'):
                                    config_key = key[8:].lower()  # Remove HUNYUAN_ prefix
                                    self.backend_configs["hunyuan"].config[config_key] = value

                                elif key.startswith('SF3D_') or key.startswith('COMFYUI_'):
                                    config_key = key.split('_', 1)[1].lower()
                                    self.backend_configs["sf3d"].config[config_key] = value

                                # ComfyUI availability flag
                                elif key == 'COMFYUI_AVAILABLE':
                                    if value.lower() in ['true', '1', 'yes']:
                                        self.backend_configs["sf3d"].config["available"] = True
                                    else:
                                        self.backend_configs["sf3d"].config["available"] = False

                                # ComfyUI server address
                                elif key == 'COMFYUI_SERVER':
                                    self.backend_configs["sf3d"].config["server_address"] = value

                                # SF3D workflow template path
                                elif key == 'SF3D_WORKFLOW_TEMPLATE':
                                    self.backend_configs["sf3d"].config["workflow_template"] = value

                                elif key == '3D_BACKEND_PRIORITY':
                                    # Set backend priority
                                    backends = value.split(',')
                                    for i, backend in enumerate(backends):
                                        backend = backend.strip().lower()
                                        if backend in self.backend_configs:
                                            # Higher priority for earlier in list
                                            self.backend_configs[backend].priority = 100 - i

                                elif key == 'DISABLE_HUNYUAN_3D':
                                    if value.lower() in ['true', '1', 'yes']:
                                        self.backend_configs["hunyuan"].enabled = False

                                elif key == 'DISABLE_SF3D':
                                    if value.lower() in ['true', '1', 'yes']:
                                        self.backend_configs["sf3d"].enabled = False

                    logger.info(f"Loaded configuration from {env_path}")
                    break  # Use first found .env file

                except Exception as e:
                    logger.warning(f"Failed to load .env from {env_path}: {e}")

    def _load_env_vars(self):
        """Load configuration from environment variables."""
        # Backend priority from environment
        backend_priority = os.getenv('3D_BACKEND_PRIORITY')
        if backend_priority:
            backends = backend_priority.split(',')
            for i, backend in enumerate(backends):
                backend = backend.strip().lower()
                if backend in self.backend_configs:
                    self.backend_configs[backend].priority = 100 - i

        # ComfyUI availability from environment
        if os.getenv('COMFYUI_AVAILABLE', '').lower() in ['true', '1', 'yes']:
            self.backend_configs["sf3d"].config["available"] = True
        elif os.getenv('COMFYUI_AVAILABLE', '').lower() in ['false', '0', 'no']:
            self.backend_configs["sf3d"].config["available"] = False

        # ComfyUI server address from environment
        comfyui_server = os.getenv('COMFYUI_SERVER')
        if comfyui_server:
            self.backend_configs["sf3d"].config["server_address"] = comfyui_server

        # SF3D workflow template from environment
        sf3d_workflow = os.getenv('SF3D_WORKFLOW_TEMPLATE')
        if sf3d_workflow:
            self.backend_configs["sf3d"].config["workflow_template"] = sf3d_workflow

        # Disable flags
        if os.getenv('DISABLE_HUNYUAN_3D', '').lower() in ['true', '1', 'yes']:
            self.backend_configs["hunyuan"].enabled = False

        if os.getenv('DISABLE_SF3D', '').lower() in ['true', '1', 'yes']:
            self.backend_configs["sf3d"].enabled = False

    def _detect_available_backends(self):
        """Detect which backends are available and working."""
        logger.info("Detecting available 3D generation backends...")

        # Test Hunyuan 3D availability
        if self.backend_configs["hunyuan"].enabled:
            try:
                secret_id = os.getenv("HUNYUAN_SECRET_ID") or self.backend_configs["hunyuan"].config.get("secret_id")
                secret_key = os.getenv("HUNYUAN_SECRET_KEY") or self.backend_configs["hunyuan"].config.get("secret_key")

                try:
                    # Use from_env to automatically load .env files
                    test_client = Hunyuan3DClient.from_env()
                    if test_client.test_connection():
                        self.available_backends["hunyuan"] = {
                            "client": test_client,
                            "config": self.backend_configs["hunyuan"]
                        }
                        logger.info("✅ Hunyuan 3D backend available")
                    else:
                        logger.warning("⚠️  Hunyuan 3D credentials invalid")
                except Exception as e:
                    logger.info(f"ℹ️  Hunyuan 3D credentials not configured or error: {e}")

            except Exception as e:
                logger.warning(f"⚠️  Hunyuan 3D backend not available: {e}")

        # Test SF3D availability
        if self.backend_configs["sf3d"].enabled:
            try:
                # Check if ComfyUI is explicitly marked as available
                comfyui_available = self.backend_configs["sf3d"].config.get("available")

                if comfyui_available is False:
                    logger.info("ℹ️  SF3D backend disabled via COMFYUI_AVAILABLE=false")
                else:
                    # Get server address from config
                    server_address = self.backend_configs["sf3d"].config.get("server_address", "127.0.0.1:8189")

                    sf3d_client = SF3DClient(server_address=server_address)

                    # Note: We can't easily test SF3D availability without async context
                    # So we'll assume it's available and let the generation handle failures
                    self.available_backends["sf3d"] = {
                        "client": sf3d_client,
                        "config": self.backend_configs["sf3d"]
                    }

                    if comfyui_available is True:
                        logger.info(f"✅ SF3D backend available (COMFYUI_AVAILABLE=true, server: {server_address})")
                    else:
                        logger.info(f"✅ SF3D backend available (server: {server_address})")

            except Exception as e:
                logger.warning(f"⚠️  SF3D backend not available: {e}")

        logger.info(f"Available backends: {list(self.available_backends.keys())}")

    def get_optimal_backend(self) -> Optional[str]:
        """Get the optimal backend based on priority and availability."""
        if not self.available_backends:
            return None

        # Sort by priority (highest first)
        sorted_backends = sorted(
            self.available_backends.items(),
            key=lambda x: x[1]["config"].priority,
            reverse=True
        )

        # Return the highest priority available backend
        return sorted_backends[0][0]

    def get_all_backends(self) -> List[str]:
        """Get list of all available backends sorted by priority."""
        if not self.available_backends:
            return []

        sorted_backends = sorted(
            self.available_backends.items(),
            key=lambda x: x[1]["config"].priority,
            reverse=True
        )

        return [name for name, _ in sorted_backends]

    def get_available_backends(self) -> List[str]:
        """Get list of available backends (alias for get_all_backends)."""
        return self.get_all_backends()

    def get_backend_client(self, backend_name: str):
        """Get client for specific backend."""
        if backend_name not in self.available_backends:
            raise ValueError(f"Backend '{backend_name}' not available")

        return self.available_backends[backend_name]["client"]

    def is_backend_available(self, backend_name: str) -> bool:
        """Check if a specific backend is available."""
        return backend_name in self.available_backends

    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about available backends and their priorities."""
        info = {
            "available_backends": list(self.available_backends.keys()),
            "optimal_backend": self.get_optimal_backend(),
            "backend_priorities": {
                name: backend_info["config"].priority
                for name, backend_info in self.available_backends.items()
            },
            "all_configs": {
                name: {
                    "priority": config.priority,
                    "enabled": config.enabled,
                    "config": config.config
                }
                for name, config in self.backend_configs.items()
            }
        }

        return info

    def reload_configuration(self):
        """Reload configuration from environment."""
        logger.info("Reloading backend configuration...")
        self._load_environment_config()
        self._detect_available_backends()


# Convenience functions for easy access
_selector_instance = None


def get_backend_selector(workspace_root: str = "workspace") -> BackendSelector:
    """Get global backend selector instance."""
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = BackendSelector(workspace_root)
    return _selector_instance


def get_optimal_backend() -> Optional[str]:
    """Get optimal backend name."""
    selector = get_backend_selector()
    return selector.get_optimal_backend()


def is_backend_available(backend_name: str) -> bool:
    """Check if backend is available."""
    selector = get_backend_selector()
    return selector.is_backend_available(backend_name)


def get_backend_info() -> Dict[str, Any]:
    """Get backend information."""
    selector = get_backend_selector()
    return selector.get_backend_info()


def reload_backend_configuration():
    """Reload backend configuration."""
    selector = get_backend_selector()
    selector.reload_configuration()