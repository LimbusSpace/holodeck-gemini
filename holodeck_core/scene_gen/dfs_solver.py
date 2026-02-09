"""
DFS Layout Solver - Depth-First Search Based Layout Generation

Implements the core DFS algorithm from HOLODECK 2.0 for solving spatial constraints.
Features:
- Topological sorting of objects based on constraints
- Candidate position sampling based on constraints
- Depth-first search with backtracking
- Constraint validation at each step
"""

from typing import List, Dict, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from time import time
import math
from .constraint_primitives import ConstraintCalculator
from .collision_detection import CollisionDetector

@dataclass
class SearchState:
    """State maintained during DFS search."""
    placed_objects: Dict[str, Any]
    placed_count: int
    total_objects: int
    candidates_tried: int = 0
    backtrack_count: int = 0
    max_depth_reached: int = 0
    nodes_visited: int = 0

class DFSSolver:
    """Main DFS Layout Solver class."""

    @staticmethod
    def solve(
        objects: List[Any],
        constraints: List[Any],
        config: Optional[Any] = None
    ) -> Tuple[Dict[str, Any], Optional[Any]]:
        """Solve layout using DFS.

        Args:
            objects: List of scene objects
            constraints: List of spatial constraints
            config: Solver configuration

        Returns:
            (best_placement, trace_if_failed)
        """
        if config is None:
            config = DFSSolver._default_config()

        # Build object dictionary for quick lookup
        object_dict = {obj.object_id: obj for obj in objects}

        # Topological sort objects
        sorted_object_ids = DFSSolver._topological_sort_objects(objects, constraints)

        # Initialize search state
        search_state = SearchState(
            placed_objects={},
            placed_count=0,
            total_objects=len(objects)
        )

        start_time = time()

        # Recursive DFS function
        def dfs_search(depth: int, object_order: List[str]) -> bool:
            """Return True if successful, False if failed."""
            search_state.nodes_visited += 1
            search_state.max_depth_reached = max(search_state.max_depth_reached, depth)

            # Check timeout
            if time() - start_time > getattr(config, 'timeout_seconds', 30.0):
                return False

            # Solution found
            if depth >= len(object_order):
                return True

            current_object_id = object_order[depth]
            current_object = object_dict[current_object_id]

            # Generate candidates for this object
            candidates = DFSSolver._generate_candidates(
                current_object,
                search_state.placed_objects,
                constraints,
                config
            )

            # Try each candidate
            for candidate_pos in candidates:
                search_state.candidates_tried += 1

                # Validate placement
                if not DFSSolver._validate_placement(
                    current_object,
                    candidate_pos,
                    search_state.placed_objects,
                    object_dict,
                    constraints,
                    config
                ):
                    continue

                # Place the object
                search_state.placed_objects[current_object_id] = candidate_pos
                search_state.placed_count += 1

                # Recurse
                if dfs_search(depth + 1, object_order):
                    return True

                # Backtrack
                del search_state.placed_objects[current_object_id]
                search_state.backtrack_count += 1
                search_state.placed_count -= 1

            return False

        # Run DFS
        success = dfs_search(0, sorted_object_ids)

        elapsed_time = time() - start_time

        if success:
            # Full success - no trace needed
            return search_state.placed_objects, None

        # Generate failure trace
        failed_object_id = sorted_object_ids[search_state.placed_count] if search_state.placed_count < len(sorted_object_ids) else sorted_object_ids[-1]

        trace = {
            "failed_object_id": failed_object_id,
            "placed_objects": sorted_object_ids[:search_state.placed_count],
            "conflict_type": "constraint",
            "candidates_tried": search_state.candidates_tried,
            "nodes_visited": search_state.nodes_visited,
            "backtrack_count": search_state.backtrack_count,
            "time_at_failure": elapsed_time,
            "natural_language_summary": f"Failed to place {failed_object_id} after {search_state.candidates_tried} candidates in {elapsed_time:.2f}s"
        }

        return search_state.placed_objects, trace

    @staticmethod
    def _topological_sort_objects(
        objects: List[Any],
        constraints: List[Any]
    ) -> List[str]:
        """Sort objects based on dependency graph from constraints."""
        # Build dependency graph
        object_ids = [obj.object_id for obj in objects]
        dependencies = {obj_id: set() for obj_id in object_ids}

        for constraint in constraints:
            if hasattr(constraint, 'source') and constraint.source in dependencies:
                if hasattr(constraint, 'target') and constraint.target in dependencies:
                    dependencies[constraint.source].add(constraint.target)

        # Topological sort using Kahn's algorithm
        incoming_count = {obj_id: 0 for obj_id in dependencies}
        for obj_id, deps in dependencies.items():
            for dep_target in deps:
                if dep_target in incoming_count:
                    incoming_count[dep_target] += 1

        # Start with objects that have no dependencies
        sorted_objects = []
        zero_deps = [obj_id for obj_id, count in incoming_count.items() if count == 0]

        while zero_deps:
            obj_id = zero_deps.pop(0)
            sorted_objects.append(obj_id)

            # Remove this object's outgoing edges
            for dep_target in dependencies[obj_id]:
                incoming_count[dep_target] -= 1
                if incoming_count[dep_target] == 0:
                    zero_deps.append(dep_target)

        # If there are still objects (cycle detected), add them at the end
        remaining = [obj_id for obj_id in incoming_count if obj_id not in sorted_objects]
        sorted_objects.extend(remaining)

        return sorted_objects

    @staticmethod
    def _generate_candidates(
        obj: Any,
        placed_objects: Dict[str, Any],
        constraints: List[Any],
        config: Any
    ) -> List[Any]:
        """Generate candidate positions for an object."""
        candidates = []

        # Simple grid-based sampling around initial position
        grid_size = getattr(config, 'sampling_resolution', 0.5)
        grid_range = 2  # Sample in a 4x4x1 grid

        for dx in range(-grid_range, grid_range + 1):
            for dy in range(-grid_range, grid_range + 1):
                for dz in range(0, 1):  # Keep on same level
                    candidate = type('obj', (), {})()
                    candidate.x = obj.position.x + dx * grid_size
                    candidate.y = obj.position.y + dy * grid_size
                    candidate.z = obj.position.z + dz * grid_size
                    candidates.append(candidate)

        # Limit number of candidates
        max_candidates = getattr(config, 'max_candidates_per_object', 100)
        if len(candidates) > max_candidates:
            candidates = candidates[:max_candidates]

        return candidates

    @staticmethod
    def _validate_placement(
        obj: Any,
        position: Any,
        placed_objects: Dict[str, Any],
        all_objects: Dict[str, Any],
        constraints: List[Any],
        config: Any
    ) -> bool:
        """Validate if object can be placed at given position."""
        # Check collision with ground
        clearance_m = getattr(config, 'collision_clearance_m', 0.02)

        # Check collision with other objects
        for other_id, other_pos in placed_objects.items():
            other_obj = all_objects.get(other_id)
            if other_obj and CollisionDetector.check_collision(obj, position, other_obj, other_pos, clearance_m):
                return False

        return True

    @staticmethod
    def _default_config() -> Any:
        """Create default configuration."""
        class DefaultConfig:
            timeout_seconds = 30.0
            max_candidates_per_object = 100
            sampling_resolution = 0.5
            collision_clearance_m = 0.02

        return DefaultConfig()