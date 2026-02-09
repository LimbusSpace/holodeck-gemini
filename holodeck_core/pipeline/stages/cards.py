# -*- coding: utf-8 -*-
"""Stage 3: Object Card Generation."""

from ..base_stage import BaseStage
from ..stage_data import StageData


class CardsStage(BaseStage):
    """Generate object card images."""

    name = "cards"

    def __init__(self, image_client):
        self.client = image_client

    async def execute(self, data: StageData) -> StageData:
        cards_dir = data.session_dir / "object_cards"
        cards_dir.mkdir(exist_ok=True)

        cards = await self.client.generate_object_cards(
            session_id=data.session_id,
            objects=data.objects,
            ref_image_path=str(data.scene_ref_path) if data.scene_ref_path else ""
        )

        data.cards = [
            {
                "object_id": card.object_id,
                "card_path": str(card.card_image_path),
                "prompt": card.prompt_used
            }
            for card in cards
        ]

        return data
