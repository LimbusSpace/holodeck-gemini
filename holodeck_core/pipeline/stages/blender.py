# -*- coding: utf-8 -*-
"""Stage 7: Blender Import - Auto-import assets into Blender via MCP."""

import logging
from ..base_stage import BaseStage
from ..stage_data import StageData

logger = logging.getLogger(__name__)


class BlenderStage(BaseStage):
    """Import 3D assets into Blender via MCP."""

    name = "blender"

    async def execute(self, data: StageData) -> StageData:
        from ...blender.mcp_bridge import BlenderMCPBridge

        logger.info(f"Importing assets to Blender for session {data.session_id}")

        bridge = BlenderMCPBridge()
        result = bridge.apply_layout(str(data.session_dir))

        if result.get("success"):
            logger.info(f"Blender import successful: {result.get('blend_path')}")
        else:
            logger.warning(f"Blender import failed: {result.get('error')}")

        data.blender_result = result
        return data
