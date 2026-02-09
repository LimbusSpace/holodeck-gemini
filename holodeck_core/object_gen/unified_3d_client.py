#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified 3D Generation Client

Provides a unified interface for all 3D generation backends with:
- Standardized workflow handling
- Consistent polling mechanisms
- Resource cleanup and management
- Error recovery and fallback
- Performance monitoring
"""

import asyncio
import time
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple
from dataclasses import dataclass
import aiofiles

from ..config.base import ConfigManager
from ..logging.standardized import StandardizedLogger, get_logger, log_time
from ..exceptions.framework import (
    ThreeDGenerationError, ValidationError, APIError, ConfigurationError, ResourceError
)
from ..clients.base import Base3DClient, GenerationResult, ServiceType, ClientConfig
from ..clients.factory import ThreeDClientFactory, create_3d_client


@dataclass
class WorkflowConfig:
    """Configuration for 3D generation workflows"""
    max_polling_time: int = 600  # 10 minutes
    polling_interval: float = 3.0  # 3 seconds
    max_concurrent_jobs: int = 5
    cleanup_temp_files: bool = True
    retry_failed_jobs: bool = True
    max_retries: int = 2


@dataclass
class ResourceLimits:
    """Resource limits for 3D generation"""
    max_file_size_mb: int = 100
    max_polling_attempts: int = 200
    max_temp_files: int = 10
    max_concurrent_operations: int = 3


class ResourceManager:
    """Manages temporary files and resources for 3D generation"""

    def __init__(self, cleanup_enabled: bool = True):
        """
        Initialize resource manager.

        Args:
            cleanup_enabled: Whether to automatically cleanup temporary files
        """
        self.cleanup_enabled = cleanup_enabled
        self.temp_dir = Path(tempfile.gettempdir()) / "holodeck_3d"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.active_files = set()
        self.logger = get_logger(__name__)

    def create_temp_file(self, suffix: str =".glb", prefix: str = "3d_") -> Path:
        """Create a temporary file for 3D generation"""
        import tempfile

        temp_file = Path(tempfile.mktemp(suffix=suffix, prefix=prefix, dir=self.temp_dir))
        self.active_files.add(temp_file)
        return temp_file

    def create_temp_dir(self, prefix: str = "3d_job_") -> Path:
        """Create a temporary directory for 3D generation job"""
        import tempfile

        temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=self.temp_dir))
        self.active_files.add(temp_dir)
        return temp_dir

    def cleanup_file(self, file_path: Path) -> None:
        """Cleanup a specific temporary file"""
        try:
            if file_path in self.active_files:
                if file_path.is_file():
                    file_path.unlink(missing_ok=True)
                elif file_path.is_dir():
                    shutil.rmtree(file_path, ignore_errors=True)

                self.active_files.discard(file_path)
                self.logger.debug(f"Cleaned up temporary file: {file_path}")

        except Exception as e:
            self.logger.warning(f"Failed to cleanup file {file_path}: {e}")

    def cleanup_all(self) -> None:
        """Cleanup all temporary files"""
        if not self.cleanup_enabled:
            return

        for file_path in list(self.active_files):
            self.cleanup_file(file_path)

        # Cleanup old files in temp directory
        try:
            current_time = time.time()
            for item in self.temp_dir.iterdir():
                if item.is_file():
                    # Remove files older than 1 hour
                    if current_time - item.stat().st_mtime > 3600:
                        item.unlink(missing_ok=True)
                elif item.is_dir():
                    # Remove directories older than 1 hour
                    if current_time - item.stat().st_mtime > 3600:
                        shutil.rmtree(item, ignore_errors=True)

        except Exception as e:
            self.logger.warning(f"Failed to cleanup old temporary files: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup_all()


class JobManager:
    """Manages 3D generation jobs with proper tracking and cleanup"""

    def __init__(self, max_concurrent: int = 5):
        """
        Initialize job manager.

        Args:
            max_concurrent: Maximum concurrent jobs
        """
        self.max_concurrent = max_concurrent
        self.active_jobs = {}
        self.completed_jobs = {}
        self.failed_jobs = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = get_logger(__name__)

    async def submit_job(self, job_id: str, job_func, *args, **kwargs) -> Any:
        """Submit a job for execution"""
        async with self.semaphore:
            self.active_jobs[job_id] = {
                "start_time": time.time(),
                "status": "running"
            }

            try:
                self.logger.info(f"Starting job: {job_id}")
                result = await job_func(*args, **kwargs)

                self.active_jobs[job_id]["status"] = "completed"
                self.active_jobs[job_id]["end_time"] = time.time()
                self.active_jobs[job_id]["result"] = result

                self.completed_jobs[job_id] = self.active_jobs.pop(job_id)
                self.logger.info(f"Job completed: {job_id}")

                return result

            except Exception as e:
                self.active_jobs[job_id]["status"] = "failed"
                self.active_jobs[job_id]["end_time"] = time.time()
                self.active_jobs[job_id]["error"] = str(e)

                self.failed_jobs[job_id] = self.active_jobs.pop(job_id)
                self.logger.error(f"Job failed: {job_id} - {e}")
                raise

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        elif job_id in self.completed_jobs:
            return self.completed_jobs[job_id]
        elif job_id in self.failed_jobs:
            return self.failed_jobs[job_id]
        return None

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> None:
        """Cleanup old completed and failed jobs"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        # Cleanup completed jobs
        old_completed = [
            job_id for job_id, job_info in self.completed_jobs.items()
            if current_time - job_info["end_time"] > max_age_seconds
        ]
        for job_id in old_completed:
            del self.completed_jobs[job_id]

        # Cleanup failed jobs
        old_failed = [
            job_id for job_id, job_info in self.failed_jobs.items()
            if current_time - job_info["end_time"] > max_age_seconds
        ]
        for job_id in old_failed:
            del self.failed_jobs[job_id]

        if old_completed or old_failed:
            self.logger.info(f"Cleaned up {len(old_completed) + len(old_failed)} old jobs")


class Unified3DClient(Base3DClient):
    """
    Unified interface for all 3D generation backends.

    Features:
    - Standardized workflow handling across backends
    - Consistent polling mechanisms with timeout handling
    - Resource cleanup and management
    - Error recovery and automatic fallback
    - Performance monitoring and statistics
    - Intelligent backend selection based on input type
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        client_config: Optional[ClientConfig] = None,
        workflow_config: Optional[WorkflowConfig] = None,
        resource_limits: Optional[ResourceLimits] = None
    ):
        """
        Initialize unified 3D client.

        Args:
            config_manager: Configuration manager instance
            client_config: Client-specific configuration
            workflow_config: Workflow configuration
            resource_limits: Resource limits configuration
        """
        super().__init__(config_manager, None, client_config)

        # Setup workflow configuration
        self.workflow_config = workflow_config or WorkflowConfig()

        # Setup resource limits
        self.resource_limits = resource_limits or ResourceLimits()

        # Initialize resource and job managers
        self.resource_manager = ResourceManager(self.workflow_config.cleanup_temp_files)
        self.job_manager = JobManager(self.resource_limits.max_concurrent_operations)

        # Initialize backend factory
        self.backend_factory = ThreeDClientFactory(self.config_manager)

        # Track backend performance
        self.backend_stats = {}

        self.logger.info("Unified 3D Client initialized")

    def get_service_type(self) -> ServiceType:
        return ServiceType.THREED_GENERATION

    def validate_configuration(self) -> bool:
        """Validate client configuration"""
        try:
            # Check if at least one 3D backend is configured
            backend_info = self.backend_factory.get_client_info()

            if not backend_info["configured_clients"]:
                raise ConfigurationError(
                    "No 3D generation backends are configured. "
                    "Please configure at least one backend (SF3D, Hunyuan3D, etc.)."
                )

            self.logger.info(
                f"Configuration validated. Available backends: {backend_info['configured_clients']}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise ConfigurationError(f"3D client configuration invalid: {e}")

    def _setup_client(self) -> None:
        """Setup client-specific configuration"""
        # Initialize backend statistics
        backend_info = self.backend_factory.get_client_info()
        for backend in backend_info["configured_clients"]:
            self.backend_stats[backend] = {
                "success_count": 0,
                "failure_count": 0,
                "avg_generation_time": 0.0,
                "avg_file_size_mb": 0.0,
                "last_used": 0
            }

    @log_time("generate_3d_from_image")
    async def generate_3d_from_image(
        self,
        image_path: Union[str, Path],
        output_format: str = "glb",
        output_dir: Optional[Union[str, Path]] = None,
        backend: Optional[str] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate 3D model from input image using best available backend.

        Args:
            image_path: Path to input image
            output_format: Output format (glb, obj, fbx, etc.)
            output_dir: Directory to save generated 3D model
            backend: Specific backend to use (None for auto-selection)
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult containing 3D model data and metadata
        """
        start_time = time.time()

        try:
            # Input validation
            self._validate_inputs(image_path=image_path, output_format=output_format, **kwargs)

            # Convert to Path objects
            image_path = Path(image_path)

            # Select optimal backend
            selected_backend = await self._select_backend(
                backend, "image_to_3d", output_format, **kwargs
            )

            # Setup output directory
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = self.resource_manager.create_temp_dir("3d_output_")

            # Generate 3D model
            result = await self._generate_3d_with_backend(
                selected_backend,
                image_path=image_path,
                output_format=output_format,
                output_dir=output_dir,
                **kwargs
            )

            # Update backend statistics
            duration = time.time() - start_time
            file_size = self._get_file_size(result.data) if result.data else 0
            self._update_backend_stats(selected_backend, True, duration, file_size)

            # Log success
            self.logger.info(
                f"3D generation completed: {image_path.name} -> {output_format}",
                context={
                    "backend": selected_backend,
                    "duration": duration,
                    "file_size_mb": file_size,
                    "output_format": output_format
                }
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Update backend statistics on failure
            if 'selected_backend' in locals():
                self._update_backend_stats(selected_backend, False, duration, 0)

            # Log error
            self.logger.error(
                f"3D generation from image failed: {e}",
                context={
                    "image": str(image_path),
                    "format": output_format,
                    "error": str(e)
                }
            )

            # Convert to appropriate error type
            if isinstance(e, ValidationError):
                raise
            elif isinstance(e, (APIError, ConfigurationError)):
                raise ThreeDGenerationError(
                    f"3D generation failed: {e}",
                    image_path=image_path,
                    backend=backend or "unknown"
                )
            else:
                raise ThreeDGenerationError(
                    f"Unexpected error in 3D generation: {e}",
                    image_path=image_path,
                    backend=backend or "unknown"
                )

    @log_time("generate_3d_from_prompt")
    async def generate_3d_from_prompt(
        self,
        prompt: str,
        output_format: str = "glb",
        output_dir: Optional[Union[str, Path]] = None,
        backend: Optional[str] = None,
        **kwargs
    ) -> GenerationResult:
        """
        Generate 3D model from text prompt using best available backend.

        Args:
            prompt: Text description for 3D generation
            output_format: Output format
            output_dir: Directory to save generated 3D model
            backend: Specific backend to use (None for auto-selection)
            **kwargs: Additional generation parameters

        Returns:
            GenerationResult containing 3D model data and metadata
        """
        start_time = time.time()

        try:
            # Input validation
            self._validate_inputs(prompt=prompt, output_format=output_format, **kwargs)

            # Select optimal backend
            selected_backend = await self._select_backend(
                backend, "text_to_3d", output_format, **kwargs
            )

            # Setup output directory
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = self.resource_manager.create_temp_dir("3d_output_")

            # Generate 3D model
            result = await self._generate_3d_with_backend(
                selected_backend,
                prompt=prompt,
                output_format=output_format,
                output_dir=output_dir,
                **kwargs
            )

            # Update backend statistics
            duration = time.time() - start_time
            file_size = self._get_file_size(result.data) if result.data else 0
            self._update_backend_stats(selected_backend, True, duration, file_size)

            # Log success
            self.logger.info(
                f"3D generation from prompt completed",
                context={
                    "backend": selected_backend,
                    "duration": duration,
                    "file_size_mb": file_size,
                    "output_format": output_format,
                    "prompt": prompt[:50]
                }
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            # Update backend statistics on failure
            if 'selected_backend' in locals():
                self._update_backend_stats(selected_backend, False, duration, 0)

            # Log error
            self.logger.error(
                f"3D generation from prompt failed: {e}",
                context={
                    "prompt": prompt[:50],
                    "format": output_format,
                    "error": str(e)
                }
            )

            # Convert to appropriate error type
            if isinstance(e, ValidationError):
                raise
            elif isinstance(e, (APIError, ConfigurationError)):
                raise ThreeDGenerationError(
                    f"3D generation failed: {e}",
                    backend=backend or "unknown"
                )
            else:
                raise ThreeDGenerationError(
                    f"Unexpected error in 3D generation: {e}",
                    backend=backend or "unknown"
                )

    async def _select_backend(
        self,
        preferred_backend: Optional[str],
        generation_type: str,
        output_format: str,
        **kwargs
    ) -> str:
        """Select the best backend for the generation request"""

        if preferred_backend:
            # Use preferred backend if specified and available
            backend_info = self.backend_factory.get_client_info()
            if preferred_backend in backend_info["configured_clients"]:
                capabilities = self.backend_factory.get_capabilities(preferred_backend)
                if capabilities.get(generation_type.replace('_', '-'), False):
                    if output_format in capabilities.get("formats", []):
                        return preferred_backend

            self.logger.warning(f"Preferred backend {preferred_backend} not suitable, using auto-selection")

        # Auto-select based on capabilities and performance
        try:
            backend_client = self.backend_factory.create_client(
                generation_type=generation_type,
                output_format=output_format
            )
            return type(backend_client).__name__.lower().replace('client', '')

        except ConfigurationError:
            # Fallback to any available backend
            backend_info = self.backend_factory.get_client_info()
            available_backends = backend_info["configured_clients"]

            if not available_backends:
                raise ConfigurationError("No 3D generation backends available")

            # Return first available backend
            return available_backends[0]

    async def _generate_3d_with_backend(
        self,
        backend: str,
        image_path: Optional[Path] = None,
        prompt: Optional[str] = None,
        output_format: str = "glb",
        output_dir: Path = None,
        **kwargs
    ) -> GenerationResult:
        """Generate 3D model using specific backend"""

        job_id = f"3d_job_{int(time.time())}_{backend}"
        self.logger.info(f"Starting 3D generation job: {job_id} with backend: {backend}")

        try:
            # Create backend client
            backend_client = self.backend_factory.create_client(backend)

            # Submit job for execution
            if image_path:
                result = await self.job_manager.submit_job(
                    job_id,
                    self._execute_image_to_3d_job,
                    backend_client, image_path, output_format, output_dir, **kwargs
                )
            elif prompt:
                result = await self.job_manager.submit_job(
                    job_id,
                    self._execute_text_to_3d_job,
                    backend_client, prompt, output_format, output_dir, **kwargs
                )
            else:
                raise ValidationError("Either image_path or prompt must be provided")

            # Standardize result format
            if not isinstance(result, GenerationResult):
                result = GenerationResult(
                    success=True,
                    data=result.get("model_path"),
                    metadata={
                        "backend": backend,
                        "job_id": job_id,
                        "generation_type": "image_to_3d" if image_path else "text_to_3d",
                        "output_format": output_format,
                        "backend_metadata": result.get("metadata", {})
                    },
                    duration=result.get("generation_time", 0)
                )

            # Add backend information
            result.metadata["backend"] = backend
            result.metadata["job_id"] = job_id

            return result

        except Exception as e:
            self.logger.error(f"Backend {backend} generation failed: {e}")
            raise

    async def _execute_image_to_3d_job(
        self,
        backend_client,
        image_path: Path,
        output_format: str,
        output_dir: Path,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute image-to-3D generation job"""
        return await backend_client.generate_3d_from_image(
            image_path=image_path,
            output_format=output_format,
            output_dir=output_dir,
            **kwargs
        )

    async def _execute_text_to_3d_job(
        self,
        backend_client,
        prompt: str,
        output_format: str,
        output_dir: Path,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute text-to-3D generation job"""
        return await backend_client.generate_3d_from_prompt(
            prompt=prompt,
            output_format=output_format,
            output_dir=output_dir,
            **kwargs
        )

    def _update_backend_stats(self, backend: str, success: bool, duration: float, file_size_mb: float) -> None:
        """Update backend performance statistics"""
        if backend not in self.backend_stats:
            self.backend_stats[backend] = {
                "success_count": 0,
                "failure_count": 0,
                "avg_generation_time": 0.0,
                "avg_file_size_mb": 0.0,
                "last_used": 0
            }

        stats = self.backend_stats[backend]

        if success:
            stats["success_count"] += 1
            # Update average file size
            total_success = stats["success_count"]
            current_avg_size = stats["avg_file_size_mb"]
            stats["avg_file_size_mb"] = (current_avg_size * (total_success - 1) + file_size_mb) / total_success
        else:
            stats["failure_count"] += 1

        # Update average generation time
        total_requests = stats["success_count"] + stats["failure_count"]
        current_avg_time = stats["avg_generation_time"]
        stats["avg_generation_time"] = (current_avg_time * (total_requests - 1) + duration) / total_requests

        stats["last_used"] = time.time()

    def _get_file_size(self, file_path: Union[str, Path]) -> float:
        """Get file size in MB"""
        try:
            file_path = Path(file_path)
            if file_path.exists():
                return file_path.stat().st_size / (1024 * 1024)
        except Exception:
            pass
        return 0.0

    def get_backend_statistics(self) -> Dict[str, Any]:
        """Get backend performance statistics"""
        return {
            "backend_stats": self.backend_stats.copy(),
            "available_backends": list(self.backend_stats.keys()),
            "total_requests": sum(
                stats["success_count"] + stats["failure_count"]
                for stats in self.backend_stats.values()
            )
        }

    def cleanup_resources(self) -> None:
        """Cleanup all temporary resources"""
        self.resource_manager.cleanup_all()
        self.job_manager.cleanup_old_jobs()
        self.logger.info("Resources cleaned up")


# Convenience functions
async def generate_3d_from_image(
    image_path: Union[str, Path],
    output_format: str = "glb",
    output_dir: Optional[Union[str, Path]] = None,
    backend: Optional[str] = None,
    **kwargs
) -> GenerationResult:
    """Convenience function to generate 3D from image"""
    client = Unified3DClient()
    return await client.generate_3d_from_image(
        image_path=image_path,
        output_format=output_format,
        output_dir=output_dir,
        backend=backend,
        **kwargs
    )


async def generate_3d_from_prompt(
    prompt: str,
    output_format: str = "glb",
    output_dir: Optional[Union[str, Path]] = None,
    backend: Optional[str] = None,
    **kwargs
) -> GenerationResult:
    """Convenience function to generate 3D from prompt"""
    client = Unified3DClient()
    return await client.generate_3d_from_prompt(
        prompt=prompt,
        output_format=output_format,
        output_dir=output_dir,
        backend=backend,
        **kwargs
    )


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_unified_3d_client():
        """Test the unified 3D client"""
        try:
            client = Unified3DClient()
            client.initialize()

            # Test text-to-3D generation
            result = await client.generate_3d_from_prompt(
                prompt="A simple cube",
                output_format="glb",
                output_dir="test_output"
            )

            if result.success:
                print(f"3D model generated successfully: {result.data}")
                print(f"Metadata: {result.metadata}")
            else:
                print(f"Generation failed: {result.error}")

            # Print statistics
            stats = client.get_backend_statistics()
            print(f"Backend statistics: {stats}")

            # Cleanup
            client.cleanup_resources()

        except Exception as e:
            print(f"Test failed: {e}")

    # Run test
    asyncio.run(test_unified_3d_client())