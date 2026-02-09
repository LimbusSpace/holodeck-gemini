# Standardized Prompt Templates for VLM Integration

## 📋 Overview

This document integrates the standardized prompt templates for VLM-based image generation, including panoramic reference image generation and individual object image generation.

## 🎯 Provided Templates

### 1. 全景参考图生成 (Generate Reference Image)
**位置**: Supplementary Material 6.2, Prompt 1
**作用**: 生成一张包含所有物体的全景图，作为后续风格和光影的基准

**原文 (English)**:
```python
prompt = (
    f"{description}. Render in {style} style. "
    "3-D view: x->right, y->backward, z->up. "
    "Well-lit, no extra objects."
)
```

**中文版本**:
```python
prompt = (
    f"{description}。使用{style}风格渲染。"
    "3D视图：x轴向右，y轴向后，z轴向上。"
    "光照良好，无额外物体。"
)
```

### 2. 单体资产图生成 (Generate Individual Images)
**位置**: Supplementary Material 6.2, Prompt 4
**作用**: 从全景图中拆解出单个物体，生成去背景的 PNG，用于喂给 3D生成模块

**原文 (English)**:
```python
prompt = (
    f"Please generate ONE PNG image of an isolated front-view {obj_name} "
    f"with a transparent background, in {style} style, with shapes and style "
    "similar to the reference scene."
)
```

**中文版本**:
```python
prompt = (
    f"请生成一个孤立正面视图的{obj_name} PNG图像"
    f"具有透明背景，使用{style}风格，形状和风格"
    "与参考场景相似。"
)
```

## 🔧 Integration Architecture

### Integration Points in Unified VLM

#### 1. Reference Image Generation
**Location**: `CustomVLMClient.generate_reference_image()` (to be implemented)

```python
async def generate_reference_image(
    self,
    description: str,
    style: str = "realistic"
) -> bytes:
    """Generate panoramic reference image using standardized template."""

    prompt = (
        f"{description}. Render in {style} style. "
        "3-D view: x->right, y->backward, z->up. "
        "Well-lit, no extra objects."
    )

    # Implementation for image generation API call
    return await self._call_image_generation_api(prompt)
```

#### 2. Individual Object Image Generation
**Location**: `CustomVLMClient.generate_object_image()` (to be implemented)

```python
async def generate_object_image(
    self,
    obj_name: str,
    style: str = "realistic",
    reference_context: Optional[str] = None
) -> bytes:
    """Generate isolated object image with transparent background."""

    prompt = (
        f"Please generate ONE PNG image of an isolated front-view {obj_name} "
        f"with a transparent background, in {style} style, with shapes and style "
        "similar to the reference scene."
    )

    # Implementation for image generation API call
    return await self._call_image_generation_api(prompt, format="PNG")
```

## 🌍 Multi-Language Support

### Language Detection and Routing

```python
class PromptTemplateManager:
    """Manages standardized prompt templates with language support."""

    def __init__(self, default_language: str = "en"):
        self.default_language = default_language
        self.templates = {
            "reference_image": {
                "en": self._reference_image_en,
                "zh": self._reference_image_zh
            },
            "individual_object": {
                "en": self._individual_object_en,
                "zh": self._individual_object_zh
            }
        }

    def _reference_image_en(self, description: str, style: str) -> str:
        return (
            f"{description}. Render in {style} style. "
            "3-D view: x->right, y->backward, z->up. "
            "Well-lit, no extra objects."
        )

    def _reference_image_zh(self, description: str, style: str) -> str:
        return (
            f"{description}。使用{style}风格渲染。"
            "3D视图：x轴向右，y轴向后，z轴向上。"
            "光照良好，无额外物体。"
        )

    def _individual_object_en(self, obj_name: str, style: str) -> str:
        return (
            f"Please generate ONE PNG image of an isolated front-view {obj_name} "
            f"with a transparent background, in {style} style, with shapes and style "
            "similar to the reference scene."
        )

    def _individual_object_zh(self, obj_name: str, style: str) -> str:
        return (
            f"请生成一个孤立正面视图的{obj_name} PNG图像"
            f"具有透明背景，使用{style}风格，形状和风格"
            "与参考场景相似。"
        )

    def get_prompt(
        self,
        template_type: str,
        language: str = None,
        **kwargs
    ) -> str:
        """Get prompt template with specified language and parameters."""
        language = language or self.default_language

        if template_type not in self.templates:
            raise ValueError(f"Unknown template type: {template_type}")

        if language not in self.templates[template_type]:
            language = self.default_language  # Fallback

        template_func = self.templates[template_type][language]
        return template_func(**kwargs)
```

## 🔧 Enhanced CustomVLMClient

### Updated Implementation

```python
class CustomVLMClient:
    """Enhanced custom VLM client with standardized prompt templates."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        headers: Optional[Dict[str, str]] = None,
        language: str = "en"
    ):
        """Initialize custom VLM client with prompt template support."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.headers = headers or {}
        self.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        self.prompt_manager = PromptTemplateManager(language)

    async def generate_reference_image(
        self,
        description: str,
        style: str = "realistic"
    ) -> bytes:
        """Generate panoramic reference image using standardized template."""
        prompt = self.prompt_manager.get_prompt(
            "reference_image",
            description=description,
            style=style
        )

        # Call image generation API
        return await self._call_image_generation_api(prompt)

    async def generate_object_image(
        self,
        obj_name: str,
        style: str = "realistic",
        reference_context: Optional[str] = None
    ) -> bytes:
        """Generate isolated object image with transparent background."""
        prompt = self.prompt_manager.get_prompt(
            "individual_object",
            obj_name=obj_name,
            style=style
        )

        # Call image generation API with PNG format requirement
        return await self._call_image_generation_api(prompt, format="PNG")

    async def _call_image_generation_api(
        self,
        prompt: str,
        format: str = "PNG",
        size: str = "1024x1024"
    ) -> bytes:
        """Call the image generation API with the provided prompt."""
        # Implementation depends on the specific API
        # This is a placeholder for the actual API call

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json"
        }

        if format == "PNG":
            payload["response_format"] = "b64_json"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/images/generations",
                headers=self.headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Image generation failed: {response.status} - {error_text}")

                result = await response.json()
                image_data = result["data"][0]["b64_json"]
                return base64.b64decode(image_data)
```

## 🎯 Usage Examples

### 1. Reference Image Generation

```python
# Initialize client
vlm_client = CustomVLMClient(
    base_url="https://api.openai.com/v1",
    api_key="your-api-key",
    model_name="dall-e-3",
    language="en"
)

# Generate reference image
description = "A modern living room with sofa, coffee table, and TV"
style = "realistic"
reference_image = await vlm_client.generate_reference_image(description, style)
```

### 2. Individual Object Generation

```python
# Generate individual object image
obj_name = "modern sofa"
style = "realistic"
object_image = await vlm_client.generate_object_image(obj_name, style)

# Save as PNG with transparent background
with open("sofa_isolated.png", "wb") as f:
    f.write(object_image)
```

### 3. Chinese Language Support

```python
# Initialize client with Chinese language
vlm_client = CustomVLMClient(
    base_url="https://api.siliconflow.cn/v1",
    api_key="your-api-key",
    model_name="stable-diffusion-3",
    language="zh"
)

# Generate with Chinese prompts
description = "一个现代化的客厅，配有沙发、咖啡桌和电视"
style = "写实"
reference_image = await vlm_client.generate_reference_image(description, style)
```

## 🔧 Integration with Existing Architecture

### 1. Update UnifiedVLMClient

```python
class UnifiedVLMClient(BaseLLMClient):
    """Enhanced unified VLM client with image generation support."""

    async def generate_reference_image(
        self,
        description: str,
        style: str = "realistic"
    ) -> bytes:
        """Generate reference image using selected backend."""
        self.ensure_initialized()

        if hasattr(self._client, 'generate_reference_image'):
            return await self._client.generate_reference_image(description, style)
        else:
            raise NotImplementedError(
                f"Backend {type(self._client).__name__} does not support image generation"
            )

    async def generate_object_image(
        self,
        obj_name: str,
        style: str = "realistic"
    ) -> bytes:
        """Generate individual object image using selected backend."""
        self.ensure_initialized()

        if hasattr(self._client, 'generate_object_image'):
            return await self._client.generate_object_image(obj_name, style)
        else:
            raise NotImplementedError(
                f"Backend {type(self._client).__name__} does not support object image generation"
            )
```

### 2. Update SceneAnalyzer

```python
class SceneAnalyzer:
    """Enhanced SceneAnalyzer with image generation support."""

    async def generate_reference_image(
        self,
        session,
        style: str = "realistic"
    ) -> Path:
        """Generate panoramic reference image for the scene."""
        client = self._get_client()

        # Extract scene description from session
        description = self._build_scene_description(session)

        # Generate reference image
        image_data = await client.generate_reference_image(description, style)

        # Save to session workspace
        return self._save_image_to_workspace(session, image_data, "scene_reference.png")

    async def generate_object_card(
        self,
        obj_name: str,
        style: str = "realistic"
    ) -> Path:
        """Generate isolated object image for 3D asset generation."""
        client = self._get_client()

        # Generate object image
        image_data = await client.generate_object_image(obj_name, style)

        # Save as PNG with transparent background
        return self._save_image_to_workspace(
            session, image_data, f"{obj_name}_isolated.png"
        )
```

## 🚀 Benefits of Standardized Templates

### 1. Consistency
- **Uniform prompts** across all VLM backends
- **Consistent output format** for all generated images
- **Predictable results** with standardized instructions

### 2. Quality Improvement
- **Optimized prompts** for specific use cases
- **Better image quality** through detailed instructions
- **Reduced artifacts** with clear constraints

### 3. Flexibility
- **Multi-language support** with automatic detection
- **Backend-agnostic** implementation
- **Easy customization** for different requirements

### 4. Maintainability
- **Centralized template management**
- **Easy updates** without code changes
- **Version control** for prompt templates

## 📊 Implementation Status

### ✅ Ready for Integration
- **Template structure**: Defined and documented
- **Language support**: English and Chinese versions
- **Integration points**: Identified in existing architecture
- **Usage examples**: Provided for all scenarios

### 🔄 Next Steps
1. **Implement image generation methods** in CustomVLMClient
2. **Add API call logic** for different backends
3. **Integrate with SceneAnalyzer** for end-to-end workflow
4. **Add error handling** and fallback mechanisms
5. **Create comprehensive tests** for image generation

The standardized prompt templates are ready for integration into the unified VLM architecture! 🚀