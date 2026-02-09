"""
阶段执行器模块

负责执行具体的build阶段。
"""

import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from holodeck_cli.config import config
from holodeck_cli.logging_config import get_logger
from holodeck_cli.stages import BuildStage, stage_config
from holodeck_cli.utils import save_json

# 导入holodeck_core模块 - 向后兼容
try:
    from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer
    from holodeck_core.object_gen.asset_generator import AssetGenerator
    from holodeck_core.scene_gen.layout_solver import LayoutSolver
    from holodeck_core.blender.scene_assembler import SceneAssembler
except ImportError as e:
    logger = get_logger(__name__)
    logger.error(f"无法导入holodeck_core模块: {e}")
    raise

# 导入同步Session模块
try:
    from holodeck_cli.sync_session import SyncSessionManager
except ImportError as e:
    logger = get_logger(__name__)
    logger.error(f"无法导入同步Session模块: {e}")
    raise

# 导入新的管道编排架构
try:
    from holodeck_core.integration.pipeline_orchestrator import PipelineOrchestrator, PipelineConfig
    from holodeck_core.clients.factory import (
        ImageClientFactory,
        LLMClientFactory,
        ThreeDClientFactory
    )
    from holodeck_core.exceptions.framework import HolodeckError
    NEW_PIPELINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"无法导入新的管道编排架构: {e}")
    logger.warning("将使用传统架构")
    NEW_PIPELINE_AVAILABLE = False

logger = get_logger(__name__)


class StageExecutor:
    """阶段执行器 - 支持新旧架构"""

    def __init__(self, session_id: str, use_new_pipeline: bool = True):
        self.session_id = session_id
        self.workspace_path = config.get_workspace_path()
        self.session_manager = SyncSessionManager(self.workspace_path)
        self.session = None
        self.stages_executed = []
        self.stage_results = {}
        self._initialized = False
        self.use_new_pipeline = use_new_pipeline and NEW_PIPELINE_AVAILABLE

        # 新架构组件
        self.pipeline_orchestrator = None
        self.image_client = None
        self.llm_client = None
        self.threed_client = None

    def _ensure_initialized(self):
        """确保执行器已初始化"""
        if not self._initialized:
            self.session = self.session_manager.load_session(self.session_id)
            if not self.session:
                raise ValueError(f"会话 {self.session_id} 不存在")

            # 如果使用新架构，初始化管道编排器
            if self.use_new_pipeline:
                self._initialize_new_pipeline()

            self._initialized = True

    def _initialize_new_pipeline(self):
        """初始化新的管道编排器"""
        try:
            # 创建客户端工厂
            image_factory = ImageClientFactory()
            llm_factory = LLMClientFactory()
            threed_factory = ThreeDClientFactory()

            # 创建客户端实例
            self.image_client = image_factory.create_client()
            self.llm_client = llm_factory.create_client()
            self.threed_client = threed_factory.create_client()

            # 创建管道配置
            pipeline_config = PipelineConfig(
                workspace_root=str(self.workspace_path),
                session_id=self.session_id
            )

            # 创建管道编排器
            self.pipeline_orchestrator = PipelineOrchestrator(config=pipeline_config)

            logger.info("新管道编排器初始化成功")

        except Exception as e:
            logger.warning(f"新管道编排器初始化失败: {e}")
            logger.warning("将使用传统执行方式")
            self.use_new_pipeline = False

    def execute_stage(self, stage: BuildStage, skip_dependencies: bool = False, **kwargs) -> bool:
        """执行单个阶段 - 支持新旧架构"""

        self._ensure_initialized()

        logger.info(f"开始执行阶段: {stage.value} - {stage_config.get_description(stage)}")
        start_time = time.time()

        # 检查阶段依赖（除非跳过）
        if not skip_dependencies and not stage_config.validate_stage_dependencies(stage, self.stages_executed):
            logger.error(f"阶段 {stage.value} 的依赖未满足")
            return False

        # 检查阶段是否已完成
        if self.is_stage_completed(stage):
            logger.info(f"阶段 {stage.value} 已完成，跳过")
            return True

        # 根据架构选择执行方式
        if self.use_new_pipeline and self._can_use_new_pipeline_for_stage(stage):
            result = self._execute_stage_with_new_pipeline(stage, **kwargs)
        else:
            result = self._execute_stage_with_legacy_method(stage, **kwargs)

        elapsed_time = time.time() - start_time

        # 记录结果
        if result:
            self.stages_executed.append(stage)
            self.stage_results[stage] = {
                "success": True,
                "duration": elapsed_time,
                "timestamp": time.time(),
                "architecture": "new" if self.use_new_pipeline else "legacy"
            }
            logger.info(f"阶段 {stage.value} 执行成功，耗时: {elapsed_time:.2f}秒")
            return True
        else:
            self.stage_results[stage] = {
                "success": False,
                "duration": elapsed_time,
                "timestamp": time.time(),
                "architecture": "new" if self.use_new_pipeline else "legacy"
            }
            logger.error(f"阶段 {stage.value} 执行失败")
            return False

    def _can_use_new_pipeline_for_stage(self, stage: BuildStage) -> bool:
        """检查是否可以使用新管道执行该阶段"""
        # 新管道目前支持对象生成相关阶段
        supported_stages = {
            BuildStage.SCENE_REF,  # 图像生成
            BuildStage.CARDS,      # 对象卡片生成
            BuildStage.ASSETS      # 3D资产生成
        }
        return stage in supported_stages and self.pipeline_orchestrator is not None

    def _execute_stage_with_new_pipeline(self, stage: BuildStage, **kwargs) -> bool:
        """使用新管道编排器执行阶段"""
        try:
            logger.info(f"使用新管道执行阶段: {stage.value}")

            # 准备输入上下文
            input_context = self._prepare_pipeline_context(stage, **kwargs)

            # 执行管道
            import asyncio
            result = asyncio.run(self.pipeline_orchestrator.execute_pipeline(input_context))

            if result.success:
                logger.info(f"新管道执行成功: {stage.value}")
                # 更新会话数据
                self._update_session_from_pipeline_result(result)
                return True
            else:
                logger.error(f"新管道执行失败: {stage.value} - {result.error}")
                return False

        except Exception as e:
            logger.error(f"新管道执行异常: {stage.value} - {e}")
            # 回退到传统方法
            logger.info(f"回退到传统方法执行阶段: {stage.value}")
            return self._execute_stage_with_legacy_method(stage, **kwargs)

    def _execute_stage_with_legacy_method(self, stage: BuildStage, **kwargs) -> bool:
        """使用传统方法执行阶段"""
        stage_functions = {
            BuildStage.SESSION: self._create_session,
            BuildStage.SCENE_REF: self._generate_scene_ref,
            BuildStage.OBJECTS: self._extract_objects,
            BuildStage.CARDS: self._generate_object_cards,
            BuildStage.ASSETS: self._generate_assets,
            BuildStage.CONSTRAINTS: self._generate_constraints,
            BuildStage.LAYOUT: self._solve_layout,
            BuildStage.ASSEMBLE: self._assemble_scene,
            BuildStage.RENDER: self._render_scene
        }

        if stage not in stage_functions:
            logger.error(f"未知阶段: {stage.value}")
            return False

        try:
            return stage_functions[stage](**kwargs)
        except Exception as e:
            logger.exception(f"传统方法执行阶段 {stage.value} 出错: {e}")
            return False

    def _prepare_pipeline_context(self, stage: BuildStage, **kwargs) -> Dict[str, Any]:
        """为管道准备输入上下文"""
        context = {
            "session_id": self.session_id,
            "session_dir": self.session.get_session_dir(),
            "stage": stage.value
        }

        # 根据阶段类型添加特定上下文
        if stage == BuildStage.SCENE_REF:
            # 获取场景描述信息
            request_data = self.session.load_request()
            context.update({
                "object_description": request_data.get("text", ""),
                "generation_prompt": f"A {request_data.get('style', 'modern')} style scene: {request_data.get('text', '')}",
                "style": request_data.get("style", "modern")
            })

        elif stage == BuildStage.CARDS:
            # 获取对象信息
            objects_data = self.session.load_objects()
            objects = objects_data.get("objects", [])
            if objects:
                obj = objects[0]  # 处理第一个对象作为示例
                context.update({
                    "object_description": obj.get("visual_desc", obj.get("name", "")),
                    "object_name": obj.get("name", ""),
                    "generation_prompt": obj.get("visual_desc", obj.get("name", ""))
                })

        elif stage == BuildStage.ASSETS:
            # 获取对象卡片信息
            objects_data = self.session.load_objects()
            objects = objects_data.get("objects", [])
            if objects:
                obj = objects[0]  # 处理第一个对象作为示例
                card_path = self.session.get_object_card_path(obj.get("object_id"))
                context.update({
                    "object_card_path": card_path,
                    "object_description": obj.get("visual_desc", obj.get("name", "")),
                    "3d_prompt": obj.get("visual_desc", obj.get("name", "")),
                    "output_format": "glb",
                    "output_dir": self.session.get_assets_path()
                })

        # 添加kwargs中的额外参数
        context.update(kwargs)
        return context

    def _update_session_from_pipeline_result(self, result) -> None:
        """从管道结果更新会话数据"""
        try:
            # 这里可以添加逻辑来将会话数据与管道结果同步
            logger.info(f"更新会话数据从管道结果: {result.session_id}")
            # 实际实现中需要根据具体需求来同步数据
        except Exception as e:
            logger.warning(f"更新会话数据失败: {e}")

    def execute_stages(self, stages: list[BuildStage], skip_dependencies: bool = False, **kwargs) -> bool:
        """执行多个阶段，支持断点续做"""

        self._ensure_initialized()

        for stage in stages:
            # 检查阶段是否已完成
            if self.is_stage_completed(stage):
                logger.info(f"阶段 {stage.value} 已完成，跳过")
                if stage not in self.stages_executed:
                    self.stages_executed.append(stage)
                continue

            # 检查阶段依赖（除非跳过）
            if not skip_dependencies and not stage_config.validate_stage_dependencies(stage, self.stages_executed):
                missing_deps = []
                order = BuildStage.get_execution_order()
                stage_idx = order.index(stage)
                for i in range(stage_idx):
                    if order[i] not in self.stages_executed:
                        missing_deps.append(order[i].value)
                logger.error(f"阶段 {stage.value} 的依赖未满足: {missing_deps}")
                return False

            # 执行阶段
            if not self.execute_stage(stage, skip_dependencies=skip_dependencies, **kwargs):
                logger.error(f"阶段 {stage.value} 执行失败，停止后续阶段")
                return False

        return True

    def is_stage_completed(self, stage: BuildStage) -> bool:
        """检查阶段是否已完成"""

        self._ensure_initialized()

        output_files = stage_config.get_output_files(stage)

        for output_file in output_files:
            file_path = self.session.get_session_dir() / output_file

            if output_file.endswith('/'):
                # 目录检查
                if not file_path.exists() or not file_path.is_dir():
                    return False
                # 检查目录是否为空
                if not any(file_path.iterdir()):
                    return False
            else:
                # 文件检查
                if not file_path.exists():
                    return False

        return True

    def get_next_incomplete_stage(self, from_stage: BuildStage) -> Optional[BuildStage]:
        """获取下一个未完成的阶段"""

        order = BuildStage.get_execution_order()
        from_idx = order.index(from_stage)

        for i in range(from_idx, len(order)):
            stage = order[i]
            if not self.is_stage_completed(stage):
                return stage

        return None

    def get_stage_result(self, stage: BuildStage) -> Optional[Dict[str, Any]]:
        """获取阶段执行结果"""
        return self.stage_results.get(stage)

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要"""
        return {
            "session_id": self.session_id,
            "stages_executed": [stage.value for stage in self.stages_executed],
            "stage_results": {
                stage.value: result
                for stage, result in self.stage_results.items()
            },
            "total_stages": len(self.stages_executed),
            "successful_stages": sum(
                1 for result in self.stage_results.values()
                if result.get("success", False)
            )
        }

    # 以下是各个阶段的具体实现

    def _create_session(self, **kwargs) -> bool:
        """创建会话阶段"""

        # 如果会话已存在，直接返回成功
        if self.session.get_request_path().exists():
            logger.info("会话已存在")
            return True

        # 从kwargs获取参数
        text = kwargs.get("text")
        style = kwargs.get("style", "modern")
        max_objects = kwargs.get("max_objects", 25)
        room_size = kwargs.get("room_size")

        if not text:
            logger.error("创建会话需要文本描述")
            return False

        # 准备请求数据
        request_data = {
            "text": text,
            "style": style,
            "constraints": {
                "max_objects": max_objects
            }
        }

        if room_size:
            request_data["constraints"]["room_size_hint"] = list(room_size)

        # 保存请求数据
        try:
            save_json(request_data, self.session.get_request_path())
            logger.info(f"会话创建成功: {self.session_id}")
            return True
        except Exception as e:
            logger.error(f"保存会话数据失败: {e}")
            return False

    def _generate_scene_ref(self, **kwargs) -> bool:
        """生成场景参考图"""

        analyzer = SceneAnalyzer()
        try:
            scene_ref_path = analyzer.generate_reference_image(self.session)
            logger.info(f"场景参考图已保存: {scene_ref_path}")
            return True
        except Exception as e:
            logger.error(f"生成场景参考图失败: {e}")
            return False

    def _extract_objects(self, **kwargs) -> bool:
        """提取对象"""

        analyzer = SceneAnalyzer()
        try:
            objects_data = analyzer.extract_objects(self.session)
            save_json(objects_data, self.session.get_objects_path())
            logger.info(f"提取了 {len(objects_data.get('objects', []))} 个对象")
            return True
        except Exception as e:
            logger.error(f"提取对象失败: {e}")
            return False

    def _generate_object_cards(self, **kwargs) -> bool:
        """生成对象卡片"""

        analyzer = SceneAnalyzer()
        try:
            analyzer.generate_object_cards(self.session)
            logger.info("对象卡片生成完成")
            return True
        except Exception as e:
            logger.error(f"生成对象卡片失败: {e}")
            return False

    def _generate_assets(self, **kwargs) -> bool:
        """生成3D资产"""

        skip_assets = kwargs.get("skip_assets", False)
        if skip_assets:
            logger.info("跳过资产生成步骤")
            # 仍然需要生成空的asset_manifest.json
            self._generate_asset_manifest({})
            return True

        generator = AssetGenerator()
        try:
            # 获取对象列表
            objects_data = self.session.load_objects()
            objects = objects_data.get("objects", [])

            generated_count = 0
            failed_count = 0
            asset_manifest = {}

            for obj in objects:
                object_id = obj.get("object_id")
                if not object_id:
                    continue

                try:
                    logger.info(f"生成资产: {obj.get('name', object_id)}")
                    asset_path = generator.generate_from_card(self.session, object_id)
                    if asset_path:
                        logger.info(f"资产生成成功: {asset_path}")
                        generated_count += 1

                        # 添加到asset manifest
                        asset_path_obj = Path(asset_path)
                        asset_manifest[object_id] = {
                            "asset_path": str(asset_path_obj.relative_to(self.session.get_session_dir())),
                            "format": asset_path_obj.suffix[1:].lower(),  # 去掉点号
                            "size_bytes": asset_path_obj.stat().st_size if asset_path_obj.exists() else 0,
                            "checksum": "sha256:placeholder",  # 实际实现中应该计算真实的checksum
                            "metadata": {
                                "vertices": 0,  # 实际实现中应该从资产文件中读取
                                "faces": 0,
                                "materials": 1
                            }
                        }
                    else:
                        logger.warning(f"资产生成失败: {object_id}")
                        failed_count += 1

                except Exception as e:
                    logger.error(f"生成资产 {object_id} 时出错: {e}")
                    failed_count += 1

            # 生成asset_manifest.json
            self._generate_asset_manifest(asset_manifest)

            logger.info(f"资产生成完成: 成功 {generated_count}, 失败 {failed_count}")
            return generated_count > 0 or len(objects) == 0

        except Exception as e:
            logger.error(f"资产生成过程失败: {e}")
            return False

    def _generate_asset_manifest(self, assets: Dict[str, Any]) -> None:
        """生成asset_manifest.json文件"""
        total_size = sum(asset.get("size_bytes", 0) for asset in assets.values())

        manifest_data = {
            "version": "v1",
            "assets": assets,
            "total_assets": len(assets),
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }

        manifest_path = self.session.get_session_dir() / "asset_manifest.json"
        save_json(manifest_data, manifest_path)
        logger.info(f"生成asset_manifest.json: {len(assets)} 个资产")

    def _generate_blender_object_map(self, layout_solution: Dict[str, Any]) -> None:
        """生成blender_object_map.json文件"""
        object_placements = layout_solution.get("object_placements", {})

        object_mapping = {}
        for object_id in object_placements.keys():
            object_mapping[object_id] = {
                "blender_name": object_id,
                "collection": "HolodeckScene",
                "parent": None,
                "type": "MESH",
                "visibility": True,
                "renderable": True
            }

        blender_object_map = {
            "version": "v1",
            "naming_convention": "object_id_as_name",
            "object_mapping": object_mapping,
            "collections": {
                "HolodeckScene": {
                    "name": "HolodeckScene",
                    "parent": None,
                    "color": "NONE"
                }
            },
            "scene_settings": {
                "unit_system": "METRIC",
                "scale_length": 1.0,
                "frame_rate": 24,
                "frame_start": 1,
                "frame_end": 250
            }
        }

        map_path = self.session.get_session_dir() / "blender_object_map.json"
        save_json(blender_object_map, map_path)
        logger.info(f"生成blender_object_map.json: {len(object_placements)} 个对象")

    def _generate_constraints(self, **kwargs) -> bool:
        """生成约束"""

        solver = LayoutSolver()
        try:
            constraints = solver.generate_constraints(self.session)
            save_json(constraints, self.session.get_constraints_path(version="v1"))
            logger.info("约束生成完成")
            return True
        except Exception as e:
            logger.error(f"生成约束失败: {e}")
            return False

    def _solve_layout(self, **kwargs) -> bool:
        """求解布局"""

        solver = LayoutSolver()
        try:
            # 生成约束
            constraints = solver.generate_constraints(self.session)
            constraints_path = self.session.get_constraints_path(version="v1")
            save_json(constraints, constraints_path)

            # DFS求解
            max_attempts = kwargs.get("max_layout_attempts", 3)
            solution = None

            for attempt in range(max_attempts):
                logger.info(f"布局求解尝试 {attempt + 1}/{max_attempts}")

                try:
                    solution = solver.solve_dfs(self.session, constraints_path)

                    if solution and solution.get("success"):
                        logger.info("布局求解成功")
                        # 保存解决方案
                        solution_path = self.session.get_layout_solution_path(version="v1")
                        save_json(solution, solution_path)

                        # 生成blender_object_map.json
                        self._generate_blender_object_map(solution)

                        return True
                    else:
                        logger.warning(f"布局求解失败 (尝试 {attempt + 1})")

                        # 保存失败轨迹
                        if solution:
                            trace_path = self.session.get_dfs_trace_path(version="v1")
                            save_json(solution.get("trace", {}), trace_path)

                        if attempt < max_attempts - 1:
                            # 基于失败轨迹调整约束
                            logger.info("调整约束并重新尝试...")
                            constraints = solver.generate_constraints(
                                self.session,
                                hint_from_trace=solution.get("trace")
                            )
                            constraints_path = self.session.get_constraints_path(version=f"v{attempt+2}")
                            save_json(constraints, constraints_path)

                except Exception as e:
                    logger.error(f"求解过程中出错 (尝试 {attempt + 1}): {e}")
                    if attempt == max_attempts - 1:
                        return False

            # 最终失败
            logger.error(f"布局求解失败，已尝试 {max_attempts} 次")
            return False

        except Exception as e:
            logger.error(f"布局求解过程失败: {e}")
            return False

    def _assemble_scene(self, **kwargs) -> bool:
        """组装场景"""

        no_blendermcp = kwargs.get("no_blendermcp", False)
        if no_blendermcp:
            logger.info("跳过Blender MCP场景组装步骤")
            return True

        assembler = SceneAssembler()
        try:
            blend_path = assembler.assemble_scene(self.session)
            logger.info(f"场景组装完成: {blend_path}")
            return True
        except Exception as e:
            logger.error(f"场景组装失败: {e}")
            return False

    def _render_scene(self, **kwargs) -> bool:
        """渲染场景"""

        skip_render = kwargs.get("skip_render", False)
        if skip_render:
            logger.info("跳过渲染步骤")
            return True

        no_blendermcp = kwargs.get("no_blendermcp", False)
        if no_blendermcp:
            logger.info("跳过Blender MCP渲染步骤")
            return True

        assembler = SceneAssembler()
        try:
            renders = assembler.render_scene(self.session, cameras="default")
            logger.info(f"渲染完成: {len(renders)} 张图片")
            return True
        except Exception as e:
            logger.error(f"渲染失败: {e}")
            # 渲染失败不视为整个流程失败
            return True