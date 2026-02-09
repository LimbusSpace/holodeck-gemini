"""Demo script for Hunyuan Image 3.0 integration.

This script demonstrates how to use the new Hunyuan Image 3.0 client
for generating scene reference images and object cards.
"""

import os
import sys
from pathlib import Path

# Add holodeck_core to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "holodeck_core"))

from image_generation import HunyuanImageClient, generate_scene_reference, generate_object_card


def demo_scene_generation():
    """Demo scene reference image generation."""
    print("🎨 Demo: Scene Reference Generation")
    print("=" * 50)

    # Example prompts for different styles
    scene_prompts = [
        "A cozy cyberpunk bedroom with neon lights, futuristic furniture, and holographic displays",
        "A minimalist modern living room with large windows, clean lines, and natural lighting",
        "A magical forest scene with glowing mushrooms, ancient trees, and mystical atmosphere"
    ]

    for i, prompt in enumerate(scene_prompts):
        print(f"\n📝 Generating scene {i+1}: {prompt[:50]}...")

        try:
            # Generate with default style (recommended)
            result = generate_scene_reference(
                prompt=prompt,
                output_path=f"workspace/demo/scene_ref_{i+1}.png"
            )

            print(f"✅ Success! Image saved to: {result.get('local_path', 'URL only')}")
            print(f"⏱️  Generation time: {result['metadata']['generation_time_sec']}s")
            print(f"🆔 Job ID: {result['job_id']}")

        except Exception as e:
            print(f"❌ Failed: {e}")


def demo_object_card_generation():
    """Demo object card generation."""
    print("\n🎯 Demo: Object Card Generation")
    print("=" * 50)

    # Example objects with detailed descriptions
    objects = [
        {
            "name": "Cyberpunk Chair",
            "description": "Futuristic ergonomic chair with neon blue accents, metallic frame, and holographic control panel"
        },
        {
            "name": "Vintage Lamp",
            "description": "Art deco table lamp with brass finish, geometric patterns, and warm ambient lighting"
        },
        {
            "name": "Sci-fi Monitor",
            "description": "Floating holographic display with transparent screen, glowing interface, and sleek design"
        }
    ]

    for i, obj in enumerate(objects):
        print(f"\n📝 Generating object card {i+1}: {obj['name']}")

        try:
            # Generate object card with default style
            result = generate_object_card(
                object_name=obj["name"],
                description=obj["description"],
                output_path=f"workspace/demo/object_card_{i+1}.png"
            )

            print(f"✅ Success! Object card saved to: {result.get('local_path', 'URL only')}")
            print(f"⏱️  Generation time: {result['metadata']['generation_time_sec']}s")

        except Exception as e:
            print(f"❌ Failed: {e}")


def demo_style_comparison():
    """Demo different style options."""
    print("\n🎨 Demo: Style Comparison")
    print("=" * 50)

    prompt = "A futuristic robot cat with glowing eyes and metallic fur"

    # Test different approaches
    styles_to_test = [
        None,      # Default style (recommended)
        "501",     # 3D Pixar style
    ]

    for style in styles_to_test:
        style_name = "Default" if style is None else f"Style {style}"
        print(f"\n📝 Testing {style_name} style...")

        try:
            client = HunyuanImageClient(
                secret_id=os.getenv("HUNYUAN_SECRET_ID"),
                secret_key=os.getenv("HUNYUAN_SECRET_KEY")
            )

            result = client.generate_image(
                prompt=prompt,
                resolution="1024:1024",
                style=style,
                model="hunyuan-pro",
                output_path=f"workspace/demo/style_comparison_{style_name.lower().replace(' ', '_')}.png"
            )

            print(f"✅ {style_name} - Success!")
            print(f"   Generation time: {result['metadata']['generation_time_sec']}s")

        except Exception as e:
            print(f"❌ {style_name} - Failed: {e}")


def test_connection():
    """Test Hunyuan Image API connection."""
    print("🔌 Testing Hunyuan Image API Connection")
    print("=" * 50)

    try:
        client = HunyuanImageClient(
            secret_id=os.getenv("HUNYUAN_SECRET_ID"),
            secret_key=os.getenv("HUNYUAN_SECRET_KEY")
        )

        if client.test_connection():
            print("✅ Connection successful!")
            print("🚀 Hunyuan Image 3.0 is ready to use")
        else:
            print("❌ Connection failed")
            print("💡 Check your API credentials and network connection")

    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print("💡 Make sure HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY are set")


def main():
    """Main demo function."""
    print("🚀 Hunyuan Image 3.0 Integration Demo")
    print("=" * 60)
    print("This demo shows how to use Tencent Cloud Hunyuan Image 3.0")
    print("for generating high-quality images in Holodeck pipeline.\n")

    # Check if credentials are available
    if not os.getenv("HUNYUAN_SECRET_ID") or not os.getenv("HUNYUAN_SECRET_KEY"):
        print("⚠️  Warning: Hunyuan API credentials not found in environment")
        print("💡 Set HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY to run demos")
        print("\n📋 You can still review the code examples below:")
        print("-" * 60)

        # Show code examples
        print("""
# Basic usage example:
from holodeck_core.image_generation import generate_scene_reference

result = generate_scene_reference(
    prompt="A cozy cyberpunk bedroom with neon lights",
    output_path="workspace/sessions/my_session/scene_ref.png"
)

print(f"Generated image: {result['local_path']}")
print(f"Generation time: {result['metadata']['generation_time_sec']}s")

# Object card generation:
from holodeck_core.image_generation import generate_object_card

result = generate_object_card(
    object_name="Cyberpunk Chair",
    description="Futuristic chair with neon accents",
    output_path="workspace/sessions/my_session/object_cards/chair.png"
)
""")
        return

    # Run connection test first
    test_connection()

    # Ask user which demo to run
    print("\n📋 Available demos:")
    print("1. Scene Reference Generation")
    print("2. Object Card Generation")
    print("3. Style Comparison")
    print("4. Run All Demos")

    choice = input("\nEnter demo number (1-4) or 'q' to quit: ").strip()

    if choice == "1":
        demo_scene_generation()
    elif choice == "2":
        demo_object_card_generation()
    elif choice == "3":
        demo_style_comparison()
    elif choice == "4":
        demo_scene_generation()
        demo_object_card_generation()
        demo_style_comparison()
    elif choice.lower() == "q":
        print("👋 Goodbye!")
        return
    else:
        print("❌ Invalid choice")

    print("\n🎉 Demo completed!")
    print("\n📚 Next steps:")
    print("- Check generated images in workspace/demo/")
    print("- Review the HunyuanImageClient class for advanced usage")
    print("- Integrate with your Holodeck pipeline")


if __name__ == "__main__":
    main()