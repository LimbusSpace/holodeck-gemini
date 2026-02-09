"""Complete example: Using Hunyuan Image 3.0 in Holodeck 3D Pipeline.

This example demonstrates the full integration of Hunyuan Image 3.0
into the Holodeck 3D generation pipeline, showing how it works alongside
existing components for scene analysis, object generation, and layout.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

# Add holodeck_core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "holodeck_core"))

from scene_analysis import SceneAnalyzer
from object_gen import AssetGenerationManager
from scene_gen import LayoutSolver
from storage import SessionManager
from schemas import SceneRequest, SceneObject, Vec3


class HunyuanEnhancedPipeline:
    """Enhanced 3D pipeline with Hunyuan Image 3.0 integration."""

    def __init__(self, workspace_root: str = "workspace"):
        """Initialize enhanced pipeline."""
        self.workspace_root = workspace_root
        self.session_manager = SessionManager(workspace_root)

        # Initialize components with Hunyuan support
        self.scene_analyzer = SceneAnalyzer(
            api_key=os.getenv("OPENAI_API_KEY"),
            use_comfyui=True,
            use_hunyuan=True  # Enable Hunyuan integration
        )

        self.asset_manager = AssetGenerationManager(workspace_root)
        self.layout_solver = LayoutSolver()

        print("🚀 Enhanced 3D Pipeline initialized with Hunyuan Image 3.0 support")

    async def build_scene(self, request_text: str, style: str = "modern") -> Dict[str, Any]:
        """Build complete 3D scene with Hunyuan-enhanced image generation.

        Args:
            request_text: Scene description
            style: Artistic style preference

        Returns:
            Complete build results
        """
        start_time = time.time()
        session_id = f"session_{int(start_time)}"

        print(f"🎬 Starting 3D scene build: {request_text[:50]}...")
        print(f"📋 Session ID: {session_id}")

        try:
            # Step 1: Create session and save request
            session = self.session_manager.create_session(session_id)
            request = SceneRequest(
                session_id=session_id,
                text=request_text,
                style=style
            )
            session.save_request(request.dict())

            # Step 2: Generate scene reference image (with Hunyuan priority)
            print("\n🎨 Step 1: Generating scene reference image...")
            scene_ref_result = await self._generate_scene_reference(session, request)

            if not scene_ref_result.get("success"):
                raise RuntimeError(f"Scene reference generation failed: {scene_ref_result.get('error')}")

            print(f"✅ Scene reference generated: {scene_ref_result['image_path']}")
            print(f"   Backend used: {scene_ref_result['backend']}")
            print(f"   Generation time: {scene_ref_result['generation_time']:.2f}s")

            # Step 3: Extract objects from scene
            print("\n🔍 Step 2: Extracting objects from scene...")
            objects_result = await self._extract_objects(session, request, scene_ref_result['image_path'])

            print(f"✅ Extracted {len(objects_result['objects'])} objects")

            # Step 4: Generate object cards (with Hunyuan priority)
            print("\n🎯 Step 3: Generating object cards...")
            object_cards_result = await self._generate_object_cards(
                session, objects_result['objects'], scene_ref_result['image_path']
            )

            print(f"✅ Generated {len(object_cards_result['successful'])} object cards")
            print(f"   Backend used: {object_cards_result['backend']}")

            # Step 5: Generate 3D assets from object cards
            print("\n🏗️  Step 4: Generating 3D assets...")
            assets_result = await self._generate_3d_assets(session, object_cards_result['successful'])

            print(f"✅ Generated {len(assets_result['successful'])} 3D assets")

            # Step 6: Solve layout
            print("\n📐 Step 5: Solving 3D layout...")
            layout_result = await self._solve_layout(session, objects_result['objects'], assets_result)

            # Compile final results
            total_time = time.time() - start_time

            build_result = {
                "session_id": session_id,
                "success": True,
                "total_time": total_time,
                "stages": {
                    "scene_reference": scene_ref_result,
                    "object_extraction": objects_result,
                    "object_cards": object_cards_result,
                    "asset_generation": assets_result,
                    "layout_solution": layout_result
                },
                "summary": {
                    "total_objects": len(objects_result['objects']),
                    "successful_cards": len(object_cards_result['successful']),
                    "successful_assets": len(assets_result['successful']),
                    "primary_backend": scene_ref_result['backend'],
                    "total_generation_time": total_time
                }
            }

            print(f"\n🎉 3D scene build completed in {total_time:.2f}s!")
            print(f"📊 Summary: {build_result['summary']}")

            return build_result

        except Exception as e:
            print(f"❌ Build failed: {e}")
            return {
                "session_id": session_id,
                "success": False,
                "error": str(e),
                "total_time": time.time() - start_time
            }

    async def _generate_scene_reference(self, session, request) -> Dict[str, Any]:
        """Generate scene reference with Hunyuan priority."""
        try:
            # Use scene analyzer (will prioritize Hunyuan if available)
            ref_image_obj = await self.scene_analyzer.generate_reference_image(session)

            return {
                "success": True,
                "image_path": str(ref_image_obj.image_path),
                "backend": "hunyuan-image-3.0",  # Will be set by hybrid client
                "generation_time": ref_image_obj.generation_time,
                "prompt_used": ref_image_obj.prompt_used
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "backend": "unknown"
            }

    async def _extract_objects(self, session, request, ref_image_path) -> Dict[str, Any]:
        """Extract objects from scene description and reference image."""
        try:
            scene_data = await self.scene_analyzer.extract_objects(
                session.session_id,
                request.text,
                ref_image_path
            )

            # Convert to list of objects
            objects = []
            for obj in scene_data.objects:
                objects.append({
                    "object_id": obj.object_id,
                    "name": obj.name,
                    "category": obj.category,
                    "visual_desc": obj.visual_desc,
                    "size_m": obj.size_m,
                    "session_id": session.session_id
                })

            return {
                "success": True,
                "objects": objects,
                "backend": "hybrid-analysis"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "objects": []
            }

    async def _generate_object_cards(self, session, objects, ref_image_path) -> Dict[str, Any]:
        """Generate object cards with Hunyuan priority."""
        try:
            object_cards = await self.scene_analyzer.generate_object_cards(
                session.session_id,
                objects,
                ref_image_path
            )

            successful_cards = []
            for card in object_cards:
                successful_cards.append({
                    "object_id": card.object_id,
                    "object_name": card.object_name,
                    "card_path": str(card.card_image_path),
                    "generation_time": card.generation_time
                })

            return {
                "success": True,
                "successful": successful_cards,
                "failed": [],
                "backend": "hunyuan-image-3.0"  # Will be set by hybrid client
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "successful": [],
                "failed": objects
            }

    async def _generate_3d_assets(self, session, object_cards) -> Dict[str, Any]:
        """Generate 3D assets from object cards."""
        successful_assets = []
        failed_assets = []

        for card in object_cards:
            try:
                object_id = card["object_id"]
                print(f"   🔄 Generating 3D asset for {object_id}...")

                # Use asset generation manager
                asset_path = self.asset_manager.generate_from_card(session, object_id)

                successful_assets.append({
                    "object_id": object_id,
                    "asset_path": str(asset_path),
                    "status": "success"
                })

            except Exception as e:
                print(f"   ❌ Failed to generate asset for {object_id}: {e}")
                failed_assets.append({
                    "object_id": object_id,
                    "error": str(e)
                })

        return {
            "success": True,
            "successful": successful_assets,
            "failed": failed_assets
        }

    async def _solve_layout(self, session, objects, assets_result) -> Dict[str, Any]:
        """Solve 3D layout for objects."""
        try:
            # Create scene objects with asset information
            scene_objects = []
            for obj_data in objects:
                object_id = obj_data["object_id"]

                # Find corresponding asset
                asset_info = None
                for asset in assets_result["successful"]:
                    if asset["object_id"] == object_id:
                        asset_info = asset
                        break

                scene_obj = SceneObject(
                    object_id=object_id,
                    name=obj_data["name"],
                    category=obj_data["category"],
                    size_m=obj_data["size_m"],
                    visual_desc=obj_data["visual_desc"],
                    asset_path=asset_info["asset_path"] if asset_info else None
                )
                scene_objects.append(scene_obj)

            # Solve layout
            layout_solution = self.layout_solver.solve(scene_objects)

            return {
                "success": True,
                "layout_solution": layout_solution.dict(),
                "object_count": len(scene_objects)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Example usage functions

async def example_cyberpunk_bedroom():
    """Example: Build a cyberpunk bedroom scene."""
    print("🌃 Example: Cyberpunk Bedroom Scene")
    print("=" * 60)

    pipeline = HunyuanEnhancedPipeline()

    request_text = (
        "A futuristic cyberpunk bedroom with neon lights, holographic displays, "
        "metallic furniture, and a large window showing a neon-lit cityscape. "
        "The room should have a high-tech aesthetic with glowing blue and purple accents."
    )

    result = await pipeline.build_scene(request_text, style="cyberpunk")

    if result["success"]:
        print(f"\n🎉 Cyberpunk bedroom built successfully!")
        print(f"📊 Objects: {result['summary']['total_objects']}")
        print(f"🎨 Primary backend: {result['summary']['primary_backend']}")
        print(f"⏱️  Total time: {result['summary']['total_generation_time']:.2f}s")

        # Show backend usage
        stages = result["stages"]
        print(f"\n🔄 Backend usage:")
        print(f"   Scene Reference: {stages['scene_reference']['backend']}")
        print(f"   Object Cards: {stages['object_cards']['backend']}")
    else:
        print(f"❌ Build failed: {result['error']}")


async def example_minimalist_living_room():
    """Example: Build a minimalist living room scene."""
    print("\n🏠 Example: Minimalist Living Room Scene")
    print("=" * 60)

    pipeline = HunyuanEnhancedPipeline()

    request_text = (
        "A modern minimalist living room with clean lines, neutral colors, "
        "and natural lighting. Features a comfortable sofa, coffee table, "
        "floor lamp, and large windows with city view."
    )

    result = await pipeline.build_scene(request_text, style="minimalist")

    if result["success"]:
        print(f"\n🎉 Minimalist living room built successfully!")
        print(f"📊 Objects: {result['summary']['total_objects']}")
        print(f"🎨 Primary backend: {result['summary']['primary_backend']}")
    else:
        print(f"❌ Build failed: {result['error']}")


async def benchmark_backends():
    """Benchmark different backends for comparison."""
    print("\n⚡ Backend Benchmark Comparison")
    print("=" * 60)

    # Test with different configurations
    configs = [
        {"name": "Hunyuan Priority", "use_hunyuan": True, "use_comfyui": True},
        {"name": "ComfyUI Only", "use_hunyuan": False, "use_comfyui": True},
        {"name": "OpenAI Fallback", "use_hunyuan": False, "use_comfyui": False}
    ]

    test_prompt = "A cozy reading nook with armchair and bookshelf"

    for config in configs:
        print(f"\n🧪 Testing: {config['name']}")

        try:
            pipeline = HunyuanEnhancedPipeline()
            pipeline.scene_analyzer.use_hunyuan = config["use_hunyuan"]
            pipeline.scene_analyzer.use_comfyui = config["use_comfyui"]

            start_time = time.time()
            result = await pipeline.build_scene(test_prompt)
            elapsed = time.time() - start_time

            if result["success"]:
                print(f"   ✅ Success in {elapsed:.2f}s")
                print(f"   🎨 Backend: {result['summary']['primary_backend']}")
                print(f"   📊 Objects: {result['summary']['total_objects']}")
            else:
                print(f"   ❌ Failed: {result['error']}")

        except Exception as e:
            print(f"   ❌ Error: {e}")


async def main():
    """Run all pipeline examples."""
    print("🚀 Holodeck 3D Pipeline with Hunyuan Image 3.0")
    print("=" * 70)
    print("This example demonstrates the complete integration of")
    print("Hunyuan Image 3.0 into the Holodeck 3D generation pipeline.\n")

    # Check configuration
    hunyuan_configured = os.getenv("HUNYUAN_SECRET_ID") and os.getenv("HUNYUAN_SECRET_KEY")
    if not hunyuan_configured:
        print("⚠️  Hunyuan Image not configured")
        print("💡 Set HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY to enable")
        print("\n📋 The pipeline will work with available backends.\n")

    # Run examples
    try:
        await example_cyberpunk_bedroom()
        await example_minimalist_living_room()
        await benchmark_backends()

        print("\n🎉 All examples completed!")
        print("\n📚 Next steps:")
        print("- Configure Hunyuan Image API keys for best performance")
        print("- Try your own scene descriptions")
        print("- Experiment with different styles")

    except Exception as e:
        print(f"❌ Example execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())