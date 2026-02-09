# 混元图像3.0集成指南

本文档详细介绍如何在Holodeck项目中配置和使用腾讯云混元图像3.0进行图像生成。

## 目录

- [功能概述](#功能概述)
- [快速开始](#快速开始)
- [详细配置](#详细配置)
- [API使用示例](#api使用示例)
- [最佳实践](#最佳实践)
- [故障排除](#故障排除)

## 功能概述

混元图像3.0是腾讯云提供的高质量文本到图像生成服务，具有以下特点：

- **高质量输出**：支持1024x1024等高分辨率图像生成
- **多种风格**：内置多种艺术风格，包括3D Pixar风格(501)
- **稳定可靠**：云端服务，无需本地GPU资源
- **灵活集成**：可作为主要或备用图像生成后端

## 快速开始

### 1. 获取API密钥

1. 访问[腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入"访问管理" → "API密钥管理"
3. 创建新的API密钥或使用现有密钥
4. 记录下SecretId和SecretKey

### 2. 安装依赖

项目已自动包含所需依赖：

```bash
uv sync  # 会自动安装 tencentcloud-sdk-python
```

### 3. 配置环境变量

复制环境变量模板并填入你的密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# Tencent Cloud Hunyuan Image API
HUNYUAN_SECRET_ID=你的SecretId
HUNYUAN_SECRET_KEY=你的SecretKey
```

### 4. 测试连接

运行示例脚本测试连接：

```bash
python examples/hunyuan_image_demo.py
```

## 详细配置

### 环境变量配置

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `HUNYUAN_SECRET_ID` | 腾讯云SecretId | `AKIDz8krbsJ5yKBZQpn74WFkmLPx3*******` |
| `HUNYUAN_SECRET_KEY` | 腾讯云SecretKey | `Gu5t9xGARNpq86cd98joQYCN3*******` |

### 生成参数说明

#### 分辨率选项
- `1024:1024` - 方形图像（推荐用于场景参考）
- `768:1024` - 竖屏图像
- `1280:720` - 横屏图像

#### 风格选项
- `不填写` - 默认风格（推荐）
- `501` - 3D Pixar风格（C4D效果）
- 其他风格代码请参考腾讯云官方文档

#### 模型选项
- `hunyuan-pro` - 专业版（推荐，对应3.0效果）
- `standard` - 标准版

## API使用示例

### 基础用法

```python
from holodeck_core.image_generation import HunyuanImageClient

# 创建客户端
client = HunyuanImageClient(
    secret_id="你的SecretId",
    secret_key="你的SecretKey"
)

# 生成图像
result = client.generate_image(
    prompt="一只赛博朋克风格的机械猫，霓虹灯背景",
    resolution="1024:1024",
    style=None,  # 使用默认风格
    model="hunyuan-pro",
    output_path="output.png"
)

print(f"生成完成: {result['local_path']}")
```

### 在Holodeck工作流中使用

```python
from holodeck_core.image_generation import generate_scene_reference

# 生成场景参考图
result = generate_scene_reference(
    prompt="一个未来主义的卧室，霓虹灯装饰",
    output_path="workspace/sessions/my_session/scene_ref.png"
)

# 生成物体卡片
from holodeck_core.image_generation import generate_object_card

result = generate_object_card(
    object_name="赛博朋克椅子",
    description="带有霓虹灯装饰的未来主义椅子",
    output_path="workspace/sessions/my_session/object_cards/chair.png"
)
```

### 高级用法

```python
# 批量生成物体卡片
objects = [
    {"name": "桌子", "description": "金属材质的现代桌子"},
    {"name": "台灯", "description": "简约风格的LED台灯"}
]

for i, obj in enumerate(objects):
    result = generate_object_card(
        object_name=obj["name"],
        description=obj["description"],
        output_path=f"object_cards/{obj['name']}.png"
    )
```

## 最佳实践

### 提示词设计

✅ **推荐做法**：
- 详细描述：`"一只赛博朋克风格的机械猫，霓虹灯背景，电影质感"`
- 使用默认风格：不填写Style参数
- 包含质量描述：`"超高清，专业摄影"`

❌ **不推荐**：
- 过于简单：`"一只猫"`
- 依赖特定风格代码：`Style: "201"`

### 性能优化

1. **使用默认风格**：避免不必要的风格处理开销
2. **合理设置超时**：根据图像复杂度调整timeout参数
3. **批量处理**：对多个对象使用批量生成减少连接开销
4. **错误重试**：实现适当的错误处理和重试机制

### 集成策略

#### 主备切换策略

```python
def generate_with_fallback(prompt, output_path):
    """优先使用混元图像，失败时降级到ComfyUI"""

    # 尝试混元图像
    try:
        from holodeck_core.image_generation import generate_scene_reference
        return generate_scene_reference(prompt, output_path)
    except Exception as e:
        print(f"混元图像生成失败: {e}")
        print("降级到ComfyUI...")

        # 降级到ComfyUI
        try:
            # 实现ComfyUI生成逻辑
            pass
        except Exception as e2:
            print(f"ComfyUI也失败了: {e2}")
            raise
```

## 故障排除

### 常见错误

#### 1. API密钥错误
```
Error: Invalid secretId
```
**解决方案**：检查SecretId和SecretKey是否正确，确保没有多余空格

#### 2. 连接超时
```
Error: Connection timeout
```
**解决方案**：
- 检查网络连接
- 增加timeout参数值
- 确认腾讯云API地域设置正确

#### 3. 配额限制
```
Error: Quota exceeded
```
**解决方案**：
- 检查腾讯云账户配额
- 联系腾讯云客服增加配额
- 实现请求间隔控制

### 调试技巧

1. **启用详细日志**：
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **测试连接**：
   ```python
   client = HunyuanImageClient(secret_id, secret_key)
   if client.test_connection():
       print("连接正常")
   ```

3. **检查环境变量**：
   ```python
   import os
   print(f"SecretId: {os.getenv('HUNYUAN_SECRET_ID')[:10]}...")
   ```

### 性能监控

```python
import time

start_time = time.time()
result = client.generate_image(prompt, output_path)
generation_time = time.time() - start_time

print(f"生成耗时: {generation_time:.2f}秒")
print(f"图像大小: {result.get('file_size_mb', 'N/A')} MB")
```

## 参考资源

- [腾讯云混元图像API文档](https://cloud.tencent.com/document/product/1729)
- [Python SDK文档](https://github.com/TencentCloud/tencentcloud-sdk-python)
- [Holodeck项目示例](examples/hunyuan_image_demo.py)