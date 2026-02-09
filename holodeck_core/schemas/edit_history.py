"""Edit history schemas for the Scene Editing module.

Tracks user feedback and edit operations for scene refinement.
"""

from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from .constraints import SpatialConstraint


class EditCommand(BaseModel):
    """Single edit command representing user requested changes."""
    edit_id: str = Field(..., description="Unique edit identifier")
    session_id: str = Field(..., description="Associated scene session ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Edit timestamp")

    # User input
    user_feedback: str = Field(..., min_length=5, description="Original user feedback text")
    interpreted_intent: str = Field(..., description="AI-interpreted intent of the feedback")

    # Focus and type
    focus_object_id: Optional[str] = Field(None, description="Object being edited, if applicable")
    edit_type: Literal["layout", "asset", "add", "delete", "replace"] = Field(..., description="Type of edit operation")

    # Changes applied
    delta_constraints: Optional[List[SpatialConstraint]] = Field(None, description="New or modified constraints")
    removed_constraints: Optional[List[str]] = Field(None, description="IDs of constraints to remove")
    assets_to_regenerate: Optional[List[str]] = Field(None, description="Object IDs needing asset regeneration")

    # Edit metadata
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="AI confidence in interpretation")
    processing_time: float = Field(0.0, ge=0.0, description="Time to process edit (seconds)")
    requires_user_approval: bool = Field(False, description="Whether this edit requires explicit approval")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "reference": "HOLODECK 2.0 Section 3.4 - Scene Editing",
            "examples": [
                {
                    "edit_id": "edit_20260112_143022",
                    "session_id": "2026-01-12T12-30-05Z_abc123",
                    "user_feedback": "Move the lamp to the left side of the bed",
                    "interpreted_intent": "Reposition lamp object to be left of bed",
                    "focus_object_id": "lamp1",
                    "edit_type": "layout",
                    "confidence_score": 0.92,
                    "processing_time": 1.2
                }
            ]
        }
    )

    @field_validator('focus_object_id')
    @classmethod
    def validate_focus_object_for_edit_type(cls, v, info):
        """Ensure focus object is present for relevant edit types."""
        edit_type = info.data.get('edit_type')
        if edit_type in ['layout', 'asset', 'delete', 'replace'] and not v:
            raise ValueError(f"focus_object_id is required for edit_type '{edit_type}'")
        return v

    @field_validator('assets_to_regenerate')
    @classmethod
    def validate_asset_regeneration(cls, v, info):
        """Ensure asset regeneration matches focus object for asset edits."""
        edit_type = info.data.get('edit_type')
        focus_object = info.data.get('focus_object_id')

        if edit_type == 'asset' and (not v or focus_object not in v):
            raise ValueError("Asset edit must include focus_object in assets_to_regenerate")
        return v


class EditResult(BaseModel):
    """Result of applying an edit command."""
    edit_id: str = Field(..., description="Corresponding edit command ID")
    status: Literal["applied", "failed", "pending_approval"] = Field(..., description="Edit result status")

    # Success details
    affected_objects: List[str] = Field(default_factory=list, description="Objects that were modified")
    layout_regenerated: bool = Field(False, description="Whether layout was regenerated")
    assets_regenerated: List[str] = Field(default_factory=list, description="IDs of regenerated assets")

    # Failure details
    error_message: Optional[str] = Field(None, description="Error description if failed")
    partial_success: bool = Field(False, description="Whether edit partially succeeded")

    # Performance
    application_time: float = Field(0.0, ge=0.0, description="Time to apply edit (seconds)")

    # Quality metrics
    quality_impact: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Impact on scene quality (-1 to 1)")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Result timestamp")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "edit_id": "edit_20260112_143022",
                    "status": "applied",
                    "affected_objects": ["lamp1"],
                    "layout_regenerated": True,
                    "application_time": 2.5,
                    "quality_impact": 0.1
                }
            ]
        }
    )


class EditHistory(BaseModel):
    """Complete edit history for a scene session."""
    session_id: str = Field(..., description="Scene session ID")
    edits: List[EditCommand] = Field(..., description="All edit commands made")
    results: List[EditResult] = Field(..., description="Results of applied edits")

    # Summary metrics
    current_version: int = Field(0, description="Current version number after all edits")
    total_edits: int = Field(..., ge=0, description="Total number of edit attempts")
    successful_edits: int = Field(0, ge=0, description="Number of successful edits")
    failed_edits: int = Field(0, ge=0, description="Number of failed edits")

    # Edit type breakdown
    edit_type_counts: Dict[str, int] = Field(default_factory=dict, description="Count by edit type")

    # Final state
    current_constraints: List[SpatialConstraint] = Field(default_factory=list, description="Current constraint set")
    object_versions: Dict[str, int] = Field(default_factory=dict, description="Version number per object")

    # Workflow
    pending_approval: List[str] = Field(default_factory=list, description="Edit IDs awaiting user approval")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="History creation timestamp")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "session_id": "2026-01-12T12-30-05Z_abc123",
                    "current_version": 3,
                    "total_edits": 3,
                    "successful_edits": 2,
                    "edit_type_counts": {"layout": 2, "asset": 1}
                }
            ]
        }
    )

    @model_validator(mode='after')
    def calculate_metrics(self):
        """Calculate summary metrics from edits and results."""
        self.total_edits = len(self.edits)
        self.successful_edits = sum(
            1 for result in self.results
            if result.status == "applied"
        )
        self.failed_edits = sum(
            1 for result in self.results
            if result.status == "failed"
        )

        # Update version based on successful edits
        self.current_version = self.successful_edits

        # Count edit types
        self.edit_type_counts = {}
        for edit in self.edits:
            self.edit_type_counts[edit.edit_type] = self.edit_type_counts.get(edit.edit_type, 0) + 1

        # Update pending approval list
        self.pending_approval = [
            edit.edit_id for edit in self.edits
            if edit.requires_user_approval
        ]

        self.last_updated = datetime.now(timezone.utc)

        return self

    @model_validator(mode='after')
    def validate_result_consistency(self):
        """Ensure results match their edit commands."""
        edit_ids = {edit.edit_id for edit in self.edits}
        result_ids = {result.edit_id for result in self.results}

        missing_results = edit_ids - result_ids
        orphaned_results = result_ids - edit_ids

        if missing_results:
            raise ValueError(f"Edit commands missing results: {missing_results}")
        if orphaned_results:
            raise ValueError(f"Results without corresponding edits: {orphaned_results}")

        return self


class EditSummary(BaseModel):
    """Summary of all edits for user review."""
    session_id: str = Field(..., description="Scene session ID")
    summary_text: str = Field(..., description="Human-readable summary of all changes")
    edit_count: int = Field(..., description="Total number of edits made")
    quality_progression: Optional[List[float]] = Field(None, description="Quality progression over edits")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for further improvements")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {
                    "session_id": "2026-01-12T12-30-05Z_abc123",
                    "summary_text": "Moved lamp to left side of bed, replaced nightstand with modern version",
                    "edit_count": 2,
                    "quality_progression": [0.85, 0.88, 0.91]
                }
            ]
        }
    )