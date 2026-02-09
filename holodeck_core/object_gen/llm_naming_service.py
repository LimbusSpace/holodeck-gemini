#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM命名服务 (已废弃)

此类已被EnhancedLLMNamingService取代。
新服务提供了完整的图像分析功能、缓存机制、错误处理和性能监控。

迁移指南:
- 旧: from holodeck_core.object_gen.llm_naming_service import LLMNamingService
- 新: from holodeck_core.object_gen.enhanced_llm_naming_service import EnhancedLLMNamingService

新功能:
- 完整的图像分析功能
- 智能缓存机制 (TTL + LRU)
- 统一的错误处理框架
- 性能监控和日志记录
- 向后兼容的API
"""

import warnings
import logging
from typing import Optional
from pathlib import Path

# 发出废弃警告
warnings.warn(
    "LLMNamingService is deprecated and will be removed in a future version. "
    "Use EnhancedLLMNamingService instead. "
    "Migration: from holodeck_core.object_gen.enhanced_llm_naming_service import EnhancedLLMNamingService",
    DeprecationWarning,
    stacklevel=2
)

from .enhanced_llm_naming_service import EnhancedLLMNamingService


class LLMNamingService(EnhancedLLMNamingService):
    """
    旧的LLM命名服务 - 已废弃

    此类现在继承自EnhancedLLMNamingService以保持向后兼容性。
    建议尽快迁移到直接使用EnhancedLLMNamingService。
    """

    def __init__(self, hybrid_client=None):
        """
        初始化LLM命名服务 (已废弃)

        Args:
            hybrid_client: 混合分析客户端 (在新服务中不再需要)
        """
        # 发出废弃警告
        warnings.warn(
            "LLMNamingService is deprecated. Use EnhancedLLMNamingService instead.",
            DeprecationWarning,
            stacklevel=2
        )

        self.logger = logging.getLogger(__name__)

        # 调用父类初始化
        super().__init__(
            config_manager=None,  # 将自动创建默认配置管理器
            cache_ttl=3600,       # 默认缓存1小时
            enable_image_analysis=True
        )

        # 保留旧的hybrid_client参数以保持兼容性
        if hybrid_client:
            self.logger.warning("hybrid_client参数在新服务中不再使用，将被忽略")

    def generate_object_name(self, description: str, object_name: str, image_path: Optional[Path] = None) -> Optional[str]:
        """
        使用LLM生成3D对象命名 (已废弃)

        此方法现在委托给EnhancedLLMNamingService的实现。

        Args:
            description: 对象描述
            object_name: 对象名称
            image_path: 可选的图像路径

        Returns:
            生成的命名，格式：风格+材质+主体
        """
        # 发出废弃警告
        warnings.warn(
            "LLMNamingService.generate_object_name() is deprecated. "
            "Use EnhancedLLMNamingService.generate_object_name() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # 调用增强版实现
        import asyncio

        try:
            # 在同步上下文中运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                super().generate_object_name(description, object_name, image_path)
            )
            loop.close()
            return result
        except Exception as e:
            self.logger.error(f"LLM命名失败: {e}")
            return None

    def extract_style_and_material(self, description: str) -> tuple[str, str]:
        """
        从描述中提取风格和材质信息 (已废弃)

        此方法现在委托给EnhancedLLMNamingService的实现。

        Args:
            description: 对象描述

        Returns:
            (风格, 材质) 元组
        """
        # 发出废弃警告
        warnings.warn(
            "LLMNamingService.extract_style_and_material() is deprecated. "
            "Use EnhancedLLMNamingService._extract_style_and_material() instead.",
            DeprecationWarning,
            stacklevel=2
        )

        # 使用默认值返回，因为新方法需要异步调用
        self.logger.warning("extract_style_and_material方法在新服务中需要异步调用，返回默认值")
        return "通用", "标准"