"""
CLI 错误捕获器和处理中间件

统一捕获和处理 CLI 中的错误，提供一致的错误响应格式
"""

import argparse
import json
import sys
import traceback
from functools import wraps
from typing import Any, Callable, Dict, Optional

from holodeck_core.schemas.error_codes import ErrorCode
from holodeck_core.schemas.holodeck_error import ErrorHandler, ErrorResponse, SuccessResponse
from holodeck_core.exceptions.framework import (
    HolodeckError, ConfigurationError, ValidationError,
    APIError, ImageGenerationError, ThreeDGenerationError, LLMError
)


class CLIErrorHandler:
    """
    CLI 错误处理器
    """

    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode

    def handle_exception(
        self,
        func: Callable,
        *args,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        处理函数异常的装饰器
        """
        try:
            return func(*args, **kwargs)
        except SystemExit:
            # 允许 SystemExit 正常传播
            raise
        except KeyboardInterrupt:
            # 用户中断
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INTERNAL_ERROR,
                session_id=session_id,
                message="操作被用户中断",
                additional_actions=["重新运行命令"]
            )
            self._output_error(error_response)
            sys.exit(130)  # 标准中断退出码

        except argparse.ArgumentError as e:
            # 参数错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INVALID_INPUT,
                session_id=session_id,
                message=f"参数错误: {str(e)}",
                additional_actions=["使用 --help 查看参数说明"]
            )
            self._output_error(error_response)
            sys.exit(2)

        except FileNotFoundError as e:
            # 文件未找到
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_FILE_NOT_FOUND,
                session_id=session_id,
                message=f"文件未找到: {str(e)}",
                original_exception=e
            )
            self._output_error(error_response)
            sys.exit(2)

        except PermissionError as e:
            # 权限错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_FILE_PERMISSION_DENIED,
                session_id=session_id,
                message=f"权限被拒绝: {str(e)}",
                original_exception=e,
                additional_actions=["检查文件权限", "使用管理员权限运行"]
            )
            self._output_error(error_response)
            sys.exit(13)

        except ConnectionError as e:
            # 连接错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_NETWORK_TIMEOUT,
                session_id=session_id,
                message=f"连接错误: {str(e)}",
                original_exception=e,
                additional_actions=["检查网络连接", "验证服务端状态"]
            )
            self._output_error(error_response)
            sys.exit(7)

        except TimeoutError as e:
            # 超时错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_NETWORK_TIMEOUT,
                session_id=session_id,
                message=f"操作超时: {str(e)}",
                original_exception=e,
                additional_actions=["增加超时时间", "重试操作"]
            )
            self._output_error(error_response)
            sys.exit(124)

        except json.JSONDecodeError as e:
            # JSON 解析错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INVALID_INPUT,
                session_id=session_id,
                message=f"JSON 解析错误: {str(e)}",
                original_exception=e,
                additional_actions=["检查输入格式", "确保输入为有效 JSON"]
            )
            self._output_error(error_response)
            sys.exit(3)

        # 新的异常框架处理
        except ConfigurationError as e:
            # 配置错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_CONFIG_ERROR,
                session_id=session_id,
                message=f"配置错误: {e.message}",
                original_exception=e,
                additional_actions=e.recovery_suggestion or ["检查配置文件", "验证环境变量"]
            )
            self._output_error(error_response)
            sys.exit(6)  # 配置错误退出码

        except ValidationError as e:
            # 验证错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INVALID_INPUT,
                session_id=session_id,
                message=f"输入验证失败: {e.message}",
                original_exception=e,
                additional_actions=["检查输入参数", "确保参数格式正确"]
            )
            self._output_error(error_response)
            sys.exit(2)  # 参数错误退出码

        except APIError as e:
            # API 错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_NETWORK_TIMEOUT,
                session_id=session_id,
                message=f"API 错误: {e.message}",
                original_exception=e,
                additional_actions=["检查网络连接", "验证API密钥", "稍后重试"]
            )
            self._output_error(error_response)
            sys.exit(7)  # 网络错误退出码

        except ImageGenerationError as e:
            # 图像生成错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_RENDERING_ERROR,
                session_id=session_id,
                message=f"图像生成错误: {e.message}",
                original_exception=e,
                additional_actions=["检查图像参数", "重试生成", "尝试不同的后端"]
            )
            self._output_error(error_response)
            sys.exit(8)  # 渲染错误退出码

        except ThreeDGenerationError as e:
            # 3D 生成错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_ASSET_GENERATION_ERROR,
                session_id=session_id,
                message=f"3D 生成错误: {e.message}",
                original_exception=e,
                additional_actions=["检查3D参数", "重试生成", "尝试不同的后端"]
            )
            self._output_error(error_response)
            sys.exit(9)  # 资产生成错误退出码

        except LLMError as e:
            # LLM 错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_LLM_ERROR,
                session_id=session_id,
                message=f"LLM 错误: {e.message}",
                original_exception=e,
                additional_actions=["检查LLM配置", "验证API密钥", "重试操作"]
            )
            self._output_error(error_response)
            sys.exit(10)  # LLM错误退出码

        except HolodeckError as e:
            # 其他 Holodeck 错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INTERNAL_ERROR,
                session_id=session_id,
                message=f"Holodeck 错误: {e.message}",
                original_exception=e,
                additional_actions=e.recovery_suggestion or ["重试操作", "联系技术支持"]
            )
            self._output_error(error_response)
            sys.exit(1)

        except Exception as e:
            # 未知错误
            error_response = ErrorHandler.create_error_response(
                error_code=ErrorCode.E_INTERNAL_ERROR,
                session_id=session_id,
                message=f"内部错误: {str(e)}",
                original_exception=e,
                additional_actions=["重试操作", "联系技术支持"]
            )
            self._output_error(error_response)
            sys.exit(1)

    def _output_error(self, error_response: ErrorResponse) -> None:
        """
        输出错误信息
        """
        if self.json_mode:
            # JSON 模式：输出结构化错误
            print(error_response.to_json())
        else:
            # 人类模式：输出友好错误信息
            print(ErrorHandler.format_human_readable(error_response), file=sys.stderr)

        # 保存错误到 session
        if error_response.session_id:
            ErrorHandler.save_last_error(error_response.session_id, error_response)

    def output_success(self, success_response: SuccessResponse) -> None:
        """
        输出成功信息
        """
        if self.json_mode:
            print(success_response.to_json())
        else:
            print(success_response.message)
            if success_response.artifacts:
                print("\n生成文件:")
                for name, path in success_response.artifacts.items():
                    print(f"  - {name}: {path}")
            if success_response.stages_completed:
                print(f"\n完成阶段: {', '.join(success_response.stages_completed)}")


def cli_error_handler(json_mode: bool = False):
    """
    CLI 错误处理装饰器
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = CLIErrorHandler(json_mode=json_mode)

            # 尝试从参数中提取 session_id
            session_id = None
            for arg in args:
                if hasattr(arg, 'session_id') and arg.session_id:
                    session_id = arg.session_id
                    break
                if hasattr(arg, 'session') and arg.session:
                    session_id = arg.session
                    break

            return handler.handle_exception(func, *args, session_id=session_id, **kwargs)
        return wrapper
    return decorator


class CLIErrorMiddleware:
    """
    CLI 错误处理中间件
    """

    def __init__(self, json_mode: bool = False):
        self.json_mode = json_mode
        self.error_handler = CLIErrorHandler(json_mode)

    def wrap_command(self, func: Callable) -> Callable:
        """
        包装命令函数
        """
        @wraps(func)
        def wrapped(*args, **kwargs):
            return self.error_handler.handle_exception(func, *args, **kwargs)
        return wrapped

    def handle_command_result(self, result: Any) -> None:
        """
        处理命令结果
        """
        # 使用鸭子类型检查来识别响应对象
        if hasattr(result, 'ok') and hasattr(result, 'to_json'):
            # 这是一个响应对象（SuccessResponse或ErrorResponse）
            if result.ok:
                self.error_handler.output_success(result)
            else:
                self.error_handler._output_error(result)
                sys.exit(1)
        elif isinstance(result, int):
            # 整数返回值是退出码
            if result != 0:
                sys.exit(result)
        elif result is None:
            # 默认成功
            pass
        else:
            # 其他返回值，不应该在JSON模式下出现
            if self.json_mode:
                # JSON模式下不输出任何额外内容，避免污染JSON输出
                pass
            else:
                print(str(result))


# 预定义的错误处理装饰器
json_error_handler = cli_error_handler(json_mode=True)
human_error_handler = cli_error_handler(json_mode=False)