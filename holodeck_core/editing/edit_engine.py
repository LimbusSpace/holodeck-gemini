"""Core edit engine implementing the focus object strategy for scene editing.

This module implements the key editing principles from GEMINI.md:
- Focus object strategy: only modify one object at a time
- Constraint delta updates: incremental constraint modifications
- Edit history tracking: maintain version control and audit trail
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

from holodeck_core.schemas.edit_history import EditCommand, EditResult, EditHistory
from holodeck_core.schemas.constraints import SpatialConstraint
from holodeck_core.storage import WorkspaceManager
from holodeck_core.scene_gen.layout_solver import LayoutSolver, LayoutSolution
from .feedback_parser import FeedbackParser
from .constraint_manager import ConstraintManager
from .asset_editor import AssetEditor


class EditEngine:
    """Main edit engine coordinating the editing workflow."""

    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace = workspace_manager
        self.logger = logging.getLogger(__name__)

        # Initialize sub-components
        self.feedback_parser = FeedbackParser()
        self.constraint_manager = ConstraintManager()
        self.asset_editor = AssetEditor(workspace_manager)

        # Edit configuration
        self.max_edit_iterations = 3
        self.focus_object_strategy = True  # Always use focus object strategy

    def process_feedback(self, session_id: str, feedback_text: str) -> Tuple[EditCommand, EditResult]:
        """Process user feedback and apply the edit.

        Args:
            session_id: Scene session identifier
            feedback_text: User feedback describing desired changes

        Returns:
            Tuple of (EditCommand, EditResult) representing the edit operation
        """
        start_time = time.time()

        try:
            # Step 1: Parse feedback to understand intent
            self.logger.info(f"Processing feedback for session {session_id}: {feedback_text}")
            parse_result = self.feedback_parser.parse_feedback(session_id, feedback_text)

            # Create edit command
            edit_id = f"edit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            edit_command = EditCommand(
                edit_id=edit_id,
                session_id=session_id,
                user_feedback=feedback_text,
                interpreted_intent=parse_result["interpreted_intent"],
                focus_object_id=parse_result["focus_object_id"],
                edit_type=parse_result["edit_type"],
                delta_constraints=parse_result.get("delta_constraints", []),
                removed_constraints=parse_result.get("removed_constraints", []),
                assets_to_regenerate=parse_result.get("assets_to_regenerate", []),
                confidence_score=parse_result["confidence_score"],
                processing_time=time.time() - start_time
            )

            # Step 2: Apply the edit based on type
            edit_result = self._apply_edit(edit_command, parse_result)

            # Step 3: Save edit history
            self._save_edit_history(session_id, edit_command, edit_result)

            self.logger.info(f"Edit {edit_id} completed with status: {edit_result.status}")
            return edit_command, edit_result

        except Exception as e:
            self.logger.error(f"Error processing feedback for session {session_id}: {e}")

            # Create failed edit command and result
            edit_id = f"edit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            edit_command = EditCommand(
                edit_id=edit_id,
                session_id=session_id,
                user_feedback=feedback_text,
                interpreted_intent="Failed to parse feedback",
                edit_type="layout",
                confidence_score=0.0,
                processing_time=time.time() - start_time
            )

            edit_result = EditResult(
                edit_id=edit_id,
                status="failed",
                error_message=str(e),
                application_time=0.0
            )

            return edit_command, edit_result

    def _apply_edit(self, edit_command: EditCommand, parse_result: Dict[str, Any]) -> EditResult:
        """Apply the edit based on its type."""
        start_time = time.time()

        try:
            if edit_command.edit_type == "layout":
                return self._apply_layout_edit(edit_command)
            elif edit_command.edit_type == "asset":
                return self._apply_asset_edit(edit_command)
            elif edit_command.edit_type == "replace":
                return self._apply_replace_edit(edit_command)
            elif edit_command.edit_type == "add":
                return self._apply_add_edit(edit_command)
            elif edit_command.edit_type == "delete":
                return self._apply_delete_edit(edit_command)
            else:
                raise ValueError(f"Unknown edit type: {edit_command.edit_type}")

        except Exception as e:
            self.logger.error(f"Error applying edit {edit_command.edit_id}: {e}")
            return EditResult(
                edit_id=edit_command.edit_id,
                status="failed",
                error_message=str(e),
                application_time=time.time() - start_time
            )

    def _apply_layout_edit(self, edit_command: EditCommand) -> EditResult:
        """Apply layout edit using focus object strategy."""
        start_time = time.time()

        if not edit_command.focus_object_id:
            raise ValueError("Layout edit requires focus_object_id")

        session_path = self.workspace.get_session_path(edit_command.session_id)

        # Load current scene state
        objects = self.workspace.load_objects(edit_command.session_id)
        current_constraints = self.workspace.load_constraints(edit_command.session_id)

        # Apply constraint deltas
        updated_constraints = self.constraint_manager.apply_deltas(
            current_constraints,
            edit_command.delta_constraints or [],
            edit_command.removed_constraints or []
        )

        # Save updated constraints
        constraint_version = self.workspace.save_constraints(
            edit_command.session_id, updated_constraints
        )

        # Use focus object strategy: fix all other objects
        fixed_objects = [
            obj["object_id"] for obj in objects["objects"]
            if obj["object_id"] != edit_command.focus_object_id
        ]

        # Solve layout with focus object strategy
        solver = LayoutSolver()
        solution = solver.solve_with_fixed_objects(
            objects, updated_constraints, fixed_objects
        )

        # Save layout solution
        solution_version = self.workspace.save_layout_solution(
            edit_command.session_id, solution
        )

        # Calculate quality impact
        quality_impact = self._calculate_quality_impact(solution)

        return EditResult(
            edit_id=edit_command.edit_id,
            status="applied" if solution.success else "failed",
            affected_objects=[edit_command.focus_object_id],
            layout_regenerated=True,
            application_time=time.time() - start_time,
            quality_impact=quality_impact,
            error_message=solution.error_message if not solution.success else None
        )

    def _apply_asset_edit(self, edit_command: EditCommand) -> EditResult:
        """Apply asset edit (regenerate asset with new properties)."""
        start_time = time.time()

        if not edit_command.focus_object_id:
            raise ValueError("Asset edit requires focus_object_id")

        # Regenerate asset
        asset_result = self.asset_editor.regenerate_asset(
            edit_command.session_id,
            edit_command.focus_object_id,
            edit_command.user_feedback
        )

        # Update object metadata
        self._update_object_version(edit_command.session_id, edit_command.focus_object_id)

        return EditResult(
            edit_id=edit_command.edit_id,
            status="applied",
            affected_objects=[edit_command.focus_object_id],
            assets_regenerated=[edit_command.focus_object_id],
            application_time=time.time() - start_time,
            quality_impact=asset_result.get("quality_impact", 0.0)
        )

    def _apply_replace_edit(self, edit_command: EditCommand) -> EditResult:
        """Apply asset replacement edit."""
        start_time = time.time()

        if not edit_command.focus_object_id:
            raise ValueError("Replace edit requires focus_object_id")

        # Replace asset
        replace_result = self.asset_editor.replace_asset(
            edit_command.session_id,
            edit_command.focus_object_id,
            edit_command.user_feedback
        )

        # Update object version
        self._update_object_version(edit_command.session_id, edit_command.focus_object_id)

        return EditResult(
            edit_id=edit_command.edit_id,
            status="applied",
            affected_objects=[edit_command.focus_object_id],
            assets_regenerated=[edit_command.focus_object_id],
            application_time=time.time() - start_time,
            quality_impact=replace_result.get("quality_impact", 0.0)
        )

    def _apply_add_edit(self, edit_command: EditCommand) -> EditResult:
        """Apply add object edit."""
        start_time = time.time()

        # Parse object specification from feedback
        new_object = self.feedback_parser.parse_object_specification(
            edit_command.user_feedback
        )

        # Add object to scene
        add_result = self.asset_editor.add_object(
            edit_command.session_id, new_object
        )

        # Update scene objects
        objects = self.workspace.load_objects(edit_command.session_id)
        objects["objects"].append(new_object)
        self.workspace.save_objects(edit_command.session_id, objects)

        return EditResult(
            edit_id=edit_command.edit_id,
            status="applied",
            affected_objects=[new_object["object_id"]],
            assets_regenerated=[new_object["object_id"]],
            application_time=time.time() - start_time,
            quality_impact=0.1  # Adding objects generally improves scene
        )

    def _apply_delete_edit(self, edit_command: EditCommand) -> EditResult:
        """Apply delete object edit."""
        start_time = time.time()

        if not edit_command.focus_object_id:
            raise ValueError("Delete edit requires focus_object_id")

        # Delete object
        delete_result = self.asset_editor.delete_object(
            edit_command.session_id,
            edit_command.focus_object_id
        )

        # Remove object from scene
        objects = self.workspace.load_objects(edit_command.session_id)
        objects["objects"] = [
            obj for obj in objects["objects"]
            if obj["object_id"] != edit_command.focus_object_id
        ]
        self.workspace.save_objects(edit_command.session_id, objects)

        # Remove related constraints
        constraints = self.workspace.load_constraints(edit_command.session_id)
        filtered_constraints = self.constraint_manager.remove_object_constraints(
            constraints, edit_command.focus_object_id
        )
        self.workspace.save_constraints(edit_command.session_id, filtered_constraints)

        return EditResult(
            edit_id=edit_command.edit_id,
            status="applied",
            affected_objects=[edit_command.focus_object_id],
            application_time=time.time() - start_time,
            quality_impact=-0.05  # Removing objects may reduce scene richness
        )

    def _save_edit_history(self, session_id: str, edit_command: EditCommand,
                          edit_result: EditResult) -> None:
        """Save edit history to workspace."""
        session_path = self.workspace.get_session_path(session_id)
        history_path = session_path / "edit_history.json"

        # Load existing history or create new
        if history_path.exists():
            with open(history_path, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            history = EditHistory(**history_data)
        else:
            history = EditHistory(
                session_id=session_id,
                edits=[],
                results=[],
                total_edits=0
            )

        # Add new edit and result
        history.edits.append(edit_command)
        history.results.append(edit_result)

        # Save updated history
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history.model_dump(), f, indent=2, default=str)

    def _update_object_version(self, session_id: str, object_id: str) -> None:
        """Update object version number."""
        objects = self.workspace.load_objects(session_id)

        for obj in objects["objects"]:
            if obj["object_id"] == object_id:
                obj["version"] = obj.get("version", 0) + 1
                break

        self.workspace.save_objects(session_id, objects)

    def _calculate_quality_impact(self, solution: LayoutSolution) -> float:
        """Calculate quality impact of layout solution."""
        if not solution.success:
            return -0.2  # Failed solution reduces quality

        # Calculate based on solution metrics
        constraint_satisfaction = solution.metrics.get("constraint_satisfaction", 0.0)
        spatial_efficiency = solution.metrics.get("spatial_efficiency", 0.0)

        # Normalize to -1 to 1 range
        impact = (constraint_satisfaction + spatial_efficiency) / 2.0 - 0.5
        return max(-1.0, min(1.0, impact))

    def get_edit_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of all edits for a session."""
        session_path = self.workspace.get_session_path(session_id)
        history_path = session_path / "edit_history.json"

        if not history_path.exists():
            return {"session_id": session_id, "edit_count": 0}

        with open(history_path, 'r', encoding='utf-8') as f:
            history_data = json.load(f)

        history = EditHistory(**history_data)

        # Generate human-readable summary
        summary_text = self._generate_summary_text(history)

        return {
            "session_id": session_id,
            "edit_count": len(history.edits),
            "successful_edits": history.successful_edits,
            "failed_edits": history.failed_edits,
            "summary_text": summary_text,
            "quality_progression": self._calculate_quality_progression(history),
            "recommendations": self._generate_recommendations(history)
        }

    def _generate_summary_text(self, history: EditHistory) -> str:
        """Generate human-readable summary of edits."""
        if not history.edits:
            return "No edits have been made to this scene."

        summaries = []
        for edit in history.edits:
            if edit.edit_type == "layout":
                summaries.append(f"Moved {edit.focus_object_id}")
            elif edit.edit_type == "asset":
                summaries.append(f"Updated {edit.focus_object_id} appearance")
            elif edit.edit_type == "add":
                summaries.append(f"Added new object")
            elif edit.edit_type == "delete":
                summaries.append(f"Removed {edit.focus_object_id}")

        return"; ".join(summaries)

    def _calculate_quality_progression(self, history: EditHistory) -> List[float]:
        """Calculate quality progression over edits."""
        progression = [0.8]  # Start with baseline quality

        for result in history.results:
            if result.quality_impact is not None:
                next_quality = progression[-1] + result.quality_impact * 0.1
                progression.append(max(0.0, min(1.0, next_quality)))
            else:
                progression.append(progression[-1])

        return progression

    def _generate_recommendations(self, history: EditHistory) -> List[str]:
        """Generate recommendations for further improvements."""
        recommendations = []

        # Analyze edit patterns
        edit_types = [edit.edit_type for edit in history.edits]

        if edit_types.count("layout") > 3:
            recommendations.append("Consider reviewing the overall scene layout")

        if history.failed_edits > 0:
            recommendations.append("Some edits failed - review constraints for conflicts")

        if len(set(edit.focus_object_id for edit in history.edits if edit.focus_object_id)) < 2:
            recommendations.append("Try editing different objects for variety")

        return recommendations