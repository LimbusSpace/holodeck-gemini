# Holodeck API 参考文档

## 目录

1. [概述](#概述)
2. [核心架构](#核心架构)
3. [客户端工厂](#客户端工厂)
4. [配置管理](#配置管理)
5. [异常处理](#异常处理)
6. [日志系统](#日志系统)
7. [性能监控](#性能监控)
8. [LLM命名服务](#llm命名服务)
9. [管道编排器](#管道编排器)

## 概述

Holodeck 提供了统一的API接口来访问各种AI服务，包括图像生成、3D模型生成、LLM分析等。所有API都设计为向后兼容，并提供完整的错误处理和性能监控。

### 快速开始

```python
from holodeck_core.clients.factory import (
    ImageClientFactory,
    LLMClientFactory,
    ThreeDClientFactory
)
from holodeck_core.config.base import ConfigManager

# 初始化配置管理器
config = ConfigManager()

# 创建客户端
image_client = ImageClientFactory(config).create_client()
llm_client = LLMClientFactory(config).create_client()
three_d_client = ThreeDClientFactory(config).create_client()
```

## 核心架构

### 分层架构

```
+------------------+
|     CLI命令层    |  # 支持新旧架构的智能命令
+------------------+
|   性能优化层     |  # 缓存、并发、内存管理
+------------------+
|   管道编排层     |  # PipelineOrchestrator
+------------------+
|   客户端工厂层   |  # 统一客户端创建
+------------------+
|   异常处理层     |  # 增强的错误处理框架
+------------------+
```

## 客户端工厂

### ImageClientFactory

管理图像生成客户端的创建和生命周期。

```python
from holodeck_core.clients.factory import ImageClientFactory

class ImageClientFactory(AbstractClientFactory):
    """图像客户端工厂"""

    def __init__(self, config_manager: ConfigManager):
        """
        初始化图像客户端工厂

        Args:
            config_manager: 配置管理器实例
        """
        super().__init__(config_manager)

    def create_client(self, client_type: Optional[str] = None) -> BaseImageClient:
        """
        创建图像客户端

        Args:
            client_type: 客户端类型 ('comfyui', 'hunyuan')

        Returns:
            图像客户端实例

        Raises:
            ConfigurationError: 配置错误时
            ClientError: 客户端创建失败时
        """

    def get_available_backends(self) -> List[str]:
        """
        获取可用的后端列表

        Returns:
            可用后端名称列表
        """

    def check_backend_health(self, backend: str) -> bool:
        """
        检查后端健康状态

        Args:
            backend: 后端名称

        Returns:
            健康状态 (True/False)
        """
```

### LLMClientFactory

管理LLM客户端的创建和生命周期。

```python
from holodeck_core.clients.factory import LLMClientFactory

class LLMClientFactory(AbstractClientFactory):
    """LLM客户端工厂"""

    def create_client(self, client_type: Optional[str] = None) -> BaseLLMClient:
        """
        创建LLM客户端

        Args:
            client_type: 客户端类型 ('openai', 'claude')

        Returns:
            LLM客户端实例
        """

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> GenerationResult:
        """
        聊天完成

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            生成结果
        """
```

### ThreeDClientFactory

管理3D模型生成客户端的创建和生命周期。

```python
from holodeck_core.clients.factory import ThreeDClientFactory

class ThreeDClientFactory(AbstractClientFactory):
    """3D客户端工厂"""

    def create_client(self, client_type: Optional[str] = None) -> BaseThreeDClient:
        """
        创建3D客户端

        Args:
            client_type: 客户端类型 ('sf3d', 'hunyuan3d')

        Returns:
            3D客户端实例
        """
```

## 配置管理

### ConfigManager

统一的配置管理系统，支持多种配置源和缓存。

```python
from holodeck_core.config.base import ConfigManager

class ConfigManager:
    """配置管理器 (单例模式)"""

    @classmethod
    def get_instance(cls) -> 'ConfigManager':
        """
        获取配置管理器实例

        Returns:
            配置管理器实例
        """

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """

    def get_llm_config(self) -> Dict[str, Any]:
        """
        获取LLM配置

        Returns:
            LLM配置字典
        """

    def get_image_config(self) -> Dict[str, Any]:
        """
        获取图像生成配置

        Returns:
            图像生成配置字典
        """

    def get_three_d_config(self) -> Dict[str, Any]:
        """
        获取3D生成配置

        Returns:
            3D生成配置字典
        """

    def get_workspace_path(self) -> Path:
        """
        获取工作空间路径

        Returns:
            工作空间路径
        """
```

## 异常处理

### HolodeckError

所有Holodeck异常的基类。

```python
from holodeck_core.exceptions.framework import HolodeckError

class HolodeckError(Exception):
    """Holodeck异常基类"""

    def __init__(self, message: str, error_code: Optional[str] = None,
                 context: Optional[Dict[str, Any]] = None):
        """
        初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码
            context: 错误上下文
        """
```

### 具体异常类型

```python
class ConfigurationError(HolodeckError):
    """配置错误"""
    pass

class ValidationError(HolodeckError):
    """验证错误"""
    pass

class ClientError(HolodeckError):
    """客户端错误"""
    pass

class LLMError(HolodeckError):
    """LLM错误"""
    pass

class ImageGenerationError(HolodeckError):
    """图像生成错误"""
    pass

class ThreeDGenerationError(HolodeckError):
    """3D生成错误"""
    pass
```

## 日志系统

### StandardizedLogger

标准化的日志系统，集成性能监控。

```python
from holodeck_core.logging.standardized import get_logger, log_time

# 获取日志器
logger = get_logger(__name__)

# 性能监控装饰器
@log_time("operation_name")
def my_function():
    """被监控的函数"""
    pass
```

### log_time 装饰器

```python
def log_time(operation_name: str, log_level: str = "INFO")
```

性能监控装饰器，自动记录函数执行时间和结果。

**参数:**
- `operation_name`: 操作名称
- `log_level`: 日志级别 (DEBUG, INFO, WARNING)

**示例:**
```python
@log_time("image_generation")
async def generate_image(prompt: str) -> ImageResult:
    # 函数实现
    pass
```

## 性能监控

### PerformanceMonitor

性能监控器，收集和统计性能指标。

```python
from holodeck_cli.performance import PerformanceMonitor, performance_monitor

# 记录性能指标
performance_monitor.record_metric(
    operation="my_operation",
    duration=1.23,
    success=True,
    metadata={"key": "value"}
)

# 获取统计信息
stats = performance_monitor.get_statistics("my_operation")

# 生成性能报告
report_path = performance_monitor.save_report(Path("performance_report.json"))
```

### CacheOptimizer

缓存优化器，实现LRU和TTL缓存策略。

```python
from holodeck_cli.performance import CacheOptimizer

cache = CacheOptimizer(max_size_mb=100, ttl_seconds=3600)

# 基本操作
cache.set("key", "value")
value = cache.get("key")
stats = cache.get_stats()

# 缓存管理
cache.clear()
```

### ConcurrencyManager

并发管理器，优化并发任务执行。

```python
from holodeck_cli.performance import ConcurrencyManager

manager = ConcurrencyManager(max_workers=10)

# 运行并发任务
result = await manager.run_task(my_coroutine(), "task_name")

# 获取统计信息
stats = manager.get_stats()

# 优化工作进程数量
optimal_workers = manager.optimize_worker_count()
```

### MemoryOptimizer

内存优化器，监控和优化内存使用。

```python
from holodeck_cli.performance import MemoryOptimizer

optimizer = MemoryOptimizer()

# 获取内存使用情况
memory_usage = optimizer.get_memory_usage()

# 获取优化建议
suggestions = optimizer.suggest_optimizations()

# 清理内存
optimizer.cleanup_memory()
```

## LLM命名服务

### EnhancedLLMNamingService

增强版LLM命名服务，支持图像分析和缓存。

```python
from holodeck_core.object_gen.enhanced_llm_naming_service import EnhancedLLMNamingService

# 初始化服务
service = EnhancedLLMNamingService(
    config_manager=None,  # 使用默认配置
    cache_ttl=3600,       # 缓存1小时
    enable_image_analysis=True
)

# 生成对象名称
generated_name = await service.generate_object_name(
    description="A futuristic chair with neon blue accents",
    object_name="Cyberpunk Chair",
    image_path=Path("chair_image.png")  # 可选
)

# 服务统计
stats = service.get_statistics()

# 清理缓存
service.clear_cache()
```

## 管道编排器

### PipelineOrchestrator

管道编排器，管理复杂的工作流程。

```python
from holodeck_core.integration.pipeline_orchestrator import PipelineOrchestrator

# 初始化编排器
orchestrator = PipelineOrchestrator(config_manager)

# 执行场景生成
result = await orchestrator.generate_scene(
    prompt="A modern living room",
    output_dir=Path("output"),
    quality="high"
)

# 执行编辑操作
result = await orchestrator.edit_scene(
    scene_path=Path("scene.json"),
    edits=[{"type": "add", "object": "chair"}]
)

# 获取编排器状态
status = orchestrator.get_status()
```

## CLI命令

### Build命令

```bash
# 基本用法
holodeck build "A modern living room"

# 指定输出目录
holodeck build "A modern living room" --output ./scenes

# 指定质量
holodeck build "A modern living room" --quality high

# 使用特定客户端
holodeck build "A modern living room" --backend hunyuan

# 生成性能报告
holodeck build "A modern living room" --performance-report
```

### Session命令

```bash
# 查看会话信息
holodeck session info

# 清理会话缓存
holodeck session cache-clear

# 查看缓存统计
holodeck session cache-stats

# 导出会话
holodeck session export ./backup.json
```

### Debug命令

```bash
# 系统健康检查
holodeck debug health

# 客户端状态检查
holodeck debug clients

# 性能监控
holodeck debug performance

# 详细系统信息
holodeck debug system-info
```

## 错误代码

完整的错误代码列表请参考 [ERROR_CODES.md](ERROR_CODES.md)。

## 最佳实践

1. **错误处理**: 始终使用try-catch捕获HolodeckError及其子类
2. **性能监控**: 为关键操作添加@log_time装饰器
3. **缓存使用**: 合理使用缓存减少重复计算
4. **配置管理**: 使用ConfigManager而不是直接读取配置文件
5. **客户端创建**: 通过工厂类创建客户端，而不是直接实例化
6. **资源清理**: 及时清理缓存和释放资源

## 迁移指南

从旧版本迁移到新版本，请参考 [REFACTORING_COMPLETION_SUMMARY.md](REFACTORING_COMPLETION_SUMMARY.md)。

## 支持与反馈

遇到问题时，请：
1. 查看相关文档
2. 使用debug命令检查系统状态
3. 查看日志文件获取详细信息
4. 如果问题持续存在，请提交issue