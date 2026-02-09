# pylint: skip-file
"""Test object card schemas."""

import pytest
from datetime import datetime, timezone

from holodeck_core.schemas.object_cards import (
    ObjectCard, SceneRefImage, BackgroundImage, ObjectCardBatch
)


@pytest.mark.unit
class TestObjectCardSchemas:
    """Test object card related schemas."""

    def test_object_card_creation(self):
        """Test ObjectCard creation."""
        card = ObjectCard(
            object_id="bed1",
            object_name="King Bed",
            card_image_path="object_cards/bed1.png",
            prompt_used="Generate isolated front-view King Bed...",
            generation_time=2.3,
            qc_status="approved"
        )
        assert card.object_id == "bed1"
        assert card.qc_status == "approved"
        assert card.rejection_reason is None

    def test_object_card_rejection(self):
        """Test ObjectCard with rejection."""
        card = ObjectCard(
            object_id="faucet1",
            object_name="Faucet",
            card_image_path="object_cards/faucet1.png",
            prompt_used="Generate isolated front-view Faucet...",
            generation_time=1.8,
            qc_status="rejected",
            rejection_reason="Already included in bathtub image"
        )
        assert card.qc_status == "rejected"
        assert card.rejection_reason == "Already included in bathtub image"

    def test_scene_ref_image(self):
        """Test SceneRefImage creation."""
        img = SceneRefImage(
            image_path="scene_ref.png",
            prompt_used="A cozy bedroom with modern style...",
            style="realistic",
            generation_time=3.7
        )
        assert img.image_path == "scene_ref.png"
        assert img.style == "realistic"
        assert isinstance(img.created_at, datetime)

    def test_background_image(self):
        """Test BackgroundImage creation."""
        bg = BackgroundImage(
            image_path="background.png",
            source_reference="scene_ref.png",
            surface_type="floor",
            material_description="Light wood plank with subtle grain",
            generation_time=2.1
        )
        assert bg.tileable is True
        assert bg.surface_type == "floor"

    def test_object_card_batch(self):
        """Test ObjectCardBatch creation."""
        cards = [
            ObjectCard(
                object_id="bed1",
                object_name="King Bed",
                card_image_path="bed1.png",
                prompt_used="Generate bed...",
                generation_time=2.0,
                qc_status="approved"
            ),
            ObjectCard(
                object_id="nightstand1",
                object_name="Nightstand",
                card_image_path="nightstand1.png",
                prompt_used="Generate nightstand...",
                generation_time=1.5,
                qc_status="approved"
            )
        ]

        batch = ObjectCardBatch(
            batch_id="batch_001",
            scene_session_id="session_123",
            total_objects=2,
            successful_cards=cards,
            parallel_workers=2,
            total_time=5.0
        )
        assert len(batch.successful_cards) == 2
        assert batch.successful_cards[0].object_id == "bed1"
        assert isinstance(batch.created_at, datetime)

    def test_batch_integrity_validation(self):
        """Test batch integrity validation."""
        card = ObjectCard(
            object_id="bed1",
            object_name="King Bed",
            card_image_path="bed1.png",
            prompt_used="Generate bed...",
            generation_time=2.0,
            qc_status="approved"
        )

        # Valid batch
        with pytest.raises(ValueError) as exc_info:
            ObjectCardBatch(
                batch_id="batch_001",
                scene_session_id="session_123",
                total_objects=2,
                successful_cards=[card],  # Only 1 success but total=2
                failed_objects=["lamp1"],  # 1 failed
                parallel_workers=1,
                total_time=3.0
            )
        assert "Batch integrity check failed" in str(exc_info.value)

    def test_invalid_object_card(self):
        """Test invalid ObjectCard data."""
        # Negative generation time
        with pytest.raises(ValueError):
            ObjectCard(
                object_id="bed1",
                object_name="Bed",
                card_image_path="bed.png",
                prompt_used="Generate bed...",
                generation_time=-1.0,
                qc_status="pending"
            )