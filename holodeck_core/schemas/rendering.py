"""Rendering schemas for final scene output.

Handles camera poses, render configurations, and output specifications.
"""

from typing import List, Optional, Literal, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .scene_objects import Vec3


class CameraPose(BaseModel):
    """Camera position and orientation for rendering."""
    type: Literal[
        "wide", "top", "front", "right", "left", "back", "corner_front_right",
        "corner_front_left", "corner_back_right", "corner_back_left", "custom"
    ] = Field(..., description="Preset type of camera view")
    name: str = Field(..., description="Human-readable camera name")

    # Position and orientation
    position: Vec3 = Field(..., description="Camera position in world coordinates")
    rotation: Vec3 = Field(..., description="Camera rotation in Euler angles (degrees)")

    # Camera properties
    fov: float = Field(45.0, ge=10.0, le=120.0, description="Field of view in degrees")
    focal_length: Optional[float] = Field(50.0, gt=0.0, le=500.0, description="Focal length in mm")

    # Target information
    target_point: Optional[Vec3] = Field(None, description="Point camera is looking at")
    height_offset: float = Field(1.0, ge=0.0, le=5.0, description="Height offset from ground")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "type": "wide",
                    "name": "Overview",
                    "position": {"x": -2.0, "y": -2.0, "z": 2.5},
                    "rotation": {"x": 60.0, "y": 45.0, "z": 0.0},
                    "fov": 45.0,
                    "target_point": {"x": 0.0, "y": 0.0, "z": 0.5}
                },
                {
                    "type": "top",
                    "name": "Floor Plan",
                    "position": {"x": 0.0, "y": 0.0, "z": 4.0},
                    "rotation": {"x": 90.0, "y": 0.0, "z": 0.0},
                    "fov": 50.0
                }
            ]
        }
    )

    @field_validator('rotation')
    @classmethod
    def normalize_rotation(cls, v):
        """Normalize rotation to 0-360 degree range."""
        normalized = v.model_dump()
        for axis, value in normalized.items():
            normalized[axis] = value % 360.0
        return Vec3(**normalized)


class RenderConfig(BaseModel):
    """Configuration for rendering process."""

    # Output settings
    resolution: Tuple[int, int] = Field((1920, 1080), description="Output resolution (width, height)")
    pixel_aspect: float = Field(1.0, gt=0.1, le=10.0, description="Pixel aspect ratio")

    # Quality settings
    samples: int = Field(1024, ge=64, le=10000, description="Number of samples per pixel")
    noise_threshold: float = Field(0.01, ge=0.001, le=1.0, description="Noise threshold for adaptive sampling")

    # Lighting
    environment_type: Literal["hdri", "studio", "outdoor", "indoor"] = Field("indoor", description="Type of environment lighting")
    hdri_path: Optional[str] = Field(None, description="Path to HDRI environment map")

    # Materials
    include_background: bool = Field(True, description="Whether to render background")
    background_color: Tuple[float, float, float] = Field((0.95, 0.95, 0.95), description="Background RGB color")

    # Performance
    max_render_time: float = Field(120.0, ge=1.0, le=3600.0, description="Maximum render time per frame (seconds)")
    use_gpu: bool = Field(True, description="Whether to use GPU rendering")
    memory_limit_gb: Optional[float] = Field(None, gt=1.0, le=128.0, description="GPU memory limit in GB")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "resolution": (3840, 2160),
                    "samples": 2048,
                    "environment_type": "indoor",
                    "max_render_time": 300.0
                }
            ]
        }
    )


class RenderOutput(BaseModel):
    """Output of a single render operation."""
    render_id: str = Field(..., description="Unique render identifier")
    camera_pose: CameraPose = Field(..., description="Camera used for this render")
    render_config: RenderConfig = Field(..., description="Configuration used")

    # Output files
    image_path: str = Field(..., description="Path to rendered image")
    depth_path: Optional[str] = Field(None, description="Path to depth buffer (if requested)")
    normal_path: Optional[str] = Field(None, description="Path to normal map (if requested)")

    # Render statistics
    render_time: float = Field(..., ge=0.0, description="Actual render time (seconds)")
    samples_used: int = Field(..., ge=64, description="Samples actually reached")
    memory_used_mb: Optional[float] = Field(None, ge=0.0, description="Peak memory usage")

    # Quality metrics
    render_status: Literal["success", "failed", "timeout", "cancelled"] = Field("success", description="Render status")
    error_message: Optional[str] = Field(None, description="Error if render failed")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Render timestamp")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "render_id": "render_20260112_144530",
                    "image_path": "renders/scene_wide_001.png",
                    "render_time": 125.3,
                    "samples_used": 2048,
                    "render_status": "success"
                }
            ]
        }
    )


class RenderBatch(BaseModel):
    """Batch render operation for multiple camera views."""
    batch_id: str = Field(..., description="Unique batch identifier")
    session_id: str = Field(..., description="Associated scene session ID")

    # Render targets
    camera_poses: List[CameraPose] = Field(..., description="All cameras to render")
    render_config: RenderConfig = Field(..., description="Configuration for all renders")

    # Batch results
    outputs: List[RenderOutput] = Field(default_factory=list, description="Render outputs in order")

    # Batch statistics
    total_renders: int = Field(..., ge=1, description="Total number of renders in batch")
    successful_renders: int = Field(0, description="Count of successful renders")
    total_time: float = Field(0.0, ge=0.0, description="Total batch time (seconds)")
    average_time: float = Field(0.0, ge=0.0, description="Average time per render")

    # Performance
    parallel_workers: int = Field(1, ge=1, le=8, description="Number of parallel rendering processes")
    memory_peak_mb: Optional[float] = Field(None, ge=0.0, description="Peak memory usage across batch")

    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Batch start time")
    completed_at: Optional[datetime] = Field(None, description="Batch completion time")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "batch_id": "render_batch_20260112_144500",
                    "session_id": "2026-01-12T12-30-05Z_abc123",
                    "total_renders": 3,
                    "successful_renders": 3,
                    "total_time": 380.5,
                    "parallel_workers": 1
                }
            ]
        }
    )

    @model_validator(mode='after')
    def calculate_batch_metrics(self):
        """Calculate batch statistics from outputs."""
        self.successful_renders = sum(
            1 for output in self.outputs
            if output.render_status == "success"
        )

        if self.outputs:
            self.total_time = sum(output.render_time for output in self.outputs)
            self.average_time = self.total_time / len(self.outputs)

        if self.successful_renders == self.total_renders and self.successful_renders > 0:
            self.completed_at = datetime.now(timezone.utc)

        return self


class RenderQualityMetrics(BaseModel):
    """Quality assessment of rendered outputs."""
    render_batch_id: str = Field(..., description="Associated render batch")

    # Technical metrics
    sharpness_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Image sharpness score")
    noise_level: Optional[float] = Field(None, ge=0.0, description="Noise level detected")
    exposure_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Exposure quality score")

    # Visual assessment (typically from VLM or user)
    visual_coherence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Coherence with scene description")
    aesthetic_quality: Optional[float] = Field(None, ge=0.0, le=1.0, description="Aesthetic quality score")

    # Overall assessment
    overall_quality: float = Field(0.0, ge=0.0, le=1.0, description="Overall quality score")
    recommendation: Literal["accept", "rerender", "adjust_lighting", "adjust_camera"] = Field(
        "accept", description="Recommendation for this batch"
    )

    # Notes
    quality_notes: Optional[str] = Field(None, description="Additional notes about quality")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Assessment timestamp")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "render_batch_id": "render_batch_20260112_144500",
                    "overall_quality": 0.87,
                    "recommendation": "accept",
                    "quality_notes": "Good lighting and composition"
                }
            ]
        }
    )