"""
Tests for standardized prompt templates.
"""

import pytest
from holodeck_core.scene_analysis.prompt_templates import (
    PromptTemplateManager,
    get_reference_image_prompt,
    get_object_image_prompt
)


class TestPromptTemplateManager:
    """Test PromptTemplateManager functionality."""

    def test_english_reference_template(self):
        """Test English reference image template."""
        manager = PromptTemplateManager()
        prompt = manager.get_prompt(
            "reference_image",
            "en",
            description="A modern living room",
            style="realistic"
        )

        expected = (
            "A modern living room. Render in realistic style. "
            "3-D view: x->right, y->backward, z->up. "
            "Well-lit, no extra objects."
        )
        assert prompt == expected

    def test_chinese_reference_template(self):
        """Test Chinese reference image template."""
        manager = PromptTemplateManager()
        prompt = manager.get_prompt(
            "reference_image",
            "zh",
            description="一个现代化的客厅",
            style="写实"
        )

        expected = (
            "一个现代化的客厅。使用写实风格渲染。"
            "3D视图：x轴向右，y轴向后，z轴向上。"
            "光照良好，无额外物体。"
        )
        assert prompt == expected

    def test_english_object_template(self):
        """Test English object image template."""
        manager = PromptTemplateManager()
        prompt = manager.get_prompt(
            "individual_object",
            "en",
            obj_name="modern sofa",
            style="realistic"
        )

        expected = (
            "Please generate ONE PNG image of an isolated front-view modern sofa "
            "with a transparent background, in realistic style, with shapes and style "
            "similar to the reference scene."
        )
        assert prompt == expected

    def test_chinese_object_template(self):
        """Test Chinese object image template."""
        manager = PromptTemplateManager()
        prompt = manager.get_prompt(
            "individual_object",
            "zh",
            obj_name="现代沙发",
            style="写实"
        )

        expected = (
            "请生成一个孤立正面视图的现代沙发 PNG图像"
            "具有透明背景，使用写实风格，形状和风格"
            "与参考场景相似。"
        )
        assert prompt == expected

    def test_language_detection_english(self):
        """Test language detection for English text."""
        manager = PromptTemplateManager()
        detected = manager.detect_language("This is an English text")
        assert detected == "en"

    def test_language_detection_chinese(self):
        """Test language detection for Chinese text."""
        manager = PromptTemplateManager()
        detected = manager.detect_language("这是一个中文文本")
        assert detected == "zh"

    def test_auto_language_detection(self):
        """Test automatic language detection in prompts."""
        manager = PromptTemplateManager()

        # English text should use English template
        prompt_en = manager.get_prompt_auto_language(
            "reference_image",
            "A modern living room",
            description="A modern living room",
            style="realistic"
        )
        assert "3-D view: x->right" in prompt_en

        # Chinese text should use Chinese template
        prompt_zh = manager.get_prompt_auto_language(
            "reference_image",
            "一个现代化的客厅",
            description="一个现代化的客厅",
            style="写实"
        )
        assert "3D视图：x轴向右" in prompt_zh

    def test_invalid_template_type(self):
        """Test error handling for invalid template type."""
        manager = PromptTemplateManager()
        with pytest.raises(ValueError, match="Unknown template type"):
            manager.get_prompt("invalid_template", "en")

    def test_invalid_language_fallback(self):
        """Test fallback to default language for invalid language."""
        manager = PromptTemplateManager(default_language="en")
        prompt = manager.get_prompt(
            "reference_image",
            "invalid_lang",
            description="test",
            style="test"
        )
        # Should fallback to English
        assert "3-D view: x->right" in prompt


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_reference_image_prompt(self):
        """Test global reference image prompt function."""
        prompt = get_reference_image_prompt(
            "A modern living room",
            "realistic",
            "en"
        )
        assert "A modern living room. Render in realistic style." in prompt

    def test_get_object_image_prompt(self):
        """Test global object image prompt function."""
        prompt = get_object_image_prompt(
            "modern sofa",
            "realistic",
            "en"
        )
        assert "modern sofa" in prompt
        assert "transparent background" in prompt

    def test_auto_detection_in_global_functions(self):
        """Test auto-detection in global functions."""
        # English text
        prompt_en = get_reference_image_prompt("A modern living room")
        assert "3-D view: x->right" in prompt_en

        # Chinese text
        prompt_zh = get_reference_image_prompt("一个现代化的客厅")
        assert "3D视图：x轴向右" in prompt_zh


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])