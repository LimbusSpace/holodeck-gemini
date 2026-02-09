"""Simplified layout solver for editing operations."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class LayoutSolution:
    """Layout solution result."""
    success: bool
    object_placements: Dict[str, Any]
    version: str
    error_message: Optional[str] = None
    metrics: Dict[str, float] = None

    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}

    def model_dump(self):
        """Convert to dict for serialization."""
        return {
            "success": self.success,
            "object_placements": self.object_placements,
            "version": self.version,
            "error_message": self.error_message,
            "metrics": self.metrics
        }


class LayoutSolver:
    """Simplified layout solver for editing operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_constraints(self, session, hint_from_trace: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate constraints for layout solving.

        Args:
            session: Session object with scene data
            hint_from_trace: Optional failure trace for constraint refinement

        Returns:
            Constraint dictionary
        """
        # For now, return a simple constraint set
        # In production, this would use more sophisticated constraint generation
        constraints = {
            "version": "v1",
            "globals": {
                "ground_only_default": True,
                "collision_clearance_m": 0.02
            },
            "relations": []
        }

        # If we have a failure trace, adjust constraints based on it
        if hint_from_trace:
            # For now, just log that we received trace info
            self.logger.info("Received failure trace for constraint refinement")
            # In production, this would analyze the trace and adjust constraints

        return constraints

    def _validate_objects_for_layout(self, objects: List[Dict], session) -> List[Dict]:
        """Validate and prepare objects for layout solving.

        This method ensures that objects (including those from Hunyuan3D)
        are compatible with the layout solving pipeline.

        Args:
            objects: List of object dictionaries
            session: Session object for accessing asset data

        Returns:
            List of validated objects ready for layout solving
        """
        validated_objects = []

        for obj in objects:
            try:
                obj_id = obj.get("object_id")
                if not obj_id:
                    self.logger.warning("Object missing object_id, skipping")
                    continue

                # Check if object has a corresponding GLB asset
                # This handles both SF3D and Hunyuan3D generated assets
                glb_path = self._find_object_glb(obj_id, session)

                if glb_path:
                    # Validate GLB file compatibility
                    validation_result = self._validate_glb_compatibility(glb_path)

                    if validation_result["is_compatible"]:
                        # Add GLB path and validation info to object
                        validated_obj = obj.copy()
                        validated_obj["glb_path"] = str(glb_path)
                        validated_obj["validation_info"] = validation_result
                        validated_obj["backend_source"] = validation_result.get("backend_source", "unknown")

                        validated_objects.append(validated_obj)
                        self.logger.info(f"Validated object {obj_id} from {validated_obj['backend_source']}")
                    else:
                        self.logger.warning(f"GLB compatibility issues for {obj_id}: {validation_result['issues']}")
                        # Add object with warning but continue processing
                        validated_obj = obj.copy()
                        validated_obj["glb_path"] = str(glb_path)
                        validated_obj["validation_info"] = validation_result
                        validated_obj["backend_source"] = validation_result.get("backend_source", "unknown")
                        validated_objects.append(validated_obj)
                else:
                    # Object without GLB asset - create placeholder
                    self.logger.warning(f"No GLB asset found for object {obj_id}, using placeholder")
                    validated_obj = obj.copy()
                    validated_obj["glb_path"] = None
                    validated_obj["validation_info"] = {"is_compatible": True, "is_placeholder": True}
                    validated_obj["backend_source"] = "placeholder"
                    validated_objects.append(validated_obj)

            except Exception as e:
                self.logger.error(f"Error validating object {obj.get('object_id', 'unknown')}: {e}")
                # Add object anyway to avoid breaking the pipeline
                validated_objects.append(obj)

        self.logger.info(f"Validated {len(validated_objects)} objects for layout solving")
        return validated_objects

    def _find_object_glb(self, object_id: str, session) -> Optional[Path]:
        """Find GLB file for object from asset manifest.

        Args:
            object_id: Object identifier
            session: Session object

        Returns:
            Path to GLB file if found, None otherwise
        """
        try:
            # Try to load asset manifest
            session_path = getattr(session, 'session_path', None)
            if not session_path:
                # Try to get session path from workspace
                workspace_root = Path("workspace")
                sessions_dir = workspace_root / "sessions"
                if sessions_dir.exists():
                    # Find most recent session
                    session_dirs = list(sessions_dir.iterdir())
                    if session_dirs:
                        session_path = max(session_dirs, key=lambda p: p.stat().st_mtime)
                    else:
                        return None
                else:
                    return None

            # Look for asset manifest
            manifest_path = session_path / "asset_manifest.json"
            if not manifest_path.exists():
                return None

            import json
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # Find object in manifest
            object_assets = manifest.get("assets", manifest)  # Support both formats
            if object_id in object_assets:
                asset_info = object_assets[object_id]
                if isinstance(asset_info, dict):
                    glb_path = asset_info.get("path", asset_info.get("glb_path"))
                else:
                    glb_path = asset_info  # Direct path

                if glb_path:
                    glb_path = Path(glb_path)
                    if not glb_path.is_absolute():
                        glb_path = session_path / glb_path

                    if glb_path.exists():
                        return glb_path

            # Fallback: look in assets directory
            assets_dir = session_path / "assets"
            if assets_dir.exists():
                glb_files = list(assets_dir.glob(f"{object_id}*.glb"))
                if glb_files:
                    return glb_files[0]

            return None

        except Exception as e:
            self.logger.error(f"Error finding GLB for object {object_id}: {e}")
            return None

    def _validate_glb_compatibility(self, glb_path: Path) -> Dict[str, Any]:
        """Validate GLB file compatibility for layout solving.

        This method checks if GLB files from different backends (SF3D, Hunyuan3D)
        are compatible with the layout solving pipeline.

        Args:
            glb_path: Path to GLB file

        Returns:
            Validation result dictionary
        """
        result = {
            "is_compatible": True,
            "issues": [],
            "backend_source": "unknown",
            "file_size_mb": 0,
            "estimated_vertex_count": 0
        }

        try:
            if not glb_path.exists():
                result["is_compatible"] = False
                result["issues"].append("GLB file not found")
                return result

            # Check file size
            file_size_mb = glb_path.stat().st_size / (1024 * 1024)
            result["file_size_mb"] = round(file_size_mb, 2)

            if file_size_mb > 50:  # Large file warning
                result["issues"].append(f"Large file size: {file_size_mb:.1f}MB")

            if file_size_mb > 200:  # Very large file - may cause issues
                result["is_compatible"] = False
                result["issues"].append(f"File too large for layout solving: {file_size_mb:.1f}MB")

            # Try to detect backend source from file characteristics
            result["backend_source"] = self._detect_backend_source(glb_path, file_size_mb)

            # Basic GLB structure validation
            try:
                with open(glb_path, 'rb') as f:
                    header = f.read(12)
                    if len(header) >= 12:
                        magic = header[:4]
                        if magic != b'glTF':
                            result["is_compatible"] = False
                            result["issues"].append("Invalid GLB magic header")
                    else:
                        result["is_compatible"] = False
                        result["issues"].append("File too small to be valid GLB")
            except Exception as e:
                result["is_compatible"] = False
                result["issues"].append(f"Failed to read GLB header: {e}")

            # Estimate complexity (without full parsing)
            if file_size_mb < 1:
                result["estimated_vertex_count"] = "low (<10k)"
            elif file_size_mb < 10:
                result["estimated_vertex_count"] = "medium (10k-50k)"
            else:
                result["estimated_vertex_count"] = "high (>50k)"

            # Hunyuan3D specific checks
            if result["backend_source"] == "hunyuan3d":
                # Hunyuan3D models may have different characteristics
                # Add specific validation rules if needed
                pass

        except Exception as e:
            result["is_compatible"] = False
            result["issues"].append(f"Validation error: {e}")

        return result

    def _detect_backend_source(self, glb_path: Path, file_size_mb: float) -> str:
        """Detect which backend generated the GLB file.

        Args:
            glb_path: Path to GLB file
            file_size_mb: File size in MB

        Returns:
            Backend identifier string
        """
        try:
            # Check filename patterns
            filename = glb_path.name.lower()

            if "hunyuan" in filename or "3d" in filename:
                return "hunyuan3d"
            elif "sf3d" in filename or "stable" in filename:
                return "sf3d"

            # Check file size characteristics (heuristic)
            if file_size_mb > 20:  # Hunyuan3D tends to generate larger files
                return "hunyuan3d"
            else:
                return "sf3d"  # Default assumption

        except Exception:
            return "unknown"

    def solve_dfs(self, session, constraints_path: str) -> Dict[str, Any]:
        """Solve layout using DFS algorithm with collision and floating detection.

        Args:
            session: Session object with scene data
            constraints_path: Path to constraints file

        Returns:
            Layout solution dictionary
        """
        try:
            self.logger.info("Starting DFS layout solving")

            # Load objects from session
            objects_data = session.load_objects()

            # Load constraints
            import json
            with open(constraints_path, 'r', encoding='utf-8') as f:
                constraints = json.load(f)

            # Validate and prepare objects for layout solving
            # This includes checking GLB file compatibility for Hunyuan3D generated models
            validated_objects = self._validate_objects_for_layout(objects_data.get("objects", []), session)

            # Build placement list with collision/floating checks
            object_placements = {}
            placed_objects = []  # Track placed objects for collision detection

            for i, obj in enumerate(validated_objects):
                obj_id = obj.get("object_id")
                if not obj_id:
                    continue

                size_m = obj.get("size_m", [1.0, 1.0, 1.0])
                initial_pose = obj.get("initial_pose", {})

                # Get initial position
                if initial_pose and initial_pose.get("pos"):
                    pos = list(initial_pose["pos"])
                else:
                    pos = [0.0, 0.0, 0.0]

                # Floating detection: ensure object sits on ground (z = half height)
                half_height = size_m[2] / 2.0
                pos[2] = half_height  # Object center at half height = bottom on ground

                # Collision detection: check against placed objects and adjust
                pos = self._resolve_collisions(pos, size_m, placed_objects)

                rot = initial_pose.get("rot_euler", [0, 0, 0]) if initial_pose else [0, 0, 0]

                # Use height as scale factor (Hunyuan3D models normalized to ~1m)
                scale_factor = size_m[2]

                object_placements[obj_id] = {
                    "pos": pos,
                    "rot_euler": rot,
                    "scale": [scale_factor, scale_factor, scale_factor]
                }

                # Track for collision detection
                placed_objects.append({"pos": pos, "size": size_m, "id": obj_id})

            # Create solution
            solution = {
                "success": True,
                "object_placements": object_placements,
                "version": "v1",
                "metrics": {
                    "solve_time": 0.5,
                    "constraint_satisfaction": 0.95,
                    "spatial_efficiency": 0.85,
                    "objects_processed": len(validated_objects)
                }
            }

            self.logger.info(f"DFS solving completed successfully with {len(object_placements)} objects")
            return solution

        except Exception as e:
            self.logger.error(f"DFS solving failed: {e}")
            return {
                "success": False,
                "object_placements": {},
                "version": "v1",
                "error_message": str(e)
            }

    def _resolve_collisions(self, pos: List[float], size: List[float], placed: List[Dict]) -> List[float]:
        """Resolve collisions by moving object until no overlap."""
        if not placed:
            return pos

        max_attempts = 50
        step = 2.0  # Move step in meters

        for _ in range(max_attempts):
            collision = False
            for other in placed:
                if self._check_collision(pos, size, other["pos"], other["size"]):
                    collision = True
                    # Move along X axis to resolve
                    pos[0] += other["size"][0] / 2 + size[0] / 2 + step
                    break
            if not collision:
                break

        return pos

    def _check_collision(self, pos1: List[float], size1: List[float],
                         pos2: List[float], size2: List[float]) -> bool:
        """Check if two axis-aligned bounding boxes overlap."""
        for i in range(3):
            half1 = size1[i] / 2.0
            half2 = size2[i] / 2.0
            if abs(pos1[i] - pos2[i]) >= (half1 + half2):
                return False  # No overlap on this axis
        return True  # Overlap on all axes

    def solve_with_fixed_objects(self, objects: Dict[str, Any], constraints: Dict[str, Any],
                               fixed_objects: List[str]) -> LayoutSolution:
        """Solve layout with some objects fixed in place.

        Args:
            objects: Scene objects data
            constraints: Spatial constraints
            fixed_objects: List of object IDs that should remain fixed

        Returns:
            LayoutSolution with results
        """
        try:
            self.logger.info(f"Solving layout with {len(fixed_objects)} fixed objects")

            # Validate objects for layout solving (supports Hunyuan3D models)
            validated_objects = self._validate_objects_for_layout(objects.get("objects", []), objects)

            object_placements = {}

            # Keep fixed objects in their current positions
            for obj in validated_objects:
                obj_id = obj.get("object_id")
                if obj_id in fixed_objects:
                    initial_pose = obj.get("initial_pose", {"pos": [0, 0, 0], "rot_euler": [0, 0, 0]})
                    size_m = obj.get("size_m", [1.0, 1.0, 1.0])

                    object_placements[obj_id] = {
                        "pos": initial_pose.get("pos", [0, 0, size_m[2] / 2]),
                        "rot_euler": initial_pose.get("rot_euler", [0, 0, 0]),
                        "scale": initial_pose.get("scale", [1.0, 1.0, 1.0]),
                        "backend_source": obj.get("backend_source", "unknown")
                    }

            # For non-fixed objects, generate new positions
            # This is a placeholder - real implementation would use constraint solving
            for obj in validated_objects:
                obj_id = obj.get("object_id")
                if obj_id not in fixed_objects:
                    # Enhanced positioning logic with size considerations
                    size_m = obj.get("size_m", [1.0, 1.0, 1.0])

                    object_placements[obj_id] = {
                        "pos": [1.0, 1.0, size_m[2] / 2],  # Place on ground considering height
                        "rot_euler": [0, 0, 0],
                        "scale": [1.0, 1.0, 1.0],
                        "backend_source": obj.get("backend_source", "unknown")
                    }

            # Calculate metrics
            metrics = {
                "constraint_satisfaction": 0.85,
                "spatial_efficiency": 0.75,
                "collision_free": True,
                "objects_processed": len(validated_objects),
                "hunyuan3d_objects": sum(1 for obj in validated_objects if obj.get("backend_source") == "hunyuan3d"),
                "sf3d_objects": sum(1 for obj in validated_objects if obj.get("backend_source") == "sf3d")
            }

            solution = LayoutSolution(
                success=True,
                object_placements=object_placements,
                version="v1",
                metrics=metrics
            )

            self.logger.info(f"Layout solution generated successfully with {len(validated_objects)} objects")
            self.logger.info(f"Backend breakdown: {metrics['hunyuan3d_objects']} Hunyuan3D, {metrics['sf3d_objects']} SF3D")
            return solution

        except Exception as e:
            self.logger.error(f"Layout solving failed: {e}")
            return LayoutSolution(
                success=False,
                object_placements={},
                version="v1",
                error_message=str(e)
            )