# pylint: skip-file
"""Test QC report schemas."""

import pytest
from datetime import datetime, timezone

from holodeck_core.schemas.qc_reports import (
    QCRecommendation, QCReport, QCHistory
)


@pytest.mark.unit
class TestQCReportSchemas:
    """Test QC report related schemas."""

    def test_qc_recommendation(self):
        """Test QCRecommendation creation."""
        rec = QCRecommendation(
            object_id="faucet1",
            object_name="Faucet",
            action="remove",
            reason="Already included in bathtub image",
            confidence=0.9
        )
        assert rec.object_id == "faucet1"
        assert rec.action == "remove"
        assert rec.confidence == 0.9

    def test_invalid_confidence(self):
        """Test invalid confidence score."""
        with pytest.raises(ValueError):
            QCRecommendation(
                object_id="faucet1",
                object_name="Faucet",
                action="remove",
                reason="Already included",
                confidence=1.5  # Invalid > 1.0
            )

    def test_qc_report(self):
        """Test QCReport creation."""
        recommendations = [
            QCRecommendation(
                object_id="faucet1",
                object_name="Faucet",
                action="remove",
                reason="Already included in bathtub",
                confidence=0.9
            ),
            QCRecommendation(
                object_id="lamp1",
                object_name="Lamp",
                action="keep",
                reason="Clear and isolated object",
                confidence=0.95
            )
        ]

        report = QCReport(
            qc_round=1,
            scene_session_id="session_123",
            total_objects=3,
            approved_objects=["bed1", "lamp1"],
            redundant_removed=["faucet1"],
            recommendations=recommendations,
            prompt_used="Identify redundant sub-components...",
            evaluation_time=5.2,
            summary="Identified 1 redundant object (faucet)"
        )
        assert report.qc_round == 1
        assert report.success_rate == 0.67  # 2/3 objects approved
        assert report.requires_regenerate is False

    def test_qc_report_with_rejections(self):
        """Test QCReport with rejected objects."""
        recommendations = [
            QCRecommendation(
                object_id="chair1",
                object_name="Chair",
                action="regenerate",
                reason="Image is blurry",
                confidence=0.85
            )
        ]

        report = QCReport(
            qc_round=1,
            scene_session_id="session_123",
            total_objects=2,
            approved_objects=["bed1"],
            rejected_objects=["chair1"],
            recommendations=recommendations,
            prompt_used="Check image quality...",
            evaluation_time=3.1,
            summary="1 object needs regeneration"
        )
        assert report.qc_round == 1
        assert report.success_rate == 0.5  # 1/2 objects approved
        assert report.requires_regenerate is True

    def test_qc_history(self):
        """Test QCHistory creation."""
        report = QCReport(
            qc_round=1,
            scene_session_id="session_123",
            total_objects=2,
            approved_objects=["bed1"],
            rejected_objects=["chair1"],
            recommendations=[
                QCRecommendation(
                    object_id="chair1",
                    object_name="Chair",
                    action="regenerate",
                    reason="Blurry image",
                    confidence=0.85
                )
            ],
            prompt_used="Check quality...",
            evaluation_time=3.0,
            summary="Regenerate chair"
        )

        history = QCHistory(
            scene_session_id="session_123",
            reports=[report]
        )
        assert history.scene_session_id == "session_123"
        assert history.total_rounds == 1
        assert history.final_approval_count == 1
        assert history.final_rejection_count == 1
        assert history.is_complete is False
        assert isinstance(history.created_at, datetime)

    def test_qc_history_complete(self):
        """Test QCHistory with all objects approved."""
        report = QCReport(
            qc_round=1,
            scene_session_id="session_123",
            total_objects=2,
            approved_objects=["bed1", "chair1"],
            recommendations=[
                QCRecommendation(
                    object_id="bed1",
                    object_name="Bed",
                    action="keep",
                    reason="Clear image",
                    confidence=0.95
                ),
                QCRecommendation(
                    object_id="chair1",
                    object_name="Chair",
                    action="keep",
                    reason="Clear image",
                    confidence=0.9
                )
            ],
            prompt_used="Final QC check...",
            evaluation_time=2.5,
            summary="All objects approved"
        )

        history = QCHistory(
            scene_session_id="session_123",
            reports=[report]
        )
        assert history.is_complete is True
        assert history.final_approval_count == 2
        assert history.final_rejection_count == 0
        assert history.completed_at is not None