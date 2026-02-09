#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Orchestrator

Orchestrates the complete visual LLM to 3D pipeline, integrating:
- Enhanced LLM naming service
- Unified image generation client
- Unified 3D generation client
- Workflow management and monitoring
- Error handling and recovery
"""

import asyncio
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass
import uuid

from ..config.base import ConfigManager
from ..logging.standardized import StandardizedLogger, get_logger, log_time
from ..exceptions.framework import (
    WorkflowError, ConfigurationError, HolodeckError, ImageGenerationError, ThreeDGenerationError
)
from ..clients.base import GenerationResult
from ..object_gen.enhanced_llm_naming_service import EnhancedLLMNamingService
from ..image_generation.unified_image_client import UnifiedImageClient
from ..object_gen.unified_3d_client import Unified3DClient


@dataclass
class PipelineConfig:
    """Configuration for the complete pipeline"""
    workspace_root: str = "workspace"
    session_id: Optional[str] = None
    enable_naming: bool = True
    enable_image_generation: bool = True
    enable_3d_generation: bool = True
    cleanup_intermediate_files: bool = True
    max_pipeline_time: int = 1800  # 30 minutes
    enable_performance_logging: bool = True


@dataclass
class PipelineResult:
    """Result of the complete pipeline execution"""
    success: bool
    session_id: str
    stages: Dict[str, GenerationResult]
    metadata: Dict[str, Any]
    total_time: float
    error: Optional[str] = None


@dataclass
class StageConfig:
    """Configuration for individual pipeline stages"""
    name: str
    enabled: bool
    timeout: int
    retry_count: int = 0
    fallback_enabled: bool = True


class PipelineStage:
    """Base class for pipeline stages"""

    def __init__(self, name: str, logger: StandardizedLogger):
        self.name = name
        self.logger = logger

    async def execute(self, context: Dict[str, Any]) -> GenerationResult:
        """Execute the stage"""
        raise NotImplementedError

    async def validate_input(self, context: Dict[str, Any]) -> bool:
        """Validate stage inputs"""
        return True

    async def cleanup(self, context: Dict[str, Any]) -> None:
        """Cleanup stage resources"""
        pass


class NamingStage(PipelineStage):
    """Pipeline stage for LLM-based naming"""

    def __init__(self, naming_service: EnhancedLLMNamingService, logger: StandardizedLogger):
        super().__init__("naming", logger)
        self.naming_service = naming_service

    async def execute(self, context: Dict[str, Any]) -> GenerationResult:
        """Execute naming stage"""
        try:
            object_description = context.get("object_description", "")
            object_name = context.get("object_name", "")
            image_path = context.get("reference_image_path")

            if not object_description or not object_name:
                raise ConfigurationError("Object description and name are required for naming stage")

            generated_name = await self.naming_service.generate_object_name(
                description=object_description,
                object_name=object_name,
                image_path=Path(image_path) if image_path else None
            )

            if not generated_name:
                raise WorkflowError("Naming service returned empty result", step_name=self.name)

            self.logger.info(f"Generated name: {object_name} -> {generated_name}")

            return GenerationResult(
                success=True,
                data={"original_name": object_name, "generated_name": generated_name},
                metadata={
                    "stage": self.name,
                    "input_description": object_description,
                    "input_name": object_name,
                    "used_image_analysis": image_path is not None
                },
                duration=context.get("naming_duration", 0.0)
            )

        except Exception as e:
            self.logger.error(f"Naming stage failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                metadata={"stage": self.name}
            )


class ImageGenerationStage(PipelineStage):
    """Pipeline stage for image generation"""

    def __init__(self, image_client: UnifiedImageClient, logger: StandardizedLogger):
        super().__init__("image_generation", logger)
        self.image_client = image_client

    async def execute(self, context: Dict[str, Any]) -> GenerationResult:
        """Execute image generation stage"""
        try:
            prompt = context.get("generation_prompt", "")
            resolution = context.get("resolution", "1024:1024")
            style = context.get("style")
            output_path = context.get("image_output_path")

            if not prompt:
                raise ConfigurationError("Generation prompt is required for image generation stage")

            result = await self.image_client.generate_image(
                prompt=prompt,
                resolution=resolution,
                style=style,
                output_path=Path(output_path) if output_path else None
            )

            if not result.success:
                raise ImageGenerationError(
                    f"Image generation failed: {result.error}",
                    prompt=prompt[:50]
                )

            self.logger.info(f"Image generated successfully: {result.data}")

            return GenerationResult(
                success=True,
                data=result.data,
                metadata={
                    "stage": self.name,
                    "prompt": prompt,
                    "resolution": resolution,
                    "style": style,
                    "backend": result.metadata.get("backend", "unknown"),
                    "generation_time": result.duration
                },
                duration=result.duration
            )

        except Exception as e:
            self.logger.error(f"Image generation stage failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                metadata={"stage": self.name}
            )


class ThreeDGenerationStage(PipelineStage):
    """Pipeline stage for 3D generation"""

    def __init__(self, threed_client: Unified3DClient, logger: StandardizedLogger):
        super().__init__("3d_generation", logger)
        self.threed_client = threed_client

    async def execute(self, context: Dict[str, Any]) -> GenerationResult:
        """Execute 3D generation stage"""
        try:
            # Determine generation type
            image_path = context.get("object_card_path")
            prompt = context.get("3d_prompt")
            output_format = context.get("output_format", "glb")
            output_dir = context.get("output_dir")

            if image_path:
                # Image-to-3D generation
                result = await self.threed_client.generate_3d_from_image(
                    image_path=Path(image_path),
                    output_format=output_format,
                    output_dir=Path(output_dir) if output_dir else None
                )
            elif prompt:
                # Text-to-3D generation
                result = await self.threed_client.generate_3d_from_prompt(
                    prompt=prompt,
                    output_format=output_format,
                    output_dir=Path(output_dir) if output_dir else None
                )
            else:
                raise ConfigurationError("Either image_path or prompt is required for 3D generation")

            if not result.success:
                raise ThreeDGenerationError(
                    f"3D generation failed: {result.error}",
                    backend=result.metadata.get("backend", "unknown")
                )

            self.logger.info(f"3D model generated successfully: {result.data}")

            return GenerationResult(
                success=True,
                data=result.data,
                metadata={
                    "stage": self.name,
                    "generation_type": "image_to_3d" if image_path else "text_to_3d",
                    "output_format": output_format,
                    "backend": result.metadata.get("backend", "unknown"),
                    "generation_time": result.duration,
                    "file_size_mb": result.metadata.get("file_size_mb", 0)
                },
                duration=result.duration
            )

        except Exception as e:
            self.logger.error(f"3D generation stage failed: {e}")
            return GenerationResult(
                success=False,
                error=str(e),
                metadata={"stage": self.name}
            )


class PipelineOrchestrator:
    """
    Orchestrates the complete visual LLM to 3D pipeline.

    Manages:
    - Stage execution order and dependencies
    - Error handling and recovery
    - Resource management
    - Performance monitoring
    - Result aggregation
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        config_manager: Optional[ConfigManager] = None
    ):
        """
        Initialize pipeline orchestrator.

        Args:
            config: Pipeline configuration
            config_manager: Configuration manager instance
        """
        self.config = config or PipelineConfig()
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(__name__)

        # Initialize services
        self.naming_service = EnhancedLLMNamingService(self.config_manager)
        self.image_client = UnifiedImageClient(self.config_manager)
        self.threed_client = Unified3DClient(self.config_manager)

        # Setup workspace
        self.workspace_root = Path(self.config.workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

        # Initialize stages
        self.stages = self._initialize_stages()

        self.logger.info("Pipeline Orchestrator initialized")

    def _initialize_stages(self) -> Dict[str, PipelineStage]:
        """Initialize pipeline stages based on configuration"""
        stages = {}

        if self.config.enable_naming:
            stages["naming"] = NamingStage(self.naming_service, self.logger)

        if self.config.enable_image_generation:
            stages["image_generation"] = ImageGenerationStage(self.image_client, self.logger)

        if self.config.enable_3d_generation:
            stages["3d_generation"] = ThreeDGenerationStage(self.threed_client, self.logger)

        return stages

    @log_time("execute_pipeline", log_threshold=60.0)
    async def execute_pipeline(self, input_context: Dict[str, Any]) -> PipelineResult:
        """
        Execute the complete pipeline.

        Args:
            input_context: Input context for the pipeline

        Returns:
            PipelineResult containing all stage results and metadata
        """
        start_time = time.time()

        # Generate session ID if not provided
        session_id = self.config.session_id or f"session_{int(start_time)}_{uuid.uuid4().hex[:8]}"

        self.logger.info(f"Starting pipeline execution: {session_id}")

        try:
            # Validate input context
            self._validate_input_context(input_context)

            # Create session workspace
            session_dir = self.workspace_root / "sessions" / session_id
            session_dir.mkdir(parents=True, exist_ok=True)

            # Initialize pipeline context
            context = {
                "session_id": session_id,
                "session_dir": session_dir,
                "start_time": start_time,
                **input_context
            }

            # Execute stages in order
            stage_results = {}
            stage_order = ["naming", "image_generation", "3d_generation"]

            for stage_name in stage_order:
                if stage_name not in self.stages:
                    continue

                stage = self.stages[stage_name]
                self.logger.info(f"Executing stage: {stage_name}")

                try:
                    # Validate stage input
                    if not await stage.validate_input(context):
                        raise WorkflowError(f"Stage {stage_name} input validation failed", step_name=stage_name)

                    # Execute stage
                    stage_start = time.time()
                    result = await stage.execute(context)
                    stage_duration = time.time() - stage_start

                    # Store result
                    stage_results[stage_name] = result
                    context[f"{stage_name}_result"] = result
                    context[f"{stage_name}_duration"] = stage_duration

                    # Update context with stage output
                    if result.success and result.data:
                        context.update(self._extract_stage_output(stage_name, result))

                    # Log stage completion
                    status = "completed" if result.success else "failed"
                    self.logger.info(f"Stage {stage_name} {status} in {stage_duration:.2f}s")

                    if not result.success:
                        raise WorkflowError(
                            f"Stage {stage_name} failed: {result.error}",
                            step_name=stage_name
                        )

                except Exception as e:
                    self.logger.error(f"Stage {stage_name} execution failed: {e}")
                    stage_results[stage_name] = GenerationResult(
                        success=False,
                        error=str(e),
                        metadata={"stage": stage_name}
                    )

                    # Try to continue with next stages if possible
                    if not self._can_continue_after_failure(stage_name):
                        raise WorkflowError(
                            f"Critical stage {stage_name} failed, stopping pipeline",
                            step_name=stage_name
                        )

            # Pipeline completed successfully
            total_time = time.time() - start_time

            pipeline_result = PipelineResult(
                success=True,
                session_id=session_id,
                stages=stage_results,
                metadata={
                    "total_time": total_time,
                    "session_dir": str(session_dir),
                    "completed_stages": [name for name, result in stage_results.items() if result.success],
                    "failed_stages": [name for name, result in stage_results.items() if not result.success]
                },
                total_time=total_time
            )

            self.logger.info(
                f"Pipeline completed successfully: {session_id}",
                context={
                    "session_id": session_id,
                    "total_time": total_time,
                    "successful_stages": len(pipeline_result.metadata["completed_stages"]),
                    "failed_stages": len(pipeline_result.metadata["failed_stages"])
                }
            )

            return pipeline_result

        except Exception as e:
            total_time = time.time() - start_time

            self.logger.error(
                f"Pipeline execution failed: {session_id}",
                context={
                    "session_id": session_id,
                    "error": str(e),
                    "total_time": total_time
                }
            )

            return PipelineResult(
                success=False,
                session_id=session_id,
                stages={},
                metadata={"total_time": total_time},
                total_time=total_time,
                error=str(e)
            )

        finally:
            # Cleanup resources
            if self.config.cleanup_intermediate_files:
                await self._cleanup_session_resources(session_id)

    def _validate_input_context(self, context: Dict[str, Any]) -> None:
        """Validate pipeline input context"""
        required_fields = []

        if self.config.enable_naming:
            required_fields.extend(["object_description", "object_name"])

        if self.config.enable_image_generation:
            required_fields.append("generation_prompt")

        for field in required_fields:
            if field not in context or not context[field]:
                raise ConfigurationError(f"Required field missing: {field}")

    def _extract_stage_output(self, stage_name: str, result: GenerationResult) -> Dict[str, Any]:
        """Extract relevant output from stage result to update context"""
        output = {}

        if stage_name == "naming" and result.data:
            output["generated_name"] = result.data.get("generated_name")

        elif stage_name == "image_generation" and result.data:
            output["generated_image_path"] = result.data
            output["object_card_path"] = result.data

        elif stage_name == "3d_generation" and result.data:
            output["generated_3d_path"] = result.data

        return output

    def _can_continue_after_failure(self, stage_name: str) -> bool:
        """Determine if pipeline can continue after stage failure"""
        # Define stage dependencies
        dependencies = {
            "naming": [],
            "image_generation": [],
            "3d_generation": ["image_generation", "naming"]
        }

        # Check if any subsequent stages depend on this one
        for other_stage, deps in dependencies.items():
            if stage_name in deps:
                return False

        return True

    async def _cleanup_session_resources(self, session_id: str) -> None:
        """Cleanup session-specific resources"""
        try:
            # Cleanup 3D client resources
            if hasattr(self.threed_client, 'cleanup_resources'):
                self.threed_client.cleanup_resources()

            self.logger.info(f"Cleaned up resources for session: {session_id}")

        except Exception as e:
            self.logger.warning(f"Failed to cleanup session resources: {e}")

    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics"""
        stats = {
            "naming_service": self.naming_service.get_statistics(),
            "image_client": self.image_client.get_backend_statistics(),
            "threed_client": self.threed_client.get_backend_statistics(),
            "pipeline_config": {
                "enable_naming": self.config.enable_naming,
                "enable_image_generation": self.config.enable_image_generation,
                "enable_3d_generation": self.config.enable_3d_generation,
                "max_pipeline_time": self.config.max_pipeline_time
            }
        }

        return stats


# Convenience functions for easy pipeline usage
async def run_complete_pipeline(
    object_description: str,
    object_name: str,
    generation_prompt: Optional[str] = None,
    **kwargs
) -> PipelineResult:
    """
    Run the complete pipeline from object description to 3D model.

    Args:
        object_description: Description of the object
        object_name: Name of the object
        generation_prompt: Prompt for image generation (optional)
        **kwargs: Additional pipeline parameters

    Returns:
        PipelineResult containing all stage results
    """
    config = PipelineConfig(**kwargs)
    orchestrator = PipelineOrchestrator(config)

    context = {
        "object_description": object_description,
        "object_name": object_name,
    }

    if generation_prompt:
        context["generation_prompt"] = generation_prompt
    else:
        # Use object description as generation prompt if not provided
        context["generation_prompt"] = f"{object_name}: {object_description}"

    # Add any additional context from kwargs
    context.update({k: v for k, v in kwargs.items() if k not in config.__dict__})

    return await orchestrator.execute_pipeline(context)


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def test_pipeline():
        """Test the complete pipeline"""
        try:
            result = await run_complete_pipeline(
                object_description="A futuristic cyberpunk chair with neon blue accents",
                object_name="Cyberpunk Chair",
                workspace_root="test_workspace"
            )

            if result.success:
                print(f"Pipeline completed successfully!")
                print(f"Session ID: {result.session_id}")
                print(f"Total time: {result.total_time:.2f}s")
                print(f"Completed stages: {result.metadata['completed_stages']}")

                # Print stage results
                for stage_name, stage_result in result.stages.items():
                    status = "✅" if stage_result.success else "❌"
                    print(f"{status} {stage_name}: {stage_result.metadata}")

            else:
                print(f"Pipeline failed: {result.error}")

        except Exception as e:
            print(f"Test failed: {e}")

    # Run test
    asyncio.run(test_pipeline())