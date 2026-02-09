"""
Standardized Prompt Templates for VLM Integration

This module provides standardized prompt templates for VLM-based image generation,
including panoramic reference image generation and individual object image generation.
Supports multi-language prompts and backend-specific optimizations.
"""

from typing import Dict, Any, Optional


class PromptTemplateManager:
    """Manages standardized prompt templates with language support."""

    def __init__(self, default_language: str = "en"):
        """Initialize prompt template manager.

        Args:
            default_language: Default language for prompts ('en' or 'zh')
        """
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
        """English template for reference image generation."""
        return (
            f"{description}. Render in {style} style. "
            "3-D view: x->right, y->backward, z->up. "
            "Well-lit, no extra objects."
        )

    def _reference_image_zh(self, description: str, style: str) -> str:
        """Chinese template for reference image generation."""
        return (
            f"{description}。使用{style}风格渲染。"
            "3D视图：x轴向右，y轴向后，z轴向上。"
            "光照良好，无额外物体。"
        )

    def _individual_object_en(self, obj_name: str, style: str) -> str:
        """English template for individual object generation."""
        return (
            f"Please generate ONE PNG image of an isolated front-view {obj_name} "
            f"with a transparent background, in {style} style, with shapes and style "
            "similar to the reference scene."
        )

    def _individual_object_zh(self, obj_name: str, style: str) -> str:
        """Chinese template for individual object generation."""
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
        """Get prompt template with specified language and parameters.

        Args:
            template_type: Type of template ('reference_image' or 'individual_object')
            language: Language code ('en' or 'zh'), defaults to instance default
            **kwargs: Template-specific parameters

        Returns:
            Formatted prompt string

        Raises:
            ValueError: If template type or language is not supported
        """
        language = language or self.default_language

        if template_type not in self.templates:
            raise ValueError(f"Unknown template type: {template_type}")

        if language not in self.templates[template_type]:
            language = self.default_language  # Fallback

        template_func = self.templates[template_type][language]
        return template_func(**kwargs)

    def detect_language(self, text: str) -> str:
        """Detect language from text content.

        Args:
            text: Text to analyze

        Returns:
            Language code ('zh' for Chinese, 'en' for English)
        """
        # Simple detection based on character ranges
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        total_chars = len(text)

        if total_chars == 0:
            return self.default_language

        # If more than 30% of characters are Chinese, consider it Chinese text
        if chinese_chars / total_chars > 0.3:
            return "zh"
        else:
            return "en"

    def get_prompt_auto_language(
        self,
        template_type: str,
        text_context: str = "",
        **kwargs
    ) -> str:
        """Get prompt with automatic language detection.

        Args:
            template_type: Type of template
            text_context: Text context for language detection
            **kwargs: Template-specific parameters

        Returns:
            Formatted prompt string in detected language
        """
        detected_language = self.detect_language(text_context)
        return self.get_prompt(template_type, detected_language, **kwargs)


# Global template manager instance
_default_template_manager = PromptTemplateManager()


def get_reference_image_prompt(
    description: str,
    style: str = "realistic",
    language: str = None
) -> str:
    """Get standardized prompt for reference image generation.

    Args:
        description: Scene description
        style: Artistic style
        language: Language code ('en', 'zh', or None for auto-detection)

    Returns:
        Formatted prompt string
    """
    if language is None:
        language = _default_template_manager.detect_language(description)

    return _default_template_manager.get_prompt(
        "reference_image",
        language,
        description=description,
        style=style
    )


def get_object_image_prompt(
    obj_name: str,
    style: str = "realistic",
    language: str = None,
    reference_context: str = ""
) -> str:
    """Get standardized prompt for individual object image generation.

    Args:
        obj_name: Object name
        style: Artistic style
        language: Language code ('en', 'zh', or None for auto-detection)
        reference_context: Reference context for language detection

    Returns:
        Formatted prompt string
    """
    if language is None:
        text_for_detection = f"{obj_name} {reference_context}"
        language = _default_template_manager.detect_language(text_for_detection)

    return _default_template_manager.get_prompt(
        "individual_object",
        language,
        obj_name=obj_name,
        style=style
    )


# Example usage and testing
if __name__ == "__main__":
    # Test English prompts
    ref_prompt_en = get_reference_image_prompt(
        "A modern living room with sofa, coffee table, and TV",
        "realistic",
        "en"
    )
    print("English Reference Prompt:")
    print(ref_prompt_en)
    print()

    obj_prompt_en = get_object_image_prompt(
        "modern sofa",
        "realistic",
        "en"
    )
    print("English Object Prompt:")
    print(obj_prompt_en)
    print()

    # Test Chinese prompts
    ref_prompt_zh = get_reference_image_prompt(
        "一个现代化的客厅，配有沙发、咖啡桌和电视",
        "写实",
        "zh"
    )
    print("Chinese Reference Prompt:")
    print(ref_prompt_zh)
    print()

    obj_prompt_zh = get_object_image_prompt(
        "现代沙发",
        "写实",
        "zh"
    )
    print("Chinese Object Prompt:")
    print(obj_prompt_zh)
    print()

    # Test auto-detection
    auto_prompt = get_reference_image_prompt(
        "A modern living room with sofa, coffee table, and TV"
    )
    print("Auto-detected Prompt:")
    print(auto_prompt)