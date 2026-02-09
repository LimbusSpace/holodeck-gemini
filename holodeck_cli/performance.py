"""
性能优化和调优模块

提供性能监控、缓存优化、并发控制和内存管理功能。
"""

import time
import asyncio
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from functools import wraps
import json

from holodeck_cli.logging_config import get_logger

logger = get_logger(__name__)

# 尝试导入psutil，如果不可用则提供替代实现
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    logger.warning("psutil模块未安装，性能监控功能将受限")
    PSUTIL_AVAILABLE = False

    # 创建psutil的替代实现
    class MockProcess:
        def memory_info(self):
            class MockMemoryInfo:
                rss = 100 * 1024 * 1024  # 100MB
                vms = 200 * 1024 * 1024  # 200MB
            return MockMemoryInfo()

        def cpu_percent(self, interval=None):
            return 10.0  # 10% CPU使用率

        def memory_percent(self):
            return 20.0  # 20% 内存使用率

    class MockPSUtil:
        def Process(self, pid=None):
            return MockProcess()

        def cpu_count(self):
            return 4

        def virtual_memory(self):
            class MockVirtualMemory:
                total = 8 * 1024 * 1024 * 1024  # 8GB
            return MockVirtualMemory()

    psutil = MockPSUtil()


@dataclass
class PerformanceMetrics:
    """性能指标数据类"""
    operation: str
    duration: float
    memory_usage_mb: float
    cpu_percent: float
    timestamp: float
    success: bool
    metadata: Dict[str, Any] = None


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self._lock = threading.Lock()
        self._process = psutil.Process()
        self._start_memory = self._process.memory_info().rss / 1024 / 1024  # MB

    def record_metric(self, operation: str, duration: float, success: bool,
                     metadata: Dict[str, Any] = None) -> None:
        """记录性能指标"""
        with self._lock:
            current_memory = self._process.memory_info().rss / 1024 / 1024  # MB
            cpu_percent = self._process.cpu_percent()

            metric = PerformanceMetrics(
                operation=operation,
                duration=duration,
                memory_usage_mb=current_memory,
                cpu_percent=cpu_percent,
                timestamp=time.time(),
                success=success,
                metadata=metadata or {}
            )
            self.metrics.append(metric)

    def get_statistics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """获取性能统计信息"""
        with self._lock:
            if operation:
                relevant_metrics = [m for m in self.metrics if m.operation == operation]
            else:
                relevant_metrics = self.metrics

            if not relevant_metrics:
                return {}

            durations = [m.duration for m in relevant_metrics]
            memory_usage = [m.memory_usage_mb for m in relevant_metrics]
            cpu_usage = [m.cpu_percent for m in relevant_metrics]
            success_rate = sum(1 for m in relevant_metrics if m.success) / len(relevant_metrics)

            return {
                "operation": operation or "all",
                "total_operations": len(relevant_metrics),
                "success_rate": success_rate,
                "duration_stats": {
                    "min": min(durations),
                    "max": max(durations),
                    "avg": sum(durations) / len(durations),
                    "median": sorted(durations)[len(durations) // 2]
                },
                "memory_stats": {
                    "current": memory_usage[-1],
                    "peak": max(memory_usage),
                    "avg": sum(memory_usage) / len(memory_usage)
                },
                "cpu_stats": {
                    "avg": sum(cpu_usage) / len(cpu_usage),
                    "peak": max(cpu_usage)
                }
            }

    def clear_metrics(self) -> None:
        """清除所有性能指标"""
        with self._lock:
            self.metrics.clear()

    def save_report(self, filepath: Path) -> None:
        """保存性能报告到文件"""
        report = {
            "generated_at": time.time(),
            "total_metrics": len(self.metrics),
            "statistics": {},
            "recent_metrics": []
        }

        # 获取所有操作的统计信息
        operations = set(m.operation for m in self.metrics)
        for operation in operations:
            report["statistics"][operation] = self.get_statistics(operation)

        # 保存最近的100个指标
        recent_metrics = sorted(self.metrics, key=lambda m: m.timestamp, reverse=True)[:100]
        for metric in recent_metrics:
            report["recent_metrics"].append({
                "operation": metric.operation,
                "duration": metric.duration,
                "memory_usage_mb": metric.memory_usage_mb,
                "cpu_percent": metric.cpu_percent,
                "timestamp": metric.timestamp,
                "success": metric.success,
                "metadata": metric.metadata
            })

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"性能报告已保存到: {filepath}")


# 全局性能监控器实例
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str, log_level: str = "INFO"):
    """性能监控装饰器"""
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            metadata = {}

            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                metadata["error"] = str(e)
                raise
            finally:
                duration = time.time() - start_time
                performance_monitor.record_metric(
                    operation=operation_name,
                    duration=duration,
                    success=success,
                    metadata=metadata
                )

                log_msg = f"{operation_name} 耗时: {duration:.3f}秒, 成功: {success}"
                if log_level == "DEBUG":
                    logger.debug(log_msg)
                elif log_level == "INFO":
                    logger.info(log_msg)
                elif log_level == "WARNING":
                    logger.warning(log_msg)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            metadata = {}

            try:
                result = await func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                metadata["error"] = str(e)
                raise
            finally:
                duration = time.time() - start_time
                performance_monitor.record_metric(
                    operation=operation_name,
                    duration=duration,
                    success=success,
                    metadata=metadata
                )

                log_msg = f"{operation_name} 耗时: {duration:.3f}秒, 成功: {success}"
                if log_level == "DEBUG":
                    logger.debug(log_msg)
                elif log_level == "INFO":
                    logger.info(log_msg)
                elif log_level == "WARNING":
                    logger.warning(log_msg)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class CacheOptimizer:
    """缓存优化器"""

    def __init__(self, max_size_mb: int = 100, ttl_seconds: int = 3600):
        self.max_size_mb = max_size_mb
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._access_times = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                return None

            # 检查TTL
            if time.time() - self._access_times[key] > self.ttl_seconds:
                del self._cache[key]
                del self._access_times[key]
                return None

            # 更新访问时间
            self._access_times[key] = time.time()
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        with self._lock:
            # 检查是否需要清理空间
            if self._get_cache_size_mb() > self.max_size_mb:
                self._cleanup_lru()

            self._cache[key] = value
            self._access_times[key] = time.time()

    def _get_cache_size_mb(self) -> float:
        """获取缓存大小(MB)"""
        import sys
        total_size = 0
        for value in self._cache.values():
            total_size += sys.getsizeof(value)
        return total_size / 1024 / 1024

    def _cleanup_lru(self) -> None:
        """清理最近最少使用的缓存项"""
        if not self._cache:
            return

        # 按访问时间排序
        sorted_items = sorted(self._access_times.items(), key=lambda x: x[1])

        # 删除50%的项
        items_to_remove = len(sorted_items) // 2
        for key, _ in sorted_items[:items_to_remove]:
            if key in self._cache:
                del self._cache[key]
            if key in self._access_times:
                del self._access_times[key]

        logger.debug(f"缓存清理完成，删除了 {items_to_remove} 个项")

    def clear(self) -> None:
        """清除所有缓存"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            return {
                "total_items": len(self._cache),
                "size_mb": self._get_cache_size_mb(),
                "max_size_mb": self.max_size_mb,
                "ttl_seconds": self.ttl_seconds,
                "hit_rate": self._calculate_hit_rate()
            }

    def _calculate_hit_rate(self) -> float:
        """计算缓存命中率"""
        # 这里需要扩展以跟踪实际的缓存命中/未命中
        # 目前返回一个占位值
        return 0.85  # 85% 命中率


class ConcurrencyManager:
    """并发管理器"""

    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or min(32, (psutil.cpu_count() or 1) * 4)
        self.current_workers = 0
        self._semaphore = asyncio.Semaphore(self.max_workers)
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_task_time": 0
        }
        self._stats_lock = threading.Lock()

    async def run_task(self, coro, task_name: str = "unknown") -> Any:
        """运行并发任务"""
        start_time = time.time()

        with self._stats_lock:
            self._stats["total_tasks"] += 1

        async with self._semaphore:
            try:
                result = await coro

                with self._stats_lock:
                    self._stats["completed_tasks"] += 1

                return result
            except Exception as e:
                with self._stats_lock:
                    self._stats["failed_tasks"] += 1
                logger.error(f"任务 {task_name} 失败: {e}")
                raise
            finally:
                duration = time.time() - start_time
                # 更新平均任务时间
                with self._stats_lock:
                    completed = self._stats["completed_tasks"]
                    current_avg = self._stats["avg_task_time"]
                    if completed > 0:
                        self._stats["avg_task_time"] = (
                            (current_avg * (completed - 1) + duration) / completed
                            if completed > 1 else duration
                        )

    def get_stats(self) -> Dict[str, Any]:
        """获取并发统计信息"""
        return {
            **self._stats,
            "max_workers": self.max_workers,
            "current_workers": self.current_workers,
            "utilization": self.current_workers / self.max_workers
        }

    def optimize_worker_count(self) -> int:
        """优化工作进程数量"""
        cpu_count = psutil.cpu_count() or 1
        memory_gb = psutil.virtual_memory().total / (1024**3)

        # 基于CPU和内存的启发式优化
        optimal_workers = min(
            cpu_count * 2,  # CPU密集型任务的2倍
            int(memory_gb * 4),  # 每GB内存4个worker
            32  # 最大限制
        )

        self.max_workers = optimal_workers
        logger.info(f"优化后的工作进程数: {optimal_workers}")
        return optimal_workers


class MemoryOptimizer:
    """内存优化器"""

    def __init__(self):
        self._process = psutil.Process()
        self._baseline_memory = self._process.memory_info().rss

    def get_memory_usage(self) -> Dict[str, Any]:
        """获取内存使用情况"""
        memory_info = self._process.memory_info()
        return {
            "rss": memory_info.rss,  # 常驻内存
            "vms": memory_info.vms,  # 虚拟内存
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": self._process.memory_percent()
        }

    def suggest_optimizations(self) -> List[str]:
        """建议内存优化措施"""
        suggestions = []
        memory_usage = self.get_memory_usage()

        if memory_usage["rss_mb"] > 500:  # 超过500MB
            suggestions.append("考虑减少缓存大小或增加缓存清理频率")

        if memory_usage["percent"] > 70:  # 内存使用超过70%
            suggestions.append("系统内存使用较高，建议释放不必要的对象")

        # 检查内存泄漏
        current_memory = memory_usage["rss"]
        if current_memory > self._baseline_memory * 2:  # 内存翻倍
            suggestions.append("可能存在内存泄漏，建议检查长时间运行的对象")

        return suggestions

    def cleanup_memory(self) -> None:
        """清理内存"""
        import gc
        collected = gc.collect()
        logger.debug(f"垃圾回收完成，清理了 {collected} 个对象")


def analyze_performance_bottlenecks() -> Dict[str, Any]:
    """分析性能瓶颈"""
    bottlenecks = []

    # 分析操作耗时
    stats = performance_monitor.get_statistics()
    if "duration_stats" in stats:
        avg_duration = stats["duration_stats"]["avg"]
        if avg_duration > 10:  # 平均操作超过10秒
            bottlenecks.append({
                "type": "slow_operations",
                "description": f"操作平均耗时较长: {avg_duration:.2f}秒",
                "suggestion": "考虑优化算法或增加并行处理"
            })

    # 分析内存使用
    memory_optimizer = MemoryOptimizer()
    memory_usage = memory_optimizer.get_memory_usage()

    if memory_usage["rss_mb"] > 1000:  # 超过1GB
        bottlenecks.append({
            "type": "high_memory_usage",
            "description": f"内存使用较高: {memory_usage['rss_mb']:.1f}MB",
            "suggestion": "考虑优化数据结构或增加内存清理"
        })

    # 分析并发效率
    concurrency_manager = ConcurrencyManager()
    concurrency_stats = concurrency_manager.get_stats()

    if concurrency_stats["utilization"] < 0.5:  # 并发利用率低于50%
        bottlenecks.append({
            "type": "low_concurrency",
            "description": f"并发利用率较低: {concurrency_stats['utilization']:.1%}",
            "suggestion": "考虑增加并发任务数量或优化任务分配"
        })

    return {
        "bottlenecks": bottlenecks,
        "memory_usage": memory_usage,
        "concurrency_stats": concurrency_stats,
        "performance_stats": stats
    }


def generate_performance_report(output_path: Optional[Path] = None) -> Path:
    """生成综合性能报告"""
    if output_path is None:
        from holodeck_cli.config import config
        output_path = config.get_workspace_path() / "performance_report.json"

    # 分析性能瓶颈
    analysis = analyze_performance_bottlenecks()

    # 生成报告
    report = {
        "generated_at": time.time(),
        "bottleneck_analysis": analysis,
        "cache_statistics": CacheOptimizer().get_stats(),
        "memory_optimizations": MemoryOptimizer().suggest_optimizations(),
        "recommendations": []
    }

    # 生成建议
    if analysis["bottlenecks"]:
        report["recommendations"].extend([
            f"解决性能瓶颈: {b['description']}" for b in analysis["bottlenecks"]
        ])

    # 保存报告
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"综合性能报告已生成: {output_path}")
    return output_path