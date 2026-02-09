# Holodeck 错误码文档

## 📋 概述

本文档定义了 Holodeck 系统中所有可能的错误码及其含义。错误码采用统一的命名规范，便于机器处理和人类理解。

### 错误码命名规范

```
E_<COMPONENT>_<SPECIFIC_ERROR>
```

- `E_`: 错误码前缀
- `<COMPONENT>`: 组件名称（如 COMFYUI, SOLVER, ASSET 等）
- `<SPECIFIC_ERROR>`: 具体错误类型

### 错误响应格式

所有错误都遵循以下 JSON 格式：

```json
{
  "ok": false,
  "session_id": "session_id",
  "failed_stage": "stage_name",
  "error": {
    "code": "E_COMPONENT_ERROR",
    "component": "component.name",
    "message": "错误描述",
    "retryable": true,
    "suggested_actions": [
      "建议操作1",
      "建议操作2"
    ],
    "logs": {
      "run_log": "path/to/log",
      "trace": "path/to/trace"
    },
    "timestamp": "2026-01-22T17:43:23Z",
    "details": {
      "exception_type": "ExceptionClass",
      "exception_message": "异常消息",
      "traceback": "堆栈跟踪"
    }
  }
}
```

## 🔍 错误码分类

### 通用错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_UNKNOWN` | system | 未知错误 | 否 | 联系技术支持 |
| `E_INTERNAL_ERROR` | system | 内部系统错误 | 是 | 重试操作，联系技术支持 |
| `E_INVALID_INPUT` | input_validation | 输入参数无效 | 否 | 检查输入参数格式 |
| `E_CONFIG_ERROR` | system | 配置错误 | 否 | 检查配置文件 |

### ComfyUI 相关错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_COMFYUI_CONNECT` | image_generation.comfyui | 无法连接到 ComfyUI | 是 | 验证 ComfyUI 可用性，设置替代方案 |
| `E_COMFYUI_JOB_LOST` | image_generation.comfyui | ComfyUI 任务丢失 | 是 | 重新提交任务，检查日志 |
| `E_COMFYUI_TIMEOUT` | image_generation.comfyui | ComfyUI 请求超时 | 是 | 增加超时时间，检查网络 |
| `E_COMFYUI_INVALID_RESPONSE` | image_generation.comfyui | ComfyUI 响应无效 | 是 | 检查 ComfyUI 状态，重试 |

### 布局求解器错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_SOLVER_NO_SOLUTION` | scene_gen.layout_solver | 找不到解决方案 | 是 | 简化约束，减少对象数量 |
| `E_SOLVER_TIMEOUT` | scene_gen.layout_solver | 求解超时 | 是 | 增加时间限制，简化约束 |
| `E_SOLVER_CONSTRAINT_CONFLICT` | scene_gen.layout_solver | 约束冲突 | 否 | 检查约束条件 |
| `E_SOLVER_INVALID_INPUT` | scene_gen.layout_solver | 输入无效 | 否 | 验证输入数据 |

### 资产生成错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_ASSET_MISSING` | object_gen.asset_manager | 资产文件缺失 | 是 | 重新生成资产，检查缓存 |
| `E_ASSET_IMPORT_FAILED` | object_gen.asset_manager | 资产导入失败 | 是 | 检查文件格式，重新下载 |
| `E_ASSET_GENERATION_FAILED` | object_gen.asset_generator | 资产生成失败 | 是 | 重试生成，检查网络 |
| `E_ASSET_NORMALIZATION_FAILED` | object_gen.normalizer | 资产标准化失败 | 是 | 检查资产格式 |
| `E_ASSET_CACHE_ERROR` | object_gen.cache | 缓存错误 | 是 | 清理缓存，重试 |

### Blender MCP 错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_BLENDER_MCP_DISCONNECTED` | blender.mcp_client | Blender MCP 断开连接 | 是 | 检查服务器状态，重启 MCP |
| `E_BLENDER_MCP_TIMEOUT` | blender.mcp_client | Blender MCP 操作超时 | 是 | 增加超时时间，检查性能 |
| `E_BLENDER_MCP_EXECUTION_FAILED` | blender.mcp_client | Blender MCP 执行失败 | 是 | 检查 Blender 状态 |
| `E_BLENDER_SCENE_CORRUPTED` | blender.scene_manager | 场景损坏 | 否 | 重新创建场景 |

### 场景分析错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_SCENE_ANALYSIS_FAILED` | scene_analysis.analyzer | 场景分析失败 | 是 | 检查输入质量，提供清晰描述 |
| `E_OBJECT_EXTRACTION_FAILED` | scene_analysis.object_extractor | 对象提取失败 | 是 | 提供更清晰的图像 |
| `E_IMAGE_GENERATION_FAILED` | scene_analysis.image_generator | 图像生成失败 | 是 | 检查生成参数 |
| `E_BACKGROUND_EXTRACTION_FAILED` | scene_analysis.background_extractor | 背景提取失败 | 是 | 提供更好的背景图像 |

### 会话管理错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_SESSION_NOT_FOUND` | storage.session_manager | 会话不存在 | 否 | 验证会话 ID，创建新会话 |
| `E_SESSION_CORRUPTED` | storage.session_manager | 会话损坏 | 否 | 创建新会话 |
| `E_SESSION_STORAGE_ERROR` | storage.session_manager | 存储错误 | 是 | 检查存储空间 |

### 文件系统错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_FILE_NOT_FOUND` | storage.file_storage | 文件未找到 | 否 | 检查文件路径 |
| `E_FILE_PERMISSION_DENIED` | storage.file_storage | 权限被拒绝 | 否 | 检查文件权限 |
| `E_DISK_SPACE_INSUFFICENT` | storage.file_storage | 磁盘空间不足 | 否 | 清理磁盘空间 |

### 网络错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_NETWORK_TIMEOUT` | network.http_client | 网络请求超时 | 是 | 检查网络连接，增加超时 |
| `E_API_RATE_LIMIT` | network.api_client | API 频率限制 | 是 | 等待后重试 |
| `E_API_AUTH_FAILED` | network.api_client | API 认证失败 | 否 | 检查 API 密钥 |

### 3D 模型服务错误

| 错误码 | 组件 | 描述 | 可重试 | 建议操作 |
|--------|------|------|--------|----------|
| `E_HUNYUAN3D_API_ERROR` | object_gen.hunyuan3d_client | Hunyuan3D API 错误 | 是 | 检查 API 密钥，验证网络 |
| `E_HYPER3D_API_ERROR` | object_gen.hyper3d_client | Hyper3D API 错误 | 是 | 检查 API 密钥，验证网络 |
| `E_SKETCHFAB_API_ERROR` | object_gen.sketchfab_client | Sketchfab API 错误 | 是 | 检查 API 密钥，验证网络 |
| `E_POLYHAVEN_API_ERROR` | object_gen.polyhaven_client | PolyHaven API 错误 | 是 | 检查网络连接 |

## 🛠️ 错误处理最佳实践

### 1. 错误码选择

```python
# 正确：使用具体的错误码
ErrorHandler.create_error_response(
    error_code=ErrorCode.E_COMFYUI_CONNECT,
    session_id=session_id,
    failed_stage="assets"
)

# 避免：使用通用错误码
ErrorHandler.create_error_response(
    error_code=ErrorCode.E_UNKNOWN,  # 不推荐
    session_id=session_id
)
```

### 2. 错误信息提供

```python
# 提供详细的错误信息
ErrorHandler.create_error_response(
    error_code=ErrorCode.E_SOLVER_NO_SOLUTION,
    session_id=session_id,
    failed_stage="layout",
    message="布局求解器找不到解决方案，可能是房间太小或对象太多",
    additional_details={
        "room_size": [6, 4, 3],
        "object_count": 15,
        "constraint_count": 8
    }
)
```

### 3. 建议操作

```python
# 提供具体的建议操作
ErrorHandler.create_error_response(
    error_code=ErrorCode.E_COMFYUI_CONNECT,
    session_id=session_id,
    additional_actions=[
        "运行 `holodeck debug validate` 验证 ComfyUI",
        "设置 asset_gen_provider=cloud_hunyuan3d",
        "使用 `--force --only assets` 重新生成"
    ]
)
```

## 📊 错误监控和统计

### 错误收集

```python
# 在 session 目录保存错误
ErrorHandler.save_last_error(session_id, error_response)

# 加载历史错误
last_error = ErrorHandler.load_last_error(session_id)
```

### 错误统计

```python
# 统计错误频率
error_stats = {
    "E_COMFYUI_CONNECT": 15,
    "E_SOLVER_NO_SOLUTION": 8,
    "E_ASSET_MISSING": 3
}
```

## 🔧 调试工具

### 1. 验证配置
```bash
holodeck debug validate
```

### 2. 查看错误详情
```bash
holodeck debug show-error --session <session_id>
```

### 3. 错误码查询
```bash
holodeck debug error-code E_COMFYUI_CONNECT
```

## 📈 错误处理流程

### 1. 错误检测
```python
try:
    # 业务逻辑
    result = some_operation()
except SpecificException as e:
    # 捕获特定异常
    error_response = ErrorHandler.create_error_response(
        error_code=ErrorCode.SPECIFIC_ERROR,
        original_exception=e
    )
```

### 2. 错误分类
```python
# 根据异常类型选择错误码
if isinstance(e, ConnectionError):
    error_code = ErrorCode.E_NETWORK_TIMEOUT
elif isinstance(e, FileNotFoundError):
    error_code = ErrorCode.E_FILE_NOT_FOUND
else:
    error_code = ErrorCode.E_INTERNAL_ERROR
```

### 3. 错误响应
```python
# 返回结构化的错误响应
return error_response.to_dict()  # JSON 模式
# 或
print(ErrorHandler.format_human_readable(error_response))  # 人类模式
```

### 4. 错误持久化
```python
# 保存错误到 session
if session_id:
    ErrorHandler.save_last_error(session_id, error_response)
```

## 🚀 集成示例

### CLI 集成
```python
from holodeck_cli.error_handler import CLIErrorHandler

# 创建错误处理器
handler = CLIErrorHandler(json_mode=args.json)

# 处理命令结果
if isinstance(result, ErrorResponse):
    handler._output_error(result)
    sys.exit(1)
```

### API 集成
```python
from fastapi import HTTPException

# 转换 HolodeckError 为 HTTP 响应
if isinstance(error, HolodeckError):
    raise HTTPException(
        status_code=500,
        detail=error.to_dict()
    )
```

### 日志集成
```python
import logging

logger = logging.getLogger(__name__)

# 记录错误
logger.error(
    f"Error {error.code}: {error.message}",
    extra={
        "error_code": error.code,
        "component": error.component,
        "session_id": session_id
    }
)
```

## 📝 更新日志

### v1.0 (2026-01-22)
- 初始版本发布
- 定义了 30+ 个错误码
- 实现了统一的错误处理类
- 集成了 CLI 错误捕获器

---

**最后更新**: 2026年1月22日
**版本**: 1.0
**适用版本**: Holodeck CLI v1.0+