#!/usr/bin/env python3
"""Generate a Gothic-style wardrobe using Hunyuan 3D."""

import os
import sys
import time
from pathlib import Path

# Load environment variables
def load_env_file():
    """Load environment variables from .env file."""
    env_paths = [
        Path(".env"),
        Path(__file__).parent / ".env",
        Path.home() / ".env"
    ]

    for env_path in env_paths:
        if env_path.exists():
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip().strip('"\'')
                print(f"Loaded environment from {env_path}")
                break
            except Exception as e:
                print(f"Failed to load {env_path}: {e}")

load_env_file()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "holodeck_core"))

from holodeck_core.object_gen.hunyuan_3d_client import Hunyuan3DClient, Hunyuan3DTask

def generate_gothic_wardrobe():
    """Generate a Gothic-style wardrobe."""
    print("[GOTHIC] Generating Gothic-style Wardrobe")
    print("=" * 60)

    # Check environment variables
    secret_id = os.getenv("HUNYUAN_SECRET_ID")
    secret_key = os.getenv("HUNYUAN_SECRET_KEY")

    if not secret_id or not secret_key:
        print("[ERROR] HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY not set")
        print("Please check your .env file")
        return False

    try:
        # Initialize client with Pro version for best quality
        print("[INIT] Initializing Hunyuan 3D client...")
        client = Hunyuan3DClient(
            secret_id=secret_id,
            secret_key=secret_key,
            use_pro_version=True,  # Use Pro for best quality
            timeout=900,  # 15 minutes timeout for complex model
            poll_interval=5  # Check status every 5 seconds
        )
        print("[OK] Client initialized successfully")

        # Test connection
        print("[TEST] Testing API connection...")
        if not client.test_connection():
            print("[FAIL] API connection failed")
            return False
        print("[OK] API connection successful")

        # Create task with detailed Gothic wardrobe description
        print("[TASK] Creating generation task...")
        task = Hunyuan3DTask(
            task_id=f"gothic_wardrobe_{int(time.time())}",
            prompt="""
A detailed Gothic-style wardrobe with the following characteristics:
- Tall, ornate wooden cabinet with intricate Gothic carvings
- Pointed arches and spires typical of Gothic architecture
- Dark wood texture with ornate metal handles and hinges
- Detailed Gothic patterns and decorative elements
- Stained glass-style decorative panels
- Medieval Gothic furniture style
- Rich, dark color palette typical of Gothic design
- Intricate scrollwork and Gothic ornamental details
- Double doors with Gothic arch design
- Suitable for medieval or Gothic interior decoration
            """.strip(),
            output_dir="gothic_models",
            enable_pbr=True,  # Enable PBR for realistic materials
            result_format="GLB"  # Use GLB format for best compatibility
        )

        print(f"[INFO] Task created:")
        print(f"   Task ID: {task.task_id}")
        print(f"   Output directory: {task.output_dir}")
        print(f"   PBR enabled: {task.enable_pbr}")
        print(f"   Format: {task.result_format}")

        # Start generation
        print("\n[START] Starting 3D generation...")
        print("[WAIT] This may take several minutes...")

        start_time = time.time()
        result = client.generate_3d_from_task(task)
        total_time = time.time() - start_time

        # Check results
        if result.success:
            print(f"\n[SUCCESS] Generation successful!")
            print(f"[STATS] Statistics:")
            print(f"   Total time: {total_time:.2f} seconds")
            print(f"   Generation time: {result.generation_time:.2f} seconds")
            print(f"   Job ID: {result.job_id}")

            print(f"[FILES] Generated files:")
            for i, path in enumerate(result.local_paths, 1):
                file_size = Path(path).stat().st_size if Path(path).exists() else 0
                print(f"   {i}. {path} ({file_size:,} bytes)")

            print(f"\n[INFO] Next steps:")
            print(f"   - Check the generated GLB file in '{task.output_dir}' directory")
            print(f"   - Use a 3D viewer to examine the Gothic wardrobe")
            print(f"   - The model is ready for use in 3D scenes or games")

            return True
        else:
            print(f"\n[FAIL] Generation failed: {result.error_message}")
            print(f"[TIPS] Troubleshooting tips:")
            print(f"   - Check your API quota and credentials")
            print(f"   - Try a simpler prompt if the model is too complex")
            print(f"   - Ensure stable internet connection")
            print(f"   - Try again with Rapid version for faster results")
            return False

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_gothic_wardrobe_rapid():
    """Generate a Gothic-style wardrobe using Rapid version for quick preview."""
    print("[GOTHIC-RAPID] Generating Gothic-style Wardrobe (Rapid Preview)")
    print("=" * 60)

    try:
        # Initialize client with Rapid version for quick preview
        client = Hunyuan3DClient(
            secret_id=os.getenv("HUNYUAN_SECRET_ID"),
            secret_key=os.getenv("HUNYUAN_SECRET_KEY"),
            use_pro_version=False,  # Use Rapid for quick preview
            timeout=300,  # 5 minutes timeout
            poll_interval=3
        )

        # Simpler prompt for rapid generation
        task = Hunyuan3DTask(
            task_id=f"gothic_wardrobe_rapid_{int(time.time())}",
            prompt="A Gothic-style wooden wardrobe with pointed arches and ornate details",
            output_dir="gothic_models_rapid",
            enable_pbr=True,
            result_format="GLB"
        )

        print("⚡ Generating rapid preview...")
        result = client.generate_3d_from_task(task)

        if result.success:
            print(f"[OK] Rapid preview generated successfully!")
            print(f"   Files: {result.local_paths}")
            print(f"   Time: {result.generation_time:.2f} seconds")
        else:
            print(f"[FAIL] Rapid generation failed: {result.error_message}")

    except Exception as e:
        print(f"[ERROR] Error in rapid generation: {e}")

if __name__ == "__main__":
    print("[GOTHIC] Gothic Wardrobe 3D Generation")
    print("=" * 60)
    print("This script will generate a detailed Gothic-style wardrobe")
    print("using Tencent Hunyuan 3D API.\n")

    # Auto-select Pro version for best quality
    print("[AUTO] Auto-selecting Pro version for best quality...")
    generate_gothic_wardrobe()