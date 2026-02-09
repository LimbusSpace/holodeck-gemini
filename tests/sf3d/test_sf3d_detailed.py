#!/usr/bin/env python3
"""Detailed SF3D test with full workflow debugging."""

import asyncio
import json
import logging
import websocket
from pathlib import Path
from holodeck_core.object_gen.sf3d_client import SF3DClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_detailed_sf3d():
    """Detailed SF3D test with full debugging."""

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

        # Upload image
        logger.info("Uploading image...")
        client.upload_image_to_comfyui(str(image_path))

        # Build workflow
        logger.info("Building workflow...")
        workflow = client.build_sf3d_workflow(
            image_path=str(image_path),
            filename_prefix=object_id,
            use_prepared_image=True
        )
        logger.info(f"Workflow image input: {workflow['1']['inputs']['image']}")

        # Queue workflow
        logger.info("Queuing workflow...")
        prompt_data = client.queue_prompt(workflow)
        prompt_id = prompt_data["prompt_id"]
        logger.info(f"Workflow queued: {prompt_id}")

        # Wait for completion with detailed logging
        logger.info("Waiting for completion...")
        ws_url = f"ws://{client.server_address}/ws?clientId={client.client_id}"
        ws = websocket.WebSocket()

        try:
            ws.connect(ws_url, timeout=client.timeout)
            logger.info(f"WebSocket connected for prompt {prompt_id[:8]}")

            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    logger.info(f"WebSocket: {message.get('type', 'unknown')}")

                    if message['type'] == 'executing':
                        data = message['data']
                        node = data.get('node')
                        logger.info(f"Executing node: {node}")
                        if node is None and data['prompt_id'] == prompt_id:
                            logger.info("Execution complete")
                            break
                    elif message['type'] == 'execution_error':
                        logger.error(f"Execution error: {message}")
                        return False
                    elif message['type'] == 'progress':
                        data = message['data']
                        logger.info(f"Progress: {data.get('value', 0)}/{data.get('max', 1)}")
                else:
                    logger.info(f"Non-string message: {type(out)}")

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            return False
        finally:
            ws.close()

        # Get history and analyze
        logger.info("Getting execution history...")
        history = client.get_history(prompt_id)

        if prompt_id not in history:
            logger.error(f"Prompt {prompt_id} not found in history")
            return False

        prompt_history = history[prompt_id]
        logger.info(f"History keys: {list(prompt_history.keys())}")

        # Check outputs
        if 'outputs' in prompt_history:
            outputs = prompt_history['outputs']
            logger.info(f"Found {len(outputs)} output nodes")

            for node_id, node_output in outputs.items():
                logger.info(f"Node {node_id}: {list(node_output.keys())}")
                if 'files' in node_output:
                    logger.info(f"  Files: {node_output['files']}")
                if 'images' in node_output:
                    logger.info(f"  Images: {node_output['images']}")
        else:
            logger.error("No outputs in history")

        # Check status
        if 'status' in prompt_history:
            status = prompt_history['status']
            logger.info(f"Execution status: {status}")
            if status.get('status_str') == 'error':
                logger.error(f"Execution failed: {status.get('error', 'Unknown error')}")
                return False

        # Try to find GLB files
        glb_files = []
        if 'outputs' in prompt_history:
            for node_id in prompt_history['outputs']:
                node_output = prompt_history['outputs'][node_id]
                if 'files' in node_output:
                    for file_info in node_output['files']:
                        if file_info['filename'].endswith('.glb'):
                            glb_files.append(file_info)

        if glb_files:
            logger.info(f"Found {len(glb_files)} GLB files")

            # Download first GLB
            file_info = glb_files[0]
            logger.info(f"Downloading: {file_info}")

            glb_data = client.get_file(
                file_info['filename'],
                file_info.get('subfolder', ''),
                file_info.get('type', 'output')
            )

            # Save file
            local_path = assets_dir / f"{object_id}_test.glb"
            with open(local_path, 'wb') as f:
                f.write(glb_data)

            logger.info(f"Saved GLB: {local_path} ({len(glb_data)} bytes)")
            return True
        else:
            logger.error("No GLB files found in outputs")
            return False

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_detailed_sf3d())
    if success:
        print("SF3D test PASSED!")
    else:
        print("SF3D test FAILED!")