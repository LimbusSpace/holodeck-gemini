"""
Scene Generation Module for HOLODECK 2.0

This module implements the core scene generation logic including:
- Constraint Primitives: Mathematical definitions for spatial relationships
- Collision Detection: 3D boundary box collision checking
- DFS Solver: Depth-first search based layout solving
- Failure Analysis: Trace generation for iterative refinement
"""

from .constraint_primitives import (
    ConstraintCalculator,
    ConstraintViolation,
    ConstraintRegion,
    check_constraint_satisfaction,
    get_constraint_region,
)

from .collision_detection import (
    CollisionDetector,
    AABB,
    check_collision,
    calculate_min_distance,
)

from .dfs_solver import (
    DFSSolver,
    # SearchNode,  # Not implemented yet
    # CandidateGenerator,  # Not implemented yet
    # PlacementValidator,  # Not implemented yet
)

from .failure_analysis import (
    FailureAnalyzer,
    ConflictType,
    generate_trace,
)

from .constraint_generator import (
    ConstraintGenerator,
    generate_constraints_from_scene,
)

__all__ = [
    'ConstraintCalculator',
    'ConstraintViolation',
    'ConstraintRegion',
    'check_constraint_satisfaction',
    'get_constraint_region',
    'CollisionDetector',
    'AABB',
    'check_collision',
    'calculate_min_distance',
    'DFSSolver',
    # 'SearchNode',  # Not implemented yet
    # 'CandidateGenerator',  # Not implemented yet
    # 'PlacementValidator',  # Not implemented yet
    'FailureAnalyzer',
    'ConflictType',
    'generate_trace',
    'ConstraintGenerator',
    'generate_constraints_from_scene',
]