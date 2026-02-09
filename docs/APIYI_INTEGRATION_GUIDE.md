# APIYi (Gemini-3-Pro-Image) 集成指南

## 📋 概述

本指南介绍如何将APIAyi的Gemini-3-Pro-Image模型集成到Holodeck的3D全管道中。APIAyi提供了高质量的图像生成能力，支持2K分辨率输出。

## 🚀 快速开始

### 1. 获取API密钥

1. 访问 [APIAyi官网](https://api.apiyi.com)
2. 注册账户并获取API密钥
3. 选择适合的计费计划

### 2. 配置环境

#### 方法一：环境变量

```bash
# Linux/macOS
export APIAYI_API_KEY="sk-your-actual-api-key"
export APIAYI_BASE_URL="https://api.apiyi.com/v1beta/models"
export APIAYI_MODEL="gemini-3-pro-image-preview"
export APIAYI_TIMEOUT="300"

# Windows
set APIAYI_API_KEY=sk-your-actual-api-key
set APIAYI_BASE_URL=https://api.apiyi.com/v1beta/models
set APIAYI_MODEL=gemini-3-pro-image-preview
set APIAYI_TIMEOUT=300
```

#### 方法二：配置文件

创建 `.env` 文件：
```env
APIAYI_API_KEY=sk-your-actual-api-key
APIAYI_BASE_URL=https://api.apiyi.com/v1beta/models
APIAYI_MODEL=gemini-3-pro-image-preview
APIAYI_TIMEOUT=300
```

或者更新 `~/.holodeck/config.yaml`：
```yaml
APIAYI_API_KEY: "sk-your-actual-api-key"
APIAYI_BASE_URL: "https://api.apiyi.com/v1beta/models"
APIAYI_MODEL: "gemini-3-pro-image-preview"
APIAYI_TIMEOUT: 300
DEFAULT_IMAGE_BACKEND: "apiyi"
```

### 3. 验证安装

```bash
# 运行演示脚本
python examples/apiyi_demo.py

# 或者运行测试
python -m pytest tests/integration/test_apiyi_integration.py -v
```

## 💻 使用示例

### 直接使用APIAyi客户端

```python
import asyncio
from holodeck_core.image_generation.apiyi_client import APIYiClient

async def main():
    # 创建客户端
    client = APIYiClient()
    client.initialize()

    # 生成图像
    result = await client.generate_image(
        prompt="一只可爱的小猫坐在花园里，油画风格，高清，细节丰富",
        resolution="1024:1024",
        style="oil_painting",
        output_path="cute_cat.png"
    )

    if result.success:
        print(f"图像已生成: {result.data}")
        print(f"耗时: {result.duration:.2f}秒")
    else:
        print(f"生成失败: {result.error}")

asyncio.run(main())
```

### 通过统一客户端使用

```python
import asyncio
from holodeck_core.image_generation.unified_image_client import UnifiedImageClient

async def main():
    # 创建统一客户端
    client = UnifiedImageClient()

    # 指定使用APIAyi后端
    result = await client.generate_image(
        prompt="未来城市天际线，科幻风格",
        resolution="1920:1080",
        style="digital_art",
        backend="apiyi",  # 明确指定后端
        output_path="future_city.png"
    )

    # 或者让系统自动选择最佳后端
    result = await client.generate_image(
        prompt="宁静的湖面倒映着雪山",
        resolution="1536:1536",
        style="watercolor",
        output_path="mountain_lake.png"
        # 不指定backend，系统会自动选择APIAyi（如果配置了）
    )

asyncio.run(main())
```

### 在完整管道中使用

```python
import asyncio
from holodeck_core.integration.pipeline_orchestrator import run_complete_pipeline

async def main():
    # 在完整管道中指定APIAyi作为图像生成后端
    result = await run_complete_pipeline(
        object_description="一个未来主义的椅子，具有流线型设计",
        object_name="未来椅子",
        image_generation_backend="apiyi",  # 指定图像生成使用APIAyi
        workspace_root="my_project"
    )

    if result.success:
        print(f"管道执行成功!")
        print(f"会话ID: {result.session_id}")
        print(f"完成阶段: {result.metadata['completed_stages']}")

asyncio.run(main())
```

## 🎨 支持的参数

### 分辨率和宽高比

| 分辨率 | 宽高比 | 推荐用途 |
|--------|--------|----------|
| 1024:1024 | 1:1 | 头像、图标、方形图像 |
| 1920:1080 | 16:9 | 横幅、视频封面、宽屏 |
| 1024:768 | 4:3 | 传统显示器、演示文稿 |
| 1536:1024 | 3:2 | 照片、印刷品 |

### 图像质量

| 尺寸 | 适用场景 | 生成时间 |
|------|----------|----------|
| 480p | 快速预览、测试 | 30-60秒 |
| 720p | 中等质量 | 60-120秒 |
| 1080p | 高质量 | 120-180秒 |
| 2K | 最高质量 | 180-300秒 |

### 风格参数

| 风格 | 描述 | 示例 |
|------|------|------|
| `oil_painting` | 油画风格 | 厚重笔触，纹理丰富 |
| `watercolor` | 水彩风格 | 柔和色彩，流动感 |
| `digital_art` | 数字艺术 | 清晰线条，现代感 |
| `realistic` | 写实风格 | 照片级真实感 |
| `cartoon` | 卡通风格 | 鲜艳色彩，简化形式 |
| `anime` | 动漫风格 | 日式动画美学 |
| `sketch` | 素描风格 | 铅笔手绘效果 |
| `abstract` | 抽象风格 | 非具象形式 |

## 🔧 配置选项

### 环境变量

| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `APIAYI_API_KEY` | (必需) | APIYi API密钥 |
| `APIAYI_BASE_URL` | `https://api.apiyi.com/v1beta/models` | API基础URL |
| `APIAYI_MODEL` | `gemini-3-pro-image-preview` | 使用的模型 |
| `APIAYI_TIMEOUT` | `300` | 请求超时时间（秒） |

### 运行时参数

```python
# 生成时的可选参数
result = await client.generate_image(
    prompt="提示词",
    resolution="1024:1024",  # 分辨率
    style="oil_painting",     # 风格
    model="gemini-3-pro-image-preview",  # 模型
    output_path="output.png", # 输出路径
    timeout=300,             # 超时时间
    quality="high"           # 质量参数（如果API支持）
)
```

## 📊 性能监控

### 查看后端统计

```python
client = UnifiedImageClient()
stats = client.get_backend_statistics()
print(f"APIAyi统计: {stats['backend_stats']['apiyi']}")
```

### 监控指标

- **成功率**: APIYi的成功请求比例
- **平均响应时间**: 每次生成的平均耗时
- **文件平均大小**: 生成图像的平均文件大小
- **最后使用时间**: 最近一次使用的时间

## ⚠️ 错误处理

### 常见错误

1. **API密钥错误**
   ```python
   # 检查环境变量
   import os
   api_key = os.getenv("APIAYI_API_KEY")
   if not api_key:
       raise ValueError("请设置APIAYI_API_KEY环境变量")
   ```

2. **网络超时**
   ```python
   try:
       result = await client.generate_image(prompt="test", timeout=600)
   except asyncio.TimeoutError:
       print("请求超时，请重试或增加超时时间")
   ```

3. **提示词限制**
   ```python
   # 检查提示词长度
   if len(prompt) > 1000:
       prompt = prompt[:997] + "..."
   ```

### 重试机制

```python
from holodeck_core.clients.base import ClientConfig

# 配置重试参数
config = ClientConfig(
    max_retries=3,
    retry_delay=2.0
)

client = APIYiClient(client_config=config)
```

## 🧪 测试

### 运行测试

```bash
# 运行所有APIAyi相关测试
python -m pytest tests/integration/test_apiyi_integration.py -v

# 运行特定测试
python -m pytest tests/integration/test_apiyi_integration.py::TestAPIYiClient::test_generate_image_success -v

# 运行演示
python examples/apiyi_demo.py
```

### 测试覆盖范围

- ✅ 配置验证
- ✅ 提示词验证
- ✅ API调用
- ✅ 错误处理
- ✅ 工厂集成
- ✅ 统一客户端集成
- ✅ 性能统计

## 🔄 与其他后端的比较

| 特性 | APIYi | Hunyuan | ComfyUI | OpenAI DALL-E |
|------|-------|---------|---------|---------------|
| 最高分辨率 | 2K | 1024px | 无限制 | 1024px |
| 风格控制 | ✅ | ✅ | ✅ | ⚠️ |
| API调用 | ✅ | ✅ | 本地 | ✅ |
| 成本 | 中等 | 低 | 免费 | 高 |
| 生成速度 | 慢 | 中等 | 快 | 快 |
| 质量 | 极高 | 高 | 可变 | 高 |

## 🚀 最佳实践

### 1. 提示词工程

```python
# 好的提示词
prompt = "一只可爱的小猫坐在花园里，油画风格，高清，细节丰富，阳光明媚"

# 避免过于简单的提示词
prompt = "cat"  # ❌ 不够详细
```

### 2. 批量处理

```python
async def batch_generate(prompts):
    client = APIYiClient()
    tasks = []

    for prompt in prompts:
        task = client.generate_image(
            prompt=prompt,
            resolution="1024:1024",
            output_path=f"output_{len(tasks)}.png"
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### 3. 缓存策略

```python
# 简单的缓存实现
cache = {}

def get_cached_result(prompt, resolution):
    key = f"{prompt}:{resolution}"
    return cache.get(key)

def cache_result(prompt, resolution, result):
    key = f"{prompt}:{resolution}"
    cache[key] = result
```

### 4. 错误恢复

```python
async def robust_generation(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = await client.generate_image(prompt=prompt)
            if result.success:
                return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(2 ** attempt)  # 指数退避
```

## 📞 支持与故障排除

### 常见问题

**Q: 如何获取APIAyi API密钥？**
A: 访问 https://api.apiyi.com 注册账户，在控制台中创建API密钥。

**Q: 生成速度很慢怎么办？**
A: 2K图像生成需要较长时间（3-5分钟），可以：
- 使用较低分辨率（1080p）
- 增加超时时间
- 检查网络连接

**Q: 提示词有什么限制？**
A: 提示词长度限制为1000字符，避免包含不当内容。

**Q: 如何监控使用情况？**
A: 使用统一客户端的 `get_backend_statistics()` 方法查看性能统计。

### 联系支持

- APIYi官方支持：support@apiyi.com
- APIYi文档：https://docs.apiyi.com
- Holodeck问题：请在GitHub提交issue

## 🎉 总结

APIAyi集成提供了：

✅ **高质量图像生成** - 支持2K分辨率输出
✅ **灵活的风格控制** - 多种艺术风格可选
✅ **完整的错误处理** - 健壮的API调用和异常处理
✅ **性能监控** - 详细的统计和监控指标
✅ **易于集成** - 与现有Holodeck架构无缝集成
✅ **自动fallback** - 与其他后端配合工作

通过本指南，你应该能够成功地将APIAyi集成到你的Holodeck工作流中，享受高质量的图像生成服务！