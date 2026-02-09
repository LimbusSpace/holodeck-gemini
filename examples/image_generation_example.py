"""
Example demonstrating the standardized prompt templates for image generation
using the UnifiedVLMClient with multi-language support.
"""

import asyncio
import os
from pathlib import Path

# Add the project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend


async def main():
    """Demonstrate image generation with standardized prompts."""
    print("=== UnifiedVLMClient Image Generation Example ===\n")

    # Initialize client with auto backend selection
    client = UnifiedVLMClient(backend=VLMBackend.AUTO)

    try:
        # Test connection
        print("Testing connection...")
        if await client.test_connection():
            print("✅ Connection successful\n")
        else:
            print("❌ Connection failed")
            return

        # Example 1: English reference image generation
        print("1. Generating English reference image...")
        description_en = "A modern living room with sofa, coffee table, and TV"
        style_en = "realistic"

        try:
            reference_image_en = await client.generate_reference_image(
                description=description_en,
                style=style_en,
                language="en"
            )
            print(f"✅ Generated reference image ({len(reference_image_en)} bytes)")

            # Save image
            with open("reference_image_en.png", "wb") as f:
                f.write(reference_image_en)
            print("✅ Saved as 'reference_image_en.png'\n")

        except Exception as e:
            print(f"❌ Reference image generation failed: {e}\n")

        # Example 2: Chinese reference image generation
        print("2. Generating Chinese reference image...")
        description_zh = "一个现代化的客厅，配有沙发、咖啡桌和电视"
        style_zh = "写实"

        try:
            reference_image_zh = await client.generate_reference_image(
                description=description_zh,
                style=style_zh,
                language="zh"
            )
            print(f"✅ Generated reference image ({len(reference_image_zh)} bytes)")

            # Save image
            with open("reference_image_zh.png", "wb") as f:
                f.write(reference_image_zh)
            print("✅ Saved as 'reference_image_zh.png'\n")

        except Exception as e:
            print(f"❌ Reference image generation failed: {e}\n")

        # Example 3: English object image generation
        print("3. Generating English object image...")
        obj_name_en = "modern sofa"
        style_obj_en = "realistic"

        try:
            object_image_en = await client.generate_object_image(
                obj_name=obj_name_en,
                style=style_obj_en,
                language="en",
                reference_context=description_en
            )
            print(f"✅ Generated object image ({len(object_image_en)} bytes)")

            # Save image
            with open("sofa_isolated_en.png", "wb") as f:
                f.write(object_image_en)
            print("✅ Saved as 'sofa_isolated_en.png'\n")

        except Exception as e:
            print(f"❌ Object image generation failed: {e}\n")

        # Example 4: Chinese object image generation
        print("4. Generating Chinese object image...")
        obj_name_zh = "现代沙发"
        style_obj_zh = "写实"

        try:
            object_image_zh = await client.generate_object_image(
                obj_name=obj_name_zh,
                style=style_obj_zh,
                language="zh",
                reference_context=description_zh
            )
            print(f"✅ Generated object image ({len(object_image_zh)} bytes)")

            # Save image
            with open("sofa_isolated_zh.png", "wb") as f:
                f.write(object_image_zh)
            print("✅ Saved as 'sofa_isolated_zh.png'\n")

        except Exception as e:
            print(f"❌ Object image generation failed: {e}\n")

        # Example 5: Auto-language detection
        print("5. Testing auto-language detection...")

        # English text should auto-detect as English
        auto_image_en = await client.generate_reference_image(
            description="A cozy bedroom with bed and nightstand",
            style="realistic"
            # language=None (auto-detection)
        )
        print(f"✅ Auto-detected English: {len(auto_image_en)} bytes")

        # Chinese text should auto-detect as Chinese
        auto_image_zh = await client.generate_reference_image(
            description="一个舒适的卧室，配有床和床头柜",
            style="写实"
            # language=None (auto-detection)
        )
        print(f"✅ Auto-detected Chinese: {len(auto_image_zh)} bytes")

        print("\n=== Example completed successfully! ===")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())