#!/usr/bin/env python3
"""Test SF3D generation with existing object cards."""

import asyncio
import logging
from pathlib import Path

from holodeck_core.object_gen.sf3d_client import SF3DClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_sf3d_generation():
    """Test SF3D generation with object card image."""

    # Session directory with object cards
    session_dir = Path("C:/Users/Administrator/Desktop/holodeck-gemini/workspace/sessions/2026-01-24T12-49-27Z_10fc9e95")
    object_cards_dir = session_dir / "object_cards"
    assets_dir = session_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    # Test with first object
    object_id = "obj_001"
    image_path = object_cards_dir / f"{object_id}.png"

    if not image_path.exists():
        logger.error(f"Object card image not found: {image_path}")
        return

    logger.info(f"Testing SF3D generation with: {image_path}")

    try:
        # Create SF3D client
        client = SF3DClient()

        # Test SF3D availability
        logger.info("Testing SF3D availability...")
        available = await client.test_sf3d_availability()
        logger.info(f"SF3D available: {available}")

        if not available:
            logger.error("SF3D is not available")
            return

        # Generate 3D asset step by step for debugging
        logger.info(f"Starting SF3D generation for {object_id}...")

        # Upload image first
        logger.info("Uploading image to ComfyUI...")
        client.upload_image_to_comfyui(str(image_path))

        # Build workflow
        logger.info("Building SF3D workflow...")
        workflow = client.build_sf3d_workflow(
            image_path=str(image_path),
            foreground_ratio=0.85,
            texture_resolution=1024,
            remesh="triangle",
            vertex_count=-1,
            filename_prefix=object_id
        )

        # Queue workflow
        logger.info("Queuing SF3D workflow...")
        prompt_data = client.queue_prompt(workflow)
        prompt_id = prompt_data["prompt_id"]
        logger.info(f"SF3D workflow queued: {prompt_id}")

        # Wait for completion
        logger.info("Waiting for SF3D completion...")
        import websocket
        ws_url = f"ws://{client.server_address}/ws?clientId={client.client_id}"
        ws = websocket.WebSocket()

        try:
            ws.connect(ws_url, timeout=client.timeout)
            logger.info(f"Connected to ComfyUI WebSocket for SF3D: {prompt_id[:8]}...")

            # Wait for execution to complete
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    import json
                    message = json.loads(out)
                    logger.debug(f"WebSocket message: {message}")
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            logger.info("SF3D execution complete")
                            break
                else:
                    continue

        except websocket.WebSocketTimeoutException:
            logger.error(f"WebSocket timeout after {client.timeout} seconds")
            return
        except Exception as e:
            logger.error(f"WebSocket error during SF3D generation: {e}")
            return
        finally:
            ws.close()

        # Get execution results
        logger.info("Getting SF3D execution history...")
        try:
            history = client.get_history(prompt_id)
            prompt_history = history[prompt_id]
            logger.info(f"SF3D execution history: {prompt_history}")

            # Print all outputs for debugging
            for node_id, node_output in prompt_history.get('outputs', {}).items():
                logger.info(f"Node {node_id}: {node_output}")
                if 'files' in node_output:
                    for i, file_info in enumerate(node_output['files']):
                        logger.info(f"  File {i}: {file_info}")
        except Exception as e:
            logger.error(f"Failed to get SF3D execution history: {e}")
            return

        # Check for outputs
        logger.info("Checking for SF3D outputs...")
        if 'outputs' not in prompt_history:
            logger.error("No outputs in SF3D history")
            return

        # Look for GLB files
        glb_files = []
        for node_id, node_output in prompt_history['outputs'].items():
            logger.info(f"Node {node_id} output: {node_output}")
            if 'files' in node_output:
                for file_info in node_output['files']:
                    logger.info(f"Found file: {file_info}")
                    if file_info['filename'].endswith('.glb'):
                        glb_files.append(file_info)

        if not glb_files:
            logger.error("No GLB files found in SF3D output")
            return

        logger.info(f"Found {len(glb_files)} GLB files: {glb_files}")

        # Download first GLB file
        file_info = glb_files[0]
        logger.info(f"Downloading GLB file: {file_info['filename']}")
        glb_data = client.get_file(
            file_info['filename'],
            file_info.get('subfolder', ''),
            file_info.get('type', 'output')
        )

        # Save GLB file
        glb_path = assets_dir / f"{object_id}.glb"
        with open(glb_path, 'wb') as f:
            f.write(glb_data)

        logger.info(f"SF3D generation completed: {glb_path}")

        # Check file size
        size_mb = glb_path.stat().st_size / (1024 * 1024)
        logger.info(f"Generated GLB file size: {size_mb:.2f} MB")

    except Exception as e:
        logger.error(f"SF3D generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sf3d_generation())