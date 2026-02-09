#!/usr/bin/env python3
"""
Test SF3D 3D generation with an existing image

Usage:
1. Make sure ComfyUI with SF3D plugin is running (default: 127.0.0.1:8189)
2. Prepare an image file (PNG format recommended)
3. Run: python test_sf3d_generation.py --image path/to/your/image.png --output test_output.glb
"""

import asyncio
import argparse
import logging
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from holodeck_core.object_gen.sf3d_client import SF3DClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_sf3d_generation(image_path: str, output_path: str = None):
    """Test SF3D generation with a specific image"""

    image_path = Path(image_path)
    if not image_path.exists():
        logger.error(f"Image file not found: {image_path}")
        return False

    # Set default output path if not provided
    if output_path is None:
        output_path = image_path.with_suffix('.glb')
    else:
        output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Testing SF3D generation with image: {image_path}")
    logger.info(f"Output will be saved to: {output_path}")

    # Initialize SF3D client
    client = SF3DClient()

    try:
        # Test SF3D availability
        logger.info("Testing SF3D availability...")
        if not await client.test_sf3d_availability():
            logger.error("SF3D is not available. Please ensure ComfyUI with SF3D plugin is running.")
            logger.error("Expected server: 127.0.0.1:8189")
            return False

        logger.info("SF3D is available. Starting generation...")

        # Generate 3D asset
        glb_path, metadata = await client.generate_3d_asset(
            image_path=str(image_path),
            output_path=str(output_path),
            foreground_ratio=0.85,
            texture_resolution=1024,
            remesh="triangle",
            vertex_count=-1
        )

        logger.info(f"Successfully generated 3D asset: {glb_path}")
        logger.info(f"Generation metadata: {metadata}")

        # Verify the output file
        if Path(glb_path).exists():
            file_size = Path(glb_path).stat().st_size
            logger.info(f"Output file size: {file_size} bytes")
            return True
        else:
            logger.error("Generated file not found!")
            return False

    except Exception as e:
        logger.error(f"Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sf3d_connection():
    """Test SF3D connection without generation"""
    async def check_connection():
        client = SF3DClient()
        try:
            available = await client.test_sf3d_availability()
            if available:
                logger.info("SF3D connection successful")
                return True
            else:
                logger.error("SF3D connection failed")
                return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    return asyncio.run(check_connection())

def main():
    parser = argparse.ArgumentParser(description="Test SF3D 3D generation")
    parser.add_argument("--image", type=str, help="Path to input image file")
    parser.add_argument("--output", type=str, help="Path to output GLB file (optional)")
    parser.add_argument("--test-connection", action="store_true", help="Only test SF3D connection")
    parser.add_argument("--server", type=str, default="127.0.0.1:8189", help="ComfyUI server address")

    args = parser.parse_args()

    if args.test_connection:
        logger.info("Testing SF3D connection only...")
        success = test_sf3d_connection()
        return success

    if not args.image:
        logger.error("Please provide an image file with --image")
        parser.print_help()
        return False

    logger.info(f"Starting SF3D generation test...")
    success = asyncio.run(test_sf3d_generation(args.image, args.output))

    if success:
        logger.info("SF3D generation test completed successfully!")
    else:
        logger.error("SF3D generation test failed!")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)