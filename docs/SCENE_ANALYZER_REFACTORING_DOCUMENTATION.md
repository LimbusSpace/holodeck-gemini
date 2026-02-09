# SceneAnalyzer Refactoring Documentation

## Overview

This document describes the comprehensive refactoring of the `SceneAnalyzer` class to support multi-backend image generation with strict error handling and improved architecture consistency.

## Problem Statement

The original `SceneAnalyzer` implementation had several critical issues:

1. **Architecture Inconsistency**: `SceneAnalyzer` hardcoded ComfyUI usage while `HybridClient` already implemented multi-backend priority support
2. **Poor Error Handling**: Image generation failures created placeholder images instead of interrupting the pipeline
3. **Limited Backend Support**: No way to leverage Hunyuan Image or OpenAI backends from SceneAnalyzer
4. **Debugging Difficulties**: Silent failures made it hard to identify and resolve issues

## Solution Overview

The refactoring implements a comprehensive solution with the following key features:

### 1. Multi-Backend Priority System

**Priority Order**: Hunyuan Image > OpenAI > ComfyUI

- **Hunyuan Image**: Primary backend for high-quality image generation
- **OpenAI**: Secondary fallback for reliable generation
- **ComfyUI**: Tertiary fallback for local/stable generation

**Implementation**: Uses existing `HybridClient` infrastructure instead of direct ComfyUI calls

### 2. Strict Error Handling

**Modes of Operation**:

- **Strict Mode** (default): Pipeline fails when error rate exceeds threshold
- **Lenient Mode**: Continues processing despite failures (with warnings)

**Failure Rate Control**:
- Configurable threshold (default: 30%)
- Real-time monitoring during generation
- Immediate failure when threshold exceeded in strict mode

### 3. Test Mode vs Production Mode

**Production Mode** (default):
- Placeholder images are NOT created
- Failures interrupt pipeline with detailed error messages
- Provides actionable troubleshooting guidance

**Test Mode**:
- Placeholder images created for development/testing
- Allows pipeline completion for debugging
- Useful for UI development and testing workflows

## Code Changes

### Method Signatures

#### `generate_object_cards()`
```python
def generate_object_cards(
    self,
    session,
    strict_mode: bool = True,
    max_failure_rate: float = 0.3,
    test_mode: bool = False
) -> dict:
```

**Parameters**:
- `session`: Session object (unchanged)
- `strict_mode`: Enable/disable strict error handling (default: True)
- `max_failure_rate`: Maximum acceptable failure rate (default: 0.3 = 30%)
- `test_mode`: Enable placeholder creation for testing (default: False)

#### `_generate_object_cards_fallback()`
```python
def _generate_object_cards_fallback(
    self,
    objects,
    objects_data,
    object_cards_dir,
    scene_ref_path,
    test_mode: bool = False
):
```

#### `_create_placeholder_image()`
```python
def _create_placeholder_image(
    self,
    output_path: Path,
    object_name: str,
    test_mode: bool = False
):
```

### Key Implementation Details

#### 1. HybridClient Integration

```python
# Priority: Use HybridClient if available
if self.hybrid_client and hasattr(self.hybrid_client, 'generate_object_cards'):
    # Uses Hunyuan Image > OpenAI > ComfyUI priority
    successful_cards, failed_objects = self.hybrid_client.generate_object_cards(...)
else:
    # Fallback to native implementation
    successful_cards, failed_objects = self._generate_object_cards_fallback(...)
```

#### 2. Enhanced Error Handling

```python
# Production mode: Raise detailed exceptions
if not test_mode:
    raise RuntimeError(
        f"图像生成失败: 无法为对象 '{object_name}' 生成图像。\n"
        f"建议操作:\n"
        f"1. 检查网络连接和API密钥配置\n"
        f"2. 验证对象描述是否合适\n"
        f"3. 尝试使用不同的对象名称或描述\n"
        f"4. 如果是测试环境，请设置test_mode=True"
    )
```

#### 3. Failure Rate Monitoring

```python
# Real-time failure rate calculation
failure_rate = len(failed_objects) / total_objects if total_objects > 0 else 0

# Strict mode enforcement
if strict_mode and failure_rate > max_failure_rate:
    raise Exception(
        f"对象卡片生成失败率 ({failure_rate:.1%}) 超过阈值 ({max_failure_rate:.1%})。\n"
        f"失败对象: {', '.join(failed_objects)}\n"
        f"建议操作:\n"
        f"1. 检查网络连接和API服务状态\n"
        f"2. 减少并发数量或增加超时时间\n"
        f"3. 验证对象描述的质量和适当性\n"
        f"4. 考虑使用test_mode=True进行调试"
    )
```

## Usage Examples

### Production Usage

```python
# Standard production usage (strict mode, no placeholders)
result = scene_analyzer.generate_object_cards(session)

# Custom failure threshold
result = scene_analyzer.generate_object_cards(
    session,
    strict_mode=True,
    max_failure_rate=0.2  # 20% max failure rate
)
```

### Development/Testing Usage

```python
# Test mode with placeholders for debugging
result = scene_analyzer.generate_object_cards(
    session,
    strict_mode=False,
    test_mode=True  # Allows placeholder creation
)

# Lenient mode for batch processing
result = scene_analyzer.generate_object_cards(
    session,
    strict_mode=False,  # Continue despite failures
    max_failure_rate=0.5  # 50% tolerance
)
```

## Error Handling Scenarios

### Scenario 1: Network/API Failure

**Production Mode**:
```
RuntimeError: 图像生成失败: 无法为对象 'test_object' 生成图像。
建议操作:
1. 检查网络连接和API密钥配置
2. 验证对象描述是否合适
3. 尝试使用不同的对象名称或描述
4. 如果是测试环境，请设置test_mode=True
```

**Test Mode**: Creates placeholder image and continues

### Scenario 2: High Failure Rate

**Strict Mode**:
```
Exception: 对象卡片生成失败率 (40.0%) 超过阈值 (30.0%)。
失败对象: obj_001, obj_002, obj_003, obj_004
建议操作:
1. 检查网络连接和API服务状态
2. 减少并发数量或增加超时时间
3. 验证对象描述的质量和适当性
4. 考虑使用test_mode=True进行调试
```

**Lenient Mode**: Continues processing with warning logs

## Benefits

### 1. Improved Reliability
- Failures are detected and reported immediately
- No silent degradation with placeholder images
- Clear error messages with actionable solutions

### 2. Better Architecture
- Consistent backend usage across the codebase
- Leverages existing HybridClient infrastructure
- Eliminates code duplication

### 3. Enhanced Debugging
- Detailed error messages with troubleshooting guidance
- Configurable failure thresholds
- Test mode for development workflows

### 4. Production Safety
- Prevents silent failures in production
- Configurable error tolerance
- Proper error propagation

## Backward Compatibility

The refactoring maintains full backward compatibility:

- Existing method calls work without modification
- Default parameters preserve original behavior
- Deprecated methods provide migration warnings
- No breaking changes to public interfaces

## Testing

The refactoring includes comprehensive testing:

### Unit Tests
- Method signature validation
- Placeholder creation behavior
- Error handling scenarios
- Parameter validation

### Integration Tests
- Multi-backend priority switching
- Failure rate monitoring
- Error propagation
- Backward compatibility

## Migration Guide

### For Existing Code

No changes required for basic usage:
```python
# This continues to work unchanged
result = scene_analyzer.generate_object_cards(session)
```

### For Enhanced Error Handling

Enable strict mode and custom thresholds:
```python
# Add error handling and monitoring
result = scene_analyzer.generate_object_cards(
    session,
    strict_mode=True,
    max_failure_rate=0.2
)
```

### For Development/Testing

Enable test mode for debugging:
```python
# Allow placeholders for testing
result = scene_analyzer.generate_object_cards(
    session,
    test_mode=True,
    strict_mode=False
)
```

## Future Enhancements

Potential areas for future improvement:

1. **Dynamic Backend Weights**: Adaptive priority based on success rates
2. **Circuit Breaker Pattern**: Automatic backend failover and recovery
3. **Performance Monitoring**: Real-time backend performance metrics
4. **Configuration Management**: External configuration for backend priorities
5. **Advanced Retry Logic**: Intelligent retry strategies with exponential backoff

## Conclusion

The SceneAnalyzer refactoring successfully addresses the core architectural and reliability issues while maintaining backward compatibility. The implementation provides:

- ✅ Multi-backend priority support (Hunyuan Image > OpenAI > ComfyUI)
- ✅ Strict error handling with configurable thresholds
- ✅ Production-safe error propagation (no silent placeholders)
- ✅ Test mode for development and debugging
- ✅ Comprehensive error messages with troubleshooting guidance
- ✅ Full backward compatibility
- ✅ Extensive testing coverage

This refactoring significantly improves the reliability, maintainability, and debuggability of the object card generation pipeline while leveraging the existing HybridClient infrastructure for optimal backend utilization.