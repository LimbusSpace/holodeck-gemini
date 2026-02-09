#!/usr/bin/env python3
"""Debug SF3D generation with detailed logging."""

import asyncio
import logging
import json
from pathlib import Path

from holodeck_core.object_gen.sf3d_client import SF3DClient

# Configure logging to show everything
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def debug_sf3d_generation():
    """Debug SF3D generation step by step."""

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
            filename_prefix=object_id,
            use_prepared_image=True
        )
        logger.info(f"Built workflow with image: {workflow.get('1', {}).get('inputs', {}).get('image', 'unknown')}")

        # Queue workflow
        logger.info("Queuing SF3D workflow...")
        prompt_data = client.queue_prompt(workflow)
        prompt_id = prompt_data["prompt_id"]
        logger.info(f"SF3D workflow queued: {prompt_id}")
        logger.info(f"Prompt data: {prompt_data}")

        # Wait for completion with detailed logging
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
                    message = json.loads(out)
                    logger.info(f"WebSocket message: {message}")
                    if message['type'] == 'executing':
                        data = message['data']
                        logger.info(f"Executing: node={data.get('node')}, prompt_id={data.get('prompt_id')}")
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            logger.info("SF3D execution complete")
                            break
                    elif message['type'] == 'status':
                        logger.info(f"SF3D status: {message}")
                    elif message['type'] == 'progress':
                        logger.info(f"SF3D progress: {message}")
                    elif message['type'] == 'executed':
                        logger.info(f"SF3D executed node: {message}")
                else:
                    logger.info(f"Non-string WebSocket message: {type(out)}")

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
            logger.info(f"Full history: {history}")

            if prompt_id in history:
                prompt_history = history[prompt_id]
                logger.info(f"SF3D execution history: {prompt_history}")

                # Print all outputs for debugging
                if 'outputs' in prompt_history:
                    for node_id, node_output in prompt_history['outputs'].items():
                        logger.info(f"Node {node_id}: {node_output}")
                        if 'files' in node_output:
                            for i, file_info in enumerate(node_output['files']):
                                logger.info(f"  File {i}: {file_info}")
                        if 'images' in node_output:
                            for i, image_info in enumerate(node_output['images']):
                                logger.info(f"  Image {i}: {image_info}")
                else:
                    logger.error("No outputs in prompt history")
            else:
                logger.error(f"Prompt ID {prompt_id} not found in history")

        except Exception as e:
            logger.error(f"Failed to get SF3D execution history: {e}")
            return

    except Exception as e:
        logger.error(f"SF3D generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_sf3d_generation())