"""ComfyUI Stable Fast 3D client for 3D asset generation.

Extends the base ComfyUIClient to handle Stable Fast 3D workflows specifically.
"""

import asyncio
import json
import logging
import time
import urllib.request
import urllib.parse
import urllib.error
import websocket
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from ..image_generation.comfyui_client import ComfyUIClient

logger = logging.getLogger(__name__)


class SF3DClient(ComfyUIClient):
    """Stable Fast 3D专用客户端 - Extends ComfyUIClient for SF3D workflows."""

    def __init__(
        self,
        sf3d_workflow_template_path: Optional[str] = None,
        server_address: str = "127.0.0.1:8189",
        client_id: Optional[str] = None,
        timeout: int = 120  # Longer timeout for 3D generation
    ):
        """Initialize SF3D Client.

        Args:
            sf3d_workflow_template_path: Path to SF3D workflow template JSON
            server_address: ComfyUI server address
            client_id: Unique client identifier
            timeout: Timeout in seconds for 3D generation operations
        """
        super().__init__(server_address, client_id, timeout)

        # Load SF3D workflow template
        if sf3d_workflow_template_path is None:
            # Use the default template in object_gen directory
            current_dir = Path(__file__).parent
            sf3d_workflow_template_path = current_dir / "sf3d_example.json"

        self.sf3d_workflow_template = self._load_workflow_template(
            sf3d_workflow_template_path
        )

        if not self.sf3d_workflow_template:
            raise ValueError(f"Failed to load SF3D workflow template from {sf3d_workflow_template_path}")

    def _load_workflow_template(self, template_path: str) -> Dict[str, Any]:
        """Load SF3D workflow template from JSON file.

        Args:
            template_path: Path to workflow template file

        Returns:
            Workflow template dictionary
        """
        try:
            template_path = Path(template_path)
            if not template_path.exists():
                logger.error(f"SF3D workflow template not found: {template_path}")
                return {}

            with open(template_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)

            logger.info(f"Loaded SF3D workflow template from {template_path}")
            return workflow

        except Exception as e:
            logger.error(f"Failed to load SF3D workflow template: {e}")
            return {}

    def build_sf3d_workflow(
        self,
        image_path: str,
        foreground_ratio: float = 0.85,
        texture_resolution: int = 1024,
        remesh: str = "triangle",
        vertex_count: int = -1,
        filename_prefix: str = "sf3d_output",
        use_prepared_image: bool = True
    ) -> Dict[str, Any]:
        """Build SF3D workflow with dynamic parameters.

        Args:
            image_path: Path to input image (object card)
            foreground_ratio: Foreground extraction ratio (0.0-1.0)
            texture_resolution: Texture resolution for output
            remesh: Remeshing method
            vertex_count: Target vertex count (-1 for auto)
            filename_prefix: Output filename prefix
            use_prepared_image: Whether to use RGBA-prepared image filename

        Returns:
            Complete workflow dictionary ready for ComfyUI
        """
        if not self.sf3d_workflow_template:
            raise ValueError("No SF3D workflow template available")

        import uuid

        # Create a deep copy of the template
        workflow = json.loads(json.dumps(self.sf3d_workflow_template))

        # Determine the image filename to use in workflow
        if use_prepared_image:
            # Use the RGBA-prepared image filename
            prepared_path = self._prepare_image_for_sf3d(image_path)
            image_name = Path(prepared_path).name
        else:
            # Use original image filename
            image_name = Path(image_path).name

        # Find and update LoadImage node (node 1 in template)
        if "1" in workflow:
            # Convert image path to be relative to ComfyUI input directory
            workflow["1"]["inputs"]["image"] = image_name
            workflow["1"]["inputs"]["upload"] = "image"
        else:
            raise ValueError("LoadImage node not found in SF3D workflow template")

        # Find and update StableFast3DSampler node (node 8 in template)
        if "8" in workflow:
            workflow["8"]["inputs"]["foreground_ratio"] = foreground_ratio
            workflow["8"]["inputs"]["texture_resolution"] = texture_resolution
            workflow["8"]["inputs"]["remesh"] = remesh
            workflow["8"]["inputs"]["vertex_count"] = vertex_count
        else:
            raise ValueError("StableFast3DSampler node not found in SF3D workflow template")

        # Find and update StableFast3DSave node (node 9 in template)
        if "9" in workflow:
            workflow["9"]["inputs"]["filename_prefix"] = filename_prefix
        else:
            raise ValueError("StableFast3DSave node not found in SF3D workflow template")

        return workflow

    def _prepare_image_for_sf3d(self, image_path: str) -> str:
        """Prepare image for SF3D by converting to RGBA if needed.

        Args:
            image_path: Path to input image

        Returns:
            Path to prepared image (may be same as input if no conversion needed)
        """
        try:
            from PIL import Image

            image_path = Path(image_path)
            with Image.open(image_path) as img:
                if img.mode == 'RGBA':
                    # Already RGBA, no conversion needed
                    logger.info(f"Image already RGBA: {image_path.name}")
                    return str(image_path)

                # Convert to RGBA by adding alpha channel
                logger.info(f"Converting {img.mode} image to RGBA: {image_path.name}")
                if img.mode == 'RGB':
                    # Add opaque alpha channel
                    rgba_img = Image.new('RGBA', img.size, (0, 0, 0, 255))
                    rgba_img.paste(img, (0, 0))
                else:
                    # Convert other modes to RGBA
                    rgba_img = img.convert('RGBA')

                # Save converted image to temporary file
                import tempfile
                temp_dir = Path(tempfile.gettempdir()) / "holodeck_sf3d"
                temp_dir.mkdir(exist_ok=True)

                temp_path = temp_dir / f"rgba_{image_path.name}"
                rgba_img.save(temp_path, 'PNG')

                logger.info(f"Saved RGBA image to: {temp_path}")
                return str(temp_path)

        except Exception as e:
            logger.error(f"Failed to prepare image for SF3D: {e}")
            # Fall back to original image
            return str(image_path)

    def upload_image_to_comfyui(self, image_path: str) -> None:
        """Upload image to ComfyUI input directory.

        Args:
            image_path: Path to image file to upload
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        try:
            # Prepare image for SF3D (convert to RGBA if needed)
            prepared_image_path = self._prepare_image_for_sf3d(str(image_path))

            # Get ComfyUI input directory structure
            upload_url = f"{self.base_url}/upload/image"

            with open(prepared_image_path, 'rb') as f:
                files = {'image': (Path(prepared_image_path).name, f, 'image/png')}
                response = requests.post(upload_url, files=files, timeout=30)

            if response.status_code == 200:
                logger.info(f"Successfully uploaded image: {Path(prepared_image_path).name}")
            else:
                raise Exception(f"Upload failed with status {response.status_code}: {response.text}")

        except Exception as e:
            raise Exception(f"Failed to upload image to ComfyUI: {e}")

    async def generate_3d_asset(
        self,
        image_path: str,
        foreground_ratio: float = 0.85,
        texture_resolution: int = 1024,
        remesh: str = "triangle",
        vertex_count: int = -1,
        filename_prefix: str = "sf3d_output",
        output_dir: Optional[Path] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate 3D asset from image using SF3D workflow.

        Args:
            image_path: Path to source image (should be PNG with alpha)
            foreground_ratio: Foreground extraction ratio
            texture_resolution: Output texture resolution
            remesh: Remeshing method
            vertex_count: Target vertex count (-1 for auto)
            filename_prefix: Output filename prefix
            output_dir: Directory to save downloaded asset (auto-generated if None)

        Returns:
            Tuple of (glb_path, generation_metadata)
        """
        start_time = time.time()

        # Set output directory
        if output_dir is None:
            output_dir = Path.cwd() / "workspace" / "temp"
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting SF3D generation: {image_path}")

        # First upload image to ComfyUI
        try:
            self.upload_image_to_comfyui(image_path)
        except Exception as e:
            raise Exception(f"Failed to upload image: {e}")

        # Build SF3D workflow
        try:
            workflow = self.build_sf3d_workflow(
                image_path=image_path,
                foreground_ratio=foreground_ratio,
                texture_resolution=texture_resolution,
                remesh=remesh,
                vertex_count=vertex_count,
                filename_prefix=filename_prefix
            )
        except Exception as e:
            raise Exception(f"Failed to build SF3D workflow: {e}")

        # Queue the workflow for execution
        try:
            prompt_data = self.queue_prompt(workflow)
            prompt_id = prompt_data["prompt_id"]
            logger.info(f"SF3D workflow queued: {prompt_id[:8]}...")
        except Exception as e:
            raise Exception(f"Failed to queue SF3D workflow: {e}")

        # Wait for completion by polling history instead of WebSocket
        max_wait_time = self.timeout
        poll_interval = 2  # Check every 2 seconds
        start_time = time.time()

        logger.info(f"Waiting for SF3D completion (max {max_wait_time}s)...")

        while time.time() - start_time < max_wait_time:
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history:
                    prompt_history = history[prompt_id]
                    # Check if execution is complete
                    if 'status' in prompt_history:
                        status = prompt_history['status']
                        if status.get('completed', False):
                            logger.info("SF3D execution completed")
                            break
                    elif 'outputs' in prompt_history:
                        # If we have outputs, consider it complete
                        logger.info("SF3D outputs found, execution complete")
                        break

                logger.info(f"SF3D still running... (waited {time.time() - start_time:.1f}s)")
                time.sleep(poll_interval)

            except Exception as e:
                logger.warning(f"Error checking SF3D status: {e}")
                time.sleep(poll_interval)

        else:
            raise Exception(f"SF3D execution timeout after {max_wait_time} seconds")

        # Get final execution results
        try:
            history = self.get_history(prompt_id)
            prompt_history = history[prompt_id]
        except Exception as e:
            raise Exception(f"Failed to get SF3D execution history: {e}")

        # Find and download generated 3D models
        glb_files = []
        for node_id in prompt_history['outputs']:
            node_output = prompt_history['outputs'][node_id]

            # Check for 'files' output (traditional format)
            if 'files' in node_output:
                for file_info in node_output['files']:
                    if file_info['filename'].endswith('.glb'):
                        # Download GLB file
                        glb_data = self.get_file(
                            file_info['filename'],
                            file_info.get('subfolder', ''),
                            file_info.get('type', 'output')
                        )

                        # Save GLB file
                        local_filename = f"{filename_prefix}_{prompt_id[:8]}_{file_info['filename']}"
                        local_path = output_dir / local_filename

                        with open(local_path, 'wb') as f:
                            f.write(glb_data)

                        glb_files.append({
                            'filename': local_filename,
                            'path': str(local_path),
                            'subfolder': file_info.get('subfolder', ''),
                            'type': file_info.get('type', 'output')
                        })

            # Check for 'glbs' output (StableFast3DSave format)
            elif 'glbs' in node_output:
                import base64
                for glb_data_str in node_output['glbs']:
                    # Handle different GLB data formats
                    if glb_data_str.startswith('data:application/octet-stream;base64,'):
                        # Base64 encoded data URL
                        base64_data = glb_data_str.replace('data:application/octet-stream;base64,', '')
                        glb_data = base64.b64decode(base64_data)
                    else:
                        # Base64 encoded string (most common case)
                        try:
                            glb_data = base64.b64decode(glb_data_str)
                        except Exception:
                            # Fallback: try latin1 encoding for binary data as string
                            glb_data = glb_data_str.encode('latin1')

                    # Save GLB file
                    local_filename = f"{filename_prefix}_{prompt_id[:8]}.glb"
                    local_path = output_dir / local_filename

                    with open(local_path, 'wb') as f:
                        f.write(glb_data)

                    glb_files.append({
                        'filename': local_filename,
                        'path': str(local_path),
                        'subfolder': '',
                        'type': 'output'
                    })

        if not glb_files:
            raise Exception("No GLB files generated by SF3D workflow")

        # Return first GLB file and metadata
        glb_path = glb_files[0]['path']
        glb_file_path = Path(glb_path)

        # Build generation metadata
        end_time = time.time()
        metadata = {
            'prompt_id': prompt_id,
            'workflow_type': 'sf3d',
            'input_image': str(image_path),
            'generation_time_sec': round(end_time - start_time, 2),
            'client_id': self.client_id,
            'parameters': {
                'foreground_ratio': foreground_ratio,
                'texture_resolution': texture_resolution,
                'remesh': remesh,
                'vertex_count': vertex_count,
                'filename_prefix': filename_prefix
            },
            'files': glb_files,
            'file_size_mb': round(glb_file_path.stat().st_size / (1024 * 1024), 2),
            'file_size_bytes': glb_file_path.stat().st_size
        }

        logger.info(f"SF3D generation completed: {glb_path} ({metadata['generation_time_sec']}s)")
        return glb_path, metadata

    def get_file(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """Download file from ComfyUI (generic for any file type).

        Args:
            filename: Filename to download
            subfolder: Subfolder path
            folder_type: Folder type ("input" or "output")

        Returns:
            File data as bytes

        Raises:
            urllib.error.URLError: If download fails
        """
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        url = self._make_request_url(f"view?{url_values}")

        with urllib.request.urlopen(url) as response:
            return response.read()

    async def test_sf3d_availability(self) -> bool:
        """Test if SF3D nodes are available in ComfyUI.

        Returns:
            True if SF3D nodes are available, False otherwise
        """
        try:
            # Get list of available nodes
            object_info_url = f"{self.base_url}/object_info"
            response = requests.get(object_info_url, timeout=5)

            if response.status_code == 200:
                object_info = response.json()
                sf3d_nodes = [
                    "StableFast3DLoader",
                    "StableFast3DSampler",
                    "StableFast3DSave"
                ]

                for node in sf3d_nodes:
                    if node not in object_info:
                        logger.warning(f"SF3D node not available: {node}")
                        return False

                logger.info("All SF3D nodes are available in ComfyUI")
                return True
            else:
                logger.error(f"Failed to get ComfyUI object info: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error testing SF3D availability: {e}")
            return False