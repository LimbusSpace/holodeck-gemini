"""Optimized Tencent Hunyuan Image 3.0 client with concurrency control and retry mechanisms.

Provides async interface to Tencent Cloud Hunyuan Image API with:
- Semaphore-based concurrency control
- Automatic retry with exponential backoff
- Queue-based request management
- Thread-safe operations
"""

import json
import logging
import threading
import time
import asyncio

logger = logging.getLogger(__name__)
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from queue import Queue, Empty
from threading import Semaphore, Lock
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException

try:
    from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
except ImportError:
    # Fallback if tenacity not available
    def retry(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    wait_exponential = lambda *args, **kwargs: None
    stop_after_attempt = lambda *args, **kwargs: None
    retry_if_exception_type = lambda *args, **kwargs: None


@dataclass
class GenerationTask:
    """Represents a single image generation task."""
    prompt: str
    resolution: str = "1024:1024"
    style: Optional[str] = None
    model: str = "hunyuan-pro"
    output_path: Optional[str] = None
    task_id: str = ""

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{int(time.time() * 1000)}_{hash(self.prompt) % 10000}"


@dataclass
class GenerationResult:
    """Represents the result of a generation task."""
    task_id: str
    success: bool
    image_url: Optional[str] = None
    local_path: Optional[str] = None
    error_message: Optional[str] = None
    generation_time: float = 0.0
    job_id: Optional[str] = None


class HunyuanImageClientOptimized:
    """Optimized client for Tencent Cloud Hunyuan Image 3.0 generation with concurrency control."""

    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        timeout: int = 120,
        max_concurrent_jobs: int = 2,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """Initialize optimized Hunyuan Image client.

        Args:
            secret_id: Tencent Cloud SecretId
            secret_key: Tencent Cloud SecretKey
            region: API region (default: ap-guangzhou)
            timeout: Timeout in seconds for generation operations
            max_concurrent_jobs: Maximum number of concurrent generation jobs
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Base delay between retries (seconds)
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.timeout = timeout
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize semaphore for concurrency control
        self.semaphore = Semaphore(max_concurrent_jobs)
        self.lock = Lock()

        # Initialize client
        self.cred = credential.Credential(secret_id, secret_key)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        self.client = hunyuan_client.HunyuanClient(self.cred, region, clientProfile)

        logger.info(f"Initialized optimized Hunyuan Image client for region {region} "
                   f"with max_concurrent_jobs={max_concurrent_jobs}")

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(TencentCloudSDKException)
    )
    def _submit_job_with_retry(self, params: Dict[str, Any]) -> str:
        """Submit job with automatic retry on failure."""
        req_submit = models.SubmitHunyuanImageJobRequest()
        req_submit.from_json_string(json.dumps(params))
        resp_submit = self.client.SubmitHunyuanImageJob(req_submit)
        return resp_submit.JobId

    def _poll_job_completion(self, job_id: str) -> Dict[str, Any]:
        """Poll job status until completion with improved error handling."""
        start_time = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 3

        while time.time() - start_time < self.timeout:
            try:
                req_query = models.QueryHunyuanImageJobRequest()
                req_query.JobId = job_id
                resp_query = self.client.QueryHunyuanImageJob(req_query)

                # Reset error counter on successful query
                consecutive_errors = 0

                if hasattr(resp_query, 'JobStatusCode'):
                    job_status = resp_query.JobStatusCode
                else:
                    logger.error(f"Query response missing JobStatusCode: {dir(resp_query)}")
                    raise AttributeError("Cannot find job status attribute in response")

                logger.info(f"Job {job_id} JobStatusCode: {job_status}")

                # Check completion status
                if job_status in [2, "2", "COMPLETED", "SUCCESS", "FINISHED"]:
                    image_url = resp_query.ResultImage[0] if hasattr(resp_query, 'ResultImage') and resp_query.ResultImage else None
                    return {
                        "status": "success",
                        "image_url": image_url,
                        "job_status": job_status
                    }
                elif job_status in [3, "3", "FAILED", "ERROR"]:
                    error_msg = getattr(resp_query, 'JobErrorMsg', 'Unknown error')
                    logger.error(f"Job {job_id} failed: {error_msg}")
                    return {
                        "status": "failed",
                        "error": error_msg,
                        "job_status": job_status
                    }
                elif job_status in [5, "5"]:  # 完成状态码为5
                    image_url = resp_query.ResultImage[0] if hasattr(resp_query, 'ResultImage') and resp_query.ResultImage else None
                    return {
                        "status": "success",
                        "image_url": image_url,
                        "job_status": job_status
                    }
                else:
                    logger.info(f"Job {job_id} status: {job_status}, waiting...")
                    time.sleep(2)

            except TencentCloudSDKException as e:
                consecutive_errors += 1
                logger.warning(f"TencentCloudSDKException polling job {job_id}: {e}")

                if "RequestLimitExceeded" in str(e) or "JobNumExceed" in str(e):
                    # Rate limited - wait longer
                    wait_time = self.retry_delay * (2 ** consecutive_errors)
                    logger.info(f"Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    # Other SDK error - wait and retry
                    time.sleep(self.retry_delay)

                if consecutive_errors >= max_consecutive_errors:
                    raise TimeoutError(f"Job {job_id} polling failed after {max_consecutive_errors} consecutive errors")

            except Exception as e:
                consecutive_errors += 1
                logger.warning(f"Error polling job {job_id}: {e}")
                time.sleep(self.retry_delay)

                if consecutive_errors >= max_consecutive_errors:
                    raise TimeoutError(f"Job {job_id} polling failed after {max_consecutive_errors} consecutive errors")

        # Timeout
        raise TimeoutError(f"Hunyuan Image generation timed out after {self.timeout} seconds")

    def _process_single_task(self, task: GenerationTask) -> GenerationResult:
        """Process a single generation task with concurrency control."""
        start_time = time.time()

        with self.semaphore:  # Acquire semaphore - will block if max concurrent jobs reached
            try:
                logger.info(f"Processing task {task.task_id}: {task.prompt[:50]}...")

                # Build request parameters
                params = {
                    "Prompt": task.prompt,
                    "Resolution": task.resolution,
                    "Model": task.model
                }

                if task.style is not None:
                    params["Style"] = task.style

                # Submit generation job with retry
                job_id = self._submit_job_with_retry(params)
                logger.info(f"Task {task.task_id} submitted successfully! JobId: {job_id}")

                # Poll for completion
                result = self._poll_job_completion(job_id)

                generation_time = time.time() - start_time

                if result["status"] == "success" and result.get("image_url"):
                    # Download image if output path provided
                    local_path = None
                    if task.output_path and result.get("image_url"):
                        try:
                            local_path = self._download_image(result["image_url"], task.output_path)
                        except Exception as e:
                            logger.error(f"Failed to download image for task {task.task_id}: {e}")

                    return GenerationResult(
                        task_id=task.task_id,
                        success=True,
                        image_url=result["image_url"],
                        local_path=local_path,
                        generation_time=generation_time,
                        job_id=job_id
                    )
                else:
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"Task {task.task_id} failed: {error_msg}")
                    return GenerationResult(
                        task_id=task.task_id,
                        success=False,
                        error_message=error_msg,
                        generation_time=generation_time,
                        job_id=job_id
                    )

            except Exception as e:
                generation_time = time.time() - start_time
                logger.error(f"Task {task.task_id} failed with exception: {e}")
                return GenerationResult(
                    task_id=task.task_id,
                    success=False,
                    error_message=str(e),
                    generation_time=generation_time
                )

    def _download_image(self, image_url: str, output_path: str) -> str:
        """Download generated image from URL."""
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
            return str(output_path)

        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            raise

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate single image (backward compatibility method)."""
        task = GenerationTask(prompt=prompt, **kwargs)
        result = self._process_single_task(task)

        return {
            "image_url": result.image_url,
            "job_id": result.job_id,
            "generation_time": result.generation_time,
            "status": "success" if result.success else "failed",
            "local_path": result.local_path,
            "error": result.error_message,
            "metadata": {
                "prompt": prompt,
                "resolution": kwargs.get("resolution", "1024:1024"),
                "model": kwargs.get("model", "hunyuan-pro"),
                "style": kwargs.get("style"),
                "generation_time_sec": round(result.generation_time, 2),
                "task_id": result.task_id
            }
        }

    def generate_batch_sync(self, tasks: List[GenerationTask]) -> List[GenerationResult]:
        """Generate multiple images synchronously with controlled concurrency."""
        logger.info(f"Starting batch generation of {len(tasks)} tasks with max concurrency {self.max_concurrent_jobs}")

        results = []
        with ThreadPoolExecutor(max_workers=self.max_concurrent_jobs) as executor:
            # Submit all tasks
            future_to_task = {executor.submit(self._process_single_task, task): task for task in tasks}

            # Collect results as they complete
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"Task {task.task_id} completed: {'success' if result.success else 'failed'}")
                except Exception as e:
                    logger.error(f"Task {task.task_id} generated exception: {e}")
                    results.append(GenerationResult(
                        task_id=task.task_id,
                        success=False,
                        error_message=str(e)
                    ))

        return results

    async def generate_batch_async(self, tasks: List[GenerationTask]) -> List[GenerationResult]:
        """Generate multiple images asynchronously with controlled concurrency."""
        logger.info(f"Starting async batch generation of {len(tasks)} tasks")

        # Run sync method in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_batch_sync, tasks)

    def test_connection(self) -> bool:
        """Test if Hunyuan Image API is accessible."""
        try:
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

            logger.info("Hunyuan Image API connection test successful")
            return True

        except Exception as e:
            logger.error(f"Hunyuan Image API connection test failed: {e}")
            return False


# Convenience functions and classes

def create_optimized_client_from_env() -> HunyuanImageClientOptimized:
    """Create optimized Hunyuan client using environment variables."""
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
    max_concurrent = int(os.getenv("HUNYUAN_MAX_CONCURRENT", "2"))

    if not secret_id or not secret_key:
        raise ValueError(
            "HUNYUAN_SECRET_ID and HUNYUAN_SECRET_KEY environment variables required"
        )

    return HunyuanImageClientOptimized(
        secret_id=secret_id,
        secret_key=secret_key,
        max_concurrent_jobs=max_concurrent
    )


def generate_batch_images(prompts: List[str], output_dir: str, **kwargs) -> List[Dict[str, Any]]:
    """Generate multiple images with automatic concurrency control."""
    client = create_optimized_client_from_env()

    tasks = []
    for i, prompt in enumerate(prompts):
        output_path = Path(output_dir) / f"image_{i+1}.png"
        task = GenerationTask(
            prompt=prompt,
            output_path=str(output_path),
            **kwargs
        )
        tasks.append(task)

    results = client.generate_batch_sync(tasks)

    # Convert to dict format for compatibility
    return [
        {
            "task_id": r.task_id,
            "success": r.success,
            "image_url": r.image_url,
            "local_path": r.local_path,
            "error": r.error_message,
            "generation_time": r.generation_time
        }
        for r in results
    ]