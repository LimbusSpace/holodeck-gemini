"""
Holodeck 统一错误处理类

实现标准化的错误对象和错误处理机制
"""

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from holodeck_core.schemas.error_codes import ErrorCode, ErrorInfo, get_error_info


class HolodeckError(BaseModel):
    """
    Holodeck 标准错误对象
    """

    code: str = Field(..., description="错误码")
    component: str = Field(..., description="错误组件")
    message: str = Field(..., description="错误消息")
    retryable: bool = Field(False, description="是否可重试")
    suggested_actions: List[str] = Field(default_factory=list, description="建议操作")
    logs: Dict[str, str] = Field(default_factory=dict, description="相关日志文件")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="错误时间戳")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return self.model_dump()

    def to_json(self) -> str:
        """
        转换为 JSON 字符串
        """
        return self.model_dump_json(indent=2)

    @classmethod
    def from_exception(
        cls,
        error_code: ErrorCode,
        original_exception: Exception,
        session_id: Optional[str] = None,
        component: Optional[str] = None,
        additional_details: Optional[Dict[str, Any]] = None
    ) -> 'HolodeckError':
        """
        从异常创建 HolodeckError
        """
        error_info = get_error_info(error_code)

        # 构建日志信息
        logs = {}
        if session_id:
            session_dir = Path("workspace/sessions") / session_id
            if session_dir.exists():
                run_log = session_dir / "run.log"
                if run_log.exists():
                    logs["run_log"] = str(run_log)

                dfs_trace = session_dir / "dfs_trace_v1.json"
                if dfs_trace.exists():
                    logs["trace"] = str(dfs_trace)

        # 构建错误详情
        details = {
            "exception_type": type(original_exception).__name__,
            "exception_message": str(original_exception),
            "traceback": traceback.format_exc()
        }

        if additional_details:
            details.update(additional_details)

        return cls(
            code=error_code.value,
            component=component or error_info.component,
            message=f"{error_info.message}: {str(original_exception)}",
            retryable=error_info.retryable,
            suggested_actions=error_info.suggested_actions,
            logs=logs,
            details=details
        )

    @classmethod
    def from_error_code(
        cls,
        error_code: ErrorCode,
        message: Optional[str] = None,
        session_id: Optional[str] = None,
        component: Optional[str] = None,
        additional_actions: Optional[List[str]] = None,
        additional_details: Optional[Dict[str, Any]] = None
    ) -> 'HolodeckError':
        """
        从错误码创建 HolodeckError
        """
        error_info = get_error_info(error_code)

        # 构建日志信息
        logs = {}
        if session_id:
            session_dir = Path("workspace/sessions") / session_id
            if session_dir.exists():
                run_log = session_dir / "run.log"
                if run_log.exists():
                    logs["run_log"] = str(run_log)

                dfs_trace = session_dir / "dfs_trace_v1.json"
                if dfs_trace.exists():
                    logs["trace"] = str(dfs_trace)

        # 合并建议操作
        suggested_actions = error_info.suggested_actions.copy()
        if additional_actions:
            suggested_actions.extend(additional_actions)

        return cls(
            code=error_code.value,
            component=component or error_info.component,
            message=message or error_info.message,
            retryable=error_info.retryable,
            suggested_actions=suggested_actions,
            logs=logs,
            details=additional_details
        )


class ErrorResponse(BaseModel):
    """
    错误响应对象
    """

    ok: bool = Field(False, description="操作是否成功")
    session_id: Optional[str] = Field(None, description="会话ID")
    failed_stage: Optional[str] = Field(None, description="失败阶段")
    error: HolodeckError = Field(..., description="错误详情")

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return self.model_dump()

    def to_json(self) -> str:
        """
        转换为 JSON 字符串
        """
        return self.model_dump_json(indent=2)


class SuccessResponse(BaseModel):
    """
    成功响应对象
    """

    ok: bool = Field(True, description="操作是否成功")
    session_id: str = Field(..., description="会话ID")
    workspace_path: str = Field(..., description="工作空间路径")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="产物文件")
    stages_completed: List[str] = Field(default_factory=list, description="完成的阶段")
    message: str = Field("操作成功", description="成功消息")

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return self.model_dump()

    def to_json(self) -> str:
        """
        转换为 JSON 字符串
        """
        return self.model_dump_json(indent=2)


class ErrorHandler:
    """
    错误处理器
    """

    @staticmethod
    def create_error_response(
        error_code: ErrorCode,
        session_id: Optional[str] = None,
        failed_stage: Optional[str] = None,
        message: Optional[str] = None,
        component: Optional[str] = None,
        additional_actions: Optional[List[str]] = None,
        additional_details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ) -> ErrorResponse:
        """
        创建错误响应
        """
        if original_exception:
            error = HolodeckError.from_exception(
                error_code=error_code,
                original_exception=original_exception,
                session_id=session_id,
                component=component,
                additional_details=additional_details
            )
        else:
            error = HolodeckError.from_error_code(
                error_code=error_code,
                message=message,
                session_id=session_id,
                component=component,
                additional_actions=additional_actions,
                additional_details=additional_details
            )

        return ErrorResponse(
            ok=False,
            session_id=session_id,
            failed_stage=failed_stage,
            error=error
        )

    @staticmethod
    def create_success_response(
        session_id: str,
        workspace_path: str,
        artifacts: Optional[Dict[str, str]] = None,
        stages_completed: Optional[List[str]] = None,
        message: str = "操作成功"
    ) -> SuccessResponse:
        """
        创建成功响应
        """
        return SuccessResponse(
            ok=True,
            session_id=session_id,
            workspace_path=workspace_path,
            artifacts=artifacts or {},
            stages_completed=stages_completed or [],
            message=message
        )

    @staticmethod
    def save_last_error(session_id: str, error_response: ErrorResponse) -> None:
        """
        保存最后的错误到 session 目录
        """
        try:
            session_dir = Path("workspace/sessions") / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            error_file = session_dir / "last_error.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_response.to_dict(), f, indent=2, ensure_ascii=False)

        except Exception as e:
            # 如果保存错误失败，至少打印到控制台
            print(f"警告: 无法保存错误信息到文件: {e}")

    @staticmethod
    def load_last_error(session_id: str) -> Optional[ErrorResponse]:
        """
        从 session 目录加载最后的错误
        """
        try:
            error_file = Path("workspace/sessions") / session_id / "last_error.json"
            if error_file.exists():
                with open(error_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ErrorResponse(**data)
        except Exception as e:
            print(f"警告: 无法加载错误信息: {e}")
        return None

    @staticmethod
    def format_human_readable(error_response: ErrorResponse) -> str:
        """
        格式化人类可读的错误信息
        """
        error = error_response.error
        lines = [
            f"❌ 错误: {error.message}",
            f"🔧 组件: {error.component}",
            f"🏷️  错误码: {error.code}"
        ]

        if error_response.failed_stage:
            lines.append(f"📋 失败阶段: {error_response.failed_stage}")

        if error.retryable:
            lines.append(f"🔄 可重试: 是")

        if error.suggested_actions:
            lines.append(f"💡 建议操作:")
            for i, action in enumerate(error.suggested_actions, 1):
                lines.append(f"   {i}. {action}")

        if error.logs:
            lines.append(f"📁 相关日志:")
            for log_name, log_path in error.logs.items():
                lines.append(f"   {log_name}: {log_path}")

        return "\n".join(lines)

    @staticmethod
    def format_short_error(error_response: ErrorResponse) -> str:
        """
        格式化简短错误信息
        """
        error = error_response.error
        return f"[{error.code}] {error.message}"