# Image Generation with Standardized Prompt Templates

This guide explains how to use the standardized prompt templates for image generation in the UnifiedVLMClient.

## 🎯 Overview

The system now supports two types of image generation:

1. **Reference Image Generation**: Creates panoramic scene images using standardized prompts
2. **Object Image Generation**: Creates isolated object images with transparent backgrounds

Both support multi-language prompts (English and Chinese) with automatic language detection.

## 🚀 Quick Start

### Basic Usage

```python
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend
import asyncio

async def main():
    # Initialize client
    client = UnifiedVLMClient(backend=VLMBackend.AUTO)

    # Generate reference image
    reference_image = await client.generate_reference_image(
        description="A modern living room with sofa, coffee table, and TV",
        style="realistic"
    )

    # Generate object image
    object_image = await client.generate_object_image(
        obj_name="modern sofa",
        style="realistic"
    )

    # Save images
    with open("reference.png", "wb") as f:
        f.write(reference_image)

    with open("sofa_isolated.png", "wb") as f:
        f.write(object_image)

asyncio.run(main())
```

## 🌍 Multi-Language Support

### English Prompts

```python
# English reference image
reference_en = await client.generate_reference_image(
    description="A modern living room with sofa, coffee table, and TV",
    style="realistic",
    language="en"  # Explicit English
)

# English object image
object_en = await client.generate_object_image(
    obj_name="modern sofa",
    style="realistic",
    language="en"
)
```

### Chinese Prompts

```python
# Chinese reference image
reference_zh = await client.generate_reference_image(
    description="一个现代化的客厅，配有沙发、咖啡桌和电视",
    style="写实",
    language="zh"  # Explicit Chinese
)

# Chinese object image
object_zh = await client.generate_object_image(
    obj_name="现代沙发",
    style="写实",
    language="zh"
)
```

### Auto-Detection

```python
# Auto-detect language from text content
reference_auto = await client.generate_reference_image(
    description="A modern living room with sofa, coffee table, and TV",
    style="realistic"
    # language=None (auto-detection)
)
```

## 📋 API Reference

### generate_reference_image()

Generates a panoramic reference image using standardized prompts.

```python
async def generate_reference_image(
    self,
    description: str,
    style: str = "realistic",
    language: Optional[str] = None
) -> bytes:
```

**Parameters:**
- `description`: Scene description text
- `style`: Artistic style (e.g., "realistic", "artistic", "写实", "艺术")
- `language`: Language code ("en", "zh", or None for auto-detection)

**Returns:**
- Image data as bytes

### generate_object_image()

Generates an isolated object image with transparent background.

```python
async def generate_object_image(
    self,
    obj_name: str,
    style: str = "realistic",
    reference_context: Optional[str] = None,
    language: Optional[str] = None
) -> bytes:
```

**Parameters:**
- `obj_name`: Name of the object to generate
- `style`: Artistic style
- `reference_context`: Optional reference context for style consistency
- `language`: Language code ("en", "zh", or None for auto-detection)

**Returns:**
- PNG image data with transparent background as bytes

## 🎨 Standardized Prompt Templates

### Reference Image Templates

**English:**
```
{description}. Render in {style} style. 3-D view: x->right, y->backward, z->up. Well-lit, no extra objects.
```

**Chinese:**
```
{description}。使用{style}风格渲染。3D视图：x轴向右，y轴向后，z轴向上。光照良好，无额外物体。
```

### Object Image Templates

**English:**
```
Please generate ONE PNG image of an isolated front-view {obj_name} with a transparent background, in {style} style, with shapes and style similar to the reference scene.
```

**Chinese:**
```
请生成一个孤立正面视图的{obj_name} PNG图像具有透明背景，使用{style}风格，形状和风格与参考场景相似。
```

## 🔧 Configuration

### Backend Selection

```python
# Auto-select best backend
client = UnifiedVLMClient(backend=VLMBackend.AUTO)

# Force specific backend
client = UnifiedVLMClient(backend=VLMBackend.OPENAI)
client = UnifiedVLMClient(backend=VLMBackend.SILICONFLOW)

# Use custom model with explicit configuration
client = UnifiedVLMClient(
    backend=VLMBackend.CUSTOM,
    custom_config={
        "base_url": "https://api.example.com/v1",
        "api_key": "your-api-key",
        "model_name": "your-model-name"
    }
)

# Use custom model with environment variables (recommended)
client = UnifiedVLMClient(backend=VLMBackend.CUSTOM)
# Automatically reads from CUSTOM_VLM_BASE_URL, CUSTOM_VLM_API_KEY, CUSTOM_VLM_MODEL_NAME
```

### Environment Variables

#### Standard API Keys
```bash
# OpenAI
OPENAI_API_KEY=your_openai_key

# SiliconFlow
SILICONFLOW_API_KEY=your_siliconflow_key
```

#### Custom VLM Configuration
```bash
# Custom backend (URL + API Key + Model Name)
CUSTOM_VLM_BASE_URL=https://api.example.com/v1
CUSTOM_VLM_API_KEY=your_custom_key
CUSTOM_VLM_MODEL_NAME=your_model_name
```

#### Usage Patterns

**Pattern 1: Command line**
```bash
export CUSTOM_VLM_BASE_URL=https://api.example.com/v1
export CUSTOM_VLM_API_KEY=your-api-key
export CUSTOM_VLM_MODEL_NAME=your-model-name
python your_script.py
```

**Pattern 2: .env file**
```env
CUSTOM_VLM_BASE_URL=https://api.example.com/v1
CUSTOM_VLM_API_KEY=your-api-key
CUSTOM_VLM_MODEL_NAME=your-model-name
```

**Pattern 3: Docker**
```dockerfile
ENV CUSTOM_VLM_BASE_URL=https://api.example.com/v1
ENV CUSTOM_VLM_API_KEY=your-api-key
ENV CUSTOM_VLM_MODEL_NAME=your-model-name
```

**Pattern 4: Programmatically**
```python
import os
os.environ['CUSTOM_VLM_BASE_URL'] = 'https://api.example.com/v1'
os.environ['CUSTOM_VLM_API_KEY'] = 'your-api-key'
os.environ['CUSTOM_VLM_MODEL_NAME'] = 'your-model-name'
```

## 🔄 Production Pipeline Integration

The image generation functionality integrates seamlessly with the existing production pipeline:

```python
async def production_pipeline():
    # Initialize client
    client = UnifiedVLMClient(backend=VLMBackend.AUTO)

    # Step 1: Extract objects from scene description
    scene_data = await client.extract_objects("A modern living room with sofa, coffee table, and TV")

    # Step 2: Generate reference image
    reference_image = await client.generate_reference_image(
        description="A modern living room with sofa, coffee table, and TV",
        style="realistic"
    )

    # Step 3: Generate object images for each extracted object
    for obj in scene_data.objects:
        object_image = await client.generate_object_image(
            obj_name=obj.name,
            style="realistic",
            reference_context="A modern living room with sofa, coffee table, and TV"
        )

        # Save object image
        with open(f"{obj.name}_isolated.png", "wb") as f:
            f.write(object_image)

    # Step 4: Use images for 3D asset generation
    # (Integration with Hunyuan3D or other 3D generation services)
```

## 🌐 Language Detection

The system automatically detects language based on text content:

- **Chinese**: Text with >30% Chinese characters (Unicode range \u4e00-\u9fff)
- **English**: Text with ≤30% Chinese characters

You can override auto-detection by explicitly specifying the language parameter.

## 🔍 Template Customization

### Using PromptTemplateManager Directly

```python
from holodeck_core.scene_analysis.prompt_templates import PromptTemplateManager

manager = PromptTemplateManager(default_language="en")

# Get formatted prompts
ref_prompt = manager.get_prompt(
    "reference_image",
    "en",
    description="A modern living room",
    style="realistic"
)

obj_prompt = manager.get_prompt(
    "individual_object",
    "zh",
    obj_name="现代沙发",
    style="写实"
)
```

### Global Convenience Functions

```python
from holodeck_core.scene_analysis.prompt_templates import (
    get_reference_image_prompt,
    get_object_image_prompt
)

# Simple usage
ref_prompt = get_reference_image_prompt("A modern living room", "realistic")
obj_prompt = get_object_image_prompt("modern sofa", "realistic")

# With explicit language
ref_prompt_zh = get_reference_image_prompt(
    "一个现代化的客厅",
    "写实",
    "zh"
)
```

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Unit tests for prompt templates
python -m pytest tests/unit/scene_analysis/test_prompt_templates.py -v

# Integration tests for image generation
python -m pytest tests/integration/test_image_generation_integration.py -v

# Example usage
python examples/image_generation_example.py
```

## 📊 Performance Considerations

1. **Async Operations**: All image generation methods are async for better performance
2. **Connection Pooling**: Reuses HTTP connections for multiple requests
3. **Timeout Handling**: Default 120-second timeout for image generation
4. **Error Handling**: Comprehensive error handling with fallback mechanisms

## 🚨 Error Handling

```python
try:
    image_data = await client.generate_reference_image(
        description="A modern living room",
        style="realistic"
    )
except NotImplementedError as e:
    print(f"Backend doesn't support image generation: {e}")
except Exception as e:
    print(f"Image generation failed: {e}")
```

## 🔄 Migration Guide

### From Legacy Image Generation

**Before:**
```python
# Legacy approach (if it existed)
image_data = await some_legacy_method(prompt)
```

**After:**
```python
# New standardized approach
client = UnifiedVLMClient(backend=VLMBackend.AUTO)
image_data = await client.generate_reference_image(
    description="Scene description",
    style="realistic"
)
```

### Integration with Existing Code

The new image generation functionality is fully backward compatible. Existing object extraction code continues to work unchanged:

```python
# This continues to work as before
scene_data = await client.extract_objects("A modern living room")

# New functionality can be added incrementally
reference_image = await client.generate_reference_image(
    description="A modern living room",
    style="realistic"
)
```

## 🎯 Best Practices

1. **Language Consistency**: Use the same language for both reference and object images
2. **Style Matching**: Use consistent styles across all images in a scene
3. **Context Provision**: Provide reference context for better object image consistency
4. **Error Handling**: Always implement proper error handling for production use
5. **Async Usage**: Use async/await pattern for better performance
6. **Resource Management**: Properly close files and connections

## 🔮 Future Enhancements

- Additional language support (Japanese, Korean, etc.)
- More artistic styles and rendering options
- Batch image generation capabilities
- Advanced prompt customization options
- Integration with more image generation backends

The standardized prompt template system provides a solid foundation for consistent, high-quality image generation across multiple backends and languages! 🚀