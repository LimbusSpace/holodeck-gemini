# pylint: skip-file
"""Test schema validation."""

import pytest
from datetime import datetime

from holodeck_core.schemas import (
    Session, SessionRequest, SessionStatus,
    SceneObject, Vec3, SceneData,
    SpatialConstraint, ConstraintType, RelationType,
    ConstraintSet, LayoutSolution, PlacementInfo
)


@pytest.mark.unit
class TestSessionSchemas:
    """Test session-related schemas."""

    def test_session_request(self):
        """Test SessionRequest validation."""
        request = SessionRequest(
            text="A cozy bedroom with a bed and nightstand",
            style="realistic",
            constraints={"max_objects": 10}
        )
        assert request.text == "A cozy bedroom with a bed and nightstand"
        assert request.style == "realistic"
        assert request.constraints["max_objects"] == 10

    def test_session_creation(self):
        """Test Session creation."""
        request = SessionRequest(text="Test scene")
        session = Session(
            session_id="test_001",
            request=request,
            status=SessionStatus.INIT
        )
        assert session.session_id == "test_001"
        assert session.status == SessionStatus.INIT
        assert isinstance(session.created_at, datetime)


@pytest.mark.unit
class TestSceneObjectSchemas:
    """Test scene object schemas."""

    def test_vec3_validation(self):
        """Test Vec3 coordinate validation."""
        # Valid coordinates
        pos = Vec3(x=1.0, y=2.0, z=0.5)
        assert pos.x == 1.0
        assert pos.y == 2.0
        assert pos.z == 0.5

        # Valid - zero is allowed for center positioning
        pos2 = Vec3(x=0.0, y=0.0, z=0.0)
        assert pos2.x == 0.0
        assert pos2.y == 0.0
        assert pos2.z == 0.0

        # Invalid coordinates (too large)
        with pytest.raises(ValueError):
            Vec3(x=6.0, y=1.0, z=1.0)

    def test_scene_object(self):
        """Test SceneObject validation."""
        obj = SceneObject(
            id="bed_001",
            name="King Bed",
            position=Vec3(x=0.0, y=1.0, z=0.4),
            rotation=Vec3(x=0.0, y=0.0, z=0.0),
            size=Vec3(x=2.0, y=1.5, z=0.6),
            visual_description="A king-sized bed with wooden frame",
            category="furniture"
        )
        assert obj.id == "bed_001"
        assert obj.name == "King Bed"
        assert obj.category == "furniture"

    def test_scene_data(self):
        """Test SceneData validation."""
        objects = [
            SceneObject(
                id="bed_001",
                name="Bed",
                position=Vec3(x=0.0, y=0.0, z=0.4),
                rotation=Vec3(x=0.0, y=0.0, z=0.0),
                size=Vec3(x=2.0, y=1.5, z=0.6),
                visual_description="A bed"
            )
        ]
        scene = SceneData(
            scene_style="modern",
            objects=objects
        )
        assert scene.scene_style == "modern"
        assert len(scene.objects) == 1

        # Empty objects should raise error
        with pytest.raises(ValueError):
            SceneData(objects=[])


@pytest.mark.unit
class TestConstraintSchemas:
    """Test constraint schemas."""

    def test_spatial_constraint(self):
        """Test SpatialConstraint creation."""
        constraint = SpatialConstraint(
            type=ConstraintType.RELATIVE,
            relation=RelationType.LEFT_OF,
            source="nightstand_001",
            target="bed_001"
        )
        assert constraint.type == ConstraintType.RELATIVE
        assert constraint.relation == RelationType.LEFT_OF
        assert constraint.source == "nightstand_001"
        assert constraint.target == "bed_001"

    def test_distance_constraint(self):
        """Test distance constraint with threshold."""
        constraint = SpatialConstraint(
            type=ConstraintType.DISTANCE,
            relation=RelationType.NEAR,
            source="lamp_001",
            target="bed_001",
            threshold_m=2.0
        )
        assert constraint.threshold_m == 2.0

        # NEAR constraint should not exceed 2m
        with pytest.raises(ValueError):
            SpatialConstraint(
                type=ConstraintType.DISTANCE,
                relation=RelationType.NEAR,
                source="lamp_001",
                target="bed_001",
                threshold_m=3.0
            )

    def test_constraint_set(self):
        """Test ConstraintSet validation."""
        constraints = [
            SpatialConstraint(
                type=ConstraintType.RELATIVE,
                relation=RelationType.LEFT_OF,
                source="nightstand_001",
                target="bed_001"
            )
        ]
        constraint_set = ConstraintSet(relations=constraints)
        assert len(constraint_set.relations) == 1

        # Self-reference should raise error
        with pytest.raises(ValueError):
            ConstraintSet(relations=[
                SpatialConstraint(
                    type=ConstraintType.RELATIVE,
                    relation=RelationType.LEFT_OF,
                    source="obj_001",
                    target="obj_001"
                )
            ])


@pytest.mark.unit
class TestLayoutSchemas:
    """Test layout schemas."""

    def test_placement_info(self):
        """Test PlacementInfo."""
        placement = PlacementInfo(
            object_id="bed_001",
            position=[0.0, 1.0, 0.4],
            rotation=[0.0, 0.0, 0.0],
            successful=True
        )
        assert placement.object_id == "bed_001"
        assert placement.successful is True

    def test_layout_solution(self):
        """Test LayoutSolution."""
        placements = [
            PlacementInfo(
                object_id="bed_001",
                position=[0.0, 1.0, 0.4],
                rotation=[0.0, 0.0, 0.0],
                successful=True
            ),
            PlacementInfo(
                object_id="nightstand_001",
                position=[1.2, 1.0, 0.35],
                rotation=[0.0, 0.0, 0.0],
                successful=True
            )
        ]
        solution = LayoutSolution(
            version=1,
            placements=placements,
            objects={}  # Would contain actual SceneObjects
        )
        assert solution.version == 1
        assert len(solution.placements) == 2
        assert solution.is_collision_free()

        # Duplicate object IDs should raise error
        with pytest.raises(ValueError):
            LayoutSolution(
                version=1,
                placements=[
                    PlacementInfo(
                        object_id="bed_001",
                        position=[0.0, 0.0, 0.0],
                        rotation=[0.0, 0.0, 0.0],
                        successful=True
                    ),
                    PlacementInfo(
                        object_id="bed_001",
                        position=[1.0, 0.0, 0.0],
                        rotation=[0.0, 0.0, 0.0],
                        successful=True
                    )
                ],
                objects={}
            )