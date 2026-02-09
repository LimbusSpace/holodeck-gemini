#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Holodeck Exception Framework

Provides a comprehensive exception hierarchy and error handling framework
for all Holodeck components with standardized error codes, messages,
and recovery suggestions.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for Holodeck components"""

    # Configuration Errors (1000-1099)
    CONFIG_MISSING = 1001
    CONFIG_INVALID = 1002
    CONFIG_LOAD_FAILED = 1003

    # API Communication Errors (2000-2099)
    API_CONNECTION_FAILED = 2001
    API_TIMEOUT = 2002
    API_RATE_LIMITED = 2003
    API_AUTH_FAILED = 2004
    API_INVALID_RESPONSE = 2005
    API_SERVICE_UNAVAILABLE = 2006

    # Input Validation Errors (3000-3099)
    VALIDATION_REQUIRED_FIELD = 3001
    VALIDATION_INVALID_FORMAT = 3002
    VALIDATION_OUT_OF_RANGE = 3003
    VALIDATION_FILE_NOT_FOUND = 3004
    VALIDATION_FILE_INVALID = 3005

    # Image Generation Errors (4000-4099)
    IMAGE_GEN_FAILED = 4001
    IMAGE_GEN_TIMEOUT = 4002
    IMAGE_GEN_QUALITY_LOW = 4003
    IMAGE_GEN_INVALID_PROMPT = 4004

    # 3D Generation Errors (5000-5099)
    THREED_GEN_FAILED = 5001
    THREED_GEN_TIMEOUT = 5002
    THREED_GEN_INVALID_IMAGE = 5003
    THREED_GEN_MODEL_ERROR = 5004

    # LLM/Naming Errors (6000-6099)
    LLM_REQUEST_FAILED = 6001
    LLM_INVALID_RESPONSE = 6002
    LLM_TIMEOUT = 6003
    LLM_QUOTA_EXCEEDED = 6004

    # Workflow/Orchestration Errors (7000-7099)
    WORKFLOW_STEP_FAILED = 7001
    WORKFLOW_DEPENDENCY_MISSING = 7002
    WORKFLOW_INVALID_STATE = 7003
    WORKFLOW_TIMEOUT = 7004

    # Resource/System Errors (8000-8099)
    RESOURCE_NOT_FOUND = 8001
    RESOURCE_BUSY = 8002
    RESOURCE_INSUFFICIENT_MEMORY = 8003
    RESOURCE_DISK_FULL = 8004

    # Unknown/Generic Errors (9000-9099)
    UNKNOWN_ERROR = 9001
    INTERNAL_ERROR = 9002


class HolodeckError(Exception):
    """
    Base exception class for all Holodeck components.

    Features:
    - Standardized error codes
    - Structured error information
    - Recovery suggestions
    - Logging integration
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[ErrorCode] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize HolodeckError.

        Args:
            message: Human-readable error message
            error_code: Standardized error code
            context: Additional context information
            recovery_suggestions: List of suggested recovery actions
            original_exception: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or ErrorCode.UNKNOWN_ERROR
        self.context = context or {}
        self.recovery_suggestions = recovery_suggestions or []
        self.original_exception = original_exception
        self.timestamp = datetime.now()
        self.error_id = f"err_{self.timestamp.strftime('%Y%m%d_%H%M%S')}_{id(self)}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format"""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "error_code": self.error_code.value,
            "error_code_name": self.error_code.name,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "recovery_suggestions": self.recovery_suggestions,
            "original_exception": str(self.original_exception) if self.original_exception else None
        }

    def to_json(self) -> str:
        """Convert error to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def log_error(self, logger_instance: Optional[logging.Logger] = None) -> None:
        """Log this error with appropriate level and context"""
        logger_instance = logger_instance or logger

        log_data = {
            "error_id": self.error_id,
            "error_code": self.error_code.name,
            "message": self.message,
            **self.context
        }

        logger_instance.error(f"HolodeckError: {self.message}", extra=log_data)

    def __str__(self) -> str:
        """String representation of the error"""
        base_str = f"[{self.error_code.name}] {self.message}"

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_str += f" (Context: {context_str})"

        if self.recovery_suggestions:
            suggestions_str ="; ".join(self.recovery_suggestions)
            base_str += f" (Suggestions: {suggestions_str})"

        return base_str


class ConfigurationError(HolodeckError):
    """Configuration-related errors"""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        error_code = ErrorCode.CONFIG_MISSING if "missing" in message.lower() else ErrorCode.CONFIG_INVALID

        context = context or {}
        if config_key:
            context["config_key"] = config_key

        recovery_suggestions = recovery_suggestions or [
            "Check environment variables",
            "Verify .env file configuration",
            "Ensure required configuration keys are set"
        ]

        super().__init__(message, error_code, context, recovery_suggestions)


class ValidationError(HolodeckError):
    """Input validation errors"""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        field_value: Any = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        error_code = ErrorCode.VALIDATION_INVALID_FORMAT
        if "required" in message.lower():
            error_code = ErrorCode.VALIDATION_REQUIRED_FIELD
        elif "range" in message.lower() or "out of" in message.lower():
            error_code = ErrorCode.VALIDATION_OUT_OF_RANGE

        context = context or {}
        if field_name:
            context["field_name"] = field_name
        if field_value is not None:
            context["field_value"] = field_value

        recovery_suggestions = recovery_suggestions or [
            "Check input format and requirements",
            "Validate input data before submission",
            "Review API documentation for correct format"
        ]

        super().__init__(message, error_code, context, recovery_suggestions)


class APIError(HolodeckError):
    """API communication errors"""

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        status_code: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None,
        original_exception: Optional[Exception] = None
    ):
        # Determine error code based on message content
        if "timeout" in message.lower():
            error_code = ErrorCode.API_TIMEOUT
        elif "rate limit" in message.lower() or "429" in str(status_code):
            error_code = ErrorCode.API_RATE_LIMITED
        elif "auth" in message.lower() or "401" in str(status_code) or "403" in str(status_code):
            error_code = ErrorCode.API_AUTH_FAILED
        elif "connection" in message.lower():
            error_code = ErrorCode.API_CONNECTION_FAILED
        elif "503" in str(status_code) or "unavailable" in message.lower():
            error_code = ErrorCode.API_SERVICE_UNAVAILABLE
        else:
            error_code = ErrorCode.API_INVALID_RESPONSE

        context = context or {}
        if service_name:
            context["service_name"] = service_name
        if status_code:
            context["http_status_code"] = status_code

        recovery_suggestions = recovery_suggestions or [
            "Check network connectivity",
            "Verify API credentials",
            "Retry the operation after a delay",
            "Check service status and documentation"
        ]

        super().__init__(message, error_code, context, recovery_suggestions, original_exception)


class ImageGenerationError(HolodeckError):
    """Image generation specific errors"""

    def __init__(
        self,
        message: str,
        prompt: Optional[str] = None,
        resolution: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        error_code = ErrorCode.IMAGE_GEN_FAILED
        if "timeout" in message.lower():
            error_code = ErrorCode.IMAGE_GEN_TIMEOUT
        elif "invalid prompt" in message.lower() or "prompt" in message.lower():
            error_code = ErrorCode.IMAGE_GEN_INVALID_PROMPT

        context = context or {}
        if prompt:
            context["prompt"] = prompt[:100] + "..." if len(prompt) > 100 else prompt
        if resolution:
            context["resolution"] = resolution

        recovery_suggestions = recovery_suggestions or [
            "Simplify the prompt",
            "Try a different resolution",
            "Check prompt for inappropriate content",
            "Retry with a shorter prompt"
        ]

        super().__init__(message, error_code, context, recovery_suggestions)


class ThreeDGenerationError(HolodeckError):
    """3D generation specific errors"""

    def __init__(
        self,
        message: str,
        image_path: Optional[str] = None,
        backend: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        error_code = ErrorCode.THREED_GEN_FAILED
        if "timeout" in message.lower():
            error_code = ErrorCode.THREED_GEN_TIMEOUT
        elif "invalid image" in message.lower() or "image" in message.lower():
            error_code = ErrorCode.THREED_GEN_INVALID_IMAGE

        context = context or {}
        if image_path:
            context["image_path"] = str(image_path)
        if backend:
            context["backend"] = backend

        recovery_suggestions = recovery_suggestions or [
            "Check input image format and quality",
            "Try a different 3D generation backend",
            "Ensure image has clear object boundaries",
            "Use higher resolution input image"
        ]

        super().__init__(message, error_code, context, recovery_suggestions)


class LLMError(HolodeckError):
    """LLM/Naming service specific errors"""

    def __init__(
        self,
        message: str,
        prompt: Optional[str] = None,
        service_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        error_code = ErrorCode.LLM_REQUEST_FAILED
        if "timeout" in message.lower():
            error_code = ErrorCode.LLM_TIMEOUT
        elif "quota" in message.lower() or "limit" in message.lower():
            error_code = ErrorCode.LLM_QUOTA_EXCEEDED

        context = context or {}
        if prompt:
            context["prompt"] = prompt[:100] + "..." if len(prompt) > 100 else prompt
        if service_name:
            context["service_name"] = service_name

        recovery_suggestions = recovery_suggestions or [
            "Check LLM service availability",
            "Verify API quota and billing",
            "Simplify the prompt",
            "Try again later"
        ]

        super().__init__(message, error_code, context, recovery_suggestions)


class WorkflowError(HolodeckError):
    """Workflow orchestration errors"""

    def __init__(
        self,
        message: str,
        step_name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        error_code = ErrorCode.WORKFLOW_STEP_FAILED
        if "timeout" in message.lower():
            error_code = ErrorCode.WORKFLOW_TIMEOUT
        elif "dependency" in message.lower() or "missing" in message.lower():
            error_code = ErrorCode.WORKFLOW_DEPENDENCY_MISSING
        elif "state" in message.lower() or "invalid" in message.lower():
            error_code = ErrorCode.WORKFLOW_INVALID_STATE

        context = context or {}
        if step_name:
            context["step_name"] = step_name
        if workflow_id:
            context["workflow_id"] = workflow_id

        recovery_suggestions = recovery_suggestions or [
            "Check workflow dependencies",
            "Verify previous steps completed successfully",
            "Restart the workflow",
            "Check system resources"
        ]

        super().__init__(message, error_code, context, recovery_suggestions)


class ResourceError(HolodeckError):
    """Resource and system errors"""

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_path: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        error_code = ErrorCode.RESOURCE_NOT_FOUND
        if "busy" in message.lower() or "locked" in message.lower():
            error_code = ErrorCode.RESOURCE_BUSY
        elif "memory" in message.lower() or "oom" in message.lower():
            error_code = ErrorCode.RESOURCE_INSUFFICIENT_MEMORY
        elif "disk" in message.lower() or "space" in message.lower():
            error_code = ErrorCode.RESOURCE_DISK_FULL

        context = context or {}
        if resource_type:
            context["resource_type"] = resource_type
        if resource_path:
            context["resource_path"] = str(resource_path)

        recovery_suggestions = recovery_suggestions or [
            "Check resource availability",
            "Free up system resources",
            "Verify file permissions",
            "Check disk space"
        ]

        super().__init__(message, error_code, context, recovery_suggestions)


class ErrorHandler:
    """Centralized error handling and recovery"""

    @staticmethod
    def handle_error(
        error: Exception,
        logger_instance: Optional[logging.Logger] = None,
        reraise: bool = True
    ) -> Dict[str, Any]:
        """
        Handle an error with standardized logging and recovery suggestions.

        Args:
            error: Exception to handle
            logger_instance: Logger to use (defaults to module logger)
            reraise: Whether to re-raise the error after handling

        Returns:
            Dictionary with error information and handling results
        """
        logger_instance = logger_instance or logger

        if isinstance(error, HolodeckError):
            # Already a HolodeckError, just log it
            error.log_error(logger_instance)
            error_info = error.to_dict()
        else:
            # Convert to HolodeckError
            holodeck_error = HolodeckError(
                message=str(error),
                error_code=ErrorCode.UNKNOWN_ERROR,
                original_exception=error
            )
            holodeck_error.log_error(logger_instance)
            error_info = holodeck_error.to_dict()

        # Log original exception if different
        if not isinstance(error, HolodeckError):
            logger_instance.exception(f"Original exception: {type(error).__name__}")

        if reraise:
            raise error

        return error_info

    @staticmethod
    def create_error_response(error: Exception) -> Dict[str, Any]:
        """Create standardized error response for APIs"""
        if isinstance(error, HolodeckError):
            return {
                "success": False,
                "error": error.to_dict()
            }
        else:
            return {
                "success": False,
                "error": {
                    "message": str(error),
                    "error_code": ErrorCode.UNKNOWN_ERROR.value,
                    "error_code_name": ErrorCode.UNKNOWN_ERROR.name,
                    "timestamp": datetime.now().isoformat()
                }
            }


# Example usage and testing
if __name__ == "__main__":
    # Test different error types
    try:
        raise ConfigurationError(
            "Missing required API key",
            config_key="HUNYUAN_SECRET_ID",
            context={"service": "hunyuan"}
        )
    except HolodeckError as e:
        print(f"Caught error: {e}")
        print(f"Error dict: {e.to_dict()}")
        print(f"Error JSON: {e.to_json()}")

    # Test error handling
    try:
        raise ValidationError(
            "Invalid image format",
            field_name="image_path",
            field_value="invalid.png"
        )
    except Exception as e:
        error_response = ErrorHandler.create_error_response(e)
        print(f"Error response: {json.dumps(error_response, indent=2)}")