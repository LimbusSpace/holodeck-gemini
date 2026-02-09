# 混元图像3.0优化客户端使用指南

## 📋 概述

优化后的混元图像客户端 (`HunyuanImageClientOptimized`) 在原有功能基础上增加了智能并发控制、自动重试机制和批量处理功能，有效解决了API限流和并发限制问题。

## 🎯 核心优势

### 1. 智能并发控制
- **信号量机制**: 使用 `threading.Semaphore` 控制同时运行的任务数
- **可配置并发数**: 根据腾讯云配额灵活调整 `max_concurrent_jobs`
- **自动排队**: 超出限制的任务自动排队等待

### 2. 自动重试机制
- **指数退避**: 使用 `tenacity` 库实现智能重试
- **异常识别**: 自动识别限流错误 (`RequestLimitExceeded`) 并延长等待时间
- **可配置重试次数**: 支持自定义最大重试次数和基础延迟

### 3. 批量任务处理
- **同步批量处理**: `generate_batch_sync()` 方法
- **异步批量处理**: `generate_batch_async()` 方法
- **结果收集**: 自动收集所有任务结果和统计信息

### 4. 线程安全
- **线程安全操作**: 所有操作都是线程安全的
- **资源管理**: 自动管理线程池和资源
- **错误隔离**: 单个任务失败不影响其他任务

## 🚀 快速开始

### 基础使用

```python
from holodeck_core.image_generation.hunyuan_image_client_optimized import HunyuanImageClientOptimized

# 创建优化客户端
client = HunyuanImageClientOptimized(
    secret_id="your_secret_id",
    secret_key="your_secret_key",
    region="ap-guangzhou",
    max_concurrent_jobs=2,  # 根据配额设置
    max_retries=3
)

# 生成单个图像 (向后兼容)
result = client.generate_image(
    prompt="一只可爱的小猫",
    resolution="1024:1024",
    output_path="cat.png"
)
```

### 批量处理

```python
from holodeck_core.image_generation.hunyuan_image_client_optimized import GenerationTask

# 创建任务列表
tasks = [
    GenerationTask(prompt="猫1", output_path="cat1.png"),
    GenerationTask(prompt="猫2", output_path="cat2.png"),
    GenerationTask(prompt="猫3", output_path="cat3.png")
]

# 批量处理
results = client.generate_batch_sync(tasks)
```

### 异步处理

```python
import asyncio

# 异步批量处理
async def main():
    results = await client.generate_batch_async(tasks)
    return results

asyncio.run(main())
```

## ⚙️ 配置参数

### 客户端初始化参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `secret_id` | str | 必填 | 腾讯云SecretId |
| `secret_key` | str | 必填 | 腾讯云SecretKey |
| `region` | str | "ap-beijing" | API地域 |
| `timeout` | int | 120 | 超时时间(秒) |
| `max_concurrent_jobs` | int | 2 | 最大并发任务数 |
| `max_retries` | int | 3 | 最大重试次数 |
| `retry_delay` | float | 2.0 | 基础重试延迟(秒) |

### 环境变量配置

```bash
# .env 文件配置
HUNYUAN_SECRET_ID=your_secret_id
HUNYUAN_SECRET_KEY=your_secret_key
HUNYUAN_MAX_CONCURRENT=2  # 可选，默认2
```

## 📊 并发控制策略

### 信号量机制

```python
# 内部实现原理
semaphore = threading.Semaphore(max_concurrent_jobs)

def _process_single_task(self, task):
    with semaphore:  # 获取令牌，如果令牌用完则等待
        # 执行任务
        return result
```

### 并发数建议

| 腾讯云配额 | 建议并发数 | 说明 |
|-----------|-----------|------|
| 基础版 | 1-2 | 保守设置，避免限流 |
| 标准版 | 2-3 | 平衡性能和稳定性 |
| 高级版 | 3-5 | 充分利用配额 |
| 企业版 | 5+ | 根据实际配额调整 |

## 🔄 重试机制

### 重试策略

1. **指数退避**: 第1次等待2秒，第2次4秒，第3次8秒
2. **限流特殊处理**: 检测到限流错误时等待更长时间
3. **异常类型过滤**: 只对网络异常和限流错误重试

### 重试配置

```python
# 自定义重试策略
client = HunyuanImageClientOptimized(
    # ... 其他参数
    max_retries=5,        # 增加重试次数
    retry_delay=1.0       # 减少基础延迟
)
```

## 📦 批量处理

### 任务创建

```python
from holodeck_core.image_generation.hunyuan_image_client_optimized import GenerationTask

task = GenerationTask(
    prompt="图像描述",
    resolution="1024:1024",
    style=None,
    model="hunyuan-pro",
    output_path="output.png",
    task_id="custom_id"  # 可选
)
```

### 批量处理结果

```python
results = client.generate_batch_sync(tasks)

for result in results:
    if result.success:
        print(f"✅ {result.task_id}: {result.image_url}")
        print(f"   耗时: {result.generation_time:.2f}秒")
    else:
        print(f"❌ {result.task_id}: {result.error_message}")
```

## 🔧 便捷函数

### 环境变量自动加载

```python
from holodeck_core.image_generation.hunyuan_image_client_optimized import create_optimized_client_from_env

# 自动从环境变量创建客户端
client = create_optimized_client_from_env()
```

### 批量图像生成

```python
from holodeck_core.image_generation.hunyuan_image_client_optimized import generate_batch_images

prompts = ["猫1", "猫2", "猫3"]
results = generate_batch_images(
    prompts=prompts,
    output_dir="images/",
    resolution="1024:1024"
)
```

## 🚨 错误处理

### 常见错误类型

| 错误类型 | 处理策略 | 建议 |
|---------|----------|------|
| `RequestLimitExceeded` | 自动重试 + 延长等待 | 降低并发数 |
| `InvalidParameter` | 立即失败 | 检查参数格式 |
| `TimeoutError` | 重试或失败 | 增加超时时间 |
| `NetworkError` | 自动重试 | 检查网络连接 |

### 错误处理示例

```python
try:
    result = client.generate_image(prompt="test")
    if result["status"] == "success":
        print("生成成功")
    else:
        print(f"生成失败: {result.get('error')}")
except Exception as e:
    print(f"异常: {e}")
```

## 📈 性能优化建议

### 1. 合理设置并发数
- 从低并发数开始测试
- 逐步增加直到达到最佳性能
- 监控限流错误频率

### 2. 批量处理优化
- 将相关任务分组处理
- 避免单次提交过多任务
- 使用异步处理避免阻塞

### 3. 资源管理
- 及时清理临时文件
- 合理设置超时时间
- 监控内存使用情况

## 🔄 向后兼容性

### 原有代码无需修改

```python
# 原有代码仍然可用
from holodeck_core.image_generation import HunyuanImageClient

client = HunyuanImageClient(secret_id, secret_key)
result = client.generate_image(prompt)
```

### 渐进式升级

```python
# 可以逐步迁移到优化版本
from holodeck_core.image_generation.hunyuan_image_client_optimized import HunyuanImageClientOptimized

client = HunyuanImageClientOptimized(secret_id, secret_key, max_concurrent_jobs=2)
result = client.generate_image(prompt)  # 相同接口
```

## 📚 示例代码

### 完整批量处理示例

```python
import asyncio
from holodeck_core.image_generation.hunyuan_image_client_optimized import (
    HunyuanImageClientOptimized, GenerationTask
)

async def batch_generation_example():
    # 创建客户端
    client = HunyuanImageClientOptimized(
        secret_id="your_id",
        secret_key="your_key",
        max_concurrent_jobs=2
    )

    # 创建任务
    tasks = [
        GenerationTask(prompt=f"第{i}只猫", output_path=f"cat_{i}.png")
        for i in range(10)
    ]

    # 异步处理
    results = await client.generate_batch_async(tasks)

    # 处理结果
    for result in results:
        if result.success:
            print(f"✅ {result.task_id} 成功")
        else:
            print(f"❌ {result.task_id} 失败: {result.error_message}")

# 运行示例
asyncio.run(batch_generation_example())
```

## 🎯 最佳实践

1. **从小规模开始**: 先测试小批量任务，确认配置正确
2. **监控性能指标**: 关注生成时间、成功率和错误类型
3. **合理设置参数**: 根据实际配额和需求调整并发数和重试策略
4. **错误日志记录**: 记录失败任务以便后续分析
5. **定期清理**: 清理临时文件和过期图像

## 📞 故障排除

### 常见问题

**Q: 如何确定合适的并发数？**
A: 从1-2开始，逐步增加，观察限流错误频率。

**Q: 遇到限流错误怎么办？**
A: 降低并发数，增加重试延迟，或联系腾讯云提高配额。

**Q: 如何监控任务状态？**
A: 使用 `GenerationResult` 对象查看任务状态和错误信息。

**Q: 支持异步操作吗？**
A: 是的，提供 `generate_batch_async()` 方法。

## 🎉 总结

优化后的混元图像客户端提供了：
- ✅ 智能并发控制，避免API限流
- ✅ 自动重试机制，提高成功率
- ✅ 批量任务处理，提升效率
- ✅ 异步支持，避免阻塞
- ✅ 向后兼容，平滑升级
- ✅ 便捷函数，简化使用

通过这些优化，您可以更高效、稳定地使用混元图像3.0服务，充分发挥其强大的图像生成能力。