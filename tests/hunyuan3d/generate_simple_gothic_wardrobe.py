#!/usr/bin/env python3
"""Generate a simple Gothic-style wardrobe using Hunyuan 3D Rapid version."""

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

def generate_simple_gothic_wardrobe():
    """Generate a simple Gothic-style wardrobe using Rapid version."""
    print("[GOTHIC-RAPID] Simple Gothic Wardrobe Generation")
    print("=" * 60)

    # Check environment variables
    secret_id = os.getenv("HUNYUAN_SECRET_ID")
    secret_key = os.getenv("HUNYUAN_SECRET_KEY")

    if not secret_id or not secret_key:
        print("[ERROR] HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY not set")
        return False

    try:
        # Initialize client with Rapid version
        print("[INIT] Initializing Hunyuan 3D Rapid client...")
        client = Hunyuan3DClient(
            secret_id=secret_id,
            secret_key=secret_key,
            timeout=300,  # 5 minutes timeout
            poll_interval=3
        )
        print("[OK] Rapid client initialized successfully")

        # Test connection
        print("[TEST] Testing API connection...")
        if not client.test_connection():
            print("[FAIL] API connection failed")
            return False
        print("[OK] API connection successful")

        # Create task with simplified prompt
        print("[TASK] Creating simplified generation task...")
        task = Hunyuan3DTask(
            task_id=f"simple_gothic_wardrobe_{int(time.time())}",
            prompt="A Gothic-style wooden wardrobe with pointed arch design",
            output_dir="simple_gothic_models",
            enable_pbr=True,
            result_format="GLB"
        )

        print(f"[INFO] Task details:")
        print(f"   Task ID: {task.task_id}")
        print(f"   Output directory: {task.output_dir}")
        print(f"   Using Rapid version for faster generation")

        # Start generation
        print("\n[START] Starting 3D generation with Rapid version...")
        print("[WAIT] This should complete faster than Pro version...")

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
                if Path(path).exists():
                    file_size = Path(path).stat().st_size
                    print(f"   {i}. {path} ({file_size:,} bytes)")
                else:
                    print(f"   {i}. {path} (file not found)")

            print(f"\n[INFO] Generated GLB files are located in:")
            print(f"   Directory: {task.output_dir}/")
            print(f"   You can view the files using a 3D viewer or import into 3D software")

            return True
        else:
            print(f"\n[FAIL] Generation failed: {result.error_message}")
            if "ResourceInsufficient" in result.error_message:
                print("[TIPS] Resource insufficient error - possible solutions:")
                print("   - Try again later when API resources are available")
                print("   - Use an even simpler prompt")
                print("   - Check if your API quota is sufficient")
            return False

    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connection_only():
    """Test API connection without generation."""
    print("[TEST] Testing API connection only...")

    secret_id = os.getenv("HUNYUAN_SECRET_ID")
    secret_key = os.getenv("HUNYUAN_SECRET_KEY")

    if not secret_id or not secret_key:
        print("[ERROR] API credentials not set")
        return False

    try:
        client = Hunyuan3DClient(
            secret_id=secret_id,
            secret_key=secret_key
        )

        if client.test_connection():
            print("[OK] API connection test successful")
            print("[INFO] You can proceed with 3D generation")
            return True
        else:
            print("[FAIL] API connection test failed")
            return False
    except Exception as e:
        print(f"[ERROR] Connection test failed: {e}")
        return False

if __name__ == "__main__":
    print("[GOTHIC] Simple Gothic Wardrobe Generation")
    print("=" * 60)
    print("This script generates a simple Gothic-style wardrobe")
    print("using Tencent Hunyuan 3D Rapid API.\n")

    # First test connection
    if test_connection_only():
        print("\n" + "-" * 60)
        # Then try generation
        success = generate_simple_gothic_wardrobe()

        if success:
            print("\n[COMPLETE] Gothic wardrobe generation completed successfully!")
        else:
            print("\n[INCOMPLETE] Generation failed, but connection works.")
    else:
        print("\n[ABORT] Cannot proceed without working API connection.")