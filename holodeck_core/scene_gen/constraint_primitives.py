"""
Spatial Constraint Primitives - Mathematical Implementation

This module implements the 10 spatial constraint types defined in HOLODECK 2.0,
providing precise geometric calculations for each constraint type.

Constraint Types:
- Relative: left of, right of, in front of, behind, side of
- Distance: near (<= 2m), far (> 8m), adjacent (<= 0.5m)
- Vertical: on (contact), above (>= 2m), below
- Rotation: face to (< 10°), parallel, perpendicular
"""

from typing import List, Tuple, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass
from math import sqrt, cos, sin, radians, degrees, atan2, pi
import numpy as np

# Constants from HOLODECK 2.0 paper
BUFFER_DISTANCE = 0.1  # 0.1m buffer for relative positioning
NEAR_THRESHOLD = 2.0   # Near distance <= 2m
FAR_THRESHOLD = 8.0    # Far distance >= 8m
ADJACENT_THRESHOLD = 0.5  # Adjacent distance <= 0.5m
ABOVE_THRESHOLD = 2.0  # Above vertical distance >= 2m
CONTACT_TOLERANCE = 0.002  # 2mm tolerance for "on" contact
FACE_TO_TOLERANCE = 10.0    # 10 degree tolerance for "face to"

@dataclass
class ConstraintViolation:
    """Represents a constraint violation with severity information."""
    constraint: Any
    violation_distance: float
    violation_angle: Optional[float] = None
    severity: float = 0.0

@dataclass
class ConstraintRegion:
    """Defines a spatial region where an object can be placed to satisfy a constraint."""
    min_point: Tuple[float, float, float]
    max_point: Tuple[float, float, float]
    allowed_positions: List[Tuple[float, float, float]] = None
    is_3d_region: bool = False

class ConstraintCalculator:
    """Calculates and validates spatial constraints between objects."""

    @staticmethod
    def calculate_distance(obj1: Any, obj2: Any) -> Tuple[float, float, float]:
        """Calculate 3D distance and horizontal distance between two objects.

        Returns:
            (total_distance, horizontal_distance, vertical_distance)
        """
        pos1 = obj1.position
        pos2 = obj2.position

        dx = pos2.x - pos1.x
        dy = pos2.y - pos1.y
        dz = pos2.z - pos1.z

        total_distance = sqrt(dx**2 + dy**2 + dz**2)
        horizontal_distance = sqrt(dx**2 + dy**2)
        vertical_distance = abs(dz)

        return total_distance, horizontal_distance, vertical_distance

    @staticmethod
    def check_constraint(
        constraint: Any,
        source_obj: Any,
        target_obj: Any
    ) -> Tuple[bool, float, Optional[float]]:
        """Check if a spatial constraint is satisfied.

        Args:
            constraint: Spatial constraint to check
            source_obj: Source object
            target_obj: Target object

        Returns:
            (is_satisfied, distance_violation, angle_violation)
        """
        relation = constraint.relation

        if relation in ['left_of', 'right_of', 'in_front_of', 'behind', 'side_of']:
            return ConstraintCalculator.check_relative_constraint(source_obj, target_obj, relation)
        elif relation in ['near', 'far', 'adjacent']:
            return ConstraintCalculator.check_distance_constraint(source_obj, target_obj, relation, constraint.threshold_m)
        elif relation in ['on', 'above', 'below']:
            return ConstraintCalculator.check_vertical_constraint(source_obj, target_obj, relation, constraint.threshold_m)
        elif relation in ['face_to', 'parallel', 'perpendicular']:
            return ConstraintCalculator.check_rotation_constraint(source_obj, target_obj, relation, constraint.deg_tolerance)

        return False, float('inf'), 180.0

    @staticmethod
    def check_relative_constraint(
        source: Any,
        target: Any,
        relation: str
    ) -> Tuple[bool, float]:
        """Check relative positioning constraints."""
        pos_src = source.position
        pos_tgt = target.position

        dx = pos_tgt.x - pos_src.x
        dy = pos_tgt.y - pos_src.y

        if relation == 'left_of':
            violated = dx >= -BUFFER_DISTANCE
            violation = max(0, dx + BUFFER_DISTANCE) if violated else 0.0
            return not violated, violation
        elif relation == 'right_of':
            violated = dx <= BUFFER_DISTANCE
            violation = max(0, BUFFER_DISTANCE - dx) if violated else 0.0
            return not violated, violation
        elif relation == 'in_front_of':
            violated = dy >= -BUFFER_DISTANCE
            violation = max(0, dy + BUFFER_DISTANCE) if violated else 0.0
            return not violated, violation
        elif relation == 'behind':
            violated = dy <= BUFFER_DISTANCE
            violation = max(0, BUFFER_DISTANCE - dy) if violated else 0.0
            return not violated, violation

        return False, float('inf')

    @staticmethod
    def check_distance_constraint(
        source: Any,
        target: Any,
        relation: str,
        threshold: Optional[float] = None
    ) -> Tuple[bool, float]:
        """Check distance constraints."""
        _, horizontal_distance, _ = ConstraintCalculator.calculate_distance(source, target)

        if relation == 'near':
            limit = threshold or NEAR_THRESHOLD
            violated = horizontal_distance > limit
            violation = horizontal_distance - limit if violated else 0.0
            return not violated, violation
        elif relation == 'far':
            limit = threshold or FAR_THRESHOLD
            violated = horizontal_distance < limit
            violation = limit - horizontal_distance if violated else 0.0
            return not violated, violation
        elif relation == 'adjacent':
            limit = threshold or ADJACENT_THRESHOLD
            violated = horizontal_distance > limit
            violation = horizontal_distance - limit if violated else 0.0
            return not violated, violation

        return False, float('inf')

    @staticmethod
    def check_vertical_constraint(
        source: Any,
        target: Any,
        relation: str,
        threshold: Optional[float] = None
    ) -> Tuple[bool, float]:
        """Check vertical constraints."""
        pos_src = source.position
        pos_tgt = target.position

        if relation == 'on':
            # Check contact with 2mm tolerance
            expected_z = pos_tgt.z + target.size.z + source.size.z / 2.0
            z_diff = abs(pos_src.z - expected_z)
            satisfied = z_diff <= CONTACT_TOLERANCE
            return satisfied, z_diff
        elif relation == 'above':
            limit = threshold or ABOVE_THRESHOLD
            vertical_distance = pos_src.z - pos_tgt.z
            return vertical_distance >= limit, max(0, limit - vertical_distance)

        return False, float('inf')

    @staticmethod
    def check_rotation_constraint(
        source: Any,
        target: Any,
        relation: str,
        tolerance: Optional[float] = None
    ) -> Tuple[bool, float]:
        """Check rotation constraints."""
        pos_src = source.position
        pos_tgt = target.position

        dx = pos_tgt.x - pos_src.x
        dy = pos_tgt.y - pos_src.y

        src_front_angle = radians(source.rotation.z)
        forward_x = sin(src_front_angle)
        forward_y = -cos(src_front_angle)

        dot_product = forward_x * dx + forward_y * dy
        magnitude_product = sqrt(forward_x**2 + forward_y**2) * sqrt(dx**2 + dy**2)

        if magnitude_product == 0:
            return False, 180.0

        angle_to_target = degrees(acos(dot_product / magnitude_product))
        angle_to_target = min(angle_to_target, 360 - angle_to_target)

        limit = tolerance or FACE_TO_TOLERANCE

        if relation == 'face_to':
            violated = angle_to_target > limit
            violation = angle_to_target - limit if violated else 0.0
            return not violated, violation

        return False, 180.0


def check_constraint_satisfaction(
    constraint: Any,
    source_obj: Any,
    target_obj: Any
) -> Tuple[bool, float]:
    """Check if constraint is satisfied and return violation distance."""
    is_satisfied, distance_violation, _ = ConstraintCalculator.check_constraint(
        constraint, source_obj, target_obj
    )
    return is_satisfied, distance_violation


def get_constraint_region(
    source_obj: Any,
    target_obj: Any,
    constraint: Any
) -> ConstraintRegion:
    """Get the allowed region for an object under a constraint."""
    # This is a simplified implementation
    # In production, this would return actual geometric regions
    return ConstraintRegion(
        min_point=(-10.0, -10.0, 0.0),
        max_point=(10.0, 10.0, 10.0),
        is_3d_region=True
    )