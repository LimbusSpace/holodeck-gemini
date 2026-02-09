"""Tencent Hunyuan 3D client for 3D asset generation.

Implements the 4-step process for Hunyuan 3D generation:
1. Call SubmitHunyuanTo3DJob to submit (image URL/image Base64/Prompt - choose one)
2. Get JobId (valid for 24 hours)
3. Loop call QueryHunyuanTo3DJob until Status=DONE/FAIL
4. Download model files from ResultFile3Ds[].Url (valid for 24 hours)
"""

import base64
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import requests

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.common_client import CommonClient
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

from ..clients.base import Base3DClient, GenerationResult

logger = logging.getLogger(__name__)


@dataclass
class Hunyuan3DTask:
    """Represents a single 3D generation task."""
    task_id: str
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    prompt: Optional[str] = None
    output_dir: Optional[str] = None
    enable_pbr: bool = True
    result_format: str = "GLB"
    multi_views: Optional[Dict[str, str]] = None  # Multi-view images: {"front": "url1", "back": "url2"}


@dataclass
class Hunyuan3DResult:
    """Represents a 3D generation result."""
    task_id: str
    success: bool
    job_id: Optional[str] = None
    model_urls: List[str] = None
    local_paths: List[str] = None
    generation_time: float = 0.0
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.model_urls is None:
            self.model_urls = []
        if self.local_paths is None:
            self.local_paths = []


class Hunyuan3DClient(Base3DClient):
    """Tencent Hunyuan 3D client implementing the 4-step generation process."""

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",  # Default to ap-guangzhou (Guangzhou) for China
        timeout: int = 600,  # 10 minutes for 3D generation
        poll_interval: int = 3,  # 3 seconds between polls (as per example)
        endpoint: str = "ai3d.tencentcloudapi.com",  # AI3D endpoint
        api_version: str = "2025-05-13"  # API version
    ):
        """Initialize Hunyuan 3D client.

        Args:
            secret_id: Tencent Cloud Secret ID
            secret_key: Tencent Cloud Secret Key
            region: API region (default: ap-guangzhou)
            timeout: Maximum time to wait for job completion (seconds)
            poll_interval: Time between status polls (seconds)
            endpoint: API endpoint (default: ai3d.tencentcloudapi.com)
            api_version: API version (default: 2025-05-13)
        """
        # Initialize Base3DClient
        from ..clients.base import ClientConfig, ServiceType
        client_config = ClientConfig(
            service_type=ServiceType.THREED_GENERATION,
            timeout=timeout
        )
        super().__init__(client_config=client_config)

        self.timeout = timeout
        self.poll_interval = poll_interval
        self.api_version = api_version

        # Initialize Tencent Cloud client with CommonClient for maximum compatibility
        self.cred = credential.Credential(secret_id, secret_key)
        http_profile = HttpProfile()
        http_profile.endpoint = endpoint
        http_profile.reqMethod = "POST"
        http_profile.scheme = "https"

        client_profile = ClientProfile()
        client_profile.httpProfile = http_profile
        client_profile.signMethod = "TC3-HMAC-SHA256"

        # Use CommonClient for maximum compatibility with different API versions
        self.client = CommonClient("ai3d", api_version, self.cred, region, profile=client_profile)

        logger.info(f"Initialized Hunyuan 3D client for region {region}, endpoint {endpoint}, version {api_version}")

    def get_service_type(self):
        """Get the service type for this client"""
        from ..clients.base import ServiceType
        return ServiceType.THREED_GENERATION

    def validate_configuration(self) -> bool:
        """Validate Hunyuan 3D configuration."""
        if not hasattr(self, 'cred') or not self.cred:
            raise ValidationError("Hunyuan 3D client not properly initialized", field_name="client")
        return True

    def _setup_client(self) -> None:
        """Setup client-specific configuration and connections."""
        # Client is already set up in __init__
        pass

    @classmethod
    def from_env(cls, region: str = "ap-guangzhou", timeout: int = 600, poll_interval: int = 3,
                endpoint: str = "ai3d.tencentcloudapi.com", api_version: str = "2025-05-13"):
        """Create Hunyuan3DClient from environment variables with automatic .env file loading.

        Args:
            region: API region (default: ap-guangzhou)
            timeout: Maximum time to wait for job completion (seconds)
            poll_interval: Time between status polls (seconds)
            endpoint: API endpoint (default: ai3d.tencentcloudapi.com)
            api_version: API version (default: 2025-05-13)

        Returns:
            Hunyuan3DClient instance
        """
        import os

        # Load environment variables from .env file if not already set
        if not os.getenv('HUNYUAN_SECRET_ID') or not os.getenv('HUNYUAN_SECRET_KEY'):
            try:
                from dotenv import load_dotenv
                # Try to load from current directory or parent directory
                env_paths = ['.env', '../.env', '../../.env', '../../../.env']
                loaded = False
                for env_path in env_paths:
                    if os.path.exists(env_path):
                        load_dotenv(env_path)
                        loaded = True
                        logger.info(f"Loaded environment variables from {env_path}")
                        break

                if not loaded:
                    logger.warning("No .env file found, trying manual loading")
            except ImportError:
                logger.info("dotenv not available, trying manual loading")
            except Exception as e:
                logger.warning(f"Failed to load with dotenv: {e}, trying manual loading")

            # Manual loading as fallback
            if not os.getenv('HUNYUAN_SECRET_ID') or not os.getenv('HUNYUAN_SECRET_KEY'):
                env_paths = ['.env', '../.env', '../../.env', '../../../.env']
                for env_path in env_paths:
                    if os.path.exists(env_path):
                        try:
                            with open(env_path, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if line and not line.startswith('#') and '=' in line:
                                        # Handle potential quotes around the value
                                        key, value = line.split('=', 1)
                                        key = key.strip()
                                        value = value.strip()

                                        # Remove quotes if present
                                        if (value.startswith('"') and value.endswith('"')) or \
                                           (value.startswith("'") and value.endswith("'")):
                                            value = value[1:-1]

                                        if key in ['HUNYUAN_SECRET_ID', 'HUNYUAN_SECRET_KEY']:
                                            os.environ[key] = value
                                            logger.info(f"Manually loaded {key} from {env_path}")
                            break
                        except Exception as e:
                            logger.warning(f"Failed to manually load {env_path}: {e}")

        # Check environment variables
        secret_id = os.getenv('HUNYUAN_SECRET_ID')
        secret_key = os.getenv('HUNYUAN_SECRET_KEY')

        if not secret_id or not secret_key:
            raise ValueError("HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY environment variables must be set")

        return cls(secret_id, secret_key, region, timeout, poll_interval, endpoint, api_version)

    def _encode_image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 string."""
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_string
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise

    def _download_3d_models(self, model_urls: List[str], output_dir: str, file_types: Dict[str, str] = None) -> List[str]:
        """Download 3D model files from URLs."""
        local_paths = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, url in enumerate(model_urls):
            try:
                # Determine file extension
                if file_types and url in file_types:
                    extension = file_types[url].lower()
                else:
                    # Extract from URL or default to glb
                    if '?' in url:
                        url_base = url.split('?')[0]
                    else:
                        url_base = url

                    if url_base.endswith('.obj'):
                        extension = 'obj'
                    elif url_base.endswith('.stl'):
                        extension = 'stl'
                    elif url_base.endswith('.fbx'):
                        extension = 'fbx'
                    else:
                        extension = 'glb'  # Default format

                filename = f"model_{i+1}.{extension}"
                local_path = output_path / filename

                logger.info(f"Downloading 3D model from {url}")
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                with open(local_path, 'wb') as f:
                    f.write(response.content)

                local_paths.append(str(local_path))
                logger.info(f"Downloaded 3D model to {local_path}")

            except Exception as e:
                logger.error(f"Failed to download model from {url}: {e}")
                # Continue with other downloads

        return local_paths

    def _submit_3d_job(self, task: Hunyuan3DTask) -> str:
        """Step 1: Submit 3D generation job (SubmitHunyuanTo3DJob).

        Args:
            task: 3D generation task

        Returns:
            JobId for tracking the task
        """
        # Prepare request parameters based on example
        params = {
            "EnablePBR": task.enable_pbr,      # Enable PBR for best quality
            "ResultFormat": task.result_format,  # Output format
        }

        # Choose input method (priority: image_url > image_base64 > prompt)
        if task.image_url:
            params["ImageUrl"] = task.image_url
        elif task.image_base64:
            params["ImageBase64"] = task.image_base64
        elif task.prompt:
            params["Prompt"] = task.prompt
        else:
            raise ValueError("Must provide at least one of: image_base64, image_url, or prompt")

        # Support for multi-view images (optional) - only left/right/back as per API spec
        if task.multi_views:
            params["MultiViewImages"] = []
            valid_views = ["left", "right", "back"]
            for view_type, view_url in task.multi_views.items():
                if view_url and view_type.lower() in valid_views:
                    params["MultiViewImages"].append({
                        "ViewType": view_type.lower(),
                        "ViewImageUrl": view_url
                    })

        try:
            # Submit the job using CommonClient call method
            resp = self.client.call("SubmitHunyuanTo3DJob", params)
            resp_data = json.loads(resp)

            # Extract JobId from response
            job_id = resp_data["Response"]["JobId"]
            logger.info(f"Submitted 3D job {task.task_id}, JobId: {job_id}")
            logger.info(f"JobId is valid for 24 hours")

            return job_id

        except TencentCloudSDKException as e:
            logger.error(f"Failed to submit 3D job {task.task_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error submitting 3D job {task.task_id}: {e}")
            raise

    def _poll_job_status(self, job_id: str) -> Dict[str, Any]:
        """Step 3: Poll job status until completion (QueryHunyuanTo3DJob).

        Args:
            job_id: Job ID to track

        Returns:
            Dictionary with status and results
        """
        start_time = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 3

        while time.time() - start_time < self.timeout:
            try:
                # Query job status using CommonClient call method
                resp = self.client.call("QueryHunyuanTo3DJob", {"JobId": job_id})
                resp_data = json.loads(resp)
                result = resp_data["Response"]

                # Reset error counter on successful query
                consecutive_errors = 0

                # Get job status
                job_status = result.get("Status")
                logger.info(f"Job {job_id} status: {job_status}")

                # Check completion status
                if job_status == "DONE":
                    # Step 4: Get 3D model URLs (ResultFile3Ds[].Url)
                    model_urls = []
                    file_types = {}  # Track file types for proper extensions

                    result_files = result.get("ResultFile3Ds", [])
                    for file_3d in result_files:
                        url = file_3d.get("Url")
                        file_type = file_3d.get("Type", "glb").lower()
                        if url:
                            model_urls.append(url)
                            file_types[url] = file_type

                    logger.info(f"Download URLs are valid for 24 hours")

                    return {
                        "status": "success",
                        "model_urls": model_urls,
                        "file_types": file_types,
                        "job_status": job_status
                    }

                elif job_status == "FAIL":
                    error_code = result.get("ErrorCode", "Unknown")
                    error_message = result.get("ErrorMessage", "Unknown error")
                    logger.error(f"Job {job_id} failed: {error_code} - {error_message}")
                    return {
                        "status": "failed",
                        "error": f"{error_code}: {error_message}",
                        "job_status": job_status
                    }

                elif job_status in ["WAIT", "RUN"]:
                    # Job still running, wait and poll again
                    logger.info(f"Job {job_id} still processing ({job_status}), waiting {self.poll_interval}s...")
                    time.sleep(self.poll_interval)
                else:
                    logger.warning(f"Job {job_id} unknown status: {job_status}, waiting...")
                    time.sleep(self.poll_interval)

            except TencentCloudSDKException as e:
                consecutive_errors += 1
                logger.warning(f"Error querying job {job_id} (attempt {consecutive_errors}): {e}")
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Max consecutive errors reached for job {job_id}")
                    return {
                        "status": "error",
                        "error": f"API query failed after {max_consecutive_errors} attempts: {e}",
                        "job_status": "ERROR"
                    }
                time.sleep(self.poll_interval)
            except Exception as e:
                consecutive_errors += 1
                logger.warning(f"Unexpected error querying job {job_id} (attempt {consecutive_errors}): {e}")
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Max consecutive errors reached for job {job_id}")
                    return {
                        "status": "error",
                        "error": f"Unexpected error after {max_consecutive_errors} attempts: {e}",
                        "job_status": "ERROR"
                    }
                time.sleep(self.poll_interval)

        # Timeout reached
        logger.error(f"Job {job_id} timed out after {self.timeout} seconds")
        return {
            "status": "timeout",
            "error": f"Job timed out after {self.timeout} seconds",
            "job_status": "TIMEOUT"
        }

    def generate_3d_from_task(self, task: Hunyuan3DTask) -> Hunyuan3DResult:
        """Generate 3D asset from task using the complete 4-step process.

        Args:
            task: 3D generation task

        Returns:
            Generation result with model files
        """
        start_time = time.time()

        try:
            logger.info(f"Starting 3D generation for task {task.task_id}")

            # Step 1: Submit job
            job_id = self._submit_3d_job(task)

            # Step 2: JobId is obtained (stored in job_id variable)
            logger.info(f"Job {task.task_id} submitted successfully! JobId: {job_id}")

            # Step 3: Poll for completion
            result = self._poll_job_status(job_id)

            generation_time = time.time() - start_time

            if result["status"] == "success" and result.get("model_urls"):
                # Step 4: Download 3D model files
                local_paths = []
                if task.output_dir and result.get("model_urls"):
                    try:
                        local_paths = self._download_3d_models(
                            result["model_urls"],
                            task.output_dir,
                            result.get("file_types", {})
                        )
                    except Exception as e:
                        logger.error(f"Failed to download 3D models for task {task.task_id}: {e}")

                return Hunyuan3DResult(
                    task_id=task.task_id,
                    success=True,
                    job_id=job_id,
                    model_urls=result["model_urls"],
                    local_paths=local_paths,
                    generation_time=generation_time
                )
            else:
                error_msg = result.get("error", "Unknown error")
                if result["status"] == "timeout":
                    error_msg = f"3D generation timed out: {error_msg}"
                elif result["status"] == "failed":
                    error_msg = f"3D generation failed: {error_msg}"

                return Hunyuan3DResult(
                    task_id=task.task_id,
                    success=False,
                    job_id=job_id,
                    error_message=error_msg,
                    generation_time=generation_time
                )

        except Exception as e:
            generation_time = time.time() - start_time
            logger.error(f"3D generation failed for task {task.task_id}: {e}")
            return Hunyuan3DResult(
                task_id=task.task_id,
                success=False,
                error_message=str(e),
                generation_time=generation_time
            )

    def generate_3d_from_image(
        self,
        image_path: str,
        task_id: str,
        output_dir: str
    ) -> Hunyuan3DResult:
        """Generate 3D asset from image file.

        Args:
            image_path: Path to input image
            task_id: Task identifier
            output_dir: Output directory for 3D models

        Returns:
            Generation result
        """
        # Convert image to base64
        image_base64 = self._encode_image_to_base64(image_path)

        task = Hunyuan3DTask(
            task_id=task_id,
            image_base64=image_base64,
            output_dir=output_dir
        )

        return self.generate_3d_from_task(task)

    def generate_3d_from_image_url(
        self,
        image_url: str,
        task_id: str,
        output_dir: str
    ) -> Hunyuan3DResult:
        """Generate 3D asset from image URL.

        Args:
            image_url: URL to input image
            task_id: Task identifier
            output_dir: Output directory for 3D models

        Returns:
            Generation result
        """
        task = Hunyuan3DTask(
            task_id=task_id,
            image_url=image_url,
            output_dir=output_dir
        )

        return self.generate_3d_from_task(task)

    def generate_3d_from_prompt(
        self,
        prompt: str,
        task_id: str,
        output_dir: str
    ) -> Hunyuan3DResult:
        """Generate 3D asset from text prompt.

        Args:
            prompt: Text description for 3D generation
            task_id: Task identifier
            output_dir: Output directory for 3D models

        Returns:
            Generation result
        """
        task = Hunyuan3DTask(
            task_id=task_id,
            prompt=prompt,
            output_dir=output_dir
        )

        return self.generate_3d_from_task(task)

    def test_connection(self) -> bool:
        """Test API connection and credentials."""
        try:
            # Try to query a test job ID to test credentials
            resp = self.client.call("QueryHunyuanTo3DJob", {"JobId": "test-connection"})
            # If we get here, the connection works but job doesn't exist (expected)
            logger.info("Connection test successful (unexpected success)")
            return True
        except Exception as e:
            error_str = str(e).lower()
            # Check for expected job not found errors
            if any(keyword in error_str for keyword in ["invalidjobid", "jobnotfound", "invalid job", "job not found", "resourceinsufficient"]):
                # This is expected for test job ID - connection works
                logger.info("Connection test successful (expected job not found error)")
                return True
            else:
                # Other errors indicate connection/credential issues
                logger.error(f"Connection test failed: {e}")
                return False


# Convenience function for simple usage
def generate_3d_asset(
    image_path: Optional[str] = None,
    image_url: Optional[str] = None,
    prompt: Optional[str] = None,
    output_dir: str = "output_3d",
    task_id: Optional[str] = None
) -> Hunyuan3DResult:
    """Simple function to generate 3D asset from image or prompt.

    Args:
        image_path: Path to input image (optional)
        image_url: URL to input image (optional)
        prompt: Text prompt for generation (optional)
        output_dir: Output directory
        task_id: Task identifier (auto-generated if None)

    Returns:
        Generation result
    """
    import os

    # Load environment variables from .env file if not already set
    if not os.getenv('HUNYUAN_SECRET_ID') or not os.getenv('HUNYUAN_SECRET_KEY'):
        try:
            from dotenv import load_dotenv
            # Try to load from current directory or parent directory
            env_paths = ['.env', '../.env', '../../.env', '../../../.env']
            loaded = False
            for env_path in env_paths:
                if os.path.exists(env_path):
                    load_dotenv(env_path)
                    loaded = True
                    logger.info(f"Loaded environment variables from {env_path}")
                    break

            if not loaded:
                logger.warning("No .env file found, trying manual loading")
        except ImportError:
            logger.info("dotenv not available, trying manual loading")
        except Exception as e:
            logger.warning(f"Failed to load with dotenv: {e}, trying manual loading")

        # Manual loading as fallback
        if not os.getenv('HUNYUAN_SECRET_ID') or not os.getenv('HUNYUAN_SECRET_KEY'):
            env_paths = ['.env', '../.env', '../../.env', '../../../.env']
            for env_path in env_paths:
                if os.path.exists(env_path):
                    try:
                        with open(env_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith('#') and '=' in line:
                                    # Handle potential quotes around the value
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip()

                                    # Remove quotes if present
                                    if (value.startswith('"') and value.endswith('"')) or \
                                       (value.startswith("'") and value.endswith("'")):
                                        value = value[1:-1]

                                    if key in ['HUNYUAN_SECRET_ID', 'HUNYUAN_SECRET_KEY']:
                                        os.environ[key] = value
                                        logger.info(f"Manually loaded {key} from {env_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to manually load {env_path}: {e}")

    if not task_id:
        task_id = f"task_{int(time.time())}"

    # Create client using environment variables with automatic .env loading
    client = Hunyuan3DClient.from_env()

    # Generate based on input type
    if image_path:
        return client.generate_3d_from_image(image_path, task_id, output_dir)
    elif image_url:
        return client.generate_3d_from_image_url(image_url, task_id, output_dir)
    elif prompt:
        return client.generate_3d_from_prompt(prompt, task_id, output_dir)

    async def generate_3d_from_image(
        self,
        image_path: Union[str, Path],
        output_format: str = "glb",
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate 3D model from input image - async wrapper."""
        # Convert to sync call for now
        image_path = Path(image_path)
        if output_dir:
            output_dir = str(output_dir)

        task_id = kwargs.get('task_id', f"task_{int(time.time())}")

        # Convert image to base64
        image_base64 = self._encode_image_to_base64(str(image_path))

        task = Hunyuan3DTask(
            task_id=task_id,
            image_base64=image_base64,
            output_dir=output_dir
        )

        result = self.generate_3d_from_task(task)

        return GenerationResult(
            success=result.success,
            data=result.local_paths[0] if result.local_paths else None,
            metadata={
                "task_id": result.task_id,
                "job_id": result.job_id,
                "model_urls": result.model_urls,
                "generation_time": result.generation_time,
                "output_format": output_format
            },
            error=result.error_message,
            duration=result.generation_time
        )

    async def generate_3d_from_prompt(
        self,
        prompt: str,
        output_format: str = "glb",
        output_dir: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate 3D model from text prompt - async wrapper."""
        # Convert to sync call for now
        if output_dir:
            output_dir = str(output_dir)

        task_id = kwargs.get('task_id', f"task_{int(time.time())}")

        task = Hunyuan3DTask(
            task_id=task_id,
            prompt=prompt,
            output_dir=output_dir
        )

        result = self.generate_3d_from_task(task)

        return GenerationResult(
            success=result.success,
            data=result.local_paths[0] if result.local_paths else None,
            metadata={
                "task_id": result.task_id,
                "job_id": result.job_id,
                "model_urls": result.model_urls,
                "generation_time": result.generation_time,
                "output_format": output_format
            },
            error=result.error_message,
            duration=result.generation_time
        )