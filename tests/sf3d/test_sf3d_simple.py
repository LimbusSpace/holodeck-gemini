#!/usr/bin/env python3
"""Simple SF3D test to verify the fix works."""

import asyncio
import logging
from pathlib import Path
from holodeck_core.object_gen.sf3d_client import SF3DClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_simple_sf3d():
    """Simple SF3D test with detailed logging."""

    session_dir = Path("workspace/sessions/2026-01-24T18-59-51Z_6c955af2")
    object_cards_dir = session_dir / "object_cards"
    assets_dir = session_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    object_id = "obj_001"
    image_path = object_cards_dir / f"{object_id}.png"

    logger.info(f"Testing SF3D generation with: {image_path}")

    try:
        client = SF3DClient()

        # Test SF3D availability
        available = await client.test_sf3d_availability()
        logger.info(f"SF3D available: {available}")
        if not available:
            logger.error("SF3D is not available")
            return False

        # Generate 3D asset
        logger.info("Starting SF3D generation...")
        glb_path, metadata = await client.generate_3d_asset(
            image_path=str(image_path),
            output_dir=str(assets_dir),
            filename_prefix=object_id
        )

        # Check result
        glb_file = Path(glb_path)
        if glb_file.exists() and glb_file.stat().st_size > 1024:  # At least 1KB
            logger.info(f"SUCCESS! Generated GLB: {glb_path}")
            logger.info(f"File size: {glb_file.stat().st_size} bytes")
            logger.info(f"Generation time: {metadata.get('generation_time_sec')} seconds")
            return True
        else:
            logger.error(f"Generated file too small or doesn't exist: {glb_path}")
            return False

    except Exception as e:
        logger.error(f"SF3D generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_sf3d())
    if success:
        print("\nSF3D test PASSED!")
    else:
        print("\nSF3D test FAILED!")