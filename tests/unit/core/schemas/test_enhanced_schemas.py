# pylint: skip-file
"""Test enhanced schema functionality."""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from holodeck_core.schemas.scene_objects import Vec3, SceneObject, SceneData, SceneItem
from holodeck_core.schemas.session import Session, SessionStatus, SessionRequest
from holodeck_core.schemas.constraints import (
    SpatialConstraint, ConstraintSet, ConstraintType, RelationType
)
from holodeck_core.schemas.layout import LayoutConfig, PlacementInfo, CollisionInfo, DFSTrace


@pytest.mark.unit
class TestEnhancedVec3:
    """Test enhanced Vec3 class."""

    def test_vec3_range_expansion(self):
        """Test expanded coordinate range."""
        # Valid coordinates within expanded range
        v = Vec3(x=8.0, y=-8.0, z=5.0)
        assert v.x == 8.0
        assert v.y == -8.0
        assert v.z == 5.0

        # Test edge cases
        v = Vec3(x=-10.0, y=10.0, z=10.0)
        assert v.x == -10.0
        assert v.y == 10.0
        assert v.z == 10.0

    def test_vec3_out_of_range(self):
        """Test coordinates outside allowed range."""
        with pytest.raises(ValueError, match="x"):
            Vec3(x=15.0, y=0.0, z=0.0)  # > 10.0

        # Z can now be negative (for rotations)
        v = Vec3(x=0.0, y=0.0, z=-1.0)
        assert v.z == -1.0

    def test_vector_operations(self):
        """Test vector arithmetic operations."""
        v1 = Vec3(x=1.0, y=2.0, z=3.0)
        v2 = Vec3(x=4.0, y=5.0, z=6.0)

        # Addition
        v3 = v1 + v2
        assert v3.x == 5.0
        assert v3.y == 7.0
        assert v3.z == 9.0

        # Subtraction
        v4 = v2 - v1
        assert v4.x == 3.0
        assert v4.y == 3.0
        assert v4.z == 3.0

        # Distance
        distance = v1.distance_to(v2)
        assert distance == (3**2 + 3**2 + 3**2)**0.5


@pytest.mark.unit
class TestEnhancedSceneObject:
    """Test enhanced SceneObject class."""

    def test_scene_object_additional_fields(self):
        """Test additional optional fields."""
        obj = SceneObject(
            object_id="chair1",
            name="Office Chair",
            position=Vec3(x=0.0, y=0.0, z=0.4),
            rotation=Vec3(x=0.0, y=0.0, z=0.0),
            size=Vec3(x=0.5, y=0.5, z=0.9),
            visual_description="A modern ergonomic office chair with armrests",
            category="furniture",
            material="mesh",
            color="black",
            tags=["office", "seating", "ergonomic"],
            weight=15.5
        )
        assert obj.material == "mesh"
        assert obj.color == "black"
        assert "office" in obj.tags
        assert obj.weight == 15.5

    def test_scene_object_size_validation(self):
        """Test enhanced size validation."""
        # Valid sizes
        obj = SceneObject(
            object_id="table1",
            name="Table",
            position=Vec3(x=0.0, y=0.0, z=0.0),
            rotation=Vec3(x=0.0, y=0.0, z=0.0),
            size=Vec3(x=1.0, y=1.5, z=0.75),
            visual_description="A wooden dining table"
        )
        assert obj.size.z == 0.75

        # Minimum height violation
        with pytest.raises(ValueError, match="outside reasonable range"):
            SceneObject(
                object_id="paper1",
                name="Paper",
                position=Vec3(x=0.0, y=0.0, z=0.0),
                rotation=Vec3(x=0.0, y=0.0, z=0.0),
                size=Vec3(x=0.21, y=0.3, z=0.15),  # z >= 0.1
                visual_description="A sheet of paper"
            )

        # Maximum size violation
        with pytest.raises(ValueError, match="outside reasonable range"):
            SceneObject(
                object_id="building1",
                name="Building",
                position=Vec3(x=0.0, y=0.0, z=0.0),
                rotation=Vec3(x=0.0, y=0.0, z=0.0),
                size=Vec3(x=15.0, y=20.0, z=10.0),  # <= 10.0 for z
                visual_description="A large building"
            )

    def test_rotation_normalization(self):
        """Test rotation normalization."""
        obj = SceneObject(
            object_id="lamp1",
            name="Lamp",
            position=Vec3(x=0.0, y=0.0, z=0.5),
            rotation=Vec3(x=10.0, y=-5.0, z=0.0),  # Within range
            size=Vec3(x=0.2, y=0.2, z=0.4),
            visual_description="A desk lamp"
        )
        assert obj.rotation.x == 10.0
        assert obj.rotation.y == -5.0
        assert obj.rotation.z == 0.0

    def test_helper_methods(self):
        """Test SceneObject helper methods."""
        obj = SceneObject(
            object_id="book1",
            name="Book",
            position=Vec3(x=1.0, y=1.0, z=0.2),
            rotation=Vec3(x=0.0, y=0.0, z=0.0),
            size=Vec3(x=0.2, y=0.3, z=0.12),
            visual_description="A hardcover book"
        )

        # Bounds calculation
        min_point, max_point = obj.get_bounds()
        assert min_point.x == 0.9  # 1.0 - 0.1
        assert max_point.x == 1.1  # 1.0 + 0.1
        assert min_point.z == 0.14  # 0.2 - 0.06
        assert max_point.z == 0.26  # 0.2 + 0.06

        # Ground check
        assert not obj.is_on_ground()  # z = 0.2

        obj_ground = SceneObject(
            object_id="rug1",
            name="Rug",
            position=Vec3(x=0.0, y=0.0, z=0.0),
            rotation=Vec3(x=0.0, y=0.0, z=0.0),
            size=Vec3(x=2.0, y=3.0, z=0.02),
            visual_description="A floor rug"
        )
        assert obj_ground.is_on_ground()


@pytest.mark.unit
class TestEnhancedSession:
    """Test enhanced Session class."""

    def test_detailed_status_tracking(self):
        """Test detailed status enumeration."""
        session = Session(
            session_id="test_session",
            request=SessionRequest(
                text="A cozy bedroom",
                style="modern"
            ),
            status=SessionStatus.GENERATING_ASSETS
        )
        assert session.status == SessionStatus.GENERATING_ASSETS
        assert session.progress_percentage == 0.0

    def test_error_tracking(self):
        """Test error history tracking."""
        session = Session(
            session_id="test_session",
            request=SessionRequest(text="Test scene"),
            status=SessionStatus.FAILED
        )

        # Add error
        session.add_error({
            "type": "generation_failure",
            "message": "Failed to generate 3D asset",
            "object_id": "lamp1"
        })

        assert len(session.error_history) == 1
        assert session.error_history[0]["type"] == "generation_failure"
        assert "timestamp" in session.error_history[0]

    def test_retry_logic(self):
        """Test retry logic."""
        session = Session(
            session_id="test_session",
            request=SessionRequest(text="Test scene"),
            status=SessionStatus.FAILED,
            retry_count=2,
            max_retries=3
        )

        # Can retry
        assert session.can_retry()

        # Increment retry
        session.increment_retry()
        assert session.retry_count == 3
        assert session.status == SessionStatus.INIT

        # Cannot retry anymore
        session.status = SessionStatus.FAILED
        assert not session.can_retry()


@pytest.mark.unit
class TestEnhancedConstraints:
    """Test enhanced constraint system."""

    def test_new_relation_types(self):
        """Test new relation types."""
        constraint = SpatialConstraint(
            constraint_id="c001",
            type=ConstraintType.RELATIVE,
            relation=RelationType.ADJACENT,
            source="nightstand1",
            target="bed1",
            threshold_m=0.3,  # Must be <= 0.5 for ADJACENT
            priority="primary",
            weight=0.8
        )
        assert constraint.relation == "adjacent"
        assert constraint.threshold_m == 0.3

    def test_adjacent_threshold_validation(self):
        """Test ADJACENT threshold validation."""
        with pytest.raises(ValueError, match="ADJACENT threshold"):
            SpatialConstraint(
                type=ConstraintType.DISTANCE,
                relation=RelationType.ADJACENT,
                source="obj1",
                target="obj2",
                threshold_m=1.0,  # > 0.5
                priority="primary"
            )

    def test_soft_constraints(self):
        """Test soft constraint functionality."""
        soft_constraint = SpatialConstraint(
            type=ConstraintType.DISTANCE,
            relation=RelationType.NEAR,
            source="lamp1",
            target="bed1",
            threshold_m=1.5,
            priority="secondary",
            weight=0.5,
            is_soft=True
        )
        assert soft_constraint.is_soft
        assert soft_constraint.weight == 0.5

    def test_constraint_inverse_and_symmetry(self):
        """Test constraint inverse and symmetry methods."""
        # Non-symmetric constraint
        left_constraint = SpatialConstraint(
            type=ConstraintType.RELATIVE,
            relation=RelationType.LEFT_OF,
            source="nightstand1",
            target="bed1"
        )
        assert not left_constraint.is_symmetric()
        assert left_constraint.get_inverse() == RelationType.RIGHT_OF

        # Symmetric constraint
        near_constraint = SpatialConstraint(
            type=ConstraintType.DISTANCE,
            relation=RelationType.NEAR,
            source="lamp1",
            target="bed1"
        )
        assert near_constraint.is_symmetric()
        assert near_constraint.get_inverse() == RelationType.NEAR

    def test_constraint_set_features(self):
        """Test ConstraintSet advanced features."""
        constraints = [
            SpatialConstraint(
                type=ConstraintType.RELATIVE,
                relation=RelationType.LEFT_OF,
                source="nightstand1",
                target="bed1",
                priority="primary"
            ),
            SpatialConstraint(
                type=ConstraintType.DISTANCE,
                relation=RelationType.NEAR,
                source="lamp1",
                target="bed1",
                priority="secondary"
            )
        ]

        cset = ConstraintSet(relations=constraints)

        # Check categorization
        primary = cset.get_primary_constraints()
        secondary = cset.get_secondary_constraints()
        assert len(primary) == 1
        assert len(secondary) == 1
        assert primary[0].source == "nightstand1"

        # Get constraints for object
        bed_constraints = cset.get_constraints_for_object("bed1")
        assert len(bed_constraints) == 2

        # Cycle detection (should be False for this set)
        assert not cset.has_cycles()


@pytest.mark.unit
class TestEnhancedLayout:
    """Test enhanced layout schemas."""

    def test_layout_config_expansion(self):
        """Test expanded LayoutConfig."""
        config = LayoutConfig(
            max_iterations=500,
            sampling_resolution=0.05,
            constraint_weight=2.0,
            gravity_enabled=True,
            stability_margin=0.15,
            use_adaptive_sampling=True
        )
        assert config.sampling_resolution == 0.05
        assert config.constraint_weight == 2.0
        assert config.gravity_enabled

    def test_placement_quality_metrics(self):
        """Test PlacementInfo quality metrics."""
        placement = PlacementInfo(
            object_id="chair1",
            position=[1.0, 2.0, 0.0],
            rotation=[0.0, 0.0, 45.0],
            successful=True,
            placement_time_ms=45.5,
            constraint_satisfaction_score=0.85,
            stability_score=0.92,
            collision_count=0,
            placement_method="dfs",
            attempts=15,
            confidence=0.88
        )
        assert placement.constraint_satisfaction_score == 0.85
        assert placement.stability_score == 0.92
        assert placement.attempts == 15

    def test_detailed_collision_info(self):
        """Test detailed CollisionInfo."""
        collision = CollisionInfo(
            object_a="table1",
            object_b="chair1",
            penetration_depth=0.05,
            collision_type="overlap",
            severity=1.5,
            contact_point=[1.2, 1.3, 0.0],
            impulse_magnitude=2.5,
            contact_normal=[0.0, 1.0, 0.0],
            affected_constraints=["no_overlap"]
        )
        assert collision.collision_type == "overlap"
        assert collision.severity == 1.5
        assert len(collision.affected_constraints) == 1

    def test_comprehensive_dfs_trace(self):
        """Test comprehensive DFSTrace."""
        trace = DFSTrace(
            failed_object_id="lamp1",
            placed_objects=["bed1", "nightstand1"],
            conflict_type="constraint",
            active_constraints=[
                {"source": "lamp1", "target": "bed1", "relation": "near"}
            ],
            candidates_tried=75,
            search_space_size=1000,
            best_candidate_score=0.45,
            natural_language_summary="Cannot place lamp near bed due to nightstand obstruction",
            fix_suggestions=[
                "Move nightstand 20cm away",
                "Allow lamp placement on nightstand"
            ],
            traceback_depth=3,
            time_at_failure=12.5
        )
        assert trace.candidates_tried == 75
        assert trace.search_space_size == 1000
        assert len(trace.fix_suggestions) == 2
        assert "nightstand" in trace.natural_language_summary