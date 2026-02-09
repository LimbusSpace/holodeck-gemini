"""Asset generator for 3D object generation using multiple backends."""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from .sf3d_client import SF3DClient
from .hunyuan_3d_client import Hunyuan3DClient
from .backend_selector import BackendSelector


class AssetGenerator:
    """Asset generator for 3D object generation using multiple backends."""

    def __init__(self, sf3d_client: Optional[SF3DClient] = None,
                 hunyuan_client: Optional[Hunyuan3DClient] = None):
        self.logger = logging.getLogger(__name__)

        # Initialize backend selector
        self.backend_selector = BackendSelector()

        # Initialize SF3D client
        if sf3d_client is None:
            self.sf3d_client = SF3DClient()
        else:
            self.sf3d_client = sf3d_client

        # Initialize Hunyuan3D client
        if hunyuan_client is None:
            try:
                self.hunyuan_client = Hunyuan3DClient.from_env()
            except Exception as e:
                self.logger.warning(f"Failed to initialize Hunyuan3D client: {e}")
                self.hunyuan_client = None
        else:
            self.hunyuan_client = hunyuan_client

    def generate_from_card(self, session, object_id: str) -> Path:
        """Generate 3D asset from object card using multiple backends.

        Args:
            session: Session object with workspace information
            object_id: Object identifier

        Returns:
            Path to generated GLB asset
        """
        try:
            # Get object cards directory and find the card for this object
            object_cards_dir = session.get_object_cards_dir()
            card_path = object_cards_dir / f"{object_id}.png"

            if not card_path.exists():
                # Try JSON format card
                card_path = object_cards_dir / f"{object_id}.json"
                if not card_path.exists():
                    self.logger.warning(f"Object card not found for {object_id}. Falling back to description-based generation.")
                    # Fall back to description-based generation
                    return self._generate_from_description_fallback(session, object_id)

            # Create assets directory
            assets_dir = session.session_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Select optimal backend
            backend = self.backend_selector.get_optimal_backend()
            self.logger.info(f"Generating 3D asset for object {object_id} using {backend.upper()}")

            # Try selected backend first
            if backend == "hunyuan" and self.hunyuan_client:
                try:
                    return self._generate_with_hunyuan(session, object_id, card_path, assets_dir)
                except Exception as e:
                    self.logger.warning(f"Hunyuan3D generation failed: {e}, falling back to SF3D")
                    backend = "sf3d"

            # Use SF3D as fallback or primary
            if backend == "sf3d":
                try:
                    return self._generate_with_sf3d(session, object_id, card_path, assets_dir)
                except Exception as e:
                    self.logger.error(f"SF3D generation failed: {e}")
                    # Try Hunyuan3D as fallback if not already tried
                    if self.hunyuan_client and backend != "hunyuan":
                        try:
                            self.logger.info("Attempting Hunyuan3D as fallback")
                            return self._generate_with_hunyuan(session, object_id, card_path, assets_dir)
                        except Exception as hunyuan_error:
                            self.logger.error(f"Hunyuan3D fallback also failed: {hunyuan_error}")

                    # Fall back to placeholder
                    self.logger.warning("Falling back to placeholder asset generation")
                    return self._generate_placeholder_asset(session, object_id, str(e))

        except Exception as e:
            self.logger.error(f"Asset generation failed: {e}")
            raise

    def _generate_with_hunyuan(self, session, object_id: str, card_path: Path, assets_dir: Path) -> Path:
        """Generate 3D asset using Hunyuan3D."""
        if not self.hunyuan_client:
            raise RuntimeError("Hunyuan3D client not available")

        # Create task for Hunyuan3D
        from .hunyuan_3d_client import Hunyuan3DTask
        import base64

        # Use card image for image-to-3D generation (preferred)
        if card_path.suffix == '.png' and card_path.exists():
            self.logger.info(f"Using card image for 3D generation: {card_path}")
            with open(card_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            task = Hunyuan3DTask(
                task_id=f"{session.session_id}_{object_id}",
                image_base64=image_base64,
                output_dir=str(assets_dir),
                enable_pbr=True,
                result_format="GLB"
            )
        else:
            # Fallback to text prompt if no image
            prompt = f"A 3D model of object {object_id}"
            if card_path.suffix == '.json' and card_path.exists():
                import json
                try:
                    with open(card_path, 'r', encoding='utf-8') as f:
                        card_data = json.load(f)
                        prompt = card_data.get('description', card_data.get('name', prompt))
                except Exception as e:
                    self.logger.warning(f"Failed to load card data: {e}")
            task = Hunyuan3DTask(
                task_id=f"{session.session_id}_{object_id}",
                prompt=prompt,
                output_dir=str(assets_dir),
                enable_pbr=True,
                result_format="GLB"
            )

        # Generate using Hunyuan3D
        result = self.hunyuan_client.generate_3d_from_task(task)

        if result.success:
            # Find the generated GLB file with proper naming
            # 首先尝试找到生成的文件
            glb_files = list(assets_dir.glob("*.glb"))
            if glb_files:
                # 获取第一个生成的文件
                source_file = glb_files[0]

                # 首先尝试使用LLM生成描述性文件名
                llm_filename = self._generate_llm_based_filename(card_path, object_id)

                if llm_filename:
                    new_filename = f"{llm_filename}_{object_id}.glb"
                else:
                    # LLM失败时使用回退机制
                    object_name = self._get_object_name_from_card(card_path, object_id)
                    style_info = "通用"  # 简化回退
                    material_info = "标准"  # 简化回退
                    new_filename = self._generate_descriptive_filename(
                        object_id, object_name, style_info, material_info
                    )
                new_filepath = assets_dir / new_filename

                # 重命名文件
                source_file.rename(new_filepath)

                self.logger.info(f"Successfully generated and renamed 3D asset: {new_filepath}")
                return new_filepath
            else:
                raise RuntimeError("Hunyuan3D reported success but no GLB file was found")
        else:
            raise RuntimeError(f"Hunyuan3D generation failed: {result.error_message}")

    def _generate_with_sf3d(self, session, object_id: str, card_path: Path, assets_dir: Path) -> Path:
        """Generate 3D asset using SF3D."""
        # Generate GLB using SF3D with proper naming
        # SF3D will generate with filename_prefix, so we need to find and rename it

        # Use SF3D client to generate 3D asset
        import asyncio

        async def generate_3d():
            try:
                # Test SF3D availability first
                if not await self.sf3d_client.test_sf3d_availability():
                    raise RuntimeError("SF3D is not available. Please ensure ComfyUI with SF3D plugin is running.")

                # Generate 3D asset
                glb_path, metadata = await self.sf3d_client.generate_3d_asset(
                    image_path=str(card_path),
                    output_dir=str(assets_dir),
                    foreground_ratio=0.85,
                    texture_resolution=1024,
                    remesh="triangle",
                    vertex_count=-1,
                    filename_prefix=object_id
                )

                return Path(glb_path)

            except Exception as e:
                self.logger.error(f"SF3D generation failed: {e}")
                raise

        # Run async generation
        result_path = asyncio.run(generate_3d())
        self.logger.info(f"Successfully generated 3D asset with SF3D: {result_path}")
        return result_path

    def generate_from_description(self, session_id: str, object_id: str,
                                 description: str, style_context: Optional[Dict[str, Any]] = None) -> Path:
        """Generate asset from description using multiple backends.

        Args:
            session_id: Scene session identifier
            object_id: Object identifier
            description: Object description
            style_context: Style context for consistency

        Returns:
            Path to generated asset
        """
        try:
            self.logger.info(f"Generating asset for object {object_id}")

            # Select optimal backend
            backend = self.backend_selector.get_optimal_backend()
            self.logger.info(f"Using {backend.upper()} backend for description-based generation")

            session_path = Path("workspace/sessions") / session_id
            assets_dir = session_path / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Try Hunyuan3D first if available (best for text-to-3D)
            if self.hunyuan_client:
                try:
                    # Use Hunyuan3D regardless of backend selection for description-based generation
                    # since it's the only one that supports text-to-3D properly
                    self.logger.info("Using Hunyuan3D for text-to-3D generation")

                    task = Hunyuan3DTask(
                        task_id=f"{session_id}_{object_id}",
                        prompt=description,
                        output_dir=str(assets_dir),
                        enable_pbr=True,
                        result_format="GLB"
                    )
                    result = self.hunyuan_client.generate_3d_from_task(task)
                    if result.success:
                        asset_path = assets_dir / f"{object_id}.glb"
                        self.logger.info(f"Successfully generated asset with Hunyuan3D: {asset_path}")
                        return asset_path
                except Exception as e:
                    self.logger.warning(f"Hunyuan3D description generation failed: {e}")

            # Try other backends based on selection
            if backend == "hunyuan" and not self.hunyuan_client:
                self.logger.warning("Hunyuan3D selected but client not available")

            # For now, SF3D doesn't support text-to-3D, so we fall back to placeholder
            # In the future, we could integrate other text-to-3D backends here
            self.logger.info(f"No suitable text-to-3D backend available, generating placeholder for {object_id}")

            asset_path = assets_dir / f"{object_id}.glb"
            with open(asset_path, 'w', encoding='utf-8') as f:
                f.write(f"# Placeholder GLB for {object_id}\n")
                f.write(f"# Description: {description}\n")
                if style_context:
                    f.write(f"# Style: {style_context.get('scene_style', 'unknown')}\n")
                    f.write(f"# Category: {style_context.get('category', 'unknown')}\n")
                f.write(f"# Backend: {backend}\n")
                f.write(f"# Note: Text-to-3D generation not available, using placeholder\n")

            self.logger.info(f"Generated placeholder asset: {asset_path}")
            return asset_path

        except Exception as e:
            self.logger.error(f"Asset generation failed: {e}")
            raise

    def _generate_from_description_fallback(self, session, object_id: str) -> Path:
        """Fallback method to generate asset from description when object cards don't exist.

        Args:
            session: Session object with workspace information
            object_id: Object identifier

        Returns:
            Path to generated GLB asset
        """
        try:
            # Load object data to get description
            objects_data = session.load_objects()
            objects = objects_data.get("objects", [])

            # Find the object by ID
            object_info = None
            for obj in objects:
                if obj.get("object_id") == object_id:
                    object_info = obj
                    break

            if not object_info:
                self.logger.warning(f"Object {object_id} not found in session data. Using placeholder.")
                return self._generate_placeholder_asset(session, object_id, "Object not found in session")

            # Extract description and style context
            description = object_info.get("visual_desc", object_info.get("name", f"A 3D model of {object_id}"))
            style_context = {
                "scene_style": objects_data.get("scene_style", "modern"),
                "category": object_info.get("category", "object")
            }

            self.logger.info(f"Using description-based generation for {object_id}: {description[:50]}...")

            # Call the existing description-based generation method
            return self.generate_from_description(
                session_id=session.session_id,
                object_id=object_id,
                description=description,
                style_context=style_context
            )

        except Exception as e:
            self.logger.error(f"Description-based fallback generation failed: {e}")
            return self._generate_placeholder_asset(session, object_id, str(e))

    def _generate_placeholder_asset(self, session, object_id: str, error_msg: str = "") -> Path:
        """Generate a placeholder asset file for fallback.

        Args:
            session: Session object
            object_id: Object identifier
            error_msg: Error message to include in placeholder

        Returns:
            Path to placeholder asset
        """
        assets_dir = session.session_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        asset_path = assets_dir / f"{object_id}.glb"

        with open(asset_path, 'w', encoding='utf-8') as f:
            f.write(f"# Placeholder GLB for {object_id}\n")
            f.write(f"# SF3D generation failed: {error_msg}\n")
            f.write(f"# Generated at: {session.session_dir}\n")

        return asset_path
    def _get_object_name_from_card(self, card_path: Path, object_id: str) -> str:
        """从对象卡片中提取对象名称"""
        if card_path.suffix == '.json':
            import json
            try:
                with open(card_path, 'r', encoding='utf-8') as f:
                    card_data = json.load(f)
                    return card_data.get('name', object_id)
            except Exception:
                return object_id
        return object_id

    def _generate_llm_based_filename(self, card_path: Path, object_id: str) -> Optional[str]:
        """使用LLM生成完整的描述性文件名"""
        try:
            if card_path.suffix == '.json':
                import json
                with open(card_path, 'r', encoding='utf-8') as f:
                    card_data = json.load(f)
                    description = card_data.get('description', '')
                    object_name = card_data.get('name', object_id)

                    # 使用增强版LLM命名服务（如果可用）
                    try:
                        from .enhanced_llm_naming_service import EnhancedLLMNamingService
                        import asyncio

                        naming_service = EnhancedLLMNamingService()

                        # 在同步方法中运行异步LLM调用
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            generated_name = loop.run_until_complete(
                                naming_service.generate_object_name(
                                    description, object_name, card_path
                                )
                            )
                            loop.close()
                        except RuntimeError:
                            # 如果已经在事件循环中，直接调用
                            generated_name = asyncio.get_event_loop().run_until_complete(
                                naming_service.generate_object_name(
                                    description, object_name, card_path
                                )
                            )
                    except Exception as e:
                        self.logger.info(f"增强版LLM命名服务暂时不可用: {e}，尝试使用旧版服务")

                        # 回退到旧版服务
                        try:
                            from .llm_naming_service import LLMNamingService
                            naming_service = LLMNamingService()
                            generated_name = naming_service.generate_object_name(
                                description, object_name, card_path
                            )
                        except Exception as fallback_error:
                            self.logger.info(f"LLM命名服务（包括回退）都不可用: {fallback_error}，使用回退机制")
                            generated_name = None

                    if generated_name:
                        # 清理文件名中的非法字符
                        safe_name = generated_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        return safe_name

        except Exception as e:
            self.logger.warning(f"LLM命名服务失败: {e}")

        return None

    def _generate_descriptive_filename(self, object_id: str, object_name: str,
                                     style_info: str, material_info: str) -> str:
        """生成描述性文件名：(风格+材质+对象名称)"""
        # 清理文件名，移除非法字符
        safe_name = object_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe_style = style_info.replace(' ', '_').replace('/', '_').replace('\\', '_')
        safe_material = material_info.replace(' ', '_').replace('/', '_').replace('\\', '_')

        # 生成文件名
        filename = f"{safe_style}_{safe_material}_{safe_name}_{object_id}.glb"
        return filename
