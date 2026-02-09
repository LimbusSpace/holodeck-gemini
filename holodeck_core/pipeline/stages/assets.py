# -*- coding: utf-8 -*-
"""Stage 6: 3D Asset Generation."""

import logging
from pathlib import Path
from ..base_stage import BaseStage
from ..stage_data import StageData
from ...config.base import get_config
from ...asset_retrieval import AssetDecisionEngine, AssetRetriever

logger = logging.getLogger(__name__)


class AssetsStage(BaseStage):
    """Generate 3D assets from object cards."""

    name = "assets"

    def __init__(self, asset_generator):
        self.generator = asset_generator
        self.decision_engine = AssetDecisionEngine()
        self.retriever = AssetRetriever()

    async def execute(self, data: StageData) -> StageData:
        assets_dir = data.session_dir / "assets"
        assets_dir.mkdir(exist_ok=True)

        # Create mock session for AssetGenerator
        class MockSession:
            def __init__(self, session_id, session_dir, cards_dir):
                self.session_id = session_id
                self.session_dir = session_dir
                self.cards_dir = cards_dir

            def get_object_cards_dir(self):
                return self.cards_dir

            def get_assets_dir(self):
                return self.session_dir / "assets"

        session = MockSession(data.session_id, data.session_dir, data.session_dir / "object_cards")

        # Check if asset retrieval is enabled
        retrieval_enabled = get_config("ASSET_RETRIEVAL_ENABLED", False, bool)
        threshold = get_config("ASSET_RETRIEVAL_THRESHOLD", 0.5, float)

        assets = []
        for card in data.cards:
            object_id = card["object_id"]
            visual_desc = card.get("visual_description", "")

            try:
                # Try retrieval path if enabled
                if retrieval_enabled and visual_desc:
                    score = self.decision_engine.evaluate(visual_desc)
                    if score < threshold:
                        retrieved = self.retriever.search(visual_desc)
                        if retrieved:
                            assets.append({
                                "object_id": object_id,
                                "glb_path": retrieved["path"],
                                "source": retrieved["source"],
                                "status": "success"
                            })
                            logger.info(f"Retrieved asset for {object_id} (score={score:.2f})")
                            continue

                # Fall through to generation
                result = self.generator.generate_from_card(session, object_id)
                if result:
                    assets.append({
                        "object_id": object_id,
                        "glb_path": str(result),
                        "source": "generated",
                        "status": "success"
                    })
                else:
                    assets.append({"object_id": object_id, "status": "failed"})
            except Exception as e:
                assets.append({"object_id": object_id, "status": "failed", "error": str(e)})

        data.assets = assets
        return data
