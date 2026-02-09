"""
阶段定义和配置模块

定义build流程的各个阶段和执行顺序。
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Callable

from holodeck_cli.logging_config import get_logger

logger = get_logger(__name__)


class BuildStage(Enum):
    """Build流程阶段枚举"""

    SESSION = "session"
    SCENE_REF = "scene_ref"
    OBJECTS = "objects"
    CARDS = "cards"
    ASSETS = "assets"
    CONSTRAINTS = "constraints"
    LAYOUT = "layout"
    ASSEMBLE = "assemble"
    RENDER = "render"
    ALL = "all"

    @classmethod
    def from_string(cls, stage_str: str) -> 'BuildStage':
        """从字符串创建阶段枚举"""
        try:
            return cls(stage_str.lower())
        except ValueError:
            valid_stages = [s.value for s in cls]
            raise ValueError(f"无效的阶段: {stage_str}. 有效阶段: {valid_stages}")

    @classmethod
    def get_execution_order(cls) -> List['BuildStage']:
        """获取阶段执行顺序"""
        return [
            cls.SESSION,
            cls.SCENE_REF,
            cls.OBJECTS,
            cls.CARDS,
            cls.ASSETS,
            cls.CONSTRAINTS,
            cls.LAYOUT,
            cls.ASSEMBLE,
            cls.RENDER
        ]

    @classmethod
    def get_stage_index(cls, stage: 'BuildStage') -> int:
        """获取阶段在顺序中的索引"""
        order = cls.get_execution_order()
        return order.index(stage)

    @classmethod
    def get_stage_by_index(cls, index: int) -> 'BuildStage':
        """根据索引获取阶段"""
        order = cls.get_execution_order()
        if 0 <= index < len(order):
            return order[index]
        raise ValueError(f"无效的阶段索引: {index}")

    @classmethod
    def get_stages_between(cls, from_stage: 'BuildStage', until_stage: 'BuildStage') -> List['BuildStage']:
        """获取两个阶段之间的所有阶段（包含起止阶段）"""
        order = cls.get_execution_order()
        from_idx = order.index(from_stage)
        until_idx = order.index(until_stage)

        if from_idx <= until_idx:
            return order[from_idx:until_idx + 1]
        else:
            # 如果from_stage在until_stage之后，只返回from_stage
            return [from_stage]


class StageConfig:
    """阶段配置"""

    def __init__(self):
        self.stage_descriptions = {
            BuildStage.SESSION: "创建会话和请求文件",
            BuildStage.SCENE_REF: "生成场景参考图",
            BuildStage.OBJECTS: "提取场景对象 (生成 objects.json)",
            BuildStage.CARDS: "生成对象卡片 (生成 object_cards/*)",
            BuildStage.ASSETS: "生成3D资产",
            BuildStage.CONSTRAINTS: "生成布局约束 (生成 constraints.json)",
            BuildStage.LAYOUT: "布局求解 (生成 layout_solution.json)",
            BuildStage.ASSEMBLE: "场景组装",
            BuildStage.RENDER: "渲染场景"
        }

        self.stage_output_files = {
            BuildStage.SESSION: ["request.json"],
            BuildStage.SCENE_REF: ["scene_ref.png"],
            BuildStage.OBJECTS: ["objects.json"],
            BuildStage.CARDS: ["object_cards/"],
            BuildStage.ASSETS: ["assets/"],
            BuildStage.CONSTRAINTS: ["constraints_v1.json"],
            BuildStage.LAYOUT: ["layout_solution_v1.json"],
            BuildStage.ASSEMBLE: ["blender_scene.blend"],
            BuildStage.RENDER: ["renders/"]
        }

    def get_description(self, stage: BuildStage) -> str:
        """获取阶段描述"""
        return self.stage_descriptions.get(stage, "未知阶段")

    def get_output_files(self, stage: BuildStage) -> List[str]:
        """获取阶段输出文件"""
        return self.stage_output_files.get(stage, [])

    def validate_stage_dependencies(self, stage: BuildStage, completed_stages: List[BuildStage]) -> bool:
        """验证阶段依赖关系"""
        order = BuildStage.get_execution_order()
        stage_idx = order.index(stage)

        # 检查前置阶段是否都已完成
        for i in range(stage_idx):
            if order[i] not in completed_stages:
                return False

        return True


# 全局配置实例
stage_config = StageConfig()