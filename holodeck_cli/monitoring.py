"""
监控告警系统

提供Prometheus指标导出、告警管理和健康检查功能。
"""

import time
import json
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from http.server import HTTPServer, BaseHTTPRequestHandler
import asyncio

from holodeck_cli.logging_config import get_logger
from holodeck_cli.performance import performance_monitor, CacheOptimizer, ConcurrencyManager, MemoryOptimizer

logger = get_logger(__name__)

# Prometheus指标 - 尝试导入，如果不可用则提供替代实现
try:
    from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
    from prometheus_client import CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("prometheus_client未安装，监控功能将受限")
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    # 创建替代类以避免NameError
    class MockMetric:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def inc(self, amount=1):
            pass
        def observe(self, value):
            pass
        def set(self, value):
            pass

    class MockRegistry:
        def __init__(self):
            pass

    def generate_latest_mock(registry=None):
        return b"# Mock Prometheus metrics\n"

    # 替换真实类
    Counter = Histogram = Gauge = MockMetric
    CollectorRegistry = MockRegistry
    generate_latest = generate_latest_mock


@dataclass
class AlertRule:
    """告警规则"""
    name: str
    condition: str
    threshold: float
    severity: str  # critical, warning, info
    description: str
    enabled: bool = True


class MonitoringSystem:
    """监控告警系统"""

    def __init__(self, enable_prometheus: bool = True, metrics_port: int = 8080):
        """
        初始化监控系统

        Args:
            enable_prometheus: 是否启用Prometheus指标导出
            metrics_port: 指标导出端口
        """
        self.enable_prometheus = enable_prometheus and PROMETHEUS_AVAILABLE
        self.metrics_port = metrics_port
        self.alerts: List[AlertRule] = []
        self._lock = threading.RLock()

        # 初始化Prometheus指标
        if self.enable_prometheus:
            self._setup_prometheus_metrics()

        # 默认告警规则
        self._setup_default_alerts()

        # 启动指标服务器
        if self.enable_prometheus:
            self._start_metrics_server()

    def _setup_prometheus_metrics(self):
        """设置Prometheus指标"""
        # 使用独立的registry避免冲突
        self.registry = CollectorRegistry()

        # 请求指标
        self.requests_total = Counter(
            'holodeck_requests_total',
            'Total requests',
            ['method', 'endpoint', 'status'],
            registry=self.registry
        )

        self.request_duration = Histogram(
            'holodeck_request_duration_seconds',
            'Request duration',
            ['method', 'endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )

        # 系统指标
        self.memory_usage = Gauge(
            'holodeck_memory_usage_bytes',
            'Current memory usage in bytes',
            registry=self.registry
        )

        self.cpu_usage = Gauge(
            'holodeck_cpu_usage_percent',
            'Current CPU usage percentage',
            registry=self.registry
        )

        self.cache_hit_ratio = Gauge(
            'holodeck_cache_hit_ratio',
            'Cache hit ratio',
            registry=self.registry
        )

        self.active_connections = Gauge(
            'holodeck_active_connections',
            'Number of active connections',
            registry=self.registry
        )

        # 业务指标
        self.scenes_generated = Counter(
            'holodeck_scenes_generated_total',
            'Total scenes generated',
            ['quality', 'backend'],
            registry=self.registry
        )

        self.api_errors = Counter(
            'holodeck_api_errors_total',
            'Total API errors',
            ['service', 'error_type'],
            registry=self.registry
        )

    def _setup_default_alerts(self):
        """设置默认告警规则"""
        default_alerts = [
            AlertRule(
                name="high_error_rate",
                condition="error_rate > 0.1",
                threshold=0.1,
                severity="critical",
                description="Error rate is above 10%"
            ),
            AlertRule(
                name="high_memory_usage",
                condition="memory_usage > 3221225472",  # 3GB
                threshold=3221225472,
                severity="warning",
                description="Memory usage is above 3GB"
            ),
            AlertRule(
                name="slow_requests",
                condition="request_duration > 30",
                threshold=30.0,
                severity="warning",
                description="Request duration is above 30 seconds"
            ),
            AlertRule(
                name="low_cache_hit_ratio",
                condition="cache_hit_ratio < 0.5",
                threshold=0.5,
                severity="warning",
                description="Cache hit ratio is below 50%"
            ),
            AlertRule(
                name="high_cpu_usage",
                condition="cpu_usage > 80",
                threshold=80.0,
                severity="warning",
                description="CPU usage is above 80%"
            )
        ]

        with self._lock:
            self.alerts.extend(default_alerts)

    def _start_metrics_server(self):
        """启动指标HTTP服务器"""
        def start_server():
            server = HTTPServer(('localhost', self.metrics_port), MetricsHandler)
            server.system = self  # 传递系统引用
            logger.info(f"Prometheus metrics server started on port {self.metrics_port}")
            server.serve_forever()

        # 在独立线程中启动服务器
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

    def record_request(self, method: str, endpoint: str, status: str, duration: float):
        """记录请求指标"""
        if not self.enable_prometheus:
            return

        try:
            self.requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            self.request_duration.labels(method=method, endpoint=endpoint).observe(duration)
        except Exception as e:
            logger.error(f"Failed to record request metrics: {e}")

    def record_scene_generation(self, quality: str, backend: str):
        """记录场景生成指标"""
        if not self.enable_prometheus:
            return

        try:
            self.scenes_generated.labels(quality=quality, backend=backend).inc()
        except Exception as e:
            logger.error(f"Failed to record scene generation metrics: {e}")

    def record_api_error(self, service: str, error_type: str):
        """记录API错误指标"""
        if not self.enable_prometheus:
            return

        try:
            self.api_errors.labels(service=service, error_type=error_type).inc()
        except Exception as e:
            logger.error(f"Failed to record API error metrics: {e}")

    def update_system_metrics(self):
        """更新系统指标"""
        if not self.enable_prometheus:
            return

        try:
            # 内存使用
            memory_optimizer = MemoryOptimizer()
            memory_usage = memory_optimizer.get_memory_usage()
            self.memory_usage.set(memory_usage["rss"])

            # CPU使用 (简化版)
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_usage.set(cpu_percent)

            # 缓存命中率
            cache = CacheOptimizer()
            cache_stats = cache.get_stats()
            hit_ratio = cache_stats.get("hit_rate", 0.0)
            self.cache_hit_ratio.set(hit_ratio)

        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")

    def add_alert_rule(self, alert: AlertRule):
        """添加告警规则"""
        with self._lock:
            # 移除同名的现有规则
            self.alerts = [a for a in self.alerts if a.name != alert.name]
            self.alerts.append(alert)

        logger.info(f"Added alert rule: {alert.name}")

    def remove_alert_rule(self, name: str):
        """移除告警规则"""
        with self._lock:
            self.alerts = [a for a in self.alerts if a.name != name]

        logger.info(f"Removed alert rule: {name}")

    def check_alerts(self) -> List[Dict[str, Any]]:
        """检查告警条件"""
        triggered_alerts = []

        with self._lock:
            for alert in self.alerts:
                if not alert.enabled:
                    continue

                try:
                    if self._evaluate_alert_condition(alert):
                        triggered_alerts.append({
                            "name": alert.name,
                            "severity": alert.severity,
                            "description": alert.description,
                            "threshold": alert.threshold,
                            "timestamp": time.time()
                        })
                except Exception as e:
                    logger.error(f"Failed to evaluate alert {alert.name}: {e}")

        return triggered_alerts

    def _evaluate_alert_condition(self, alert: AlertRule) -> bool:
        """评估告警条件"""
        # 这里实现简单的条件评估逻辑
        # 实际项目中可能需要更复杂的表达式引擎

        if alert.name == "high_memory_usage":
            memory_optimizer = MemoryOptimizer()
            memory_usage = memory_optimizer.get_memory_usage()
            return memory_usage["rss"] > alert.threshold

        elif alert.name == "low_cache_hit_ratio":
            cache = CacheOptimizer()
            cache_stats = cache.get_stats()
            hit_ratio = cache_stats.get("hit_rate", 0.0)
            return hit_ratio < alert.threshold

        elif alert.name == "high_cpu_usage":
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            return cpu_percent > alert.threshold

        # 其他告警条件的评估可以在这里添加
        return False

    def get_health_status(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        try:
            # 更新指标
            self.update_system_metrics()

            # 检查告警
            active_alerts = self.check_alerts()

            # 构建健康状态
            status = {
                "status": "healthy" if not active_alerts else "unhealthy",
                "timestamp": time.time(),
                "checks": {
                    "memory": self._check_memory_health(),
                    "cache": self._check_cache_health(),
                    "performance": self._check_performance_health(),
                    "alerts": {
                        "status": "pass" if not active_alerts else "fail",
                        "details": active_alerts
                    }
                }
            }

            return status

        except Exception as e:
            logger.error(f"Failed to get health status: {e}")
            return {
                "status": "error",
                "timestamp": time.time(),
                "error": str(e)
            }

    def _check_memory_health(self) -> Dict[str, Any]:
        """检查内存健康状态"""
        try:
            memory_optimizer = MemoryOptimizer()
            memory_usage = memory_optimizer.get_memory_usage()

            # 检查内存使用是否过高
            if memory_usage["rss_mb"] > 1024:  # 1GB
                return {
                    "status": "fail",
                    "details": f"Memory usage too high: {memory_usage['rss_mb']:.1f}MB"
                }
            else:
                return {
                    "status": "pass",
                    "details": f"Memory usage normal: {memory_usage['rss_mb']:.1f}MB"
                }

        except Exception as e:
            return {
                "status": "error",
                "details": f"Memory check failed: {e}"
            }

    def _check_cache_health(self) -> Dict[str, Any]:
        """检查缓存健康状态"""
        try:
            cache = CacheOptimizer()
            cache_stats = cache.get_stats()

            # 检查缓存命中率
            hit_ratio = cache_stats.get("hit_rate", 0.0)
            if hit_ratio < 0.3:  # 30%
                return {
                    "status": "warning",
                    "details": f"Cache hit ratio low: {hit_ratio:.1%}"
                }
            else:
                return {
                    "status": "pass",
                    "details": f"Cache hit ratio good: {hit_ratio:.1%}"
                }

        except Exception as e:
            return {
                "status": "error",
                "details": f"Cache check failed: {e}"
            }

    def _check_performance_health(self) -> Dict[str, Any]:
        """检查性能健康状态"""
        try:
            # 获取最近的性能指标
            stats = performance_monitor.get_statistics()

            if not stats:
                return {
                    "status": "pass",
                    "details": "No performance data available"
                }

            # 检查平均响应时间
            for operation, op_stats in stats.items():
                if isinstance(op_stats, dict) and "duration_stats" in op_stats:
                    avg_duration = op_stats["duration_stats"]["avg"]
                    if avg_duration > 10.0:  # 10秒
                        return {
                            "status": "warning",
                            "details": f"Slow operation {operation}: {avg_duration:.2f}s average"
                        }

            return {
                "status": "pass",
                "details": "Performance metrics normal"
            }

        except Exception as e:
            return {
                "status": "error",
                "details": f"Performance check failed: {e}"
            }


class MetricsHandler(BaseHTTPRequestHandler):
    """Prometheus指标HTTP处理器"""

    def do_GET(self):
        """处理GET请求"""
        if self.path == '/metrics':
            self._handle_metrics()
        elif self.path == '/health':
            self._handle_health()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_metrics(self):
        """处理指标请求"""
        try:
            # 更新系统指标
            self.server.system.update_system_metrics()

            # 生成指标数据
            metrics_data = generate_latest(self.server.system.registry)

            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(metrics_data)

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error generating metrics: {e}".encode())

    def _handle_health(self):
        """处理健康检查请求"""
        try:
            health_status = self.server.system.get_health_status()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = json.dumps(health_status, indent=2, ensure_ascii=False)
            self.wfile.write(response.encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            error_response = json.dumps({
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            })
            self.wfile.write(error_response.encode())

    def log_message(self, format, *args):
        """禁用默认的日志输出"""
        pass


# 全局监控系统实例
monitoring_system = None


def setup_monitoring(enable_prometheus: bool = True, metrics_port: int = 8080) -> MonitoringSystem:
    """设置监控系统"""
    global monitoring_system

    if monitoring_system is None:
        monitoring_system = MonitoringSystem(enable_prometheus, metrics_port)

    return monitoring_system


def get_monitoring_system() -> Optional[MonitoringSystem]:
    """获取监控系统实例"""
    return monitoring_system


# 装饰器：监控函数执行
# 监控函数执行
def monitor_execution(operation_name: str):
    """监控函数执行的装饰器"""
    def decorator(func):
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            status = "500"

            try:
                result = func(*args, **kwargs)
                success = True
                status = "200"
                return result
            except Exception as e:
                status = "500"
                raise
            finally:
                duration = time.time() - start_time

                # 记录指标
                if monitoring_system:
                    monitoring_system.record_request(
                        method="FUNCTION",
                        endpoint=operation_name,
                        status=status,
                        duration=duration
                    )

        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = False
            status = "500"

            try:
                result = await func(*args, **kwargs)
                success = True
                status = "200"
                return result
            except Exception as e:
                status = "500"
                raise
            finally:
                duration = time.time() - start_time

                # 记录指标
                if monitoring_system:
                    monitoring_system.record_request(
                        method="FUNCTION",
                        endpoint=operation_name,
                        status=status,
                        duration=duration
                    )

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator