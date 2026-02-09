"""Camera management for Blender scene rendering.

Implements camera pose generation and validation based on HOLODECK 2.0:
- Automatic camera pose generation for scene coverage
- Camera constraint validation
- View optimization for different scene types
"""

import math
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from holodeck_core.schemas.rendering import CameraPose
from holodeck_core.schemas.scene_objects import Vec3


@dataclass
class CameraPreset:
    """Camera preset configuration."""
    name: str
    position_offset: Vec3
    rotation_base: Vec3
    fov: float
    target_height: float


class CameraManager:
    """Manages camera poses for scene rendering."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Define camera presets
        self.camera_presets = {
            "wide": CameraPreset(
                name="Wide Overview",
                position_offset=Vec3(x=-3.0, y=-3.0, z=2.5),
                rotation_base=Vec3(x=60.0, y=0.0, z=45.0),
                fov=45.0,
                target_height=0.8
            ),
            "top": CameraPreset(
                name="Top View",
                position_offset=Vec3(x=0.0, y=0.0, z=4.0),
                rotation_base=Vec3(x=90.0, y=0.0, z=0.0),
                fov=50.0,
                target_height=0.0
            ),
            "front": CameraPreset(
                name="Front View",
                position_offset=Vec3(x=0.0, y=-4.0, z=1.5),
                rotation_base=Vec3(x=15.0, y=0.0, z=0.0),
                fov=40.0,
                target_height=0.8
            ),
            "right": CameraPreset(
                name="Right View",
                position_offset=Vec3(x=4.0, y=0.0, z=1.5),
                rotation_base=Vec3(x=15.0, y=0.0, z=90.0),
                fov=40.0,
                target_height=0.8
            ),
            "left": CameraPreset(
                name="Left View",
                position_offset=Vec3(x=-4.0, y=0.0, z=1.5),
                rotation_base=Vec3(x=15.0, y=0.0, z=-90.0),
                fov=40.0,
                target_height=0.8
            ),
            "corner_front_right": CameraPreset(
                name="Front Right Corner",
                position_offset=Vec3(x=2.5, y=-2.5, z=2.0),
                rotation_base=Vec3(x=45.0, y=0.0, z=45.0),
                fov=50.0,
                target_height=0.8
            ),
            "corner_front_left": CameraPreset(
                name="Front Left Corner",
                position_offset=Vec3(x=-2.5, y=-2.5, z=2.0),
                rotation_base=Vec3(x=45.0, y=0.0, z=-45.0),
                fov=50.0,
                target_height=0.8
            )
        }

    def generate_default_camera_poses(self, scene_bounds: Dict[str, Any],
                                     scene_type: str = "interior") -> List[CameraPose]:
        """Generate default camera poses for scene coverage.

        Args:
            scene_bounds: Scene bounding box information
            scene_type: Type of scene (interior, exterior, etc.)

        Returns:
            List of camera poses for comprehensive coverage
        """
        try:
            self.logger.info(f"Generating camera poses for {scene_type} scene")

            # Calculate scene center
            center = self._calculate_scene_center(scene_bounds)

            # Generate poses based on scene type
            if scene_type == "interior":
                poses = self._generate_interior_poses(center, scene_bounds)
            elif scene_type == "exterior":
                poses = self._generate_exterior_poses(center, scene_bounds)
            else:
                poses = self._generate_generic_poses(center, scene_bounds)

            # Validate poses
            validated_poses = []
            for pose in poses:
                if self._validate_camera_pose(pose, scene_bounds):
                    validated_poses.append(pose)
                else:
                    self.logger.warning(f"Camera pose validation failed: {pose.name}")

            self.logger.info(f"Generated {len(validated_poses)} valid camera poses")
            return validated_poses

        except Exception as e:
            self.logger.error(f"Camera pose generation failed: {e}")
            # Return minimal default pose
            return [self._create_default_pose()]

    def _generate_interior_poses(self, center: Vec3, bounds: Dict[str, Any]) -> List[CameraPose]:
        """Generate camera poses optimized for interior scenes."""
        poses = []

        # Add standard presets
        for preset_type, preset in self.camera_presets.items():
            if preset_type in ["wide", "top", "front", "corner_front_right", "corner_front_left"]:
                pose = self._create_pose_from_preset(preset, center)
                poses.append(pose)

        # Add room-specific poses based on objects
        room_poses = self._generate_room_specific_poses(center, bounds)
        poses.extend(room_poses)

        return poses

    def _generate_exterior_poses(self, center: Vec3, bounds: Dict[str, Any]) -> List[CameraPose]:
        """Generate camera poses optimized for exterior scenes."""
        poses = []

        # Wider angles for exterior
        exterior_presets = ["wide", "corner_front_right", "corner_front_left"]

        for preset_type in exterior_presets:
            if preset_type in self.camera_presets:
                preset = self.camera_presets[preset_type]
                # Scale up position for exterior
                scaled_preset = CameraPreset(
                    name=f"{preset.name} (Exterior)",
                    position_offset=Vec3(
                        x=preset.position_offset.x * 1.5,
                        y=preset.position_offset.y * 1.5,
                        z=preset.position_offset.z * 1.2
                    ),
                    rotation_base=preset.rotation_base,
                    fov=preset.fov,
                    target_height=preset.target_height
                )
                pose = self._create_pose_from_preset(scaled_preset, center)
                poses.append(pose)

        return poses

    def _generate_generic_poses(self, center: Vec3, bounds: Dict[str, Any]) -> List[CameraPose]:
        """Generate generic camera poses for unknown scene types."""
        poses = []

        # Use basic presets
        basic_presets = ["wide", "front", "corner_front_right"]

        for preset_type in basic_presets:
            if preset_type in self.camera_presets:
                preset = self.camera_presets[preset_type]
                pose = self._create_pose_from_preset(preset, center)
                poses.append(pose)

        return poses

    def _generate_room_specific_poses(self, center: Vec3, bounds: Dict[str, Any]) -> List[CameraPose]:
        """Generate poses optimized for specific room features."""
        poses = []

        # Calculate room dimensions
        size_x = bounds.get("size_x", 6.0)
        size_y = bounds.get("size_y", 4.0)

        # Add detail poses for larger rooms
        if size_x > 5.0 or size_y > 3.0:
            # Close-up corner view
            corner_pose = CameraPose(
                type="custom",
                name="Detail Corner",
                position=Vec3(x=center.x + size_x * 0.3, y=center.y + size_y * 0.3, z=1.2),
                rotation=Vec3(x=30.0, y=0.0, z=45.0),
                fov=35.0,
                target_point=center
            )
            poses.append(corner_pose)

        return poses

    def _create_pose_from_preset(self, preset: CameraPreset, center: Vec3) -> CameraPose:
        """Create camera pose from preset configuration."""
        position = Vec3(
            x=center.x + preset.position_offset.x,
            y=center.y + preset.position_offset.y,
            z=center.z + preset.position_offset.z + preset.target_height
        )

        return CameraPose(
            type=preset.name.lower().replace(" ", "_"),
            name=preset.name,
            position=position,
            rotation=preset.rotation_base,
            fov=preset.fov,
            target_point=Vec3(
                x=center.x,
                y=center.y,
                z=center.z + preset.target_height
            ),
            height_offset=preset.target_height
        )

    def _calculate_scene_center(self, bounds: Dict[str, Any]) -> Vec3:
        """Calculate scene center from bounds."""
        min_x = bounds.get("min_x", -3.0)
        max_x = bounds.get("max_x", 3.0)
        min_y = bounds.get("min_y", -2.0)
        max_y = bounds.get("max_y", 2.0)
        min_z = bounds.get("min_z", 0.0)
        max_z = bounds.get("max_z", 2.5)

        center_x = (min_x + max_x) / 2.0
        center_y = (min_y + max_y) / 2.0
        center_z = (min_z + max_z) / 2.0

        return Vec3(x=center_x, y=center_y, z=center_z)

    def _validate_camera_pose(self, pose: CameraPose, bounds: Dict[str, Any]) -> bool:
        """Validate camera pose for scene constraints."""
        try:
            # Check if camera is within reasonable bounds
            margin = 10.0  # Allow camera outside scene
            min_x = bounds.get("min_x", -3.0) - margin
            max_x = bounds.get("max_x", 3.0) + margin
            min_y = bounds.get("min_y", -2.0) - margin
            max_y = bounds.get("max_y", 2.0) + margin
            min_z = bounds.get("min_z", 0.0)
            max_z = bounds.get("max_z", 2.5) + margin

            pos = pose.position
            if not (min_x <= pos.x <= max_x and
                    min_y <= pos.y <= max_y and
                    min_z <= pos.z <= max_z):
                return False

            # Check FOV is reasonable
            if not (10.0 <= pose.fov <= 120.0):
                return False

            # Check rotation is normalized
            for angle in [pose.rotation.x, pose.rotation.y, pose.rotation.z]:
                if not (0.0 <= angle <= 360.0):
                    return False

            return True

        except Exception as e:
            self.logger.warning(f"Camera pose validation error: {e}")
            return False

    def _create_default_pose(self) -> CameraPose:
        """Create a safe default camera pose."""
        return CameraPose(
            type="wide",
            name="Default Overview",
            position=Vec3(x=-2.0, y=-2.0, z=2.0),
            rotation=Vec3(x=45.0, y=0.0, z=45.0),
            fov=45.0,
            target_point=Vec3(x=0.0, y=0.0, z=0.8)
        )

    def optimize_camera_poses(self, poses: List[CameraPose], scene_objects: List[Dict[str, Any]]) -> List[CameraPose]:
        """Optimize camera poses based on scene content."""
        try:
            self.logger.info(f"Optimizing {len(poses)} camera poses")

            optimized_poses = []

            for pose in poses:
                # Adjust pose based on object distribution
                adjusted_pose = self._adjust_pose_for_objects(pose, scene_objects)
                optimized_poses.append(adjusted_pose)

            # Remove redundant poses
            filtered_poses = self._remove_redundant_poses(optimized_poses)

            self.logger.info(f"Optimized to {len(filtered_poses)} poses")
            return filtered_poses

        except Exception as e:
            self.logger.error(f"Camera optimization failed: {e}")
            return poses

    def _adjust_pose_for_objects(self, pose: CameraPose, objects: List[Dict[str, Any]]) -> CameraPose:
        """Adjust camera pose to better frame important objects."""
        if not objects:
            return pose

        # Find important objects (large or central)
        important_objects = []
        for obj in objects:
            size = obj.get("size_m", [1, 1, 1])
            volume = size[0] * size[1] * size[2]
            if volume > 0.5:  # Larger objects
                important_objects.append(obj)

        if not important_objects:
            return pose

        # Calculate center of important objects
        center_x = sum(obj.get("initial_pose", {}).get("pos", [0, 0, 0])[0] for obj in important_objects) / len(important_objects)
        center_y = sum(obj.get("initial_pose", {}).get("pos", [0, 0, 0])[1] for obj in important_objects) / len(important_objects)
        center_z = sum(obj.get("initial_pose", {}).get("pos", [0, 0, 0])[2] for obj in important_objects) / len(important_objects)

        # Adjust target point
        adjusted_pose = pose.model_copy()
        adjusted_pose.target_point = Vec3(x=center_x, y=center_y, z=center_z + 0.8)

        return adjusted_pose

    def _remove_redundant_poses(self, poses: List[CameraPose]) -> List[CameraPose]:
        """Remove poses that are too similar to each other."""
        if len(poses) <= 3:
            return poses

        filtered_poses = []
        similarity_threshold = 30.0  # degrees

        for pose in poses:
            is_redundant = False

            for existing_pose in filtered_poses:
                # Calculate angular difference
                angle_diff = self._calculate_pose_angle_difference(pose, existing_pose)

                if angle_diff < similarity_threshold:
                    is_redundant = True
                    break

            if not is_redundant:
                filtered_poses.append(pose)

        return filtered_poses

    def _calculate_pose_angle_difference(self, pose1: CameraPose, pose2: CameraPose) -> float:
        """Calculate angular difference between two poses."""
        import math

        # Calculate direction vectors
        def get_direction_vector(pose: CameraPose):
            import math
            rot_x = math.radians(pose.rotation.x)
            rot_y = math.radians(pose.rotation.y)
            rot_z = math.radians(pose.rotation.z)

            # Simplified direction calculation
            dx = math.cos(rot_z) * math.cos(rot_x)
            dy = math.sin(rot_z) * math.cos(rot_x)
            dz = math.sin(rot_x)

            return (dx, dy, dz)

        dir1 = get_direction_vector(pose1)
        dir2 = get_direction_vector(pose2)

        # Calculate dot product
        dot_product = sum(a * b for a, b in zip(dir1, dir2))

        # Clamp to [-1, 1] to avoid numerical issues
        dot_product = max(-1.0, min(1.0, dot_product))

        # Calculate angle in degrees
        angle_rad = math.acos(dot_product)
        angle_deg = math.degrees(angle_rad)

        return angle_deg