"""
配置管理模块

处理配置文件、环境变量和默认设置。已迁移到新的统一配置管理系统。
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from holodeck_core.config.base import ConfigManager, get_config, get_api_credentials
from holodeck_core.logging.standardized import get_logger


logger = get_logger(__name__)


class CLIConfig:
    """CLI配置管理器 - 与新的统一配置系统集成

    此类提供了与旧Config类的向后兼容性，同时使用新的ConfigManager
    作为底层实现。
    """

    def __init__(self):
        self._config_manager = ConfigManager()
        self.config_dir = Path.home() / ".holodeck"
        self.config_file = self.config_dir / "config.json"
        self.api_keys_file = self.config_dir / "api_keys.env"
        self.workspace_dir = Path.cwd() / "workspace"

        # 默认配置（用于向后兼容）
        self.defaults = {
            "workspace_dir": str(self.workspace_dir),
            "cache_dir": str(self.config_dir / "cache"),
            "log_level": "INFO",
            "blender_path": None,
            "max_workers": 4,
            "timeout": 300,
        }

        # 迁移期间保持本地配置以支持旧API
        self.config = self.defaults.copy()
        self._migrate_old_config()

    def _migrate_old_config(self):
        """迁移旧配置文件到新的配置系统"""
        # 检查是否在JSON模式下，避免污染输出
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'

        # 加载旧配置文件以进行迁移
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    old_config = json.load(f)

                # 迁移配置值到环境变量（新的配置系统可以读取）
                for key, value in old_config.items():
                    env_key = f"HOODECK_{key.upper()}"
                    if not os.getenv(env_key):
                        os.environ[env_key] = str(value)

                if not json_mode:
                    logger.info(f"已迁移 {len(old_config)} 个配置项到新的配置系统")

            except Exception as e:
                if not json_mode:
                    logger.warning(f"迁移旧配置文件失败 {self.config_file}: {e}")

        # 迁移API密钥文件
        if self.api_keys_file.exists():
            try:
                self._load_api_keys()
                if not json_mode:
                    logger.info("已加载API密钥文件")
            except Exception as e:
                if not json_mode:
                    logger.warning(f"加载API密钥文件失败 {self.api_keys_file}: {e}")

    def _load_api_keys(self):
        """加载API密钥（保持向后兼容）"""
        if self.api_keys_file.exists():
            try:
                with open(self.api_keys_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                os.environ[key.strip()] = value.strip().strip('"\'')
            except Exception as e:
                # 检查是否在JSON模式下，避免污染输出
                json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
                if not json_mode:
                    logger.warning(f"无法加载API密钥文件 {self.api_keys_file}: {e}")

    def save_config(self):
        """保存配置到文件（向后兼容）"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            # 检查是否在JSON模式下，避免污染输出
            json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
            if not json_mode:
                logger.info(f"配置已保存到 {self.config_file}")
        except Exception as e:
            # 检查是否在JSON模式下，避免污染输出
            json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
            if not json_mode:
                logger.error(f"无法保存配置文件: {e}")

    def get(self, key: str, default=None) -> Any:
        """获取配置值 - 优先使用新的配置系统"""
        # 尝试从新配置系统获取
        try:
            # 尝试不同的键格式
            possible_keys = [
                f"HOODECK_{key.upper()}",
                key.upper(),
                key.lower()
            ]

            for env_key in possible_keys:
                value = get_config(env_key)
                if value is not None:
                    return value

        except Exception:
            pass

        # 回退到本地配置
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """设置配置值 - 同时更新本地配置和环境变量"""
        self.config[key] = value

        # 同时设置环境变量以便新的配置系统可以使用
        env_key = f"HOODECK_{key.upper()}"
        os.environ[env_key] = str(value)

        # 检查是否在JSON模式下，避免污染输出
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
        if not json_mode:
            logger.debug(f"配置项设置: {key} = {value}")

    def get_api_key(self, service: str) -> Optional[str]:
        """获取指定服务的API密钥"""
        # 使用新的配置系统
        try:
            credentials = get_api_credentials(service.upper())
            return credentials.get('api_key')
        except Exception:
            # 回退到环境变量
            env_key = f"{service.upper()}_API_KEY"
            return os.environ.get(env_key)

    def get_siliconflow_api_key(self) -> Optional[str]:
        """获取SiliconFlow API密钥"""
        return self.get_api_key("SILICONFLOW")

    def is_siliconflow_available(self) -> bool:
        """检查SiliconFlow是否可用"""
        return bool(self.get_siliconflow_api_key())

    def get_workspace_path(self) -> Path:
        """获取workspace路径"""
        workspace_dir = self.get("workspace_dir", str(self.workspace_dir))
        return Path(workspace_dir)

    def get_cache_path(self) -> Path:
        """获取缓存路径"""
        cache_dir = self.get("cache_dir", str(self.config_dir / "cache"))
        return Path(cache_dir)

    def reload(self):
        """重新加载配置"""
        self._config_manager.reload()
        self._migrate_old_config()
        # 检查是否在JSON模式下，避免污染输出
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
        if not json_mode:
            logger.info("配置已重新加载")


# 全局配置实例
config = CLIConfig()