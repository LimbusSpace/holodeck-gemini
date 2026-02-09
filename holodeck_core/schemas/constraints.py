"""Spatial constraint schemas based on HOLODECK 2.0 paper."""

from enum import Enum
from typing import Dict, Any, Optional, List, Literal, Set
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .scene_objects import Vec3


class ConstraintType(str, Enum):
    """Type of spatial constraint."""
    RELATIVE = "relative"
    DISTANCE = "distance"
    VERTICAL = "vertical"
    ROTATION = "rotation"


class RelationType(str, Enum):
    """Specific relation types for each constraint category."""
    # Relative relations
    LEFT_OF = "left of"
    RIGHT_OF = "right of"
    IN_FRONT_OF = "in front of"
    BEHIND = "behind"
    SIDE_OF = "side of"

    # Distance relations
    NEAR = "near"
    FAR = "far"
    ADJACENT = "adjacent"

    # Vertical relations
    ON = "on"
    ABOVE = "above"
    BELOW = "below"

    # Rotation relations
    FACE_TO = "face to"
    PARALLEL = "parallel"
    PERPENDICULAR = "perpendicular"


class SpatialConstraint(BaseModel):
    """Individual spatial constraint between two objects.

    Based on HOLODECK 2.0 Table 3 constraint types.
    """
    constraint_id: Optional[str] = Field(None, description="Unique constraint identifier")
    type: ConstraintType = Field(..., description="Constraint type category")
    relation: RelationType = Field(..., description="Specific relation")
    source: str = Field(..., description="Source object ID")
    target: str = Field(..., description="Target object ID")
    priority: Literal["primary", "secondary"] = Field("primary", description="Constraint priority")

    # Optional parameters with enhanced validation
    threshold_m: Optional[float] = Field(None, gt=0.0, le=20.0, description="Distance threshold in meters")
    deg_tolerance: Optional[float] = Field(None, ge=0.0, le=180.0, description="Angle tolerance in degrees")
    offset: Optional[Vec3] = Field(None, description="Positional offset from target")

    # Soft constraint parameters
    weight: float = Field(1.0, ge=0.0, le=10.0, description="Constraint weight for optimization")
    is_soft: bool = Field(False, description="Whether this is a soft constraint")

    model_config = ConfigDict(
        use_enum_values=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "reference": "HOLODECK 2.0 Table 3",
            "examples": [
                {
                    "constraint_id": "c001",
                    "type": "relative",
                    "relation": "left of",
                    "source": "nightstand_left",
                    "target": "bed1",
                    "priority": "primary",
                    "offset": {"x": -0.5, "y": 0.0, "z": 0.0}
                },
                {
                    "constraint_id": "c002",
                    "type": "distance",
                    "relation": "near",
                    "source": "lamp_left",
                    "target": "bed1",
                    "threshold_m": 2.0,
                    "priority": "primary",
                    "weight": 0.8
                }
            ]
        }
    )

    @field_validator('threshold_m')
    @classmethod
    def validate_threshold(cls, v, info):
        """Validate threshold based on relation type."""
        if v is not None:
            relation = info.data.get('relation')
            if relation == RelationType.NEAR and v > 2.0:
                raise ValueError("NEAR threshold should not exceed 2m")
            elif relation == RelationType.FAR and v < 8.0:
                raise ValueError("FAR threshold should be at least 8m")
            elif relation == RelationType.ADJACENT and v > 0.5:
                raise ValueError("ADJACENT threshold should not exceed 0.5m")
        return v

    @field_validator('deg_tolerance')
    @classmethod
    def validate_deg_tolerance(cls, v):
        """Validate angle tolerance."""
        if v is not None and (v < 0 or v > 180):
            raise ValueError("Degree tolerance must be between 0 and 180")
        return v

    def is_symmetric(self) -> bool:
        """Check if this constraint has a symmetric counterpart."""
        symmetric_relations = {
            RelationType.NEAR: RelationType.NEAR,
            RelationType.ADJACENT: RelationType.ADJACENT,
            RelationType.PARALLEL: RelationType.PARALLEL,
            RelationType.PERPENDICULAR: RelationType.PERPENDICULAR,
        }
        return self.relation in symmetric_relations

    def get_inverse(self) -> RelationType:
        """Get the inverse relation for this constraint."""
        inverse_map = {
            RelationType.LEFT_OF: RelationType.RIGHT_OF,
            RelationType.RIGHT_OF: RelationType.LEFT_OF,
            RelationType.IN_FRONT_OF: RelationType.BEHIND,
            RelationType.BEHIND: RelationType.IN_FRONT_OF,
            RelationType.ABOVE: RelationType.BELOW,
            RelationType.BELOW: RelationType.ABOVE,
            RelationType.ON: RelationType.ON,  # Self-inverse
            RelationType.FACE_TO: RelationType.FACE_TO,  # Self-inverse
            RelationType.NEAR: RelationType.NEAR,  # Symmetric
            RelationType.FAR: RelationType.FAR,  # Symmetric
            RelationType.ADJACENT: RelationType.ADJACENT,  # Symmetric
            RelationType.SIDE_OF: RelationType.SIDE_OF,  # Symmetric
            RelationType.PARALLEL: RelationType.PARALLEL,  # Symmetric
            RelationType.PERPENDICULAR: RelationType.PERPENDICULAR,  # Symmetric
        }
        return inverse_map[self.relation]


class ConstraintSet(BaseModel):
    """Collection of spatial constraints with global settings."""
    globals: Dict[str, Any] = Field(
        default={
            "ground_only_default": True,
            "collision_clearance_m": 0.02,
            "max_room_size": 20.0,
            "min_object_spacing": 0.1
        },
        description="Global constraint settings"
    )
    relations: List[SpatialConstraint] = Field(..., description="Spatial relations")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "globals": {
                        "ground_only_default": True,
                        "collision_clearance_m": 0.02
                    },
                    "relations": [
                        {
                            "type": "relative",
                            "relation": "left of",
                            "source": "nightstand_left",
                            "target": "bed1",
                            "priority": "primary"
                        }
                    ]
                }
            ]
        }
    )

    def get_primary_constraints(self) -> List[SpatialConstraint]:
        """Get primary priority constraints."""
        return [c for c in self.relations if c.priority == "primary"]

    def get_secondary_constraints(self) -> List[SpatialConstraint]:
        """Get secondary priority constraints."""
        return [c for c in self.relations if c.priority == "secondary"]

    @field_validator('relations')
    @classmethod
    def validate_no_self_reference(cls, v):
        """Ensure no constraint references the same object."""
        for constraint in v:
            if constraint.source == constraint.target:
                raise ValueError(f"Constraint cannot reference same object: {constraint.source}")
        return v

    @field_validator('relations')
    @classmethod
    def validate_no_duplicates(cls, v):
        """Ensure no duplicate constraints exist."""
        seen = set()
        for constraint in v:
            key = (constraint.source, constraint.target, constraint.relation)
            if key in seen:
                raise ValueError(f"Duplicate constraint found: {key}")
            seen.add(key)
        return v

    def get_constraints_for_object(self, object_id: str) -> List[SpatialConstraint]:
        """Get all constraints involving a specific object."""
        return [c for c in self.relations if object_id in [c.source, c.target]]

    def has_cycles(self) -> bool:
        """Check for constraint cycles using DFS."""
        graph = {}
        for constraint in self.relations:
            graph.setdefault(constraint.source, []).append(constraint.target)

        def dfs(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        rec_stack = set()
        for node in graph:
            if node not in visited:
                if dfs(node, visited, rec_stack):
                    return True
        return False