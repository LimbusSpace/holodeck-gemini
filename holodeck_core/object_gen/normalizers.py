"""GLB normalization utilities for 3D assets.

Provides tools to normalize, validate, and standardize GLB files for
consistent handling in the Holodeck system.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logging.warning("trimesh not available. Some GLB normalization features will be limited.")

logger = logging.getLogger(__name__)


class GLBNormalizer:
    """GLB归一化工具 - Normalizes GLB files for consistent handling."""

    def __init__(self):
        """Initialize GLB normalizer."""
        self.trimesh_available = TRIMESH_AVAILABLE

    def validate_glb(self, glb_path: Path) -> Dict[str, Any]:
        """Validate GLB file structure and extract basic metadata.

        Args:
            glb_path: Path to GLB file

        Returns:
            Validation report dictionary
        """
        glb_path = Path(glb_path)
        validation_report = {
            "is_valid": False,
            "file_size_mb": 0,
            "vertex_count": 0,
            "triangle_count": 0,
            "materials": 0,
            "errors": [],
            "warnings": []
        }

        if not glb_path.exists():
            validation_report["errors"].append(f"GLB file not found: {glb_path}")
            return validation_report

        # Check file size
        file_size_mb = glb_path.stat().st_size / (1024 * 1024)
        validation_report["file_size_mb"] = round(file_size_mb, 2)

        if file_size_mb > 100:  # Warning for large files
            validation_report["warnings"].append(f"Large file size: {file_size_mb:.1f}MB")

        if self.trimesh_available:
            try:
                # Load and analyze mesh
                scene = trimesh.load(str(glb_path))

                if hasattr(scene, 'geometry'):
                    # Count vertices and triangles
                    for name, geometry in scene.geometry.items():
                        if hasattr(geometry, 'vertices'):
                            validation_report["vertex_count"] += len(geometry.vertices)
                        if hasattr(geometry, 'faces'):
                            validation_report["triangle_count"] += len(geometry.faces)

                    validation_report["is_valid"] = True
                    validation_report["materials"] = len(set(
                        g.visual.material for g in scene.geometry.values()
                        if hasattr(g, 'visual') and g.visual.material is not None
                    ))
                else:
                    validation_report["errors"].append("No geometry found in GLB")

            except Exception as e:
                validation_report["errors"].append(f"Failed to parse GLB with trimesh: {e}")
        else:
            # Fallback validation without trimesh
            validation_report["warnings"].append("trimesh not available - limited validation")
            validation_report["is_valid"] = True  # Basic check that file exists

        return validation_report

    def normalize_asset(
        self,
        glb_path: Path,
        target_size_m: Optional[Tuple[float, float, float]] = None,
        pivot_adjustment: Optional[Tuple[float, float, float]] = (0.5, 0.5, 0.0),
        output_path: Optional[Path] = None,
        max_vertex_count: int = 10000
    ) -> Tuple[Path, Dict[str, Any]]:
        """Normalize GLB asset with size constraints and pivot adjustment.

        Args:
            glb_path: Input GLB file path
            target_size_m: Target dimensions in meters (x, y, z)
            pivot_adjustment: Pivot point adjustment (x, y, z) normalized 0-1
            output_path: Output file path (auto-generated if None)
            max_vertex_count: Maximum vertex count for optimization

        Returns:
            Tuple of (normalized_path, normalization_metadata)
        """
        glb_path = Path(glb_path)

        # Validate input file
        validation = self.validate_glb(glb_path)
        if not validation["is_valid"]:
            raise ValueError(f"Invalid GLB file: {validation['errors']}")

        # Generate output path
        if output_path is None:
            output_path = glb_path.parent / f"{glb_path.stem}_normalized.glb"

        normalization_metadata = {
            "original_path": str(glb_path),
            "normalized_path": str(output_path),
            "original_vertex_count": validation["vertex_count"],
            "original_size_mb": validation["file_size_mb"],
            "target_size_m": target_size_m,
            "pivot_adjustment": pivot_adjustment,
            "operations_applied": []
        }

        if self.trimesh_available:
            # Use trimesh for detailed processing
            processed_scene = self._process_with_trimesh(
                glb_path, target_size_m, pivot_adjustment, max_vertex_count,
                normalization_metadata
            )

            # Export normalized GLB
            try:
                processed_scene.export(str(output_path))
                normalization_metadata["operations_applied"].append("trimesh_export")
                logger.info(f"Successfully normalized GLB: {glb_path} -> {output_path}")
            except Exception as e:
                # Fallback: copy original file
                import shutil
                shutil.copy2(glb_path, output_path)
                normalization_metadata["operations_applied"].append("fallback_copy")
                logger.warning(f"Failed to export with trimesh, copied original: {e}")
        else:
            # Fallback: just copy the file
            import shutil
            shutil.copy2(glb_path, output_path)
            normalization_metadata["operations_applied"].append("simple_copy_no_trimesh")
            logger.warning("trimesh not available - copying original file without normalization")

        # Validate output
        output_validation = self.validate_glb(output_path)
        normalization_metadata.update({
            "final_vertex_count": output_validation["vertex_count"],
            "final_size_mb": output_validation["file_size_mb"],
            "is_valid": output_validation["is_valid"],
            "errors": output_validation["errors"],
            "warnings": output_validation["warnings"]
        })

        return output_path, normalization_metadata

    def _process_with_trimesh(
        self,
        glb_path: Path,
        target_size_m: Optional[Tuple[float, float, float]],
        pivot_adjustment: Optional[Tuple[float, float, float]],
        max_vertex_count: int,
        metadata: Dict[str, Any]
    ):
        """Process GLB using trimesh for detailed normalization.

        Args:
            glb_path: Input GLB file
            target_size_m: Target dimensions
            pivot_adjustment: Pivot adjustment
            max_vertex_count: Max vertex count
            metadata: Metadata dict to update

        Returns:
            Processed trimesh scene
        """
        scene = trimesh.load(str(glb_path))

        # Combine all geometries into single mesh if needed
        if hasattr(scene, 'geometry') and len(scene.geometry) > 1:
            meshes = list(scene.geometry.values())
            combined_mesh = trimesh.util.concatenate(meshes)
            scene.geometry.clear()
            scene.geometry["combined"] = combined_mesh
            metadata["operations_applied"].append("combine_meshes")

        # Get the main mesh
        if hasattr(scene, 'geometry') and scene.geometry:
            mesh = list(scene.geometry.values())[0]
        else:
            raise ValueError("No mesh geometry found in GLB")

        original_size_mb = glb_path.stat().st_size / (1024 * 1024)

        # 1. Vertex count reduction if needed
        if len(mesh.vertices) > max_vertex_count:
            ratio = max_vertex_count / len(mesh.vertices)
            simplified = mesh.simplify_quadric_decimation(
                face_count=int(len(mesh.faces) * ratio)
            )
            scene.geometry.clear()
            scene.geometry["simplified"] = simplified
            metadata["operations_applied"].append(f"vertex_reduce_{max_vertex_count}")
            logger.info(f"Reduced vertices from {len(mesh.vertices)} to {len(simplified.vertices)}")

        # Refresh mesh reference
        mesh = list(scene.geometry.values())[0]

        # 2. Size normalization
        if target_size_m:
            # Get current bounds
            bounds = mesh.bounds
            if bounds is not None:
                current_size = bounds[1] - bounds[0]  # Size in each dimension

                # Calculate scale factors
                scale_factors = []
                for i, target_dim in enumerate(target_size_m):
                    if current_size[i] > 0 and target_dim > 0:
                        scale_factor = target_dim / current_size[i]
                        scale_factors.append(scale_factor)

                if scale_factors:
                    # Apply uniform scaling if needed
                    scale_factors = [min(scale_factors)] * 3  # Uniform scaling
                    mesh.apply_scale(scale_factors)
                    metadata["operations_applied"].append(f"scale_{scale_factors[0]:.3f}")
                    logger.info(f"Scaled mesh by {scale_factors[0]:.3f}")

        # 3. Pivot point adjustment
        if pivot_adjustment:
            bounds = mesh.bounds
            if bounds is not None:
                # Calculate desired origin based on pivot adjustment (0-1 normalized)
                min_bound, max_bound = bounds
                target_origin = min_bound + (max_bound - min_bound) * pivot_adjustment

                # Apply transformation to move mesh
                transform = trimesh.transformations.translation_matrix(-target_origin)
                mesh.apply_transform(transform)
                metadata["operations_applied"].append(f"pivot_{pivot_adjustment}")
                logger.info(f"Adjusted pivot to {target_origin}")

        return scene

    def extract_mesh_info(self, glb_path: Path) -> Dict[str, Any]:
        """Extract detailed mesh information from GLB file.

        Args:
            glb_path: Path to GLB file

        Returns:
            Mesh information dictionary
        """
        glb_path = Path(glb_path)
        mesh_info = {
            "file_path": str(glb_path),
            "file_size_mb": 0,
            "vertex_count": 0,
            "triangle_count": 0,
            "edge_count": 0,
            "materials": 0,
            "textures": 0,
            "bounds": None,
            "center": None,
            "volume": 0.0,
            "surface_area": 0.0
        }

        if not glb_path.exists():
            return mesh_info

        mesh_info["file_size_mb"] = round(glb_path.stat().st_size / (1024 * 1024), 2)

        if self.trimesh_available:
            try:
                scene = trimesh.load(str(glb_path))

                if hasattr(scene, 'geometry'):
                    for name, geometry in scene.geometry.items():
                        if hasattr(geometry, 'vertices'):
                            mesh_info["vertex_count"] += len(geometry.vertices)
                        if hasattr(geometry, 'faces'):
                            mesh_info["triangle_count"] += len(geometry.faces)
                        if hasattr(geometry, 'edges'):
                            mesh_info["edge_count"] += len(geometry.edges)
                        if hasattr(geometry, 'mass'):
                            mesh_info["volume"] += geometry.mass if hasattr(geometry.mass, '__float__') else 0.0
                        if hasattr(geometry, 'area'):
                            mesh_info["surface_area"] += geometry.area if hasattr(geometry.area, '__float__') else 0.0
                        if hasattr(geometry, 'visual') and geometry.visual.material:
                            mesh_info["materials"] += 1

                    # Get bounds and center for primary mesh
                    if scene.geometry:
                        primary_mesh = list(scene.geometry.values())[0]
                        if hasattr(primary_mesh, 'bounds') and primary_mesh.bounds is not None:
                            mesh_info["bounds"] = primary_mesh.bounds.tolist()
                            mesh_info["center"] = primary_mesh.centroid.tolist()

            except Exception as e:
                logger.error(f"Failed to extract mesh info from {glb_path}: {e}")

        return mesh_info

    def create_placeholder_cube(self, size_m: float = 1.0, output_path: Optional[Path] = None) -> Path:
        """Create a simple placeholder cube GLB for missing assets.

        Args:
            size_m: Cube size in meters
            output_path: Output path (auto-generated if None)

        Returns:
            Path to created placeholder GLB
        """
        if self.trimesh_available:
            # Create cube with trimesh
            cube = trimesh.creation.box(extents=[size_m, size_m, size_m])

            if output_path is None:
                output_path = Path.cwd() / "workspace" / "temp" / f"placeholder_{size_m}m_cube.glb"

            output_path.parent.mkdir(parents=True, exist_ok=True)
            cube.export(str(output_path))
            logger.info(f"Created placeholder cube: {output_path}")
            return output_path
        else:
            # Fallback: Create placeholder using Blender (if available)
            return self._create_placeholder_with_blender(size_m, output_path)

    def _create_placeholder_with_blender(self, size_m: float, output_path: Optional[Path]) -> Path:
        """Create placeholder using Blender as fallback.

        Args:
            size_m: Cube size in meters
            output_path: Output path

        Returns:
            Path to created placeholder
        """
        if output_path is None:
            output_path = Path.cwd() / "workspace" / "temp" / f"placeholder_{size_m}m_cube.glb"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Try to use Blender if available
        try:
            blender_script = f"""
import bpy
import math

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create cube
bpy.ops.mesh.primitive_cube_add(size={size_m})
cube = bpy.context.active_object

# Apply default material
bpy.ops.material.new()
mat = bpy.data.materials["Material"]
cube.data.materials.append(mat)

# Export as GLB
bpy.ops.export_scene.gltf(filepath="{output_path}")
"""

            # Run Blender with script
            result = subprocess.run(
                ["blender", "--background", "--python-expr", blender_script],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"Created placeholder cube with Blender: {output_path}")
                return output_path
            else:
                raise Exception(f"Blender error: {result.stderr}")

        except Exception as e:
            logger.error(f"Failed to create placeholder with Blender: {e}")
            # Last resort: create empty file as placeholder
            output_path.write_bytes(b'')
            logger.warning(f"Created empty placeholder file: {output_path}")
            return output_path