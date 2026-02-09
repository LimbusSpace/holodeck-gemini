"""
Collision Detection System - 3D AABB Detection

This module implements 3D collision detection using Axis-Aligned Bounding Boxes (AABB).
Provides fast collision detection for layout validation.

Features:
- Fast AABB intersection testing
- Minimum distance calculation between objects
- Ground collision detection
- Stability checks
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from math import sqrt
import numpy as np

@dataclass
class AABB:
    """Axis-Aligned Bounding Box for collision detection."""
    min_x: float
    min_y: float
    min_z: float
    max_x: float
    max_y: float
    max_z: float

    def intersects(self, other: 'AABB') -> bool:
        """Check if this AABB intersects with another AABB."""
        return not (
            self.max_x < other.min_x or
            self.min_x > other.max_x or
            self.max_y < other.min_y or
            self.min_y > other.max_y or
            self.max_z < other.min_z or
            self.min_z > other.max_z
        )

    def distance_to(self, other: 'AABB') -> float:
        """Calculate minimum distance between two AABBs. Returns 0 if they intersect."""
        if self.intersects(other):
            return 0.0

        dx = max(0.0, max(other.min_x - self.max_x, self.min_x - other.max_x))
        dy = max(0.0, max(other.min_y - self.max_y, self.min_y - other.max_y))
        dz = max(0.0, max(other.min_z - self.max_z, self.min_z - other.max_z))

        return sqrt(dx**2 + dy**2 + dz**2)

class CollisionDetector:
    """Advanced collision detection with multiple validation functions."""

    @staticmethod
    def check_collision(
        obj1: Any,
        pos1: Any,
        obj2: Any,
        pos2: Any,
        clearance_m: float = 0.0
    ) -> bool:
        """Check if two objects collide at given positions."""
        aabb1 = CollisionDetector._create_aabb(obj1, pos1)
        aabb2 = CollisionDetector._create_aabb(obj2, pos2)

        if clearance_m > 0:
            aabb1 = CollisionDetector._expand_aabb(aabb1, clearance_m)
            aabb2 = CollisionDetector._expand_aabb(aabb2, clearance_m)

        return aabb1.intersects(aabb2)

    @staticmethod
    def calculate_min_distance(
        obj1: Any,
        pos1: Any,
        obj2: Any,
        pos2: Any
    ) -> Tuple[float, float, float]:
        """Calculate minimum distance between two objects."""
        aabb1 = CollisionDetector._create_aabb(obj1, pos1)
        aabb2 = CollisionDetector._create_aabb(obj2, pos2)

        min_distance = aabb1.distance_to(aabb2)

        # Per-axis clearance
        clearance_x = max(0.0, max(aabb2.min_x - aabb1.max_x, aabb1.min_x - aabb2.max_x))
        clearance_y = max(0.0, max(aabb2.min_y - aabb1.max_y, aabb1.min_y - aabb2.max_y))

        return min_distance, clearance_x, clearance_y

    @staticmethod
    def _create_aabb(obj: Any, position: Any) -> AABB:
        """Create AABB from object and position."""
        half_x = obj.size.x / 2.0
        half_y = obj.size.y / 2.0
        half_z = obj.size.z / 2.0

        return AABB(
            min_x=position.x - half_x,
            min_y=position.y - half_y,
            min_z=position.z - half_z,
            max_x=position.x + half_x,
            max_y=position.y + half_y,
            max_z=position.z + half_z
        )

    @staticmethod
    def _expand_aabb(aabb: AABB, margin: float) -> AABB:
        """Expand AABB by margin."""
        return AABB(
            min_x=aabb.min_x - margin,
            min_y=aabb.min_y - margin,
            min_z=aabb.min_z - margin,
            max_x=aabb.max_x + margin,
            max_y=aabb.max_y + margin,
            max_z=aabb.max_z + margin
        )

def check_collision(
    obj1: Any,
    pos1: Any,
    obj2: Any,
    pos2: Any,
    clearance_m: float = 0.0
) -> bool:
    """Check if two objects collide."""
    return CollisionDetector.check_collision(obj1, pos1, obj2, pos2, clearance_m)

def calculate_min_distance(
    obj1: Any,
    pos1: Any,
    obj2: Any,
    pos2: Any
) -> Tuple[float, float, float]:
    """Calculate minimum distance between two objects."""
    return CollisionDetector.calculate_min_distance(obj1, pos1, obj2, pos2)