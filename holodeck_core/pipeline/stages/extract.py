# -*- coding: utf-8 -*-
"""Stage 2: Object Extraction."""

import json
from ..base_stage import BaseStage
from ..stage_data import StageData


class ExtractStage(BaseStage):
    """Extract objects from scene description."""

    name = "extract"

    def __init__(self, analysis_client):
        self.client = analysis_client

    async def execute(self, data: StageData) -> StageData:
        result = await self.client.extract_objects(
            session_id=data.session_id,
            scene_text=data.scene_text,
            ref_image_path=str(data.scene_ref_path) if data.scene_ref_path else None
        )

        data.scene_style = result.scene_style
        data.objects = [
            {
                "object_id": obj.object_id,
                "name": obj.name,
                "category": obj.category or "furniture",
                "size_m": [obj.size.x, obj.size.y, obj.size.z],
                "initial_pose": {
                    "pos": [obj.position.x, obj.position.y, obj.position.z],
                    "rot_euler": [obj.rotation.x, obj.rotation.y, obj.rotation.z]
                },
                "visual_desc": obj.visual_description,
                "must_exist": obj.must_exist
            }
            for obj in result.objects
        ]

        # Save to file
        objects_path = data.session_dir / "objects.json"
        with open(objects_path, 'w', encoding='utf-8') as f:
            json.dump({"scene_style": data.scene_style, "objects": data.objects}, f, indent=2, ensure_ascii=False)

        return data
