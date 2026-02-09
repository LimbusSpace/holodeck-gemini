"""Integration example: Using Hunyuan Image 3.0 in Holodeck pipeline.

This example shows how to integrate Hunyuan Image 3.0 generation
into the existing Holodeck workflow alongside ComfyUI.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add holodeck_core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "holodeck_core"))

from image_generation import (
    HunyuanImageClient, generate_scene_reference, generate_object_card
)
from storage import SessionManager
from schemas import SceneRequest, SceneObject


class HunyuanImageGenerator:
    """Generator class that uses Hunyuan Image 3.0 for image generation."""

    def __init__(self):
        """Initialize Hunyuan Image generator."""
        self.client = None
        self.session_manager = SessionManager()

        # Try to create client from environment
        try:
            self.client = HunyuanImageClient(
                secret_id=os.getenv("HUNYUAN_SECRET_ID"),
                secret_key=os.getenv("HUNYUAN_SECRET_KEY")
            )
            print("✅ Hunyuan Image client initialized")
        except Exception as e:
            print(f"⚠️  Failed to initialize Hunyuan client: {e}")
            print("💡 Make sure HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY are set")

    def generate_scene_reference_image(self, session_id: str, request: SceneRequest) -> Dict[str, Any]:
        """Generate scene reference image using Hunyuan Image.

        Args:
            session_id: Session identifier
            request: Scene request with prompt and style

        Returns:
            Dictionary with generation results
        """
        if not self.client:
            raise RuntimeError("Hunyuan Image client not available")

        # Build comprehensive prompt from request
        prompt = self._build_scene_prompt(request)

        # Get session directory
        session_dir = self.session_manager.get_session_dir(session_id)
        output_path = session_dir / "scene_ref.png"

        print(f"🎨 Generating scene reference with Hunyuan Image...")
        print(f"📝 Prompt: {prompt[:100]}...")

        try:
            # Generate image with default style (recommended)
            result = self.client.generate_image(
                prompt=prompt,
                resolution="1024:1024",
                style=None,  # Use default style
                model="hunyuan-pro",
                output_path=str(output_path)
            )

            print(f"✅ Scene reference generated: {output_path}")
            print(f"⏱️  Generation time: {result['metadata']['generation_time_sec']}s")

            return {
                "success": True,
                "image_path": str(output_path),
                "generation_time": result['metadata']['generation_time_sec'],
                "job_id": result['job_id'],
                "prompt_used": prompt,
                "backend": "hunyuan-image-3.0"
            }

        except Exception as e:
            print(f"❌ Scene generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "backend": "hunyuan-image-3.0"
            }

    def generate_object_cards_batch(self, session_id: str, objects: list) -> Dict[str, Any]:
        """Generate object cards for multiple objects.

        Args:
            session_id: Session identifier
            objects: List of SceneObject instances

        Returns:
            Dictionary with batch generation results
        """
        if not self.client:
            raise RuntimeError("Hunyuan Image client not available")

        session_dir = self.session_manager.get_session_dir(session_id)
        object_cards_dir = session_dir / "object_cards"
        object_cards_dir.mkdir(exist_ok=True)

        results = {
            "successful": [],
            "failed": [],
            "total_objects": len(objects),
            "backend": "hunyuan-image-3.0"
        }

        print(f"🎯 Generating {len(objects)} object cards with Hunyuan Image...")

        for i, obj in enumerate(objects):
            print(f"📝 [{i+1}/{len(objects)}] Generating: {obj.get('name', f'object_{i}')}")

            try:
                # Build object-specific prompt
                prompt = self._build_object_prompt(obj)
                object_id = obj.get('object_id', f'obj_{i}')
                output_path = object_cards_dir / f"{object_id}.png"

                result = self.client.generate_image(
                    prompt=prompt,
                    resolution="1024:1024",
                    style=None,  # Use default style
                    model="hunyuan-pro",
                    output_path=str(output_path)
                )

                results["successful"].append({
                    "object_id": object_id,
                    "object_name": obj.get('name', f'object_{i}'),
                    "card_path": str(output_path),
                    "generation_time": result['metadata']['generation_time_sec'],
                    "job_id": result['job_id']
                })

                print(f"   ✅ Generated in {result['metadata']['generation_time_sec']}s")

            except Exception as e:
                print(f"   ❌ Failed: {e}")
                results["failed"].append({
                    "object_id": obj.get('object_id', f'obj_{i}'),
                    "object_name": obj.get('name', f'object_{i}'),
                    "error": str(e)
                })

        # Calculate statistics
        results["success_rate"] = len(results["successful"]) / len(objects)
        results["total_generation_time"] = sum(
            item["generation_time"] for item in results["successful"]
        )

        print(f"\n📊 Batch generation complete:")
        print(f"   ✅ Successful: {len(results['successful'])}")
        print(f"   ❌ Failed: {len(results['failed'])}")
        print(f"   📈 Success rate: {results['success_rate']:.1%}")
        print(f"   ⏱️  Total time: {results['total_generation_time']:.2f}s")

        return results

    def _build_scene_prompt(self, request: SceneRequest) -> str:
        """Build comprehensive scene prompt from request."""
        text = request.get('text', '')
        style = request.get('style', '')

        # Enhance prompt for better results
        enhanced_prompt = text

        # Add style context if provided
        if style:
            enhanced_prompt = f"{text} in {style} style"

        # Add quality and composition hints
        enhanced_prompt +=", high quality, detailed, well-composed, professional photography"

        return enhanced_prompt

    def _build_object_prompt(self, obj: Dict[str, Any]) -> str:
        """Build object-specific prompt for card generation."""
        name = obj.get('name', 'object')
        visual_desc = obj.get('visual_desc', '')
        category = obj.get('category', '')

        # Build comprehensive object description
        prompt_parts = [f"{name}"]

        if visual_desc:
            prompt_parts.append(f"with {visual_desc}")

        if category:
            prompt_parts.append(f"({category})")

        # Add object card specific requirements
        prompt_parts.append("isolated on neutral background")
        prompt_parts.append("professional product photography")
        prompt_parts.append("high detail, sharp focus")

        return ", ".join(prompt_parts)


# Example usage functions

def example_scene_generation():
    """Example: Generate a scene reference image."""
    print("🎨 Example: Scene Reference Generation")
    print("=" * 50)

    # Create sample request
    request = {
        "session_id": "demo_session_001",
        "text": "A futuristic cyberpunk bedroom with neon lights, holographic displays, and metallic furniture",
        "style": "Cyberpunk",
        "constraints": {
            "max_objects": 15,
            "room_size_hint": [8, 6, 3]
        }
    }

    # Initialize generator
    generator = HunyuanImageGenerator()

    # Generate scene reference
    result = generator.generate_scene_reference_image(
        session_id=request["session_id"],
        request=request
    )

    if result["success"]:
        print(f"\n🎉 Scene reference generated successfully!")
        print(f"📁 Image saved to: {result['image_path']}")
        print(f"⏱️  Generation time: {result['generation_time']}s")
        print(f"🆔 Job ID: {result['job_id']}")
    else:
        print(f"❌ Generation failed: {result['error']}")


def example_object_card_generation():
    """Example: Generate object cards for scene objects."""
    print("\n🎯 Example: Object Card Generation")
    print("=" * 50)

    # Sample objects
    objects = [
        {
            "object_id": "cyber_bed",
            "name": "Cyberpunk Bed",
            "category": "furniture",
            "visual_desc": "metallic frame with neon blue LED strips, holographic control panel"
        },
        {
            "object_id": "holo_desk",
            "name": "Holographic Desk",
            "category": "furniture",
            "visual_desc": "floating transparent surface with projected interface"
        },
        {
            "object_id": "neon_lamp",
            "name": "Neon Floor Lamp",
            "category": "lighting",
            "visual_desc": "tall chrome pole with pulsating RGB neon tube"
        }
    ]

    # Initialize generator
    generator = HunyuanImageGenerator()

    # Generate object cards
    results = generator.generate_object_cards_batch(
        session_id="demo_session_001",
        objects=objects
    )

    # Display results
    print(f"\n📊 Generation Summary:")
    print(f"✅ Successful: {len(results['successful'])}/{results['total_objects']}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"📈 Success rate: {results['success_rate']:.1%}")

    if results["successful"]:
        print(f"\n🎉 Successfully generated object cards:")
        for item in results["successful"]:
            print(f"   📁 {item['object_name']}: {item['card_path']}")


def example_fallback_strategy():
    """Example: Using Hunyuan as primary with ComfyUI fallback."""
    print("\n🔄 Example: Fallback Strategy")
    print("=" * 50)

    def generate_with_fallback(prompt: str, output_path: str) -> Dict[str, Any]:
        """Try Hunyuan first, fallback to ComfyUI if needed."""

        # Try Hunyuan Image first
        try:
            generator = HunyuanImageGenerator()
            if generator.client:
                result = generator.client.generate_image(
                    prompt=prompt,
                    output_path=output_path
                )
                result["backend"] = "hunyuan-image-3.0"
                return result
        except Exception as e:
            print(f"⚠️  Hunyuan generation failed: {e}")
            print("🔄 Falling back to ComfyUI...")

        # Fallback to ComfyUI (implement as needed)
        try:
            # Here you would implement ComfyUI generation
            # For now, just indicate fallback was needed
            print("💡 ComfyUI fallback would be implemented here")
            return {
                "success": False,
                "error": "ComfyUI fallback not implemented in this example",
                "backend": "fallback-required"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Both backends failed: {e}",
                "backend": "both-failed"
            }

    # Test the fallback strategy
    prompt = "A cozy minimalist bedroom with natural wood furniture"
    result = generate_with_fallback(prompt, "workspace/demo/fallback_test.png")

    if result.get("success"):
        print(f"✅ Generation successful with {result['backend']}")
    else:
        print(f"❌ Generation failed: {result['error']}")


def main():
    """Run all integration examples."""
    print("🚀 Hunyuan Image 3.0 Integration Examples")
    print("=" * 60)
    print("These examples show how to integrate Hunyuan Image 3.0")
    print("into the Holodeck pipeline for image generation.\n")

    # Check credentials
    if not os.getenv("HUNYUAN_SECRET_ID") or not os.getenv("HUNYUAN_SECRET_KEY"):
        print("⚠️  Hunyuan API credentials not found")
        print("💡 Set HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY to run examples")
        print("\n📋 Code examples are still available for reference.")
        return

    # Run examples
    try:
        example_scene_generation()
        example_object_card_generation()
        example_fallback_strategy()

        print("\n🎉 All integration examples completed!")
        print("\n📚 Next steps:")
        print("- Integrate HunyuanImageGenerator into your pipeline")
        print("- Configure environment variables")
        print("- Test with your specific use cases")

    except Exception as e:
        print(f"❌ Example execution failed: {e}")


if __name__ == "__main__":
    main()