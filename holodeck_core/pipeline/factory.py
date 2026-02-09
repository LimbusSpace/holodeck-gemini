# -*- coding: utf-8 -*-
"""Pipeline factory - creates configured Pipeline for holodeck-build."""

import asyncio
from pathlib import Path
from typing import Optional

from holodeck_core.pipeline import PipelineRunner, StageData
from holodeck_core.pipeline.stages import (
    SceneRefStage,
    ExtractStage,
    CardsStage,
    ConstraintsStage,
    LayoutStage,
    AssetsStage,
    BlenderStage,
)


def create_pipeline(workspace: str = "workspace", until: Optional[str] = None, from_stage: Optional[str] = None) -> PipelineRunner:
    """Create a configured Pipeline with all stages.

    Args:
        workspace: Workspace directory path
        until: Stop after this stage (scene_ref, extract, cards, constraints, layout, assets)
        from_stage: Start from this stage (default: scene_ref)
    """
    # Import clients lazily to avoid circular imports
    from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer
    from holodeck_core.scene_gen.layout_solver import LayoutSolver
    from holodeck_core.scene_gen.constraint_generator import ConstraintGenerator
    from holodeck_core.object_gen.asset_generator import AssetGenerator

    # Initialize clients
    analyzer = SceneAnalyzer(api_key=None, use_comfyui=True)
    analyzer._get_client()  # Force client initialization

    solver = LayoutSolver()
    constraint_gen = ConstraintGenerator()
    asset_gen = AssetGenerator()

    # Build pipeline
    runner = PipelineRunner(workspace=workspace)

    stages = [
        ("scene_ref", SceneRefStage(analyzer.hybrid_client)),
        ("extract", ExtractStage(analyzer.hybrid_client)),
        ("cards", CardsStage(analyzer.hybrid_client)),
        ("constraints", ConstraintsStage(constraint_gen)),
        ("layout", LayoutStage(solver)),
        ("assets", AssetsStage(asset_gen)),
        ("blender", BlenderStage()),
    ]

    # Validate parameters
    valid_stages = [name for name, _ in stages]
    if until and until not in valid_stages:
        raise ValueError(f"Invalid --until stage: '{until}'. Valid stages: {valid_stages}")
    if from_stage and from_stage not in valid_stages:
        raise ValueError(f"Invalid --from stage: '{from_stage}'. Valid stages: {valid_stages}")
    if from_stage and until:
        if valid_stages.index(from_stage) > valid_stages.index(until):
            raise ValueError(f"from_stage '{from_stage}' must be before or equal to until '{until}'")

    # from_stage 为 None 或 "scene_ref" 都表示从头开始
    adding = (from_stage is None or from_stage == "scene_ref")
    for name, stage in stages:
        if from_stage and from_stage != "scene_ref" and name == from_stage:
            adding = True
        if adding:
            runner.add_stage(stage)
        if until and name == until:
            break

    return runner


async def run_pipeline(
    text: str,
    style: str = "modern",
    workspace: str = "workspace",
    until: Optional[str] = None,
    from_stage: Optional[str] = None,
    session_id: Optional[str] = None
) -> StageData:
    """Run the complete pipeline.

    Args:
        text: Scene description
        style: Scene style
        workspace: Workspace directory
        until: Stop after this stage
        from_stage: Start from this stage
        session_id: Optional session ID

    Returns:
        StageData with all results
    """
    runner = create_pipeline(workspace=workspace, until=until, from_stage=from_stage)
    return await runner.run(scene_text=text, style=style, session_id=session_id)


def run_pipeline_sync(
    text: str,
    style: str = "modern",
    workspace: str = "workspace",
    until: Optional[str] = None,
    from_stage: Optional[str] = None,
    session_id: Optional[str] = None
) -> StageData:
    """Synchronous wrapper for run_pipeline."""
    return asyncio.run(run_pipeline(text, style, workspace, until, from_stage, session_id))
