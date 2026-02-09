# -*- coding: utf-8 -*-
"""Stage 1: Scene Reference Image Generation."""

import shutil
from pathlib import Path
from ..base_stage import BaseStage
from ..stage_data import StageData


class SceneRefStage(BaseStage):
    """Generate scene reference image using APIYI."""

    name = "scene_ref"

    def __init__(self, image_client):
        self.client = image_client

    async def execute(self, data: StageData) -> StageData:
        output_path = data.session_dir / "scene_ref.png"

        result = await self.client.generate_scene_reference(
            session_id=data.session_id,
            scene_text=data.scene_text,
            style=data.style
        )

        # Copy image to session directory if saved elsewhere
        src_path = Path(result.image_path) if hasattr(result, 'image_path') else None
        if src_path and src_path.exists() and src_path != output_path:
            shutil.copy2(src_path, output_path)
            data.scene_ref_path = output_path
        else:
            data.scene_ref_path = src_path or output_path

        return data
