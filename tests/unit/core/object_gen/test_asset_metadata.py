# pylint: skip-file
"""Test asset metadata schemas."""

import pytest
from datetime import datetime, timezone

from holodeck_core.schemas.asset_metadata import (
    AssetMetadata, AssetBatch, AssetNormalizationConfig
)
from holodeck_core.schemas.scene_objects import Vec3


@pytest.mark.unit
class TestAssetMetadataSchemas:
    """Test asset metadata related schemas."""

    def test_asset_metadata_successful(self):
        """Test AssetMetadata with successful generation."""
        asset = AssetMetadata(
            object_id="bed1",
            object_name="King Bed",
            source_card_path="object_cards/bed1.png",
            glb_path="assets/bed1.glb",
            file_size_mb=12.4,
            original_size=Vec3(x=2.1, y=1.9, z=1.1),
            normalized_size=Vec3(x=2.0, y=1.5, z=0.6),
            scaling_factor=0.9523809523809523,
            generation_time=45.2,
            generation_status="success",
            quality_score=0.87,
            vertex_count=8542
        )
        assert asset.object_id == "bed1"
        assert asset.generation_status == "success"
        assert asset.quality_score == 0.87
        assert isinstance(asset.timestamp, datetime)

    def test_asset_metadata_failed(self):
        """Test AssetMetadata with failed generation."""
        asset = AssetMetadata(
            object_id="chair1",
            object_name="Chair",
            source_card_path="object_cards/chair1.png",
            glb_path="",
            file_size_mb=0.0,
            original_size=Vec3(x=0.0, y=0.0, z=0.0),
            normalized_size=Vec3(x=0.0, y=0.0, z=0.0),
            scaling_factor=0.0,
            generation_time=120.0,
            generation_status="failed",
            failure_reason="Generation timeout after 2 minutes"
        )
        assert asset.generation_status == "failed"
        assert asset.failure_reason == "Generation timeout after 2 minutes"
        assert asset.quality_score is None
        assert asset.vertex_count is None

    def test_asset_scaling_validation(self):
        """Test scaling factor consistency validation."""
        with pytest.raises(ValueError) as exc_info:
            AssetMetadata(
                object_id="bed1",
                object_name="Bed",
                source_card_path="bed1.png",
                glb_path="bed1.glb",
                file_size_mb=10.0,
                original_size=Vec3(x=2.0, y=2.0, z=2.0),
                normalized_size=Vec3(x=2.0, y=2.0, z=2.0),
                scaling_factor=0.5,  # Should be 1.0 but set to 0.5
                generation_time=30.0,
                generation_status="success"
            )
        assert "Scaling factor mismatch for x" in str(exc_info.value)

    def test_asset_batch(self):
        """Test AssetBatch creation."""
        successful_assets = [
            AssetMetadata(
                object_id="bed1",
                object_name="King Bed",
                source_card_path="bed1.png",
                glb_path="assets/bed1.glb",
                file_size_mb=12.4,
                original_size=Vec3(x=2.1, y=1.9, z=0.6),
                normalized_size=Vec3(x=2.0, y=1.5, z=0.6),
                scaling_factor=0.714,
                generation_time=45.2,
                generation_status="success"
            ),
            AssetMetadata(
                object_id="nightstand1",
                object_name="Nightstand",
                source_card_path="nightstand1.png",
                glb_path="assets/nightstand1.glb",
                file_size_mb=8.2,
                original_size=Vec3(x=0.5, y=0.4, z=0.5),
                normalized_size=Vec3(x=0.5, y=0.4, z=0.5),
                scaling_factor=1.0,
                generation_time=25.1,
                generation_status="success"
            )
        ]

        failed_assets = [
            {
                "object_id": "lamp1",
                "object_name": "Table Lamp",
                "failure_reason": "Model generation failed"
            }
        ]

        batch = AssetBatch(
            batch_id="batch_001",
            scene_session_id="session_123",
            total_assets=3,
            parallel_workers=2,
            successful_assets=successful_assets,
            failed_assets=failed_assets,
            total_time=120.5
        )
        assert batch.success_count == 2
        assert batch.success_rate == 2/3
        assert batch.total_model_size == 20.6
        assert batch.average_time == (45.2 + 25.1) / 2

    def test_failed_asset_validation(self):
        """Test failed asset structure validation."""
        with pytest.raises(ValueError) as exc_info:
            AssetBatch(
                batch_id="batch_001",
                scene_session_id="session_123",
                total_assets=1,
                parallel_workers=1,
                successful_assets=[],
                failed_assets=[{"object_id": "lamp1"}],  # Missing required fields
                total_time=60.0
            )
        assert "Missing required field" in str(exc_info.value)

    def test_asset_normalization_config(self):
        """Test AssetNormalizationConfig creation."""
        config = AssetNormalizationConfig(
            z_axis_reference=True,
            preserve_proportions=True,
            min_scale_factor=0.1,
            max_scale_factor=5.0
        )
        assert config.z_axis_reference is True
        assert config.min_scale_factor == 0.1
        assert config.max_scale_factor == 5.0