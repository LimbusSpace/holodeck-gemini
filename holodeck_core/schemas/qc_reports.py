"""Quality Control report schemas for Scene Analysis module.

Based on HOLODECK 2.0 Supplementary Material 6.2.5 - Quality Control.
"""

from typing import List, Optional, Literal
from datetime import datetime, timezone
from pydantic import BaseModel, Field, model_validator, ConfigDict


class QCRecommendation(BaseModel):
    """Single QC recommendation for an object card."""
    object_id: str = Field(..., description="Object identifier")
    object_name: str = Field(..., description="Object name for reference")
    action: Literal["keep", "remove", "regenerate"] = Field(..., description="Recommended action")
    reason: str = Field(..., min_length=5, description="Reason for this recommendation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this recommendation")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "reference": "HOLODECK 2.0 Supp 6.2.5 - Remove Redundant Images",
            "examples": [
                {
                    "object_id": "faucet1",
                    "object_name": "Faucet",
                    "action": "remove",
                    "reason": "Already included in bathtub image",
                    "confidence": 0.9
                }
            ]
        }
    )


class QCReport(BaseModel):
    """Complete QC report for a batch of object cards.

    Tracks the quality control process across multiple rounds.
    """
    qc_round: int = Field(..., ge=1, description="QC round number (starts at 1)")
    scene_session_id: str = Field(..., description="Associated scene session ID")
    batch_id: Optional[str] = Field(None, description="Associated object card batch ID")

    # Object status tracking
    total_objects: int = Field(..., ge=1, description="Total number of objects evaluated")
    approved_objects: List[str] = Field(..., description="List of approved object IDs")
    rejected_objects: List[str] = Field(default_factory=list, description="List of rejected object IDs")
    redundant_removed: List[str] = Field(default_factory=list, description="Objects identified as redundant")

    # QC recommendations
    recommendations: List[QCRecommendation] = Field(..., description="All QC recommendations")

    # Process metadata
    prompt_used: str = Field(..., description="Exact prompt used for QC evaluation")
    evaluation_time: float = Field(..., ge=0.0, description="Time spent on evaluation (seconds)")
    success_rate: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of objects passing QC")

    # Summary fields
    summary: str = Field(..., description="Natural language summary of QC results")
    requires_regenerate: bool = Field(default=False, description="Whether any objects need regeneration")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="QC timestamp")

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "qc_round": 1,
                    "scene_session_id": "2026-01-12T12-30-05Z_abc123",
                    "total_objects": 6,
                    "approved_objects": ["bed1", "nightstand1", "lamp1", "dresser1"],
                    "redundant_removed": ["faucet1"],
                    "success_rate": 0.83,
                    "summary": "Identified 1 redundant object (faucet already in bathtub)",
                    "requires_regenerate": False
                }
            ]
        }
    )

    @model_validator(mode='after')
    def validate_report_consistency(self):
        """Ensure report metrics are consistent."""
        approved_count = len(self.approved_objects) + len(self.redundant_removed)
        rejected_count = len(self.rejected_objects)

        # Calculate expected success rate
        expected_rate = approved_count / self.total_objects
        if abs(expected_rate - self.success_rate) > 0.001:
            self.success_rate = expected_rate

        # Check if any rejected objects need regeneration
        if self.rejected_objects:
            self.requires_regenerate = True

        return self


class QCHistory(BaseModel):
    """Complete QC history for a scene, tracking multiple rounds."""
    scene_session_id: str = Field(..., description="Associated scene session ID")
    reports: List[QCReport] = Field(..., min_length=1, description="All QC reports in order")

    # Summary metrics
    total_rounds: int = Field(..., ge=1, description="Number of QC rounds completed")
    final_approval_count: int = Field(0, description="Number of objects finally approved")
    final_rejection_count: int = Field(0, description="Number of objects finally rejected")

    # Process summary
    total_evaluation_time: float = Field(0.0, ge=0.0, description="Total time spent on all QC rounds")
    is_complete: bool = Field(False, description="Whether QC process is complete (no rejections)")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")

    model_config = ConfigDict(
        validate_assignment=True,
        json_schema_extra={
            "examples": [
                {
                    "scene_session_id": "2026-01-12T12-30-05Z_abc123",
                    "total_rounds": 1,
                    "final_approval_count": 5,
                    "final_rejection_count": 1,
                    "is_complete": False
                }
            ]
        }
    )

    @model_validator(mode='after')
    def calculate_metrics(self):
        """Calculate summary metrics from reports."""
        if not self.reports:
            return self

        self.total_rounds = len(self.reports)

        # Get final object sets from the last report
        last_report = self.reports[-1]
        self.final_approval_count = len(last_report.approved_objects)
        self.final_rejection_count = len(last_report.rejected_objects)

        # Sum evaluation times
        self.total_evaluation_time = sum(r.evaluation_time for r in self.reports)

        # Check completion status
        self.is_complete = (
            self.final_rejection_count == 0 and
            not last_report.requires_regenerate
        )

        if self.is_complete:
            self.completed_at = datetime.now(timezone.utc)

        return self