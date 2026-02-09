# 混元3D生成功能使用说明

## 快速开始

### 1. 环境配置

确保你的`.env`文件中包含以下配置：

```bash
# 必需：腾讯云API密钥
HUNYUAN_SECRET_ID=your_secret_id_here
HUNYUAN_SECRET_KEY=your_secret_key_here

# 可选：3D后端配置
3D_BACKEND_PRIORITY=hunyuan,sf3d  # 混元优先，SF3D作为备选
```

### 2. 基本用法

#### 从文本提示词生成3D模型
```python
from holodeck_core.object_gen.hunyuan_3d_client import generate_3d_asset

result = generate_3d_asset(
    prompt="一个红色的苹果",
    output_dir="output_models",
    task_id="apple_task"
)

if result.success:
    print(f"✅ 生成成功！")
    print(f"   耗时: {result.generation_time:.2f}秒")
    print(f"   模型文件: {result.local_paths}")
else:
    print(f"❌ 生成失败: {result.error_message}")
```

#### 从图像生成3D模型
```python
from holodeck_core.object_gen.hunyuan_3d_client import Hunyuan3DClient

client = Hunyuan3DClient(
    secret_id=os.getenv("HUNYUAN_SECRET_ID"),
    secret_key=os.getenv("HUNYUAN_SECRET_KEY")
)

# 从图像文件
result = client.generate_3d_from_image(
    image_path="path/to/image.jpg",
    task_id="image_task",
    output_dir="output_models"
)

# 从图像URL
result = client.generate_3d_from_image_url(
    image_url="https://example.com/image.jpg",
    task_id="url_task",
    output_dir="output_models"
)
```

## 高级功能

### 选择Pro或Rapid版本

```python
# Pro版本 - 高质量，适合最终结果
client_pro = Hunyuan3DClient(
    secret_id=secret_id,
    secret_key=secret_key,
    use_pro_version=True
)

# Rapid版本 - 快速，适合预览
client_rapid = Hunyuan3DClient(
    secret_id=secret_id,
    secret_key=secret_key,
    use_pro_version=False
)
```

### 多视角3D生成

```python
from holodeck_core.object_gen.hunyuan_3d_client import Hunyuan3DTask

task = Hunyuan3DTask(
    task_id="multi_view_chair",
    output_dir="output_models",
    multi_views={
        "front": "https://example.com/front.jpg",
        "back": "https://example.com/back.jpg",
        "left": "https://example.com/left.jpg",
        "right": "https://example.com/right.jpg"
    }
)

result = client.generate_3d_from_task(task)
```

### 自定义参数

```python
task = Hunyuan3DTask(
    task_id="custom_task",
    prompt="一个木制的桌子",
    output_dir="output_models",
    enable_pbr=True,        # 启用PBR材质
    result_format="GLB"     # 输出格式：GLB/OBJ/STL/FBX
)
```

## 输出格式

支持的3D模型格式：
- **GLB** (默认) - 二进制GLTF格式，推荐使用
- **OBJ** - Wavefront OBJ格式
- **STL** - STereoLithography格式
- **FBX** - Filmbox格式

## 错误处理

```python
try:
    result = client.generate_3d_from_prompt(
        prompt="一个红色的苹果",
        task_id="test_task",
        output_dir="output"
    )

    if result.success:
        print(f"✅ 生成成功！")
        print(f"   Job ID: {result.job_id}")
        print(f"   模型文件: {result.local_paths}")
    else:
        print(f"❌ 生成失败: {result.error_message}")
        # 可能的错误：超时、API限制、参数错误等

except Exception as e:
    print(f"❌ 系统错误: {e}")
```

## 配置选项

### 客户端配置
```python
client = Hunyuan3DClient(
    secret_id="your_secret_id",
    secret_key="your_secret_key",
    region="ap-guangzhou",           # API地域
    timeout=600,                      # 超时时间（秒）
    poll_interval=3,                  # 轮询间隔（秒）
    use_pro_version=True              # 使用Pro版本
)
```

### 环境变量配置
```bash
# 后端优先级配置
3D_BACKEND_PRIORITY=hunyuan,sf3d     # 混元优先
3D_BACKEND_PRIORITY=sf3d,hunyuan     # SF3D优先
3D_BACKEND_PRIORITY=hunyuan          # 仅使用混元

# ComfyUI配置（SF3D后端）
COMFYUI_AVAILABLE=true
COMFYUI_SERVER=127.0.0.1:8189
```

## 性能提示

### 选择合适的版本
- **Pro版本**: 用于最终产品，质量最高，生成时间较长
- **Rapid版本**: 用于快速预览和测试，生成时间较短

### 优化生成速度
1. 使用Rapid版本进行快速测试
2. 合理设置超时时间
3. 使用图像URL而不是Base64编码（减少数据传输）
4. 批量处理时适当增加轮询间隔

### 节省API配额
1. 使用缓存避免重复生成
2. 先在Rapid版本测试，满意后再用Pro版本生成
3. 合理设置任务ID，便于追踪和管理

## 常见问题

### Q: 生成失败怎么办？
A: 检查以下几点：
- API密钥是否正确配置
- 网络连接是否正常
- 提示词是否过于复杂
- 是否超出API配额限制

### Q: 如何选择Pro和Rapid版本？
A:
- **Pro版本**: 最终产品展示、高质量需求
- **Rapid版本**: 快速原型、测试验证、预览

### Q: 支持哪些3D格式？
A: 支持GLB、OBJ、STL、FBX格式，推荐使用GLB格式。

### Q: 生成时间有多长？
A: 取决于模型复杂度：
- Rapid版本：通常1-3分钟
- Pro版本：通常3-10分钟

## 更多资源

- `example_hunyuan_3d.py` - 完整的使用示例
- `test_hunyuan_3d.py` - 测试用例参考
- `HUNYUAN_3D_INTEGRATION_COMPLETE.md` - 详细技术文档

## 技术支持

如果遇到问题，请检查：
1. 环境变量配置是否正确
2. API密钥是否有足够的配额
3. 网络连接是否正常
4. 查看日志输出获取详细错误信息

如需更多帮助，请参考腾讯云混元3D API官方文档。