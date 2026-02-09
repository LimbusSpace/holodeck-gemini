# -*- coding: utf-8 -*-
"""Unified data format for Pipeline stages."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class StageData:
    """Unified data container passed between Pipeline stages."""

    session_id: str
    session_dir: Path

    # Stage 1: Scene Reference
    scene_text: str = ""
    style: str = "modern"
    scene_ref_path: Optional[Path] = None

    # Stage 2: Objects
    scene_style: str = ""
    objects: List[Dict[str, Any]] = field(default_factory=list)

    # Stage 3: Cards
    cards: List[Dict[str, Any]] = field(default_factory=list)

    # Stage 4: Constraints
    constraints: Dict[str, Any] = field(default_factory=dict)

    # Stage 5: Layout
    layout: Dict[str, Any] = field(default_factory=dict)

    # Stage 6: Assets
    assets: List[Dict[str, Any]] = field(default_factory=list)

    # Stage 7: Blender
    blender_result: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    def add_error(self, stage: str, msg: str):
        self.errors.append(f"[{stage}] {msg}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_dir": str(self.session_dir),
            "scene_text": self.scene_text,
            "style": self.style,
            "scene_ref_path": str(self.scene_ref_path) if self.scene_ref_path else None,
            "scene_style": self.scene_style,
            "objects": self.objects,
            "cards": self.cards,
            "constraints": self.constraints,
            "layout": self.layout,
            "assets": self.assets,
            "blender_result": self.blender_result,
            "errors": self.errors,
            "metrics": self.metrics,
        }
