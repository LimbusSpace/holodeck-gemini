"""Example: Using Hunyuan 3D integration in Holodeck pipeline.

This example demonstrates how to use the integrated Hunyuan 3D API
alongside the existing SF3D backend for 3D asset generation.
"""

import asyncio
import os
import sys
import time
from pathlib import Path

# Add holodeck_core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "holodeck_core"))

from object_gen import AssetGenerationManager, Hunyuan3DClient
from scene_analysis import SceneAnalyzer
from storage import SessionManager
from schemas import SceneRequest, Vec3


async def example_hunyuan_priority():
    """Example: Use Hunyuan 3D with priority, fallback to SF3D."""
    print("🚀 Example: Hunyuan 3D Priority Mode")
    print("=" * 50)

    # Initialize asset manager with Hunyuan priority
    asset_manager = AssetGenerationManager(
        workspace_root="workspace",
        backend_priority="hunyuan",  # Try Hunyuan first
        use_hunyuan_3d=True
    )

    session_id = f"session_{int(time.time())}"
    session_manager = SessionManager("workspace")
    session = session_manager.create_session(session_id)

    # Example object card path (you would use real object cards from scene analysis)
    object_card_path = "path/to/object_card.png"  # Replace with actual path
    object_id = "example_chair"

    if not Path(object_card_path).exists():
        print(f"⚠️  Object card not found: {object_card_path}")
        print("💡 Create a test object card or use existing one")
        return

    try:
        # Generate 3D asset
        asset_metadata = await asset_manager.generate_asset(
            session_id=session_id,
            object_card_path=object_card_path,
            object_id=object_id,
            target_size_m=Vec3(x=0.5, y=0.8, z=0.5)  # Chair size
        )

        print(f"✅ Asset generated successfully!")
        print(f"📁 GLB path: {asset_metadata.glb_path}")
        print(f"🏭 Backend: {asset_metadata.model_name}")
        print(f"⏱️  Generation time: {asset_metadata.generation_time_sec:.2f}s")
        print(f"📊 File size: {asset_metadata.file_size_mb:.2f} MB")

        # Check which backend was used
        backend = asset_metadata.generation_parameters.get("backend", "unknown")
        print(f"🔧 Backend used: {backend}")

        if backend == "hunyuan-3d":
            job_id = asset_metadata.generation_parameters.get("hunyuan_job_id")
            print(f"🎫 Hunyuan Job ID: {job_id}")

    except Exception as e:
        print(f"❌ Generation failed: {e}")


async def example_sf3d_only():
    """Example: Use SF3D only (disable Hunyuan)."""
    print("\n🏭 Example: SF3D Only Mode")
    print("=" * 50)

    # Initialize asset manager with SF3D only
    asset_manager = AssetGenerationManager(
        workspace_root="workspace",
        backend_priority="sf3d",  # SF3D only
        use_hunyuan_3d=False
    )

    session_id = f"session_{int(time.time())}"
    session_manager = SessionManager("workspace")
    session = session_manager.create_session(session_id)

    # Example object card path
    object_card_path = "path/to/object_card.png"  # Replace with actual path
    object_id = "example_table"

    if not Path(object_card_path).exists():
        print(f"⚠️  Object card not found: {object_card_path}")
        return

    try:
        # Generate 3D asset
        asset_metadata = await asset_manager.generate_asset(
            session_id=session_id,
            object_card_path=object_card_path,
            object_id=object_id,
            target_size_m=Vec3(x=1.2, y=0.75, z=0.8)  # Table size
        )

        print(f"✅ Asset generated successfully!")
        print(f"📁 GLB path: {asset_metadata.glb_path}")
        print(f"🏭 Backend: {asset_metadata.model_name}")
        print(f"⏱️  Generation time: {asset_metadata.generation_time_sec:.2f}s")

    except Exception as e:
        print(f"❌ Generation failed: {e}")


async def example_auto_mode():
    """Example: Auto-select backend based on availability."""
    print("\n🤖 Example: Auto Mode (Smart Selection)")
    print("=" * 50)

    # Initialize asset manager with auto mode
    asset_manager = AssetGenerationManager(
        workspace_root="workspace",
        backend_priority="auto",  # Auto-select based on availability
        use_hunyuan_3d=True
    )

    session_id = f"session_{int(time.time())}"
    session_manager = SessionManager("workspace")
    session = session_manager.create_session(session_id)

    # Example object card path
    object_card_path = "path/to/object_card.png"  # Replace with actual path
    object_id = "example_lamp"

    if not Path(object_card_path).exists():
        print(f"⚠️  Object card not found: {object_card_path}")
        return

    try:
        # Generate 3D asset
        asset_metadata = await asset_manager.generate_asset(
            session_id=session_id,
            object_card_path=object_card_path,
            object_id=object_id,
            target_size_m=Vec3(x=0.3, y=0.6, z=0.3)  # Lamp size
        )

        print(f"✅ Asset generated successfully!")
        print(f"📁 GLB path: {asset_metadata.glb_path}")
        print(f"🏭 Backend: {asset_metadata.model_name}")
        print(f"⏱️  Generation time: {asset_metadata.generation_time_sec:.2f}s")

        # Check which backend was automatically selected
        backend = asset_metadata.generation_parameters.get("backend", "unknown")
        print(f"🔧 Auto-selected backend: {backend}")

    except Exception as e:
        print(f"❌ Generation failed: {e}")


def example_direct_hunyuan_client():
    """Example: Use Hunyuan3DClient directly for custom workflows."""
    print("\n🔧 Example: Direct Hunyuan3DClient Usage")
    print("=" * 50)

    # Check if Hunyuan credentials are configured
    secret_id = os.getenv('HUNYUAN_SECRET_ID')
    secret_key = os.getenv('HUNYUAN_SECRET_KEY')

    if not secret_id or not secret_key:
        print("⚠️  Hunyuan credentials not configured")
        print("💡 Set HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY environment variables")
        return

    # Create Hunyuan 3D client directly
    hunyuan_client = Hunyuan3DClient(secret_id, secret_key)

    # Test connection
    if not hunyuan_client.test_connection():
        print("❌ Failed to connect to Hunyuan 3D API")
        return

    print("✅ Connected to Hunyuan 3D API")

    # Example image path
    image_path = "path/to/test_image.png"  # Replace with actual path

    if not Path(image_path).exists():
        print(f"⚠️  Test image not found: {image_path}")
        return

    try:
        # Generate 3D from image
        result = hunyuan_client.generate_3d_from_image(
            image_path=image_path,
            task_id="direct_test",
            output_dir="output_3d"
        )

        if result.success:
            print(f"✅ 3D generation successful!")
            print(f"🎫 Job ID: {result.job_id}")
            print(f"📁 Model files: {result.local_paths}")
            print(f"⏱️  Generation time: {result.generation_time:.2f}s")
        else:
            print(f"❌ Generation failed: {result.error_message}")

    except Exception as e:
        print(f"❌ Error: {e}")


async def example_batch_generation():
    """Example: Batch generation with different backends."""
    print("\n📦 Example: Batch Generation Comparison")
    print("=" * 50)

    # Test configurations
    configs = [
        {"name": "Hunyuan Priority", "priority": "hunyuan", "use_hunyuan": True},
        {"name": "SF3D Only", "priority": "sf3d", "use_hunyuan": False},
        {"name": "Auto Mode", "priority": "auto", "use_hunyuan": True}
    ]

    test_image = "path/to/test_image.png"  # Replace with actual path

    if not Path(test_image).exists():
        print(f"⚠️  Test image not found: {test_image}")
        return

    for config in configs:
        print(f"\n🧪 Testing: {config['name']}")

        try:
            asset_manager = AssetGenerationManager(
                workspace_root="workspace",
                backend_priority=config["priority"],
                use_hunyuan_3d=config["use_hunyuan"]
            )

            session_id = f"batch_test_{config['priority']}_{int(time.time())}"

            start_time = time.time()
            asset_metadata = await asset_manager.generate_asset(
                session_id=session_id,
                object_card_path=test_image,
                object_id=f"test_{config['priority']}"
            )
            elapsed = time.time() - start_time

            if asset_metadata.generation_status == "success":
                backend = asset_metadata.generation_parameters.get("backend", "unknown")
                print(f"   ✅ Success in {elapsed:.2f}s")
                print(f"   🏭 Backend: {backend}")
                print(f"   📁 Size: {asset_metadata.file_size_mb:.2f} MB")
            else:
                print(f"   ❌ Failed: {asset_metadata.error_message}")

        except Exception as e:
            print(f"   ❌ Error: {e}")


async def main():
    """Run all examples."""
    print("🚀 Hunyuan 3D Integration Examples")
    print("=" * 60)
    print("This example demonstrates the integration of Hunyuan 3D API")
    print("with the existing Holodeck 3D generation pipeline.\n")

    # Check configuration
    hunyuan_configured = os.getenv("HUNYUAN_SECRET_ID") and os.getenv("HUNYUAN_SECRET_KEY")
    if not hunyuan_configured:
        print("⚠️  Hunyuan 3D not fully configured")
        print("💡 Set HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY for full functionality")
        print("📋 Examples will work with available backends\n")

    # Run examples
    try:
        await example_hunyuan_priority()
        await example_sf3d_only()
        await example_auto_mode()
        example_direct_hunyuan_client()
        await example_batch_generation()

        print("\n🎉 All examples completed!")
        print("\n📚 Key features demonstrated:")
        print("• Multiple backend support (Hunyuan 3D + SF3D)")
        print("• Configurable backend priority")
        print("• Automatic fallback mechanisms")
        print("• Direct client usage")
        print("• Batch generation comparison")

    except Exception as e:
        print(f"❌ Example execution failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())