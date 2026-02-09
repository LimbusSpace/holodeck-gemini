# -*- coding: utf-8 -*-
"""Base class for Pipeline stages."""

import logging
import time
from abc import ABC, abstractmethod
from typing import Optional

from .stage_data import StageData

logger = logging.getLogger(__name__)


class BaseStage(ABC):
    """Abstract base class for all Pipeline stages."""

    name: str = "base"

    @abstractmethod
    async def execute(self, data: StageData) -> StageData:
        """Execute the stage and return updated StageData."""
        pass

    async def run(self, data: StageData) -> StageData:
        """Run stage with timing and error handling."""
        start = time.time()
        logger.info(f"[{self.name}] Starting...")

        try:
            data = await self.execute(data)
            elapsed = time.time() - start
            data.metrics[f"{self.name}_time"] = elapsed
            logger.info(f"[{self.name}] Completed in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start
            data.metrics[f"{self.name}_time"] = elapsed
            data.add_error(self.name, str(e))
            logger.error(f"[{self.name}] Failed: {e}")
            raise

        return data
