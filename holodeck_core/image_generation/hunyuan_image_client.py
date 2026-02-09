"""Tencent Hunyuan Image 3.0 client for image generation.

Provides async interface to Tencent Cloud Hunyuan Image API for
high-quality text-to-image generation.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

from ..clients.base import BaseImageClient, GenerationResult, ClientConfig
from ..config.base import ConfigManager
from ..logging.standardized import get_logger


logger = get_logger(__name__)


class HunyuanImageClient(BaseImageClient):
    """Client for Tencent Cloud Hunyuan Image 3.0 generation."""

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        logger: Optional[logging.Logger] = None,
        client_config: Optional[ClientConfig] = None,
        secret_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "ap-guangzhou",
        timeout: int = 120
    ):
        """Initialize Hunyuan Image client.

        Args:
            config_manager: Configuration manager instance
            logger: Logger instance
            client_config: Client-specific configuration
            secret_id: Tencent Cloud SecretId (if not using config_manager)
            secret_key: Tencent Cloud SecretKey (if not using config_manager)
            region: API region (default: ap-guangzhou)
            timeout: Timeout in seconds for generation operations
        """
        super().__init__(config_manager, logger, client_config)

        # Get credentials from config manager or direct parameters
        if secret_id and secret_key:
            self.secret_id = secret_id
            self.secret_key = secret_key
        else:
            self.secret_id = self.config_manager.get_config("HUNYUAN_SECRET_ID")
            self.secret_key = self.config_manager.get_config("HUNYUAN_SECRET_KEY")

        self.region = region
        self.timeout = timeout
        self.client = None

    def validate_configuration(self) -> bool:
        """Validate client configuration.

        Returns:
            True if configuration is valid

        Raises:
            Exception: If configuration is invalid
        """
        if not self.secret_id or not self.secret_key:
            raise Exception("HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY are required")

        # Check for placeholder values
        if self.secret_id == "your-hunyuan-secret-id" or self.secret_key == "your-hunyuan-secret-key":
            raise Exception("Please replace placeholder Hunyuan credentials with actual values")

        return True

    def _setup_client(self) -> None:
        """Setup client-specific configuration and connections"""
        # Initialize Tencent Cloud client
        self.cred = credential.Credential(self.secret_id, self.secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        self.client = hunyuan_client.HunyuanClient(self.cred, self.region, clientProfile)

        self.logger.info(f"Initialized Hunyuan Image client for region {self.region}")

    async def validate_prompt(self, prompt: str) -> bool:
        """
        Validate if prompt is acceptable for generation.

        Args:
            prompt: Text prompt to validate

        Returns:
            True if prompt is valid

        Raises:
            Exception: If prompt is invalid
        """
        if not prompt or not prompt.strip():
            raise Exception("Prompt cannot be empty")

        if len(prompt) > 1000:
            raise Exception("Prompt too long (max 1000 characters)")

        # Check for inappropriate content
        inappropriate_words = ["violent", "nudity", "hate speech", "illegal"]
        prompt_lower = prompt.lower()
        for word in inappropriate_words:
            if word in prompt_lower:
                raise Exception(f"Prompt contains inappropriate content: {word}")

        return True

    async def generate_image(
        self,
        prompt: str,
        resolution: str = "1024:1024",
        style: Optional[str] = None,
        model: str = "hunyuan-pro",
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> GenerationResult:
        """Generate image using Hunyuan Image 3.0.

        Args:
            prompt: Text prompt for image generation
            resolution: Image resolution (e.g., "1024:1024", "768:1024", "1280:720")
            style: Artistic style (e.g., "501" for 3D Pixar style). If None, uses default.
            model: Model version ("hunyuan-pro" or "standard")
            output_path: Optional path to save the generated image
            **kwargs: Additional parameters

        Returns:
            GenerationResult containing image data and metadata
        """
        start_time = time.time()

        try:
            # Validate inputs using base class method
            self._validate_inputs(prompt=prompt, resolution=resolution)

            # Ensure client is initialized
            self.ensure_initialized()

            # Build request parameters
            params = {
                "Prompt": prompt,
                "Resolution": resolution,
                "Model": model
            }

            # Only add Style if provided (recommended approach)
            if style is not None:
                params["Style"] = style

            # Submit generation job
            req_submit = models.SubmitHunyuanImageJobRequest()
            req_submit.from_json_string(json.dumps(params))

            self.logger.info(f"Submitting Hunyuan Image generation job: {prompt[:50]}...")
            resp_submit = self.client.SubmitHunyuanImageJob(req_submit)
            job_id = resp_submit.JobId
            self.logger.info(f"Job submitted successfully! JobId: {job_id}")

            # Poll for completion
            result = self._poll_job_completion(job_id)

            generation_time = time.time() - start_time

            # Build metadata
            metadata = {
                "backend": "hunyuan",
                "prompt": prompt,
                "resolution": resolution,
                "model": model,
                "style": style,
                "generation_time_sec": round(generation_time, 2),
                "job_id": job_id
            }

            # Save image if output path provided
            local_path = None
            if output_path and result.get("image_url"):
                output_path = Path(output_path)
                self._download_image(result["image_url"], str(output_path))
                local_path = str(output_path)

            if result["status"] == "success":
                return GenerationResult(
                    success=True,
                    data=local_path or result.get("image_url"),
                    metadata=metadata,
                    duration=generation_time
                )
            else:
                return GenerationResult(
                    success=False,
                    error=result.get("error", "Generation failed"),
                    metadata=metadata,
                    duration=generation_time
                )

        except Exception as e:
            generation_time = time.time() - start_time
            self.logger.error(f"Hunyuan Image generation failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                metadata={
                    "backend": "hunyuan",
                    "prompt": prompt,
                    "resolution": resolution,
                    "model": model,
                    "style": style
                },
                duration=generation_time
            )

    def _poll_job_completion(self, job_id: str) -> Dict[str, Any]:
        """Poll job status until completion.

        Args:
            job_id: Job identifier

        Returns:
            Dictionary with completion status and results
        """
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            try:
                req_query = models.QueryHunyuanImageJobRequest()
                req_query.JobId = job_id
                resp_query = self.client.QueryHunyuanImageJob(req_query)

                # 根据实际API响应使用正确的属性名
                if hasattr(resp_query, 'JobStatusCode'):
                    job_status = resp_query.JobStatusCode
                else:
                    # 打印响应对象的所有属性来调试
                    logger.error(f"Query response attributes: {dir(resp_query)}")
                    raise AttributeError("Cannot find job status attribute in response")

                # 调试：打印实际状态值
                logger.info(f"Job {job_id} JobStatusCode: {job_status}")

                # 状态码映射: 2=运行中, 3=失败, 其他值可能是完成
                if job_status in [3, "3", "FAILED", "ERROR"]:
                    error_msg = getattr(resp_query, 'JobErrorMsg', 'Unknown error')
                    logger.error(f"Job {job_id} failed: {error_msg}")
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "job_status": job_status
                    }
                elif job_status not in [2, "2", "RUNNING", "WAITING"]:
                    # 不是2(运行中)的状态可能是完成状态
                    logger.info(f"Job {job_id} completed with status: {job_status}")

                    # Try different ways to get image URL
                    image_url = None
                    if hasattr(resp_query, 'ResultImage') and resp_query.ResultImage:
                        image_url = resp_query.ResultImage[0]
                    elif hasattr(resp_query, 'ResultDetails') and resp_query.ResultDetails:
                        # Try to parse ResultDetails for image URL
                        result_details = resp_query.ResultDetails
                        if isinstance(result_details, list) and result_details:
                            image_url = result_details[0]
                        elif isinstance(result_details, str):
                            # Try to parse as JSON
                            try:
                                import json
                                details_json = json.loads(result_details)
                                if isinstance(details_json, list) and details_json:
                                    image_url = details_json[0].get('url') or details_json[0]
                            except:
                                pass

                    return {
                        "status": "success",
                        "image_url": image_url,
                        "job_status": job_status
                    }

                else:
                    # Still running (RUNNING or WAITING)
                    logger.info(f"Job {job_id} status: {job_status}, waiting...")
                    time.sleep(2)

            except Exception as e:
                logger.warning(f"Error polling job status: {e}")
                time.sleep(2)

        # Timeout
        raise TimeoutError(f"Hunyuan Image generation timed out after {self.timeout} seconds")

    def _download_image(self, image_url: str, output_path: str) -> None:
        """Download generated image from URL.

        Args:
            image_url: URL of the generated image
            output_path: Local path to save the image
        """
        try:
            import requests

            logger.info(f"Downloading image from {image_url}")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Image saved to {output_path}")

        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            raise

    async def test_connection(self) -> bool:
        """Test if Hunyuan Image API is accessible.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Ensure client is initialized
            self.ensure_initialized()

            # Try a simple generation request to test connectivity
            test_prompt = "test"
            params = {
                "Prompt": test_prompt,
                "Resolution": "1024:1024",
                "Model": "hunyuan-pro"
            }

            req_submit = models.SubmitHunyuanImageJobRequest()
            req_submit.from_json_string(json.dumps(params))

            # Just submit, don't wait for completion
            resp_submit = self.client.SubmitHunyuanImageJob(req_submit)

            self.logger.info("Hunyuan Image API connection test successful")
            return True

        except Exception as e:
            self.logger.error(f"Hunyuan Image API connection test failed: {e}")
            return False


# Convenience functions for easy integration

def create_hunyuan_client_from_env() -> HunyuanImageClient:
    """Create Hunyuan client using environment variables.

    Expects HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY in environment.

    Returns:
        Configured HunyuanImageClient instance

    Raises:
        ValueError: If required environment variables are missing
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

    secret_id = os.getenv("HUNYUAN_SECRET_ID")
    secret_key = os.getenv("HUNYUAN_SECRET_KEY")

    if not secret_id or not secret_key:
        raise ValueError(
            "HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY environment variables required"
        )

    return HunyuanImageClient(secret_id=secret_id, secret_key=secret_key)


def generate_scene_reference(
    prompt: str,
    output_path: str,
    style: Optional[str] = None,
    client: Optional[HunyuanImageClient] = None
) -> Dict[str, Any]:
    """Generate scene reference image using Hunyuan Image.

    Args:
        prompt: Scene description prompt
        output_path: Path to save generated image
        style: Optional style parameter (recommended to leave None for default)
        client: Optional pre-configured client

    Returns:
        Generation result dictionary
    """
    if client is None:
        client = create_hunyuan_client_from_env()

    import asyncio
    return asyncio.run(client.generate_image(
        prompt=prompt,
        resolution="1024:1024",
        style=style,  # Leave as None for default style (recommended)
        model="hunyuan-pro",
        output_path=output_path
    ))


def generate_object_card(
    object_name: str,
    description: str,
    output_path: str,
    style: Optional[str] = None,
    client: Optional[HunyuanImageClient] = None
) -> Dict[str, Any]:
    """Generate object card image using Hunyuan Image.

    Args:
        object_name: Name of the object
        description: Detailed description for generation
        output_path: Path to save generated image
        style: Optional style parameter
        client: Optional pre-configured client

    Returns:
        Generation result dictionary
    """
    if client is None:
        client = create_hunyuan_client_from_env()

    # Build comprehensive prompt for object card
    prompt = f"{object_name}: {description}. Isolated object on neutral background, high detail, professional product photography style"

    import asyncio
    return asyncio.run(client.generate_image(
        prompt=prompt,
        resolution="1024:1024",
        style=style,
        model="hunyuan-pro",
        output_path=output_path
    ))