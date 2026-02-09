"""Core data schemas for Holodeck-Gemini.

Complete schema coverage for HOLODECK 2.0 pipeline including:
- Session management
- Scene objects and analysis
- Spatial constraints
- Layout solving
- Object cards and QC
- Asset metadata
- Edit history
- Rendering
"""

# Core schemas
from .session import Session, SessionStatus, SessionRequest
from .scene_objects import SceneObject, SceneItem, Vec3, SceneData
from .constraints import (
    SpatialConstraint, ConstraintType, RelationType, ConstraintSet
)
from .layout import (
    LayoutSolution, DFSTrace, PlacementInfo, LayoutConfig, CollisionInfo
)

# Scene Analysis schemas
from .object_cards import (
    ObjectCard, SceneRefImage, BackgroundImage, ObjectCardBatch
)
from .qc_reports import (
    QCReport, QCRecommendation, QCHistory
)

# Asset generation schemas
from .asset_metadata import (
    AssetMetadata, AssetBatch, AssetNormalizationConfig
)

# Editing schemas
from .edit_history import (
    EditCommand, EditResult, EditHistory, EditSummary
)

# Rendering schemas
from .rendering import (
    CameraPose, RenderConfig, RenderOutput, RenderBatch, RenderQualityMetrics
)

__all__ = [
    # Core
    "Session",
    "SessionStatus",
    "SessionRequest",
    "SceneObject",
    "SceneItem",
    "Vec3",
    "SceneData",
    "SpatialConstraint",
    "ConstraintType",
    "RelationType",
    "ConstraintSet",
    "LayoutSolution",
    "DFSTrace",
    "PlacementInfo",
    "LayoutConfig",
    "CollisionInfo",

    # Scene Analysis
    "ObjectCard",
    "SceneRefImage",
    "BackgroundImage",
    "ObjectCardBatch",
    "QCReport",
    "QCRecommendation",
    "QCHistory",

    # Asset Generation
    "AssetMetadata",
    "AssetBatch",
    "AssetNormalizationConfig",

    # Editing
    "EditCommand",
    "EditResult",
    "EditHistory",
    "EditSummary",

    # Rendering
    "CameraPose",
    "RenderConfig",
    "RenderOutput",
    "RenderBatch",
    "RenderQualityMetrics",
]