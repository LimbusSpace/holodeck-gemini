"""
Scene Analyzer 模块

实现场景分析的主要功能，包括参考图生成、对象提取和对象卡片生成。
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from holodeck_core.schemas import SceneData

# 导入客户端 - 保持向后兼容性
try:
    from .clients.hybrid_client import HybridAnalysisClient
    from .clients.unified_vlm import UnifiedVLMClient, VLMBackend
    from .prompts.templates import PromptManager
    from ..image_generation import ComfyUIClient, HunyuanImageClient
    HYBRID_CLIENT_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入Hybrid客户端: {e}")
    from .clients import UnifiedVLMClient, VLMBackend
    HYBRID_CLIENT_AVAILABLE = False

# 导入工厂模式支持
try:
    from ..clients.factory import LLMClientFactory
    FACTORY_MODE_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入LLM工厂: {e}")
    FACTORY_MODE_AVAILABLE = False


logger = logging.getLogger(__name__)


class SceneAnalyzer:
    """场景分析器"""

    def __init__(self, api_key: Optional[str] = None, use_comfyui: bool = True, use_hunyuan: bool = True, use_factory: bool = True):
        """初始化场景分析器

        Args:
            api_key: API密钥 (用于向后兼容)
            use_comfyui: 是否使用ComfyUI
            use_hunyuan: 是否使用Hunyuan
            use_factory: 是否使用工厂模式 (推荐)
        """
        self.api_key = api_key
        self.use_comfyui = use_comfyui
        self.use_hunyuan = use_hunyuan
        self.use_factory = use_factory
        self.client = None
        self.hybrid_client = None

        # 工厂模式相关属性
        self.llm_factory = None
        self.vlm_client = None

    def _get_client(self):
        """获取API客户端

        优先级：工厂模式 > Hybrid客户端 > 传统OpenAI客户端
        """
        # 如果已经有客户端，直接返回
        if self.client or self.hybrid_client or self.vlm_client:
            return self.client if self.client else (self.hybrid_client if self.hybrid_client else self.vlm_client)

        # 工厂模式优先（推荐）
        if self.use_factory and FACTORY_MODE_AVAILABLE:
            try:
                self.llm_factory = LLMClientFactory()

                # 尝试创建统一VLM客户端
                try:
                    self.vlm_client = self.llm_factory.create_client(
                        client_name="unified_vlm",
                        features=["object_extraction", "vision"]
                    )
                    logger.info("使用工厂模式创建UnifiedVLMClient")
                    return self.vlm_client
                except Exception as e:
                    logger.warning(f"无法创建UnifiedVLMClient: {e}, 尝试其他LLM客户端")

                # 如果没有VLM客户端，尝试其他LLM客户端
                self.vlm_client = self.llm_factory.create_client(
                    features=["chat", "completion"]
                )
                logger.info(f"使用工厂模式创建LLM客户端: {type(self.vlm_client).__name__}")
                return self.vlm_client

            except Exception as e:
                logger.warning(f"工厂模式不可用: {e}, 回退到传统模式")

        # 传统Hybrid客户端模式（向后兼容）
        if HYBRID_CLIENT_AVAILABLE and (self.use_comfyui or self.use_hunyuan):
            try:
                # 创建Unified VLM客户端（替代OpenAI和SiliconFlow）
                # 检查是否有CUSTOM_VLM配置可用
                has_custom_vlm = (os.getenv("CUSTOM_VLM_BASE_URL") and
                                 os.getenv("CUSTOM_VLM_API_KEY") and
                                 os.getenv("CUSTOM_VLM_MODEL_NAME"))

                if self.api_key or has_custom_vlm:
                    vlm_client = UnifiedVLMClient(
                        backend=VLMBackend.AUTO,
                        api_key=self.api_key
                    )
                else:
                    vlm_client = None
                comfyui_client = ComfyUIClient() if self.use_comfyui else None

                # 创建Hunyuan客户端（如果启用且有配置）
                hunyuan_client = None
                if self.use_hunyuan and os.getenv("HUNYUAN_SECRET_ID") and os.getenv("HUNYUAN_SECRET_KEY"):
                    try:
                        hunyuan_client = HunyuanImageClient(
                            secret_id=os.getenv("HUNYUAN_SECRET_ID"),
                            secret_key=os.getenv("HUNYUAN_SECRET_KEY")
                        )
                        logger.info("Hunyuan Image客户端可用")
                    except Exception as e:
                        logger.warning(f"无法初始化Hunyuan客户端: {e}")
                        hunyuan_client = None

                # SiliconFlow现在通过Unified VLM客户端支持
                siliconflow_client = None  # 不再需要单独的SiliconFlow客户端

                prompt_manager = PromptManager()

                # 创建hybrid客户端
                self.hybrid_client = HybridAnalysisClient(
                    vlm_client, comfyui_client, prompt_manager,
                    fallback_enabled=True, hunyuan_client=hunyuan_client
                )
                logger.info("使用Hybrid客户端（支持多后端优先级）")
            except Exception as e:
                logger.warning(f"无法初始化Hybrid客户端: {e}, 回退到Unified VLM")
                if self.api_key:
                    self.client = UnifiedVLMClient(
                        backend=VLMBackend.AUTO,
                        api_key=self.api_key
                    )
                else:
                    raise ValueError("当其他后端不可用时需要VLM API密钥")
        else:
            # 使用Unified VLM客户端
            if not self.api_key:
                raise ValueError("VLM API key is required")
            self.client = UnifiedVLMClient(
                backend=VLMBackend.AUTO,
                api_key=self.api_key
            )

        return self.client if self.client else (self.hybrid_client if self.hybrid_client else self.vlm_client)

    def generate_reference_image(self, session) -> Path:
        """生成场景参考图"""

        logger.info("生成场景参考图...")

        # 获取会话信息
        request_data = session.load_request()
        scene_text = request_data.get("text", "")
        style = request_data.get("style", "modern")

        # 异步调用API
        async def _generate():
            client = self._get_client()

            # 检查是否使用Hybrid客户端
            if hasattr(client, 'generate_scene_reference'):
                # 使用Hybrid客户端
                scene_ref_image = await client.generate_scene_reference(
                    session_id=session.session_id,
                    scene_text=scene_text,
                    style=style
                )
                # 从SceneRefImage对象读取图像数据
                image_path = scene_ref_image.image_path
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                metadata = {
                    "prompt_used": scene_ref_image.prompt_used,
                    "style": scene_ref_image.style,
                    "generation_time": scene_ref_image.generation_time
                }
                return image_bytes, metadata
            elif hasattr(client, 'generate_image'):
                # 使用ComfyUI客户端
                output_dir = Path(session.get_session_dir())
                output_dir.mkdir(parents=True, exist_ok=True)

                image_path, metadata = await client.generate_image(
                    prompt=scene_text,
                    workflow_type="scene_ref",
                    output_dir=output_dir
                )
                # 将image_path转换为Path对象并读取为bytes
                with open(image_path, 'rb') as f:
                    image_bytes = f.read()
                return image_bytes, metadata
            else:
                # 使用OpenAI客户端
                image_bytes, metadata = await client.generate_scene_image(
                    prompt=scene_text,
                    style=style,
                    size="1024x1024",
                    quality="standard"
                )
                return image_bytes, metadata

        try:
            image_bytes, metadata = asyncio.run(_generate())

            # 保存图片
            scene_ref_path = session.get_scene_ref_path()
            scene_ref_path.parent.mkdir(parents=True, exist_ok=True)

            with open(scene_ref_path, 'wb') as f:
                f.write(image_bytes)

            logger.info(f"场景参考图已保存: {scene_ref_path}")
            return scene_ref_path

        except Exception as e:
            logger.error(f"生成场景参考图失败: {e}")
            raise

    def extract_objects(self, session) -> Dict[str, Any]:
        """提取场景对象"""

        logger.info("提取场景对象...")

        # 获取会话信息
        request_data = session.load_request()
        scene_text = request_data.get("text", "")

        # 检查是否有参考图
        scene_ref_path = session.get_scene_ref_path()
        reference_image = None
        if scene_ref_path.exists():
            with open(scene_ref_path, 'rb') as f:
                reference_image = f.read()

        # 异步调用API
        async def _extract():
            client = self._get_client()

            # 检查客户端类型并调用相应的方法
            if hasattr(client, 'session_lock'):
                # Hybrid客户端
                scene_data = await client.extract_objects(
                    session_id=session.session_id,
                    scene_text=scene_text,
                    ref_image_path=str(scene_ref_path) if scene_ref_path.exists() else None
                )
            elif hasattr(client, 'extract_objects'):
                # Unified VLM客户端或其他标准客户端
                scene_data = await client.extract_objects(
                    scene_text=scene_text,
                    image=reference_image
                )
            else:
                # 传统OpenAI客户端
                scene_data = await client.extract_objects(
                    scene_text=scene_text,
                    reference_image=reference_image
                )
            return scene_data

        try:
            scene_data = asyncio.run(_extract())

            # 转换为字典格式
            objects_data = {
                "scene_style": scene_data.scene_style,
                "objects": []
            }

            for obj in scene_data.objects:
                object_dict = {
                    "object_id": obj.object_id,
                    "name": obj.name,
                    "category": obj.category or "furniture",
                    "size_m": [
                        obj.size.x if obj.size else 1.0,
                        obj.size.y if obj.size else 1.0,
                        obj.size.z if obj.size else 1.0
                    ],
                    "initial_pose": {
                        "pos": [
                            obj.position.x if obj.position else 0.0,
                            obj.position.y if obj.position else 0.0,
                            obj.position.z if obj.position else 0.0
                        ],
                        "rot_euler": [
                            obj.rotation.x if obj.rotation else 0.0,
                            obj.rotation.y if obj.rotation else 0.0,
                            obj.rotation.z if obj.rotation else 0.0
                        ]
                    },
                    "visual_desc": obj.visual_description or "",
                    "must_exist": True
                }
                objects_data["objects"].append(object_dict)

            logger.info(f"提取了 {len(objects_data['objects'])} 个对象")
            return objects_data

        except Exception as e:
            logger.error(f"提取对象失败: {e}")
            # 返回空对象数据
            return {
                "scene_style": "unknown",
                "objects": []
            }

    def generate_object_cards(self, session, strict_mode: bool = True, max_failure_rate: float = 0.3, test_mode: bool = False) -> dict:
        """生成对象卡片（JSON + 图像）

        使用HybridClient的多后端优先级系统：
        Hunyuan Image > OpenAI > ComfyUI

        Args:
            session: Session对象
            strict_mode: 严格模式，失败率超过阈值时抛出异常
            max_failure_rate: 最大允许失败率（默认30%）
            test_mode: 测试模式，允许创建占位符图像

        Returns:
            生成结果统计字典

        Raises:
            Exception: 当strict_mode=True且失败率超过阈值时
        """
        logger.info("生成对象卡片...")

        # 获取对象数据
        objects_data = session.load_objects()
        objects = objects_data.get("objects", [])

        if not objects:
            logger.warning("没有找到需要生成卡片的对象")
            return {"total": 0, "success": 0, "failed": 0, "failed_objects": []}

        # 创建对象卡片目录
        object_cards_dir = session.get_object_cards_dir()
        object_cards_dir.mkdir(parents=True, exist_ok=True)

        # 获取场景参考图路径
        scene_ref_path = session.get_scene_ref_path()

        # 统计变量
        total_objects = len(objects)
        successful_cards = 0
        failed_objects = []

        # 优先使用HybridClient（支持多后端优先级）
        client = self._get_client()

        if self.hybrid_client and hasattr(self.hybrid_client, 'generate_object_cards'):
            logger.info("使用HybridClient生成对象卡片（支持Hunyuan Image > OpenAI > ComfyUI优先级）")
            try:
                import asyncio

                # 准备对象数据，添加session_id
                objects_with_session = []
                for obj in objects:
                    obj_copy = obj.copy()
                    obj_copy['session_id'] = session.session_id
                    objects_with_session.append(obj_copy)

                # 异步调用HybridClient
                cards = asyncio.run(self.hybrid_client.generate_object_cards(
                    session.session_id,
                    objects_with_session,
                    str(scene_ref_path)
                ))

                successful_cards = len(cards)
                failed_objects = [obj.get('object_id', f'obj_{i}') for i, obj in enumerate(objects) if i >= len(cards)]

                logger.info(f"HybridClient生成完成: {successful_cards}/{total_objects} 成功")

            except Exception as e:
                logger.error(f"HybridClient生成对象卡片失败: {e}")
                logger.info("回退到SceneAnalyzer原生实现")
                successful_cards, failed_objects = self._generate_object_cards_fallback(
                    objects, objects_data, object_cards_dir, scene_ref_path, test_mode
                )
        else:
            logger.info("HybridClient不可用，使用原生实现")
            successful_cards, failed_objects = self._generate_object_cards_fallback(
                objects, objects_data, object_cards_dir, scene_ref_path
            )

        # 检查失败率
        failure_rate = len(failed_objects) / total_objects if total_objects > 0 else 0

        result = {
            "total": total_objects,
            "success": successful_cards,
            "failed": len(failed_objects),
            "failure_rate": failure_rate,
            "failed_objects": failed_objects
        }

        logger.info(f"对象卡片生成完成: {successful_cards}/{total_objects} 成功, 失败率: {failure_rate:.1%}")

        # 严格模式下检查失败率
        if strict_mode and failure_rate > max_failure_rate:
            error_msg = f"对象卡片生成失败率过高 ({failure_rate:.1%} > {max_failure_rate:.1%})"
            error_msg += f"\n失败对象: {failed_objects}"
            error_msg += f"\n\n建议操作:"
            error_msg += f"\n1. 检查Hunyuan Image API密钥配置"
            error_msg += f"\n2. 确认ComfyUI服务是否运行 (默认127.0.0.1:8188)"
            error_msg += f"\n3. 使用非严格模式继续管线: generate_object_cards(session, strict_mode=False)"
            error_msg += f"\n4. 检查网络连接和API配额"

            logger.error(error_msg)
            raise Exception(error_msg)

        return result

    def _generate_object_cards_fallback(self, objects, objects_data, object_cards_dir, scene_ref_path, test_mode: bool = False):
        """回退到原生对象卡片生成实现"""
        successful_cards = 0
        failed_objects = []

        for obj in objects:
            object_id = obj.get("object_id")
            if not object_id:
                continue

            object_name = obj.get("name", "unknown")
            visual_desc = obj.get("visual_desc", "")

            try:
                # 创建对象卡片数据
                card_data = {
                    "object_id": object_id,
                    "name": object_name,
                    "category": obj.get("category", "furniture"),
                    "visual_description": visual_desc,
                    "size": obj.get("size_m", [1.0, 1.0, 1.0]),
                    "style": objects_data.get("scene_style", "modern")
                }

                # 保存JSON卡片
                card_json_path = object_cards_dir / f"{object_id}.json"
                import json
                with open(card_json_path, 'w', encoding='utf-8') as f:
                    json.dump(card_data, f, indent=2, ensure_ascii=False)

                logger.info(f"生成对象卡片JSON: {object_id}")

                # 生成对象卡片图像（使用改进的实现）
                self._generate_object_card_image_enhanced(
                    object_id=object_id,
                    object_name=object_name,
                    visual_desc=visual_desc,
                    style=objects_data.get("scene_style", "modern"),
                    output_dir=object_cards_dir,
                    scene_ref_path=scene_ref_path
                )

                successful_cards += 1
                logger.info(f"生成对象卡片图像: {object_id}")

            except Exception as e:
                logger.error(f"生成对象卡片 {object_id} 失败: {e}")
                failed_objects.append(object_id)

                # 严格模式下不创建占位符，直接抛出异常
                output_image_path = object_cards_dir / f"{object_id}.png"
                self._create_placeholder_image(output_image_path, object_name, test_mode=test_mode)

        return successful_cards, failed_objects

    def _generate_object_card_image_enhanced(
        self,
        object_id: str,
        object_name: str,
        visual_desc: str,
        style: str,
        output_dir: Path,
        scene_ref_path: Path
    ) -> Path:
        """生成对象卡片图像（增强版，支持多后端优先级）

        优先级顺序:
        1. Hunyuan Image (如果配置可用)
        2. ComfyUI (本地服务)

        Args:
            object_id: 对象ID
            object_name: 对象名称
            visual_desc: 视觉描述
            style: 风格
            output_dir: 输出目录
            scene_ref_path: 场景参考图路径

        Returns:
            生成的图像文件路径

        Raises:
            Exception: 当所有后端都失败时
        """
        output_image_path = output_dir / f"{object_id}.png"

        # 基于 visual_desc 构建提示词
        if visual_desc and visual_desc.strip():
            object_description = visual_desc
        else:
            object_description = object_name

        prompt_template = (
            f"A photorealistic {object_name}: {object_description}. "
            f"Style: {style}. "
            f"Pure gray background, isolated object, front view, high detail."
        )

        # 错误列表，用于最终报告
        errors = []

        # 尝试1: Hunyuan Image (如果配置可用)
        if os.getenv("HUNYUAN_SECRET_ID") and os.getenv("HUNYUAN_SECRET_KEY"):
            try:
                logger.info(f"尝试使用Hunyuan Image生成对象卡片: {object_id}")
                result = self._generate_with_hunyuan_image(
                    object_id, prompt_template, output_image_path
                )
                if result:
                    logger.info(f"Hunyuan Image生成成功: {object_id}")
                    return result
            except Exception as e:
                error_msg = f"Hunyuan Image失败: {e}"
                errors.append(error_msg)
                logger.warning(f"{object_id}: {error_msg}")

        # 尝试2: ComfyUI (本地服务)
        try:
            logger.info(f"尝试使用ComfyUI生成对象卡片: {object_id}")
            result = self._generate_with_comfyui(
                object_id, prompt_template, output_image_path, output_dir
            )
            if result:
                logger.info(f"ComfyUI生成成功: {object_id}")
                return result
        except Exception as e:
            error_msg = f"ComfyUI失败: {e}"
            errors.append(error_msg)
            logger.warning(f"{object_id}: {error_msg}")

        # 所有后端都失败
        all_errors ="; ".join(errors)
        error_msg = f"对象卡片 {object_id} 生成失败，所有后端均不可用: {all_errors}"
        logger.error(error_msg)

        # 所有后端都失败，抛出异常而不是创建占位符
        raise Exception(error_msg)

    def _generate_with_hunyuan_image(self, object_id: str, prompt: str, output_path: Path) -> Path:
        """使用Hunyuan Image生成对象卡片"""
        try:
            from ..image_generation.hunyuan_image_client import HunyuanImageClient

            client = HunyuanImageClient(
                secret_id=os.getenv("HUNYUAN_SECRET_ID"),
                secret_key=os.getenv("HUNYUAN_SECRET_KEY")
            )

            # 生成图像
            result = client.generate_image(
                prompt=prompt,
                resolution="512:512",  # Object card标准尺寸
                style=None,  # 使用默认风格
                model="hunyuan-pro",
                output_path=str(output_path)
            )

            # 验证生成的文件
            if output_path.exists() and output_path.stat().st_size > 1000:  # 至少1KB
                return output_path
            else:
                raise Exception(f"Hunyuan Image生成文件无效或过小: {output_path.stat().st_size} bytes")

        except Exception as e:
            logger.error(f"Hunyuan Image生成失败 {object_id}: {e}")
            raise

    def _generate_with_comfyui(self, object_id: str, prompt: str, output_path: Path, output_dir: Path) -> Path:
        """使用ComfyUI生成对象卡片"""
        try:
            from ..image_generation.workflows import create_object_card_workflow
            from ..image_generation.comfyui_client import ComfyUIClient
            import asyncio

            # 创建工作流
            workflow = create_object_card_workflow(object_name=object_id, prompt=prompt)

            # 设置输出文件名前缀
            for node_id, node_data in workflow.items():
                if node_data.get("class_type") == "SaveImage":
                    node_data["inputs"]["filename_prefix"] = object_id
                    break

            # 异步生成图像
            async def generate_image():
                client = ComfyUIClient()

                # 直接使用现有的generate_image方法
                image_path, metadata = await client.generate_image(
                    prompt=prompt,
                    workflow_type="object_card",
                    output_dir=output_dir
                )

                # 重命名生成的图像文件为 object_id.png
                if Path(image_path).exists():
                    import shutil
                    shutil.copy2(image_path, output_path)
                    return output_path
                else:
                    raise Exception(f"生成的图像文件不存在: {image_path}")

            # 运行异步生成
            return asyncio.run(generate_image())

        except Exception as e:
            logger.error(f"ComfyUI生成失败 {object_id}: {e}")
            raise

    def _generate_object_card_image(self,
        object_id: str,
        object_name: str,
        visual_desc: str,
        style: str,
        output_dir: Path,
        scene_ref_path: Path
    ) -> Path:
        """生成对象卡片图像（兼容旧接口）"""
        logger.warning("调用已废弃的_generate_object_card_image方法，建议更新调用代码")
        return self._generate_object_card_image_enhanced(
            object_id, object_name, visual_desc, style, output_dir, scene_ref_path
        )

    def _create_placeholder_image(self, output_path: Path, object_name: str, test_mode: bool = False):
        """创建占位符图像

        Args:
            output_path: 输出路径
            object_name: 对象名称
            test_mode: 是否为测试模式，只有在测试模式下才创建占位符

        Raises:
            RuntimeError: 在非测试模式下调用此方法时抛出
        """
        if not test_mode:
            raise RuntimeError(
                f"图像生成失败: 无法为对象 '{object_name}' 生成图像。\n"
                f"建议操作:\n"
                f"1. 检查网络连接和API密钥配置\n"
                f"2. 验证对象描述是否合适\n"
                f"3. 尝试使用不同的对象名称或描述\n"
                f"4. 如果是测试环境，请设置test_mode=True"
            )

        try:
            from PIL import Image, ImageDraw, ImageFont

            # 创建白色背景图像
            img = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)

            # 绘制边框
            draw.rectangle([50, 50, 462, 462], outline=(100, 100, 100, 255), width=2)

            # 添加文本
            text = f"{object_name}\n(Test Placeholder)"
            # 简单文本居中
            bbox = draw.textbbox((0, 0), text, font=None)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            x = (512 - text_w) // 2
            y = (512 - text_h) // 2

            draw.text((x, y), text, fill=(100, 100, 100, 255))

            # 保存图像
            img.save(output_path, 'PNG')
            logger.warning(f"在测试模式下创建占位符图像: {output_path}")

        except Exception as e:
            logger.error(f"创建占位符图像失败: {e}")
            # 如果PIL不可用，创建空文件
            output_path.touch()

    def qc_object_cards(self, session) -> Dict[str, Any]:
        """质量控制对象卡片"""

        logger.info("质量控制对象卡片...")

        # 这里可以实现质量控制逻辑
        # 目前简单返回现有对象数据
        objects_data = session.load_objects()

        # TODO: 实现实际的质量控制逻辑
        # 1. 使用API评估对象卡片的合理性
        # 2. 过滤掉不合理的对象
        # 3. 调整对象属性

        logger.info("对象卡片质量控制完成")
        return objects_data