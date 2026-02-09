"""Scene object schemas based on HOLODECK 2.0 paper (Supp 6.2.2)."""

from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class Vec3(BaseModel):
    """3D vector with x, y, z coordinates in meters.

    Note: Room center is at (0, 0, 0).
    +X = right, +Y = backward, +Z = up

    Size reference (real-world scale, height-based):
    - Adult human: 1.7m tall
    - Chair: 0.9m tall
    - Table: 0.75m tall
    - Column: 5m tall
    - Building: 10-50m tall
    """
    x: float = Field(..., description="X coordinate in meters or degrees")
    y: float = Field(..., description="Y coordinate in meters or degrees")
    z: float = Field(..., description="Z coordinate (height) in meters or degrees")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {"x": 0.0, "y": 0.0, "z": 0.0},  # Room center
                {"x": -1.2, "y": 2.5, "z": 1.8},  # Elevated object
                {"x": 1.5, "y": -0.8, "z": 0.0},  # Ground object
            ]
        }
    )

    def __add__(self, other: 'Vec3') -> 'Vec3':
        """Vector addition."""
        return Vec3(x=self.x + other.x, y=self.y + other.y, z=self.z + other.z)

    def __sub__(self, other: 'Vec3') -> 'Vec3':
        """Vector subtraction."""
        return Vec3(x=self.x - other.x, y=self.y - other.y, z=self.z - other.z)

    def distance_to(self, other: 'Vec3') -> float:
        """Calculate Euclidean distance to another point."""
        return ((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)**0.5


class SceneObject(BaseModel):
    """Individual scene object with properties.

    Based on HOLODECK 2.0 Supp 6.2.2 SceneItem structure.
    Alias: SceneItem (to match paper terminology)
    """
    object_id: str = Field(..., description="Unique object identifier")
    name: str = Field(..., min_length=1, max_length=100, description="Object name")
    position: Vec3 = Field(..., description="Position in world coordinates")
    rotation: Vec3 = Field(..., description="Rotation in Euler angles (degrees)")
    size: Vec3 = Field(..., description="Size dimensions in meters")
    visual_description: str = Field(..., min_length=10, description="Visual appearance description")
    category: Optional[str] = Field(None, description="Object category (furniture, decoration, etc.)")
    must_exist: bool = Field(True, description="Whether this object must exist")
    asset_path: Optional[str] = Field(None, description="Path to generated 3D asset")

    # Additional properties for enhanced tracking
    material: Optional[str] = Field(None, description="Material type or style")
    color: Optional[str] = Field(None, description="Primary color")
    tags: List[str] = Field(default_factory=list, description="Object tags for classification")
    weight: Optional[float] = Field(None, gt=0.0, description="Weight in kg (for physics)")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "reference": "HOLODECK 2.0 Supplementary Material 6.2.2",
            "examples": [
                {
                    "object_id": "bed1",
                    "name": "King Bed",
                    "position": {"x": 0.0, "y": 1.0, "z": 0.4},
                    "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "size": {"x": 2.0, "y": 1.5, "z": 0.6},
                    "visual_description": "A king-sized bed with light-beige upholstered headboard",
                    "category": "furniture",
                    "material": "wood",
                    "color": "beige",
                    "tags": ["sleeping", "furniture"]
                }
            ]
        }
    )

    @field_validator('position')
    @classmethod
    def validate_ground_position(cls, v):
        """Ground objects should have z=0 or higher."""
        if v.z < -0.01:  # Small tolerance for floating point
            raise ValueError("Objects cannot be below ground level (z >= 0)")
        return v

    @field_validator('rotation')
    @classmethod
    def validate_rotation_range(cls, v):
        """Allow rotation values beyond position range."""
        return v  # Let the normalization happen in the model_validator

    @model_validator(mode='after')
    def validate_object_size(self):
        """Validate object size using real-world scale (no upper limit)."""
        # Only check minimum size (0.01m = 1cm)
        for axis, value in self.size.model_dump().items():
            if value < 0.01:
                raise ValueError(f"Object size {axis}={value}m is too small (min 0.01m)")
        return self

    @field_validator('rotation')
    @classmethod
    def normalize_rotation(cls, v):
        """Normalize rotation to 0-360 degree range."""
        normalized = v.model_dump()
        for axis, value in normalized.items():
            normalized[axis] = value % 360.0
        return Vec3(**normalized)

    def get_bounds(self) -> Tuple[Vec3, Vec3]:
        """Get bounding box corners (min_point, max_point)."""
        half_size = Vec3(
            x=self.size.x / 2,
            y=self.size.y / 2,
            z=self.size.z / 2
        )
        min_point = self.position - half_size
        max_point = self.position + half_size
        return min_point, max_point

    def is_on_ground(self) -> bool:
        """Check if object is positioned on the ground."""
        return abs(self.position.z) < 0.01


class SceneData(BaseModel):
    """Complete scene data with all objects.

    Matches the structure from HOLODECK 2.0 Supp 6.2.2.
    """
    scene_style: Optional[str] = Field(None, description="Overall scene style")
    objects: List[SceneObject] = Field(..., min_length=1, max_length=25, description="List of scene objects")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "reference": "HOLODECK 2.0 Supplementary Material 6.2.2",
            "examples": [
                {
                    "scene_style": "modern minimalist",
                    "objects": [
                        {
                            "object_id": "bed1",
                            "name": "King Bed",
                            "position": {"x": 0.0, "y": 0.0, "z": 0.4},
                            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
                            "size": {"x": 2.0, "y": 1.5, "z": 0.6},
                            "visual_description": "A king-sized bed with light-beige upholstered headboard"
                        }
                    ]
                }
            ]
        }
    )

    @field_validator('objects')
    @classmethod
    def validate_unique_object_ids(cls, v):
        """Ensure all object_ids are unique."""
        object_ids = [obj.object_id for obj in v]
        if len(object_ids) != len(set(object_ids)):
            duplicates = [id for id in object_ids if object_ids.count(id) > 1]
            raise ValueError(f"Duplicate object IDs found: {set(duplicates)}")
        return v

    @field_validator('objects')
    @classmethod
    def validate_scene_complexity(cls, v):
        """Check scene complexity is reasonable."""
        num_objects = len(v)
        if num_objects < 1:
            raise ValueError("Scene must have at least one object")
        if num_objects > 25:
            raise ValueError(f"Scene has too many objects ({num_objects}), maximum allowed is 25")
        return v


# Alias to match paper terminology
SceneItem = SceneObject