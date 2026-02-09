"""
错误处理系统演示

展示如何使用统一的 Error Contract 系统
"""

import json
from pathlib import Path

from holodeck_core.schemas.error_codes import ErrorCode
from holodeck_core.schemas.holodeck_error import ErrorHandler, ErrorResponse, SuccessResponse


def demo_error_creation():
    """演示错误创建"""
    print("=== 错误创建演示 ===\n")

    # 1. 从错误码创建错误
    print("1. 从错误码创建错误:")
    error_response = ErrorHandler.create_error_response(
        error_code=ErrorCode.E_COMFYUI_CONNECT,
        session_id="demo_session_001",
        failed_stage="assets",
        message="无法连接到 ComfyUI 服务器"
    )

    print("JSON 格式:")
    print(error_response.to_json())
    print("\n人类可读格式:")
    print(ErrorHandler.format_human_readable(error_response))
    print("\n简短格式:")
    print(ErrorHandler.format_short_error(error_response))

    # 2. 从异常创建错误
    print("\n2. 从异常创建错误:")
    try:
        # 模拟一个异常
        raise ConnectionError("Connection refused")
    except Exception as e:
        error_response = ErrorHandler.create_error_response(
            error_code=ErrorCode.E_NETWORK_TIMEOUT,
            session_id="demo_session_002",
            failed_stage="scene_analysis",
            original_exception=e
        )

        print("JSON 格式:")
        print(json.dumps(error_response.to_dict(), indent=2, ensure_ascii=False))


def demo_success_response():
    """演示成功响应"""
    print("\n=== 成功响应演示 ===\n")

    success_response = ErrorHandler.create_success_response(
        session_id="demo_session_003",
        workspace_path="workspace/sessions/demo_session_003",
        artifacts={
            "layout_solution": "layout_solution_v1.json",
            "asset_manifest": "asset_manifest.json",
            "blender_object_map": "blender_object_map.json"
        },
        stages_completed=["scene_ref", "objects", "constraints", "layout"],
        message="场景生成成功完成"
    )

    print("JSON 格式:")
    print(success_response.to_json())


def demo_error_persistence():
    """演示错误持久化"""
    print("\n=== 错误持久化演示 ===\n")

    session_id = "demo_session_004"

    # 创建错误响应
    error_response = ErrorHandler.create_error_response(
        error_code=ErrorCode.E_SOLVER_NO_SOLUTION,
        session_id=session_id,
        failed_stage="layout",
        message="布局求解器找不到解决方案，可能是约束过于严格"
    )

    # 保存错误
    print(f"保存错误到 session {session_id}...")
    ErrorHandler.save_last_error(session_id, error_response)

    # 加载错误
    print("从 session 加载错误...")
    loaded_error = ErrorHandler.load_last_error(session_id)

    if loaded_error:
        print("成功加载错误:")
        print(ErrorHandler.format_human_readable(loaded_error))
    else:
        print("无法加载错误")


def demo_error_codes():
    """演示错误码系统"""
    print("\n=== 错误码系统演示 ===\n")

    # 显示一些常见的错误码
    common_errors = [
        ErrorCode.E_COMFYUI_CONNECT,
        ErrorCode.E_SOLVER_NO_SOLUTION,
        ErrorCode.E_ASSET_MISSING,
        ErrorCode.E_BLENDER_MCP_DISCONNECTED
    ]

    for error_code in common_errors:
        error_info = ErrorHandler.get_error_info(error_code)
        print(f"错误码: {error_code.value}")
        print(f"  组件: {error_info.component}")
        print(f"  消息: {error_info.message}")
        print(f"  可重试: {error_info.retryable}")
        print(f"  建议操作: {len(error_info.suggested_actions)} 个")
        print()


def demo_cli_integration():
    """演示 CLI 集成"""
    print("\n=== CLI 集成演示 ===\n")

    # 模拟 CLI 中的错误处理
    from holodeck_cli.error_handler import CLIErrorHandler

    # JSON 模式
    print("JSON 模式错误输出:")
    json_handler = CLIErrorHandler(json_mode=True)
    error_response = ErrorHandler.create_error_response(
        error_code=ErrorCode.E_FILE_NOT_FOUND,
        session_id="cli_demo_001",
        message="必需的配置文件不存在"
    )
    print("JSON 输出:")
    json_handler._output_error(error_response)

    print("\n" + "="*50 + "\n")

    # 人类模式
    print("人类模式错误输出:")
    human_handler = CLIErrorHandler(json_mode=False)
    print("人类可读输出:")
    human_handler._output_error(error_response)


def main():
    """主演示函数"""
    print("Holodeck 统一错误处理系统演示")
    print("=" * 60)

    demo_error_creation()
    demo_success_response()
    demo_error_persistence()
    demo_error_codes()
    demo_cli_integration()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("\n关键特性:")
    print("✅ 标准化的错误码系统")
    print("✅ 结构化的错误响应格式")
    print("✅ 人类可读和机器可处理的错误输出")
    print("✅ 错误持久化到 session 目录")
    print("✅ CLI 集成的错误处理中间件")
    print("✅ 详细的错误信息和修复建议")


if __name__ == "__main__":
    main()