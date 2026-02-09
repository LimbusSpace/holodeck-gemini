"""
Holodeck 错误码枚举系统

定义所有可能的错误码和对应的错误信息
"""

from enum import Enum
from typing import Dict, List, Optional


class ErrorCode(str, Enum):
    """
    Holodeck 错误码枚举

    命名规范: E_<COMPONENT>_<SPECIFIC_ERROR>
    例如: E_COMFYUI_CONNECT, E_SOLVER_NO_SOLUTION
    """

    # 通用错误
    E_UNKNOWN = "E_UNKNOWN"
    E_INTERNAL_ERROR = "E_INTERNAL_ERROR"
    E_INVALID_INPUT = "E_INVALID_INPUT"
    E_CONFIG_ERROR = "E_CONFIG_ERROR"

    # ComfyUI 相关错误
    E_COMFYUI_CONNECT = "E_COMFYUI_CONNECT"
    E_COMFYUI_JOB_LOST = "E_COMFYUI_JOB_LOST"
    E_COMFYUI_TIMEOUT = "E_COMFYUI_TIMEOUT"
    E_COMFYUI_INVALID_RESPONSE = "E_COMFYUI_INVALID_RESPONSE"

    # 布局求解器错误
    E_SOLVER_NO_SOLUTION = "E_SOLVER_NO_SOLUTION"
    E_SOLVER_TIMEOUT = "E_SOLVER_TIMEOUT"
    E_SOLVER_CONSTRAINT_CONFLICT = "E_SOLVER_CONSTRAINT_CONFLICT"
    E_SOLVER_INVALID_INPUT = "E_SOLVER_INVALID_INPUT"

    # 资产生成错误
    E_ASSET_MISSING = "E_ASSET_MISSING"
    E_ASSET_IMPORT_FAILED = "E_ASSET_IMPORT_FAILED"
    E_ASSET_GENERATION_FAILED = "E_ASSET_GENERATION_FAILED"
    E_ASSET_NORMALIZATION_FAILED = "E_ASSET_NORMALIZATION_FAILED"
    E_ASSET_CACHE_ERROR = "E_ASSET_CACHE_ERROR"

    # Blender MCP 错误
    E_BLENDER_MCP_DISCONNECTED = "E_BLENDER_MCP_DISCONNECTED"
    E_BLENDER_MCP_TIMEOUT = "E_BLENDER_MCP_TIMEOUT"
    E_BLENDER_MCP_EXECUTION_FAILED = "E_BLENDER_MCP_EXECUTION_FAILED"
    E_BLENDER_SCENE_CORRUPTED = "E_BLENDER_SCENE_CORRUPTED"

    # 场景分析错误
    E_SCENE_ANALYSIS_FAILED = "E_SCENE_ANALYSIS_FAILED"
    E_OBJECT_EXTRACTION_FAILED = "E_OBJECT_EXTRACTION_FAILED"
    E_IMAGE_GENERATION_FAILED = "E_IMAGE_GENERATION_FAILED"
    E_BACKGROUND_EXTRACTION_FAILED = "E_BACKGROUND_EXTRACTION_FAILED"

    # 会话管理错误
    E_SESSION_NOT_FOUND = "E_SESSION_NOT_FOUND"
    E_SESSION_CORRUPTED = "E_SESSION_CORRUPTED"
    E_SESSION_STORAGE_ERROR = "E_SESSION_STORAGE_ERROR"

    # 文件系统错误
    E_FILE_NOT_FOUND = "E_FILE_NOT_FOUND"
    E_FILE_PERMISSION_DENIED = "E_FILE_PERMISSION_DENIED"
    E_DISK_SPACE_INSUFFICIENT = "E_DISK_SPACE_INSUFFICENT"

    # 网络错误
    E_NETWORK_TIMEOUT = "E_NETWORK_TIMEOUT"
    E_API_RATE_LIMIT = "E_API_RATE_LIMIT"
    E_API_AUTH_FAILED = "E_API_AUTH_FAILED"

    # 3D 模型服务错误
    E_HUNYUAN3D_API_ERROR = "E_HUNYUAN3D_API_ERROR"
    E_HYPER3D_API_ERROR = "E_HYPER3D_API_ERROR"
    E_SKETCHFAB_API_ERROR = "E_SKETCHFAB_API_ERROR"
    E_POLYHAVEN_API_ERROR = "E_POLYHAVEN_API_ERROR"


class ErrorInfo:
    """
    错误信息定义
    """

    def __init__(
        self,
        code: ErrorCode,
        component: str,
        message: str,
        retryable: bool = False,
        suggested_actions: Optional[List[str]] = None,
        http_status: int = 500
    ):
        self.code = code
        self.component = component
        self.message = message
        self.retryable = retryable
        self.suggested_actions = suggested_actions or []
        self.http_status = http_status


# 错误码到错误信息的映射
ERROR_DEFINITIONS: Dict[ErrorCode, ErrorInfo] = {
    # 通用错误
    ErrorCode.E_UNKNOWN: ErrorInfo(
        code=ErrorCode.E_UNKNOWN,
        component="system",
        message="未知错误",
        retryable=False,
        suggested_actions=["联系技术支持"]
    ),

    ErrorCode.E_INTERNAL_ERROR: ErrorInfo(
        code=ErrorCode.E_INTERNAL_ERROR,
        component="system",
        message="内部系统错误",
        retryable=True,
        suggested_actions=["重试操作", "如果问题持续，联系技术支持"]
    ),

    ErrorCode.E_INVALID_INPUT: ErrorInfo(
        code=ErrorCode.E_INVALID_INPUT,
        component="input_validation",
        message="输入参数无效",
        retryable=False,
        suggested_actions=["检查输入参数格式", "参考文档中的参数说明"]
    ),

    # ComfyUI 相关错误
    ErrorCode.E_COMFYUI_CONNECT: ErrorInfo(
        code=ErrorCode.E_COMFYUI_CONNECT,
        component="image_generation.comfyui",
        message="无法连接到 ComfyUI",
        retryable=True,
        suggested_actions=[
            "运行 `holodeck debug validate` 验证 ComfyUI 可用性",
            "如果 ComfyUI 不可用，设置 asset_gen_provider=cloud_hunyuan3d",
            "或者在 ComfyUI 启动后使用 `--force --only assets` 重新运行"
        ]
    ),

    ErrorCode.E_COMFYUI_JOB_LOST: ErrorInfo(
        code=ErrorCode.E_COMFYUI_JOB_LOST,
        component="image_generation.comfyui",
        message="ComfyUI 任务丢失",
        retryable=True,
        suggested_actions=[
            "重新提交任务",
            "检查 ComfyUI 日志",
            "如果问题持续，尝试重启 ComfyUI"
        ]
    ),

    ErrorCode.E_COMFYUI_TIMEOUT: ErrorInfo(
        code=ErrorCode.E_COMFYUI_TIMEOUT,
        component="image_generation.comfyui",
        message="ComfyUI 请求超时",
        retryable=True,
        suggested_actions=[
            "增加超时时间",
            "检查网络连接",
            "验证 ComfyUI 负载情况"
        ]
    ),

    # 布局求解器错误
    ErrorCode.E_SOLVER_NO_SOLUTION: ErrorInfo(
        code=ErrorCode.E_SOLVER_NO_SOLUTION,
        component="scene_gen.layout_solver",
        message="布局求解器找不到解决方案",
        retryable=True,
        suggested_actions=[
            "简化场景约束",
            "减少对象数量",
            "调整房间尺寸",
            "运行 `holodeck debug show-constraints` 查看约束详情"
        ]
    ),

    ErrorCode.E_SOLVER_TIMEOUT: ErrorInfo(
        code=ErrorCode.E_SOLVER_TIMEOUT,
        component="scene_gen.layout_solver",
        message="布局求解超时",
        retryable=True,
        suggested_actions=[
            "增加求解时间限制",
            "简化约束条件",
            "使用 `--until constraints` 提前生成约束"
        ]
    ),

    # 资产生成错误
    ErrorCode.E_ASSET_MISSING: ErrorInfo(
        code=ErrorCode.E_ASSET_MISSING,
        component="object_gen.asset_manager",
        message="资产文件缺失",
        retryable=True,
        suggested_actions=[
            "重新生成资产",
            "检查资产缓存",
            "使用 `--force --only assets` 重新生成"
        ]
    ),

    ErrorCode.E_ASSET_IMPORT_FAILED: ErrorInfo(
        code=ErrorCode.E_ASSET_IMPORT_FAILED,
        component="object_gen.asset_manager",
        message="资产导入失败",
        retryable=True,
        suggested_actions=[
            "检查资产文件格式",
            "验证文件完整性",
            "尝试重新下载资产"
        ]
    ),

    # Blender MCP 错误
    ErrorCode.E_BLENDER_MCP_DISCONNECTED: ErrorInfo(
        code=ErrorCode.E_BLENDER_MCP_DISCONNECTED,
        component="blender.mcp_client",
        message="Blender MCP 连接断开",
        retryable=True,
        suggested_actions=[
            "检查 Blender MCP 服务器状态",
            "重启 Blender MCP",
            "验证网络连接"
        ]
    ),

    ErrorCode.E_BLENDER_MCP_TIMEOUT: ErrorInfo(
        code=ErrorCode.E_BLENDER_MCP_TIMEOUT,
        component="blender.mcp_client",
        message="Blender MCP 操作超时",
        retryable=True,
        suggested_actions=[
            "增加超时时间",
            "检查 Blender 性能",
            "简化场景复杂度"
        ]
    ),

    # 场景分析错误
    ErrorCode.E_SCENE_ANALYSIS_FAILED: ErrorInfo(
        code=ErrorCode.E_SCENE_ANALYSIS_FAILED,
        component="scene_analysis.analyzer",
        message="场景分析失败",
        retryable=True,
        suggested_actions=[
            "检查输入图像质量",
            "提供更清晰的场景描述",
            "尝试不同的分析参数"
        ]
    ),

    # 会话管理错误
    ErrorCode.E_SESSION_NOT_FOUND: ErrorInfo(
        code=ErrorCode.E_SESSION_NOT_FOUND,
        component="storage.session_manager",
        message="会话不存在",
        retryable=False,
        suggested_actions=[
            "验证会话 ID",
            "列出可用会话: `holodeck session list`",
            "创建新会话"
        ]
    ),

    # 文件系统错误
    ErrorCode.E_FILE_NOT_FOUND: ErrorInfo(
        code=ErrorCode.E_FILE_NOT_FOUND,
        component="storage.file_storage",
        message="文件未找到",
        retryable=False,
        suggested_actions=[
            "检查文件路径",
            "验证文件权限",
            "重新生成文件"
        ]
    ),

    # 网络错误
    ErrorCode.E_NETWORK_TIMEOUT: ErrorInfo(
        code=ErrorCode.E_NETWORK_TIMEOUT,
        component="network.http_client",
        message="网络请求超时",
        retryable=True,
        suggested_actions=[
            "检查网络连接",
            "增加超时时间",
            "重试操作"
        ]
    ),

    # 3D 模型服务错误
    ErrorCode.E_HUNYUAN3D_API_ERROR: ErrorInfo(
        code=ErrorCode.E_HUNYUAN3D_API_ERROR,
        component="object_gen.hunyuan3d_client",
        message="Hunyuan3D API 错误",
        retryable=True,
        suggested_actions=[
            "检查 API 密钥",
            "验证网络连接",
            "稍后重试"
        ]
    ),
}


def get_error_info(error_code: ErrorCode) -> ErrorInfo:
    """
    根据错误码获取错误信息
    """
    return ERROR_DEFINITIONS.get(error_code, ERROR_DEFINITIONS[ErrorCode.E_UNKNOWN])


def get_error_info_by_code(code_str: str) -> ErrorInfo:
    """
    根据错误码字符串获取错误信息
    """
    try:
        error_code = ErrorCode(code_str)
        return get_error_info(error_code)
    except ValueError:
        return ERROR_DEFINITIONS[ErrorCode.E_UNKNOWN]