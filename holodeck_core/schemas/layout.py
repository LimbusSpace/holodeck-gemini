"""Layout solution and trace schemas."""

from typing import List, Dict, Any, Optional, Tuple, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, field_serializer, ConfigDict

from .scene_objects import SceneObject


class LayoutConfig(BaseModel):
    """Configuration for the layout solver."""
    # Core solver parameters
    max_iterations: int = Field(1000, ge=1, le=10000, description="Maximum solver iterations")
    collision_clearance_m: float = Field(0.02, ge=0.0, le=0.1, description="Minimum clearance between objects (meters)")
    ground_only_default: bool = Field(True, description="Default objects to ground plane")
    random_seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    timeout_seconds: float = Field(30.0, ge=1.0, le=300.0, description="Solver timeout in seconds")

    # Sampling and search parameters
    max_candidates_per_object: int = Field(100, ge=10, le=1000, description="Maximum placement candidates to try per object")
    sampling_resolution: float = Field(0.1, ge=0.01, le=1.0, description="Grid resolution for sampling (meters)")
    use_adaptive_sampling: bool = Field(True, description="Use adaptive sampling based on constraints")

    # Constraint satisfaction
    constraint_weight: float = Field(1.0, ge=0.0, le=10.0, description="Weight for constraint satisfaction")
    allow_soft_violations: bool = Field(True, description="Allow soft constraint violations")
    max_soft_violation_penalty: float = Field(0.5, ge=0.0, le=1.0, description="Maximum penalty for soft violations")

    # Physics parameters
    gravity_enabled: bool = Field(True, description="Enable gravity simulation")
    stability_margin: float = Field(0.1, ge=0.0, le=1.0, description="Margin for object stability")
    center_of_mass_check: bool = Field(True, description="Check center of mass for stability")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "max_iterations": 500,
                    "collision_clearance_m": 0.02,
                    "ground_only_default": True,
                    "timeout_seconds": 30.0,
                    "sampling_resolution": 0.1
                }
            ]
        }
    )


class PlacementInfo(BaseModel):
    """Placement information for a single object."""
    object_id: str = Field(..., description="Object identifier")
    position: List[float] = Field(..., min_length=3, max_length=3, description="[x, y, z] position in meters")
    rotation: List[float] = Field(..., min_length=3, max_length=3, description="[x, y, z] rotation in degrees")
    successful: bool = Field(True, description="Whether placement was successful")
    placement_time_ms: Optional[float] = Field(None, description="Time taken for placement in milliseconds")

    # Quality metrics
    constraint_satisfaction_score: float = Field(1.0, ge=0.0, le=1.0, description="How well constraints are satisfied")
    stability_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Physical stability score")
    collision_count: int = Field(0, ge=0, description="Number of collisions detected")

    # Placement metadata
    placement_method: str = Field("dfs", description="Method used for placement (dfs/sampling/optimization)")
    attempts: int = Field(1, ge=1, description="Number of placement attempts")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in placement quality")

    model_config = ConfigDict(
        validate_assignment=True
    )


class CollisionInfo(BaseModel):
    """Detailed information about object collisions."""
    object_a: str = Field(..., description="First object ID")
    object_b: str = Field(..., description="Second object ID")
    penetration_depth: float = Field(..., gt=0.0, description="How much objects intersect (meters)")
    contact_point: Optional[List[float]] = Field(None, min_length=3, max_length=3, description="Contact point coordinates")

    # Collision details
    collision_type: Literal["overlap", "contact", "boundary_violation"] = Field("overlap", description="Type of collision")
    severity: float = Field(1.0, ge=0.0, le=10.0, description="Collision severity score")
    affected_constraints: List[str] = Field(default_factory=list, description="Constraints violated by this collision")

    # Physics info
    impulse_magnitude: Optional[float] = Field(None, gt=0.0, description="Collision impulse magnitude")
    contact_normal: Optional[List[float]] = Field(None, min_length=3, max_length=3, description="Contact normal vector")

    model_config = ConfigDict(
        validate_assignment=True
    )


class DFSTrace(BaseModel):
    """Comprehensive trace information from failed DFS solving attempts."""
    failed_object_id: str = Field(..., description="Object that failed to place")
    placed_objects: List[str] = Field(..., description="Objects already placed")
    conflict_type: Literal["collision", "boundary", "constraint", "unstable", "timeout"] = Field(..., description="Type of conflict")
    active_constraints: List[Dict[str, Any]] = Field(..., description="Constraints being evaluated")

    # Search information
    candidates_tried: int = Field(0, ge=0, description="Number of placement candidates tried")
    search_space_size: int = Field(0, ge=0, description="Total search space size")
    best_candidate_score: float = Field(0.0, description="Score of best candidate found")
    rejected_candidates: List[Dict[str, Any]] = Field(default_factory=list, description="Rejected candidates with reasons")

    # Error details
    error_message: Optional[str] = Field(None, description="Detailed error description")
    natural_language_summary: Optional[str] = Field(None, description="Human-readable summary for LLM feedback")
    fix_suggestions: List[str] = Field(default_factory=list, description="Suggested fixes for this failure")

    # Performance
    traceback_depth: int = Field(0, ge=0, description="Depth of backtracking required")
    time_at_failure: float = Field(0.0, ge=0.0, description="Time elapsed when failure occurred")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "failed_object_id": "lamp1",
                    "placed_objects": ["bed1", "nightstand1"],
                    "conflict_type": "constraint",
                    "active_constraints": [{"source": "lamp1", "target": "bed1", "relation": "near"}],
                    "candidates_tried": 50,
                    "natural_language_summary": "Cannot place lamp near bed without colliding with nightstand",
                    "fix_suggestions": ["Move nightstand further from bed", "Allow lamp to be on table instead"]
                }
            ]
        }
    )


class LayoutSolution(BaseModel):
    """Complete layout solution with all object placements."""
    version: int = Field(1, ge=1, description="Solution version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation time")
    placements: List[PlacementInfo] = Field(..., description="All object placements")
    objects: Dict[str, SceneObject] = Field(..., description="Object definitions")
    collisions: List[CollisionInfo] = Field(default_factory=list, description="Any detected collisions")
    config: LayoutConfig = Field(..., description="Solver configuration used")

    # Performance metrics
    score: float = Field(0.0, description="Solution quality score")
    solve_time_seconds: float = Field(0.0, ge=0.0, description="Total solving time in seconds")
    iterations_used: int = Field(0, ge=0, description="Number of iterations actually used")
    success_rate: float = Field(1.0, ge=0.0, le=1.0, description="Fraction of successfully placed objects")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "version": 1,
                    "placements": [
                        {
                            "object_id": "bed1",
                            "position": [0.0, 0.0, 0.4],
                            "rotation": [0.0, 0.0, 0.0],
                            "successful": True
                        }
                    ],
                    "config": {
                        "max_iterations": 1000,
                        "collision_clearance_m": 0.02
                    },
                    "score": 0.95,
                    "solve_time_seconds": 2.3,
                    "success_rate": 1.0
                }
            ]
        }
    )

    @field_validator('placements')
    @classmethod
    def validate_unique_objects(cls, v):
        """Ensure each object appears only once."""
        object_ids = [p.object_id for p in v]
        if len(object_ids) != len(set(object_ids)):
            raise ValueError("Duplicate object IDs in placements")
        return v

    def is_collision_free(self) -> bool:
        """Check if layout has no collisions."""
        return len(self.collisions) == 0

    def get_placement(self, object_id: str) -> Optional[PlacementInfo]:
        """Get placement for specific object."""
        for placement in self.placements:
            if placement.object_id == object_id:
                return placement
        return None