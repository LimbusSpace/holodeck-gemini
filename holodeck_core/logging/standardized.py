#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standardized Logging Framework

Provides consistent logging patterns, formatting, and configuration
across all Holodeck components.
"""

import logging
import sys
from typing import Dict, Optional, Any
from pathlib import Path
import json
import time
from functools import wraps


class StandardizedLogger:
    """
    Standardized logging framework for Holodeck components.

    Features:
    - Consistent log formatting across all modules
    - Structured logging with JSON support
    - Performance timing decorators
    - Log level management
    - File and console output handling
    """

    _loggers: Dict[str, 'StandardizedLogger'] = {}
    _default_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    _structured_format = "%(asctime)s - %(name)s - %(levelname)s - %(structured_data)s"

    def __init__(self, name: str, log_level: Optional[str] = None,
                 log_file: Optional[str] = None, structured: bool = False):
        """
        Initialize standardized logger.

        Args:
            name: Logger name (usually __name__)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path
            structured: Whether to use structured JSON logging
        """
        self.name = name
        self.structured = structured

        # Create underlying logger
        self._logger = logging.getLogger(name)

        # Set log level
        if log_level:
            self._logger.setLevel(getattr(logging, log_level.upper()))
        else:
            self._logger.setLevel(logging.INFO)

        # Avoid adding handlers multiple times
        if not self._logger.handlers:
            self._setup_handlers(log_file, structured)

    def _setup_handlers(self, log_file: Optional[str], structured: bool) -> None:
        """Setup logging handlers with appropriate formatters"""

        # Console handler - check if we're in JSON mode
        import os
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
        stream = sys.stderr if json_mode else sys.stdout
        console_handler = logging.StreamHandler(stream)
        console_handler.setLevel(self._logger.level)

        # File handler (if specified)
        file_handler = None
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(self._logger.level)

        # Choose formatter based on structured flag
        if structured:
            formatter = logging.Formatter(self._structured_format)
        else:
            formatter = logging.Formatter(self._default_format)

        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        if file_handler:
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

    @classmethod
    def get_logger(cls, name: str, log_level: Optional[str] = None,
                   log_file: Optional[str] = None, structured: bool = False) -> 'StandardizedLogger':
        """
        Get or create a standardized logger instance.

        Args:
            name: Logger name
            log_level: Logging level
            log_file: Optional log file path
            structured: Whether to use structured logging

        Returns:
            StandardizedLogger instance
        """
        if name not in cls._loggers:
            cls._loggers[name] = cls(name, log_level, log_file, structured)
        return cls._loggers[name]

    def _log_with_context(self, level: int, message: str,
                          context: Optional[Dict[str, Any]] = None,
                          **kwargs) -> None:
        """Log message with optional context data"""
        if self.structured and context:
            structured_data = json.dumps({
                "message": message,
                "context": context,
                "extra": kwargs
            }, ensure_ascii=False)
            self._logger.log(level, structured_data)
        else:
            # Include context in message for non-structured logging
            if context or kwargs:
                context_str =", ".join([
                    f"{k}={v}" for k, v in {**(context or {}), **kwargs}.items()
                ])
                message = f"{message} [{context_str}]"
            self._logger.log(level, message)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None,
              **kwargs) -> None:
        """Log debug message"""
        self._log_with_context(logging.DEBUG, message, context, **kwargs)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None,
             **kwargs) -> None:
        """Log info message"""
        self._log_with_context(logging.INFO, message, context, **kwargs)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None,
                **kwargs) -> None:
        """Log warning message"""
        self._log_with_context(logging.WARNING, message, context, **kwargs)

    def error(self, message: str, context: Optional[Dict[str, Any]] = None,
              **kwargs) -> None:
        """Log error message"""
        self._log_with_context(logging.ERROR, message, context, **kwargs)

    def critical(self, message: str, context: Optional[Dict[str, Any]] = None,
                 **kwargs) -> None:
        """Log critical message"""
        self._log_with_context(logging.CRITICAL, message, context, **kwargs)

    def exception(self, message: str, context: Optional[Dict[str, Any]] = None,
                  **kwargs) -> None:
        """Log exception with traceback"""
        if self.structured and context:
            structured_data = json.dumps({
                "message": message,
                "context": context,
                "extra": kwargs,
                "exception": True
            }, ensure_ascii=False)
            self._logger.exception(structured_data)
        else:
            self._logger.exception(f"{message} {context or {}}")

    def log_api_call(self, service: str, operation: str, duration: float,
                     success: bool, **kwargs) -> None:
        """Log API call with standardized format"""
        context = {
            "service": service,
            "operation": operation,
            "duration_sec": round(duration, 3),
            "success": success,
            **kwargs
        }

        level = logging.INFO if success else logging.ERROR
        message = f"API call: {service}.{operation}"

        self._log_with_context(level, message, context)

    def log_performance(self, operation: str, duration: float,
                        threshold: Optional[float] = None, **kwargs) -> None:
        """Log performance metrics"""
        context = {
            "operation": operation,
            "duration_sec": round(duration, 3),
            "threshold_sec": threshold,
            **kwargs
        }

        if threshold and duration > threshold:
            level = logging.WARNING
            message = f"Performance warning: {operation} took {duration:.3f}s"
        else:
            level = logging.DEBUG
            message = f"Performance: {operation} completed in {duration:.3f}s"

        self._log_with_context(level, message, context)


def log_time(operation_name: Optional[str] = None, log_threshold: Optional[float] = None):
    """
    Decorator to log function execution time.

    Args:
        operation_name: Name for the operation (defaults to function name)
        log_threshold: Log as warning if execution time exceeds this threshold
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = StandardizedLogger.get_logger(func.__module__)
            op_name = operation_name or func.__name__

            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                logger.log_performance(
                    operation=op_name,
                    duration=duration,
                    threshold=log_threshold,
                    function=func.__name__
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Function {op_name} failed after {duration:.3f}s",
                    context={
                        "operation": op_name,
                        "duration_sec": round(duration, 3),
                        "error": str(e),
                        "function": func.__name__
                    }
                )
                raise

        return wrapper
    return decorator


class LogConfig:
    """Centralized logging configuration"""

    @staticmethod
    def setup_global_logging(
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        structured: bool = False,
        log_format: Optional[str] = None
    ) -> None:
        """
        Setup global logging configuration.

        Args:
            log_level: Global log level
            log_file: Global log file path
            structured: Use structured logging globally
            log_format: Custom log format
        """
        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Create formatters
        if log_format:
            formatter = logging.Formatter(log_format)
        elif structured:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(structured_data)s"
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        # Console handler - check if we're in JSON mode
        import os
        json_mode = os.environ.get('HOLODECK_JSON_MODE', '').lower() == 'true'
        stream = sys.stderr if json_mode else sys.stdout
        console_handler = logging.StreamHandler(stream)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        logging.info(f"Global logging configured: level={log_level}, file={log_file}")


# Convenience functions
def get_logger(name: str, log_level: Optional[str] = None,
               log_file: Optional[str] = None, structured: bool = False) -> StandardizedLogger:
    """Get standardized logger instance"""
    return StandardizedLogger.get_logger(name, log_level, log_file, structured)


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None,
                 structured: bool = False) -> None:
    """Setup global logging configuration"""
    LogConfig.setup_global_logging(log_level, log_file, structured)


# Example usage
if __name__ == "__main__":
    # Setup global logging
    setup_logging(log_level="DEBUG", structured=False)

    # Get logger for this module
    logger = get_logger(__name__, log_level="DEBUG")

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message", context={"user_id": 123, "action": "test"})
    logger.warning("This is a warning message")
    logger.error("This is an error message", error_code=500)

    # Test performance logging
    logger.log_performance("test_operation", 0.123)
    logger.log_performance("slow_operation", 2.5, threshold=1.0)

    # Test API call logging
    logger.log_api_call("test_service", "test_operation", 0.456, True)
    logger.log_api_call("test_service", "failed_operation", 1.234, False, error="Timeout")

    # Test timing decorator
    @log_time("test_function", log_threshold=0.1)
    def test_function():
        time.sleep(0.05)
        return "completed"

    result = test_function()
    print(f"Function result: {result}")