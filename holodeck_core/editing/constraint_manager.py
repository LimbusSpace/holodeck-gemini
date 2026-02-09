"""Constraint management module for handling spatial constraints during editing.

Implements constraint delta updates, validation, and conflict resolution
for the focus object editing strategy.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Set

from holodeck_core.schemas.constraints import SpatialConstraint


class ConstraintManager:
    """Manages spatial constraints during scene editing operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Define constraint compatibility rules
        self.compatibility_rules = {
            "left_of": {"compatible": ["right_of", "near"], "conflicting": ["right_of"]},
            "right_of": {"compatible": ["left_of", "near"], "conflicting": ["left_of"]},
            "in_front_of": {"compatible": ["behind", "near"], "conflicting": ["behind"]},
            "behind": {"compatible": ["in_front_of", "near"], "conflicting": ["in_front_of"]},
            "above": {"compatible": ["below", "near"], "conflicting": ["below"]},
            "below": {"compatible": ["above", "near"], "conflicting": ["above"]},
            "on": {"compatible": ["near"], "conflicting": ["below", "far_from"]},
            "near": {"compatible": ["left_of", "right_of", "in_front_of", "behind", "above", "below", "on"],
                    "conflicting": ["far_from"]},
            "far_from": {"compatible": [], "conflicting": ["near", "on"]}
        }

    def apply_deltas(self, current_constraints: Dict[str, Any], delta_constraints: List[Dict[str, Any]],
                    removed_constraint_ids: List[str]) -> Dict[str, Any]:
        """Apply constraint deltas to current constraints.

        Args:
            current_constraints: Current constraint set
            delta_constraints: New/modified constraints to add
            removed_constraint_ids: IDs of constraints to remove

        Returns:
            Updated constraint set
        """
        try:
            updated = current_constraints.copy()

            # Initialize relations if not present
            if "relations" not in updated:
                updated["relations"] = []

            # Remove specified constraints
            if removed_constraint_ids:
                updated["relations"] = [
                    rel for rel in updated["relations"]
                    if rel.get("id") not in removed_constraint_ids
                ]

            # Add or update delta constraints
            for delta_constraint in delta_constraints:
                try:
                    # Handle both dict and SpatialConstraint objects
                    if isinstance(delta_constraint, dict):
                        constraint = SpatialConstraint(**delta_constraint)
                        constraint_dict = delta_constraint.copy()
                    else:
                        constraint = delta_constraint
                        constraint_dict = constraint.model_dump()

                    # Check for conflicts with existing constraints
                    conflicts = self._find_conflicts(constraint, updated["relations"])

                    if conflicts:
                        self.logger.warning(f"Constraint conflicts detected: {conflicts}")
                        # Resolve conflicts by removing conflicting constraints
                        updated["relations"] = [
                            rel for rel in updated["relations"]
                            if rel.get("id") not in [c.get("id") for c in conflicts]
                        ]

                    # Add the new constraint
                    constraint_dict["id"] = self._generate_constraint_id(constraint)
                    updated["relations"].append(constraint_dict)

                except Exception as e:
                    self.logger.error(f"Error processing delta constraint: {e}")
                    continue

            # Validate final constraint set
            validation_result = self._validate_constraints(updated)
            if not validation_result["valid"]:
                self.logger.warning(f"Constraint validation issues: {validation_result['issues']}")

            return updated

        except Exception as e:
            self.logger.error(f"Error applying constraint deltas: {e}")
            return current_constraints

    def remove_object_constraints(self, constraints: Dict[str, Any],
                                object_id: str) -> Dict[str, Any]:
        """Remove all constraints involving a specific object.

        Args:
            constraints: Current constraint set
            object_id: Object ID to remove constraints for

        Returns:
            Updated constraint set
        """
        try:
            updated = constraints.copy()

            if "relations" in updated:
                updated["relations"] = [
                    rel for rel in updated["relations"]
                    if rel.get("a") != object_id and rel.get("b") != object_id
                ]

            return updated

        except Exception as e:
            self.logger.error(f"Error removing object constraints: {e}")
            return constraints

    def get_object_constraints(self, constraints: Dict[str, Any],
                             object_id: str) -> List[Dict[str, Any]]:
        """Get all constraints involving a specific object.

        Args:
            constraints: Constraint set
            object_id: Object ID to get constraints for

        Returns:
            List of constraints involving the object
        """
        try:
            if "relations" not in constraints:
                return []

            return [
                rel for rel in constraints["relations"]
                if rel.get("a") == object_id or rel.get("b") == object_id
            ]

        except Exception as e:
            self.logger.error(f"Error getting object constraints: {e}")
            return []

    def validate_constraint_set(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete constraint set for consistency and feasibility.

        Args:
            constraints: Constraint set to validate

        Returns:
            Dict with validation results
        """
        try:
            validation_result = {
                "valid": True,
                "issues": [],
                "warnings": [],
                "statistics": {}
            }

            if "relations" not in constraints:
                validation_result["valid"] = False
                validation_result["issues"].append("No relations found in constraints")
                return validation_result

            relations = constraints["relations"]

            # Check for constraint conflicts
            conflicts = self._find_all_conflicts(relations)
            if conflicts:
                validation_result["valid"] = False
                validation_result["issues"].extend(conflicts)

            # Check for circular dependencies
            circular_deps = self._find_circular_dependencies(relations)
            if circular_deps:
                validation_result["valid"] = False
                validation_result["issues"].extend(circular_deps)

            # Check for redundant constraints
            redundant = self._find_redundant_constraints(relations)
            if redundant:
                validation_result["warnings"].extend(redundant)

            # Generate statistics
            validation_result["statistics"] = self._generate_constraint_statistics(relations)

            return validation_result

        except Exception as e:
            self.logger.error(f"Error validating constraints: {e}")
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "warnings": [],
                "statistics": {}
            }

    def _find_conflicts(self, new_constraint: SpatialConstraint,
                       existing_relations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find constraints that conflict with the new constraint."""
        conflicts = []

        for existing in existing_relations:
            if self._constraints_conflict(new_constraint, existing):
                conflicts.append(existing)

        return conflicts

    def _find_all_conflicts(self, relations: List[Dict[str, Any]]) -> List[str]:
        """Find all conflicts in a set of relations."""
        conflicts = []

        for i, rel1 in enumerate(relations):
            for j, rel2 in enumerate(relations[i+1:], i+1):
                try:
                    constraint1 = SpatialConstraint(**rel1)
                    constraint2 = SpatialConstraint(**rel2)

                    if self._constraints_conflict(constraint1, constraint2.model_dump()):
                        conflicts.append(
                            f"Conflict between constraints {i} and {j}: "
                            f"{rel1.get('type')} vs {rel2.get('type')}"
                        )
                except Exception:
                    continue

        return conflicts

    def _constraints_conflict(self, constraint1: SpatialConstraint,
                            constraint2: Dict[str, Any]) -> bool:
        """Check if two constraints conflict with each other."""
        try:
            # Parse second constraint
            constraint2_obj = SpatialConstraint(**constraint2)

            # Check if they involve the same objects
            objects1 = {constraint1.source, constraint1.target}
            objects2 = {constraint2_obj.source, constraint2_obj.target}

            if objects1 != objects2:
                return False

            # Check compatibility rules
            constraint1_type = constraint1.type.value if hasattr(constraint1.type, 'value') else constraint1.type
            constraint2_type = constraint2_obj.type.value if hasattr(constraint2_obj.type, 'value') else constraint2_obj.type

            compatibility = self.compatibility_rules.get(constraint1_type, {})
            conflicting_types = compatibility.get("conflicting", [])

            return constraint2_type in conflicting_types

        except Exception as e:
            self.logger.warning(f"Error checking constraint conflict: {e}")
            return False

    def _find_circular_dependencies(self, relations: List[Dict[str, Any]]) -> List[str]:
        """Find circular dependencies in directional constraints."""
        circular_deps = []

        # Build directed graph for directional constraints
        graph = {}
        directional_types = ["left_of", "right_of", "in_front_of", "behind", "above", "below"]

        for rel in relations:
            if rel.get("type") in directional_types:
                a, b = rel.get("a"), rel.get("b")
                if a not in graph:
                    graph[a] = []
                graph[a].append(b)

        # Check for cycles
        visited = set()
        rec_stack = set()

        def has_cycle(node):
            if node in rec_stack:
                return True
            if node in visited:
                return False

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if has_cycle(neighbor):
                    return True

            rec_stack.remove(node)
            return False

        for node in graph:
            if has_cycle(node):
                circular_deps.append(f"Circular dependency detected involving {node}")
                break

        return circular_deps

    def _find_redundant_constraints(self, relations: List[Dict[str, Any]]) -> List[str]:
        """Find redundant constraints that don't add new information."""
        redundant = []

        # Group constraints by object pairs
        object_pair_constraints = {}
        for i, rel in enumerate(relations):
            pair = tuple(sorted([rel.get("a"), rel.get("b")]))
            if pair not in object_pair_constraints:
                object_pair_constraints[pair] = []
            object_pair_constraints[pair].append((i, rel))

        # Check for redundancy within each pair
        for pair, constraints in object_pair_constraints.items():
            if len(constraints) > 1:
                # Multiple constraints between same objects might be redundant
                constraint_types = [c[1].get("type") for c in constraints]
                if len(set(constraint_types)) < len(constraint_types):
                    redundant.append(f"Multiple constraints of same type for objects {pair}")

        return redundant

    def _generate_constraint_id(self, constraint: SpatialConstraint) -> str:
        """Generate unique ID for a constraint."""
        return f"constraint_{constraint.type}_{constraint.a}_{constraint.b}"

    def _validate_constraints(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Validate constraints for internal consistency."""
        return self.validate_constraint_set(constraints)

    def _generate_constraint_statistics(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate statistics about the constraint set."""
        stats = {
            "total_constraints": len(relations),
            "constraint_types": {},
            "objects_involved": set(),
            "average_constraints_per_object": 0.0
        }

        # Count constraint types
        for rel in relations:
            constraint_type = rel.get("type", "unknown")
            stats["constraint_types"][constraint_type] = stats["constraint_types"].get(constraint_type, 0) + 1

            # Track objects
            stats["objects_involved"].add(rel.get("a"))
            stats["objects_involved"].add(rel.get("b"))

        # Calculate averages
        num_objects = len(stats["objects_involved"])
        if num_objects > 0:
            stats["average_constraints_per_object"] = len(relations) / num_objects

        # Convert set to list for JSON serialization
        stats["objects_involved"] = list(stats["objects_involved"])
        stats["num_objects"] = num_objects

        return stats