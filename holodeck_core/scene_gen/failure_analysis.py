"""
Failure Analysis - Trace Generation for Iterative Refinement

This module analyzes failed DFS attempts and generates structured traces
with natural language summaries and fix suggestions.

Features:
- Bottleneck identification
- Conflict type classification
- Natural language summary generation
- Fix suggestion generation
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ConflictType(Enum):
    """Types of conflicts in layout solving."""
    COLLISION = "collision"
    BOUNDARY = "boundary"
    CONSTRAINT = "constraint"
    UNSTABLE = "unstable"
    TIMEOUT = "timeout"
    NO_SOLUTION = "no_solution"

@dataclass
class ConflictInfo:
    """Information about a specific conflict."""
    conflict_type: ConflictType
    object_id: str
    details: Dict[str, Any]
    severity: float  # 0.0 to 1.0, where 1.0 is most severe

class FailureAnalyzer:
    """Analyzes placement failures and generates actionable feedback."""

    @staticmethod
    def analyze_failure(
        failed_object_id: str,
        placed_objects: List[str],
        attempted_positions: List[Dict[str, Any]],
        constraints: List[Any],
        failure_type: ConflictType,
        solver_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive failure analysis.

        Args:
            failed_object_id: ID of the object that failed to place
            placed_objects: List of successfully placed object IDs
            attempted_positions: List of attempted positions with violation reasons
            constraints: List of active constraints
            failure_type: Type of failure
            solver_stats: Statistics from the solver

        Returns:
            Comprehensive failure trace
        """
        # Extract violation patterns
        violation_counts = FailureAnalyzer._analyze_violations(attempted_positions)

        # Generate natural language summary
        nl_summary = FailureAnalyzer._generate_natural_language_summary(
            failed_object_id, placed_objects, failure_type, violation_counts
        )

        # Generate fix suggestions
        fix_suggestions = FailureAnalyzer._generate_fix_suggestions(
            constraints, violation_counts, failure_type
        )

        # Build trace
        trace = {
            "failed_object_id": failed_object_id,
            "placed_objects": placed_objects,
            "conflict_type": failure_type.value,
            "active_constraints": [
                {
                    "source": getattr(c, 'source', 'unknown'),
                    "target": getattr(c, 'target', 'unknown'),
                    "relation": getattr(c, 'relation', 'unknown')
                } for c in constraints
            ],
            "violation_analysis": violation_counts,
            "natural_language_summary": nl_summary,
            "fix_suggestions": fix_suggestions,
            "solver_stats": solver_stats,
            "trace_version": "1.0"
        }

        return trace

    @staticmethod
    def _analyze_violations(attempted_positions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Analyze violation patterns from attempted positions."""
        violation_counts = {
            "collision": 0,
            "constraint_violation": 0,
            "out_of_bounds": 0,
            "unstable": 0
        }

        for attempt in attempted_positions:
            violations = attempt.get("violations", [])
            for violation in violations:
                if violation in violation_counts:
                    violation_counts[violation] += 1

        return violation_counts

    @staticmethod
    def _generate_natural_language_summary(
        failed_object_id: str,
        placed_objects: List[str],
        failure_type: ConflictType,
        violation_counts: Dict[str, int]
    ) -> str:
        """Generate human-readable summary of the failure."""
        success_count = len(placed_objects)

        if failure_type == ConflictType.COLLISION:
            return (
                f"Failed to place {failed_object_id}: "
                f"{violation_counts.get('collision', 0)} placement attempts "
                f"resulted in collisions with already placed objects "
                f"({', '.join(placed_objects)}). "
                f"The object may be too large for the available space."
            )

        elif failure_type == ConflictType.CONSTRAINT:
            return (
                f"Failed to place {failed_object_id}: "
                f"{success_count} objects placed successfully, "
                f"but constraints could not be satisfied for the remaining object. "
                f"Consider relaxing or removing conflicting constraints."
            )

        elif failure_type == ConflictType.TIMEOUT:
            return (
                f"Failed to place {failed_object_id} within timeout: "
                f"Search space too large or constrained. "
                f"Solution space may be non-existent or extremely sparse."
            )

        return (
            f"Failed to place {failed_object_id} after trying multiple positions. "
            f"Object count: {success_count} placed successfully."
        )

    @staticmethod
    def _generate_fix_suggestions(
        constraints: List[Any],
        violation_counts: Dict[str, int],
        failure_type: ConflictType
    ) -> List[str]:
        """Generate actionable suggestions for fixing the failure."""
        suggestions = []

        if failure_type == ConflictType.COLLISION:
            suggestions.append(
                "Increase spacing between objects by enabling 'spatial_buffer' flag"
            )
            suggestions.append(
                "Consider reducing object sizes or removing some objects from the scene"
            )
            suggestions.append(
                "Review near/far distance constraints - they may be too restrictive"
            )

        elif failure_type == ConflictType.CONSTRAINT:
            suggestions.append(
                "Relax spatial constraints (increase near distance, decrease far distance)"
            )
            suggestions.append(
                "Identify and remove conflicting constraints"
            )
            suggestions.append(
                "Consider making some constraints 'soft' rather than 'hard'"
            )

        elif failure_type == ConflictType.TIMEOUT:
            suggestions.append(
                "Increase timeout configuration"
            )
            suggestions.append(
                "Reduce scene complexity (fewer objects or simpler constraints)"
            )
            suggestions.append(
                "Increase sampling resolution for faster convergence"
            )

        suggestions.append("Use iterative solving with constraint refinement")
        suggestions.append("Check for cycle dependencies in constraint graph")

        return suggestions

def generate_trace(
    failed_object_id: str,
    placed_objects: List[str],
    attempted_positions: List[Dict[str, Any]],
    constraints: List[Any],
    failure_type: ConflictType,
    solver_stats: Dict[str, Any]
) -> Dict[str, Any]:
    """Convenience function to generate failure trace."""
    return FailureAnalyzer.analyze_failure(
        failed_object_id, placed_objects, attempted_positions,
        constraints, failure_type, solver_stats
    )