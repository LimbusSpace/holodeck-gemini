"""Asset generation manager for 3D object creation.

Coordinates the entire 3D asset generation pipeline: cache lookup,
SF3D generation, normalization, and metadata tracking.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..storage import SessionManager
from ..schemas import AssetMetadata, SceneObject, Vec3, AssetBatch
from .cache import ImageHashCache
from .sf3d_client import SF3DClient
from .hunyuan_3d_client import Hunyuan3DClient
from .normalizers import GLBNormalizer
from .backend_selector import BackendSelector, get_backend_selector

logger = logging.getLogger(__name__)


class AssetGenerationManager:
    """资产生成管理器 - 图生3D核心引擎.

    Coordinates 3D asset generation pipeline with caching and normalization.
    """

    def __init__(
        self,
        workspace_root: str = "workspace",
        backend_priority: Optional[str] = None,  # "hunyuan", "sf3d", None (auto-detect)
        use_backend_selector: bool = True
    ):
        """Initialize asset generation manager.

        Args:
            workspace_root: Root workspace directory
            backend_priority: Backend priority - "hunyuan", "sf3d", or None (auto-detect from env)
            use_backend_selector: Whether to use intelligent backend selection
        """
        self.workspace_root = Path(workspace_root)
        self.cache = ImageHashCache(workspace_root)
        self.normalizer = GLBNormalizer()
        self.session_manager = SessionManager()

        # Backend management
        self.use_backend_selector = use_backend_selector
        self.backend_priority = backend_priority

        if use_backend_selector:
            # Use intelligent backend selector
            self.backend_selector = get_backend_selector(str(workspace_root))
            self.sf3d_client = None  # Will be obtained from selector when needed
            self.hunyuan_3d_client = None  # Will be obtained from selector when needed
            logger.info("Using intelligent backend selection")
        else:
            # Legacy mode - manual configuration
            self.backend_selector = None
            self.sf3d_client = SF3DClient(server_address="127.0.0.1:8189")

            # Initialize Hunyuan 3D client if specified
            self.hunyuan_3d_client = None
            if backend_priority == "hunyuan":
                try:
                    import os
                    # Use the new from_env method that automatically loads .env files
                    self.hunyuan_3d_client = Hunyuan3DClient.from_env()
                    logger.info("Hunyuan 3D client initialized (auto .env loading)")
                except Exception as e:
                    logger.warning(f"Failed to initialize Hunyuan 3D client: {e}, using SF3D only")
                    self.hunyuan_3d_client = None

            logger.info("Using legacy backend configuration")

        # Generation parameters (configurable)
        self.default_foreground_ratio = 0.85
        self.default_texture_resolution = 1024
        self.default_vertex_count = -1  # Auto
        self.max_parallel_generations = 4

        # Statistics tracking
        self.generation_stats = {
            "total_generated": 0,
            "cache_hits": 0,
            "failed_generations": 0,
            "total_time_sec": 0.0
        }

    async def generate_asset(
        self,
        session_id: str,
        object_card_path: str,
        object_id: str,
        target_size_m: Optional[Vec3] = None,
        force_regenerate: bool = False,
        foreground_ratio: Optional[float] = None,
        texture_resolution: Optional[int] = None,
        vertex_count: Optional[int] = None
    ) -> AssetMetadata:
        """Generate single 3D asset from object card.

        Args:
            session_id: Current session ID
            object_card_path: Path to object card image
            object_id: Unique object identifier
            target_size_m: Target size constraints (optional)
            force_regenerate: Force regeneration even if cached
            foreground_ratio: SF3D foreground ratio (use default if None)
            texture_resolution: SF3D texture resolution (use default if None)
            vertex_count: SF3D vertex count (use default if None)

        Returns:
            AssetMetadata with generation results

        Raises:
            Exception: If generation fails
        """
        start_time = time.time()
        generation_attempt_id = f"{session_id}_{object_id}_{int(start_time)}"

        logger.info(f"Starting asset generation: {generation_attempt_id[:16]}...")

        # Validate inputs
        object_card_path = Path(object_card_path)
        if not object_card_path.exists():
            raise FileNotFoundError(f"Object card not found: {object_card_path}")

        # Set generation parameters
        foreground_ratio = foreground_ratio or self.default_foreground_ratio
        texture_resolution = texture_resolution or self.default_texture_resolution
        vertex_count = vertex_count or self.default_vertex_count

        try:
            # 1. Check cache first (unless forced)
            if not force_regenerate:
                cache_result = self.cache.lookup_cache(
                    str(object_card_path),
                    session_id,
                    foreground_ratio=foreground_ratio,
                    texture_resolution=texture_resolution,
                    vertex_count=vertex_count
                )

                if cache_result:
                    glb_path, cached_metadata = cache_result
                    self.generation_stats["cache_hits"] += 1

                    # Build AssetMetadata from cache
                    asset_metadata = AssetMetadata(
                        object_id=object_id,
                        glb_path=str(glb_path),
                        generation_status="cached",
                        generation_time_sec=cached_metadata.get("generation_time_sec", 0),
                        file_size_mb=cached_metadata.get("file_size_mb", 0),
                        vertex_count=cached_metadata.get("vertex_count", 0),
                        original_size=cached_metadata.get("original_size", Vec3()),
                        model_name="StableFast3D",
                        creation_timestamp=cached_metadata.get("creation_timestamp", datetime.now(timezone.utc).isoformat()),
                        session_id=session_id,
                        source_image_path=str(object_card_path),
                        generation_parameters={
                            "foreground_ratio": foreground_ratio,
                            "texture_resolution": texture_resolution,
                            "vertex_count": vertex_count,
                            "target_size_m": target_size_m.dict() if target_size_m else None
                        }
                    )

                    logger.info(f"Cache hit for asset {object_id}")
                    return asset_metadata

            # 2. Generate new asset
            logger.info(f"Generating new asset: {object_id}")

            # Create temporary output directory
            temp_dir = self.workspace_root / "temp" / f"{session_id}_{object_id}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Select backend based on intelligent selector or manual configuration
            generated_path = None
            generation_metadata = None
            backend_used = "sf3d"

            if self.use_backend_selector and self.backend_selector:
                # Use intelligent backend selection
                try:
                    optimal_backend = self.backend_selector.get_optimal_backend()

                    if not optimal_backend:
                        raise Exception("No 3D generation backends available")

                    logger.info(f"Intelligent backend selection: {optimal_backend} for asset {object_id}")

                    if optimal_backend == "hunyuan":
                        try:
                            hunyuan_client = self.backend_selector.get_backend_client("hunyuan")
                            logger.info(f"Using Hunyuan 3D for asset {object_id}")

                            hunyuan_result = hunyuan_client.generate_3d_from_image(
                                image_path=str(object_card_path),
                                task_id=object_id,
                                output_dir=str(temp_dir)
                            )

                            if hunyuan_result.success and hunyuan_result.local_paths:
                                generated_path = hunyuan_result.local_paths[0]
                                generation_metadata = {
                                    "generation_time": hunyuan_result.generation_time,
                                    "backend": "hunyuan-3d",
                                    "job_id": hunyuan_result.job_id,
                                    "model_urls": hunyuan_result.model_urls
                                }
                                backend_used = "hunyuan-3d"
                                logger.info(f"Hunyuan 3D generation successful for {object_id}")
                            else:
                                logger.warning(f"Hunyuan 3D failed for {object_id}, trying fallback")
                                # Try other available backends
                                fallback_backends = self.backend_selector.get_all_backends()
                                for fallback_backend in fallback_backends:
                                    if fallback_backend != "hunyuan":
                                        try:
                                            if fallback_backend == "sf3d":
                                                sf3d_client = self.backend_selector.get_backend_client("sf3d")
                                                generated_path, sf3d_metadata = await self._generate_with_sf3d_client(
                                                    sf3d_client,
                                                    str(object_card_path),
                                                    object_id,
                                                    temp_dir,
                                                    foreground_ratio,
                                                    texture_resolution,
                                                    vertex_count
                                                )
                                                generation_metadata = sf3d_metadata
                                                backend_used = "sf3d"
                                                logger.info(f"SF3D fallback successful for {object_id}")
                                                break
                                        except Exception as fallback_e:
                                            logger.warning(f"Fallback backend {fallback_backend} failed: {fallback_e}")

                        except Exception as e:
                            logger.error(f"Hunyuan 3D failed for {object_id}: {e}")
                            # Try SF3D as last resort
                            if self.backend_selector.is_backend_available("sf3d"):
                                try:
                                    sf3d_client = self.backend_selector.get_backend_client("sf3d")
                                    generated_path, sf3d_metadata = await self._generate_with_sf3d_client(
                                        sf3d_client,
                                        str(object_card_path),
                                        object_id,
                                        temp_dir,
                                        foreground_ratio,
                                        texture_resolution,
                                        vertex_count
                                    )
                                    generation_metadata = sf3d_metadata
                                    backend_used = "sf3d"
                                    logger.info(f"SF3D fallback successful for {object_id}")
                                except Exception as sf3d_e:
                                    raise Exception(f"Both Hunyuan 3D and SF3D failed: {e}, {sf3d_e}")
                            else:
                                raise

                    elif optimal_backend == "sf3d":
                        sf3d_client = self.backend_selector.get_backend_client("sf3d")
                        logger.info(f"Using SF3D for asset {object_id}")
                        generated_path, sf3d_metadata = await self._generate_with_sf3d_client(
                            sf3d_client,
                            str(object_card_path),
                            object_id,
                            temp_dir,
                            foreground_ratio,
                            texture_resolution,
                            vertex_count
                        )
                        generation_metadata = sf3d_metadata
                        backend_used = "sf3d"

                except Exception as e:
                    logger.error(f"Backend selection failed for {object_id}: {e}")
                    raise

            else:
                # Legacy mode - manual backend selection
                if self.backend_priority == "hunyuan" and self.hunyuan_3d_client:
                    try:
                        logger.info(f"Using Hunyuan 3D (legacy mode) for asset {object_id}")
                        hunyuan_result = self.hunyuan_3d_client.generate_3d_from_image(
                            image_path=str(object_card_path),
                            task_id=object_id,
                            output_dir=str(temp_dir)
                        )

                        if hunyuan_result.success and hunyuan_result.local_paths:
                            generated_path = hunyuan_result.local_paths[0]
                            generation_metadata = {
                                "generation_time": hunyuan_result.generation_time,
                                "backend": "hunyuan-3d",
                                "job_id": hunyuan_result.job_id,
                                "model_urls": hunyuan_result.model_urls
                            }
                            backend_used = "hunyuan-3d"
                            logger.info(f"Hunyuan 3D generation successful for {object_id}")
                        else:
                            logger.warning(f"Hunyuan 3D failed for {object_id}, falling back to SF3D")
                            # Fallback to SF3D
                            generated_path, sf3d_metadata = await self._generate_with_sf3d(
                                str(object_card_path),
                                object_id,
                                temp_dir,
                                foreground_ratio,
                                texture_resolution,
                                vertex_count
                            )
                            generation_metadata = sf3d_metadata
                            backend_used = "sf3d"

                    except Exception as e:
                        logger.warning(f"Hunyuan 3D failed for {object_id}: {e}, falling back to SF3D")
                        try:
                            generated_path, sf3d_metadata = await self._generate_with_sf3d(
                                str(object_card_path),
                                object_id,
                                temp_dir,
                                foreground_ratio,
                                texture_resolution,
                                vertex_count
                            )
                            generation_metadata = sf3d_metadata
                            backend_used = "sf3d"
                        except Exception as sf3d_e:
                            raise Exception(f"Both Hunyuan 3D and SF3D failed: {e}, {sf3d_e}")

                else:
                    # Default to SF3D
                    logger.info(f"Using SF3D (default) for asset {object_id}")
                    generated_path, sf3d_metadata = await self._generate_with_sf3d(
                        str(object_card_path),
                        object_id,
                        temp_dir,
                        foreground_ratio,
                        texture_resolution,
                        vertex_count
                    )
                    generation_metadata = sf3d_metadata
                    backend_used = "sf3d"

            # 3. Normalize asset if size constraints provided
            normalized_path = generated_path
            if target_size_m:
                normalized_path, norm_metadata = self.normalizer.normalize_asset(
                    Path(generated_path),
                    target_size_m=(target_size_m.x, target_size_m.y, target_size_m.z),
                    output_path=Path(temp_dir) / f"{object_id}_normalized.glb"
                )
                logger.info(f"Normalized asset for {object_id}: {norm_metadata.get('operations_applied', [])}")

            # 4. Move to final session assets directory
            final_dir = self.workspace_root / "sessions" / session_id / "assets"
            final_dir.mkdir(parents=True, exist_ok=True)

            final_glb_path = final_dir / f"{object_id}.glb"
            import shutil
            shutil.move(str(normalized_path), str(final_glb_path))

            # 5. Build AssetMetadata
            mesh_info = self.normalizer.extract_mesh_info(final_glb_path)
            file_size_mb = final_glb_path.stat().st_size / (1024 * 1024)

            # Determine model name based on backend
            model_name = "Hunyuan3D" if backend_used == "hunyuan-3d" else "StableFast3D"
            generation_time = generation_metadata.get("generation_time", 0)

            asset_metadata = AssetMetadata(
                object_id=object_id,
                glb_path=str(final_glb_path),
                generation_status="success",
                generation_time_sec=generation_time,
                file_size_mb=round(file_size_mb, 2),
                vertex_count=mesh_info.get("vertex_count", 0),
                original_size=target_size_m or Vec3(),
                model_name=model_name,
                creation_timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                source_image_path=str(object_card_path),
                generation_parameters={
                    "backend": backend_used,
                    "foreground_ratio": foreground_ratio if backend_used == "sf3d" else None,
                    "texture_resolution": texture_resolution if backend_used == "sf3d" else None,
                    "vertex_count": vertex_count if backend_used == "sf3d" else None,
                    "target_size_m": target_size_m.dict() if target_size_m else None,
                    "hunyuan_job_id": generation_metadata.get("job_id") if backend_used == "hunyuan-3d" else None
                }
            )

            # 6. Store in cache
            cache_metadata = {
                "generation_time_sec": generation_time,
                "file_size_mb": round(file_size_mb, 2),
                "vertex_count": mesh_info.get("vertex_count", 0),
                "original_size": target_size_m.dict() if target_size_m else Vec3().dict(),
                "model_name": model_name,
                "creation_timestamp": asset_metadata.creation_timestamp,
                "generation_parameters": asset_metadata.generation_parameters
            }

            self.cache.store_in_cache(
                str(object_card_path),
                str(final_glb_path),
                cache_metadata,
                session_id,
                foreground_ratio=foreground_ratio,
                texture_resolution=texture_resolution,
                vertex_count=vertex_count
            )

            # 7. Update statistics
            self.generation_stats["total_generated"] += 1
            end_time = time.time()
            self.generation_stats["total_time_sec"] += end_time - start_time

            # 8. Update session status
            await self._update_session_progress(session_id)

            # 9. Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")

            logger.info(f"Successfully generated asset {object_id}: {final_glb_path}")
            return asset_metadata

        except Exception as e:
            self.generation_stats["failed_generations"] += 1
            logger.error(f"Failed to generate asset {object_id}: {e}")

            # Return failed metadata
            return AssetMetadata(
                object_id=object_id,
                glb_path="",
                generation_status="failed",
                generation_time_sec=0,
                file_size_mb=0,
                vertex_count=0,
                original_size=target_size_m or Vec3(),
                model_name="StableFast3D",
                creation_timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id,
                source_image_path=str(object_card_path),
                generation_parameters={
                    "foreground_ratio": foreground_ratio,
                    "texture_resolution": texture_resolution,
                    "vertex_count": vertex_count
                },
                error_message=str(e)
            )

    async def _generate_with_sf3d(
        self,
        object_card_path: str,
        object_id: str,
        output_dir: Path,
        foreground_ratio: float,
        texture_resolution: int,
        vertex_count: int
    ) -> Tuple[str, Dict]:
        """Generate asset using SF3D client.

        Args:
            object_card_path: Path to object card
            object_id: Object identifier
            output_dir: Output directory
            foreground_ratio: SF3D parameters
            texture_resolution: SF3D texture resolution
            vertex_count: SF3D vertex count

        Returns:
            Tuple of (glb_path, metadata)
        """
        try:
            # Test SF3D availability
            if not await self.sf3d_client.test_sf3d_availability():
                raise Exception("SF3D nodes not available in ComfyUI")

            # Generate 3D asset
            glb_path, metadata = await self.sf3d_client.generate_3d_asset(
                image_path=object_card_path,
                foreground_ratio=foreground_ratio,
                texture_resolution=texture_resolution,
                vertex_count=vertex_count,
                filename_prefix=f"{object_id}_sf3d",
                output_dir=output_dir
            )

            return glb_path, metadata

        except Exception as e:
            logger.error(f"SF3D generation failed for {object_id}: {e}")
            raise

    async def batch_generate_assets(
        self,
        session_id: str,
        objects: List[Dict[str, str]],
        target_size_constraints: Optional[Dict[str, Vec3]] = None,
        max_parallel: Optional[int] = None
    ) -> AssetBatch:
        """Generate multiple assets in parallel.

        Args:
            session_id: Session ID
            objects: List of object dictionaries with 'object_id' and 'card_path'
            target_size_constraints: Optional size constraints per object
            max_parallel: Maximum parallel generations (override default)

        Returns:
            AssetBatch with all generation results
        """
        start_time = time.time()
        batch_id = f"batch_{session_id}_{int(start_time)}"

        logger.info(f"Starting batch generation: {batch_id[:16]}... ({len(objects)} assets)")

        max_parallel = max_parallel or self.max_parallel_generations
        target_size_constraints = target_size_constraints or {}

        # Create semaphore to limit parallel executions
        semaphore = asyncio.Semaphore(max_parallel)

        async def generate_single_asset(object_info):
            async with semaphore:
                object_id = object_info["object_id"]
                card_path = object_info["card_path"]
                target_size = target_size_constraints.get(object_id)

                return await self.generate_asset(
                    session_id=session_id,
                    object_card_path=card_path,
                    object_id=object_id,
                    target_size_m=target_size,
                    force_regenerate=False
                )

        # Execute all generations in parallel with semaphore control
        tasks = [generate_single_asset(obj) for obj in objects]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Separate successes and failures
        successful_assets = []
        failed_assets = []

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_assets.append({
                    "object_id": objects[i]["object_id"],
                    "error_message": str(result)
                })
            else:
                if result.generation_status == "success" or result.generation_status == "cached":
                    successful_assets.append(result)
                else:
                    failed_assets.append({
                        "object_id": result.object_id,
                        "error_message": result.error_message or "Generation failed"
                    })

        # Build batch result
        end_time = time.time()
        batch_result = AssetBatch(
            batch_id=batch_id,
            scene_session_id=session_id,
            total_assets=len(objects),
            successful_assets=successful_assets,
            failed_assets=failed_assets,
            total_time_sec=round(end_time - start_time, 2),
            success_rate=len(successful_assets) / len(objects),
            cache_hits=sum(1 for a in successful_assets if a.generation_status == "cached"),
            new_generations=sum(1 for a in successful_assets if a.generation_status == "success")
        )

        logger.info(
            f"Batch generation completed: {batch_id[:16]}... "
            f"({len(successful_assets)}/{len(objects)} successful, {batch_result.cache_hits} cached)"
        )

        return batch_result

    async def _update_session_progress(self, session_id: str):
        """Update session progress information.

        Args:
            session_id: Session ID to update
        """
        try:
            # Get current session
            session = await self.session_manager.load_session(session_id)
            if session:
                # Update progress based on generation stats
                total_attempts = self.generation_stats["total_generated"] + self.generation_stats["cache_hits"]
                if total_attempts > 0:
                    cache_hit_rate = self.generation_stats["cache_hits"] / total_attempts
                else:
                    cache_hit_rate = 0

                await self.session_manager.update_session_status(
                    session_id,
                    current_step="asset_generation",
                    progress_percentage=min(100, (session.current_step_progress or 0) + 10),
                    additional_data={
                        "generation_stats": self.generation_stats,
                        "cache_hit_rate": round(cache_hit_rate, 2) * 100
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to update session progress for {session_id}: {e}")

    def get_generation_statistics(self) -> Dict:
        """Get current generation statistics.

        Returns:
            Statistics dictionary
        """
        stats = self.generation_stats.copy()
        cache_stats = self.cache.get_cache_stats()

        # Calculate averages
        if stats["total_generated"] > 0:
            stats["average_time_sec"] = stats["total_time_sec"] / stats["total_generated"]
        else:
            stats["average_time_sec"] = 0

        # Merge cache statistics
        stats["cache_stats"] = cache_stats

        return stats

    async def cleanup_cache_if_needed(self):
        """Trigger cache cleanup if size limits exceeded."""
        self.cache._cleanup_cache_if_needed()
        logger.info("Cache cleanup completed")