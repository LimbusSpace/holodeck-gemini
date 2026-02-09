# -*- coding: utf-8 -*-
"""Stage 4: Constraint Generation."""

import json
from ..base_stage import BaseStage
from ..stage_data import StageData


class ConstraintsStage(BaseStage):
    """Generate spatial constraints."""

    name = "constraints"

    def __init__(self, constraint_generator):
        self.generator = constraint_generator

    async def execute(self, data: StageData) -> StageData:
        # Use VLM-based constraint generation
        ref_image_path = str(data.scene_ref_path) if data.scene_ref_path else None

        constraints_dict = await self.generator.generate_constraints_with_vlm(
            scene_description=data.scene_text,
            objects=data.objects,
            ref_image_path=ref_image_path
        )

        data.constraints = constraints_dict

        # Save to file
        constraints_path = data.session_dir / "constraints.json"
        with open(constraints_path, 'w', encoding='utf-8') as f:
            json.dump(constraints_dict, f, indent=2, ensure_ascii=False)

        return data
