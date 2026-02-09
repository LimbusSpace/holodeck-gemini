# -*- coding: utf-8 -*-
"""Pipeline runner - orchestrates stage execution."""

import logging
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Type

from .stage_data import StageData
from .base_stage import BaseStage

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrates Pipeline stage execution."""

    def __init__(self, workspace: str = "workspace"):
        self.workspace = Path(workspace)
        self.stages: List[BaseStage] = []

    def add_stage(self, stage: BaseStage) -> "PipelineRunner":
        """Add a stage to the pipeline."""
        self.stages.append(stage)
        return self

    async def run(
        self,
        scene_text: str,
        style: str = "modern",
        session_id: Optional[str] = None
    ) -> StageData:
        """Run all stages sequentially."""
        start = time.time()

        # Create session
        session_id = session_id or f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        session_dir = self.workspace / "sessions" / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize data
        data = StageData(
            session_id=session_id,
            session_dir=session_dir,
            scene_text=scene_text,
            style=style
        )

        logger.info(f"Pipeline started: {session_id}")

        # Execute stages
        for stage in self.stages:
            try:
                data = await stage.run(data)
            except Exception as e:
                logger.error(f"Pipeline stopped at {stage.name}: {e}")
                break

        data.metrics["total_time"] = time.time() - start
        logger.info(f"Pipeline finished in {data.metrics['total_time']:.2f}s")

        return data
