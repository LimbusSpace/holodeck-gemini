"""ComfyUI client for image generation.

Provides async interface to local ComfyUI instance via WebSocket.
"""

import asyncio
import json
import logging
import uuid
import urllib.request
import urllib.parse
from typing import Optional, Tuple, Any, Dict, List, Union
from pathlib import Path

import requests
import websocket

from ..clients.base import BaseImageClient, GenerationResult
from ..clients.base import ServiceType

logger = logging.getLogger(__name__)


class ComfyUIClient(BaseImageClient):
    """Client for interacting with local ComfyUI instance."""

    def __init__(
        self,
        config_manager=None,
        logger=None,
        client_config=None,
        server_address: str = "127.0.0.1:8188",
        client_id: Optional[str] = None,
        timeout: int = 30
    ):
        """Initialize ComfyUI client.

        Args:
            config_manager: Configuration manager instance
            logger: Logger instance
            client_config: Client configuration
            server_address: ComfyUI server address (default: "127.0.0.1:8188")
            client_id: Unique client identifier (auto-generated if None)
            timeout: Timeout in seconds for operations (default: 30)
        """
        super().__init__(config_manager, logger, client_config)

        self.server_address = server_address
        self.client_id = client_id or str(uuid.uuid4())
        self.timeout = timeout
        self.base_url = f"http://{server_address}"

    def get_service_type(self):
        """Return service type for this client"""
        return ServiceType.IMAGE_GENERATION

    def validate_configuration(self) -> bool:
        """Validate ComfyUI client configuration."""
        # Check if server address is configured
        if not self.server_address:
            return False

        # Try to test connection
        try:
            return self.test_connection()
        except:
            return False

    def _setup_client(self) -> None:
        """Setup ComfyUI client connections."""
        # Connection setup is handled in individual methods
        pass

    async def validate_prompt(self, prompt: str) -> bool:
        """Validate if prompt is acceptable for generation."""
        if not prompt or not prompt.strip():
            return False
        if len(prompt) > 1000:
            return False
        return True

    def _make_request_url(self, endpoint: str) -> str:
        """Construct full URL for endpoint."""
        return f"{self.base_url}/{endpoint}"

    def queue_prompt(self, prompt_workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Send generation request to ComfyUI.

        Args:
            prompt_workflow: ComfyUI workflow JSON

        Returns:
            Response containing prompt_id

        Raises:
            urllib.error.URLError: If request fails
        """
        p = {"prompt": prompt_workflow, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        url = self._make_request_url("prompt")

        req = urllib.request.Request(url, data=data)
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            error_data = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code} Error: {error_data}")
        except Exception as e:
            raise Exception(f"Failed to queue prompt: {e}")

    def get_image(self, filename: str, subfolder: str, folder_type: str) -> bytes:
        """Download generated image from ComfyUI.

        Args:
            filename: Image filename
            subfolder: Subfolder containing image
            folder_type: Type of folder ("input" or "output")

        Returns:
            Image data as bytes

        Raises:
            urllib.error.URLError: If download fails
        """
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = urllib.parse.urlencode(data)
        url = self._make_request_url(f"view?{url_values}")

        with urllib.request.urlopen(url) as response:
            return response.read()

    def get_history(self, prompt_id: str) -> Dict[str, Any]:
        """Get execution history for prompt.

        Args:
            prompt_id: Prompt identifier

        Returns:
            History dictionary

        Raises:
            urllib.error.URLError: If request fails
        """
        url = self._make_request_url(f"history/{prompt_id}")
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read())

    async def generate_image(
        self,
        prompt: str,
        resolution: str = "1024:1024",
        style: Optional[str] = None,
        model: str = "default",
        output_path: Optional[Union[str, Path]] = None,
        workflow_type: str = "scene_ref",
        **kwargs
    ) -> GenerationResult:
        """Generate image using ComfyUI workflow.

        Args:
            prompt: Text prompt for generation
            workflow_type: Type of workflow ("scene_ref" or "object_card")
            output_dir: Directory to save image (auto-generated if None)

        Returns:
            Tuple of (image_path, generation metadata)

        Raises:
            Exception: If generation fails
        """
        from .workflows import SCENE_REF_WORKFLOW, OBJECT_CARD_WORKFLOW

        # Select appropriate workflow
        if workflow_type == "scene_ref":
            workflow = SCENE_REF_WORKFLOW.copy()
        elif workflow_type == "object_card":
            workflow = OBJECT_CARD_WORKFLOW.copy()
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")

        # Inject prompt into workflow
        # TODO: Adjust based on actual workflow structure
        # This assumes there's a text node with class_type "CLIPTextEncode"
        for node_id, node_data in workflow.items():
            if node_data.get("class_type") == "CLIPTextEncode":
                if "text" in node_data["inputs"]:
                    if isinstance(node_data["inputs"]["text"], list):
                        node_data["inputs"]["text"][0] = prompt
                    else:
                        node_data["inputs"]["text"] = prompt

        # Output directory handling
        if output_path is not None:
            output_dir = Path(output_path).parent
        else:
            output_dir = Path.cwd() / "workspace" / "temp"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Queue the prompt
        prompt_data = self.queue_prompt(workflow)
        prompt_id = prompt_data["prompt_id"]

        # Connect via WebSocket and wait for completion
        ws_url = f"ws://{self.server_address}/ws?clientId={self.client_id}"
        ws = websocket.WebSocket()

        try:
            ws.connect(ws_url, timeout=self.timeout)
            logger.info(f"Connected to ComfyUI WebSocket for prompt {prompt_id}")

            # Wait for execution to complete
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break  # Execution complete
                else:
                    continue

        except websocket.WebSocketTimeoutException:
            raise Exception(f"WebSocket timeout after {self.timeout} seconds")
        except Exception as e:
            raise Exception(f"WebSocket error: {e}")
        finally:
            ws.close()

        # Get the results from history
        history = self.get_history(prompt_id)
        prompt_history = history[prompt_id]

        # Find and download generated images
        images = []
        for node_id in prompt_history['outputs']:
            node_output = prompt_history['outputs'][node_id]
            if 'images' in node_output:
                for image in node_output['images']:

                    # Download image
                    image_data = self.get_image(
                        image['filename'],
                        image.get('subfolder', ''),
                        image.get('type', 'output')
                    )

                    # Save image
                    image_filename = f"{workflow_type}_{prompt_id[:8]}_{image['filename']}"
                    image_path = output_dir / image_filename

                    with open(image_path, 'wb') as f:
                        f.write(image_data)

                    images.append({
                        'filename': image_filename,
                        'path': str(image_path),
                        'subfolder': image.get('subfolder', ''),
                        'type': image.get('type', 'output')
                    })

        if not images:
            raise Exception("No images generated")

        # Return first image and metadata
        if not images:
            return GenerationResult(
                success=False,
                error="No images generated"
            )

        first_image = images[0]
        metadata = {
            'prompt_id': prompt_id,
            'workflow_type': workflow_type,
            'prompt': prompt,
            'generation_time': prompt_history.get('prompt', {}),
            'client_id': self.client_id,
            'images': images,
            'resolution': resolution,
            'style': style,
            'model': model
        }

        return GenerationResult(
            success=True,
            data={
                'image_path': str(first_image['path']),
                'image_data': first_image
            },
            metadata=metadata
        )

    async def test_connection(self) -> bool:
        """Test connection to ComfyUI server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to fetch system stats as a simple test
            response = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ComfyUI connection test failed: {e}")
            return False

    def get_server_info(self) -> Dict[str, Any]:
        """Get ComfyUI server information.

        Returns:
            Server information dictionary
        """
        try:
            response = requests.get(f"{self.base_url}/system_stats", timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            return {"error": str(e)}