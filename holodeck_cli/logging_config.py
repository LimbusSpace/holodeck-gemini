"""
日志配置模块

已迁移到新的标准化日志框架，保持向后兼容性。
"""

import logging
import logging.config
from pathlib import Path
from typing import Dict

from holodeck_core.logging.standardized import setup_logging as setup_standardized_logging


def setup_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """设置日志配置 - 使用新的标准化日志框架"""

    # 使用新的标准化日志框架
    setup_standardized_logging(
        log_level=log_level,
        log_file=log_file,
        structured=False  # CLI使用文本格式
    )

    # 配置CLI特定的logger
    cli_logger = logging.getLogger("holodeck_cli")
    cli_logger.setLevel(getattr(logging, log_level))

    # 确保holodeck_core logger也使用正确的级别
    core_logger = logging.getLogger("holodeck_core")
    core_logger.setLevel(getattr(logging, log_level))

    # 如果有日志文件，确保文件处理器被正确配置
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 添加文件处理器到CLI logger
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level))

        # 使用详细的格式化器
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)

        cli_logger.addHandler(file_handler)
        core_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """获取logger - 使用新的标准化logger"""
    from holodeck_core.logging.standardized import get_logger as get_standardized_logger

    # 对于CLI模块，使用标准化logger
    if name.startswith(("holodeck_cli", "holodeck_core")):
        return get_standardized_logger(name)

    # 对于其他模块，保持向后兼容
    return logging.getLogger(name)