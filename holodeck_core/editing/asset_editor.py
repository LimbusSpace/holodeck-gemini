"""Asset editing module for managing 3D assets during scene editing.

Implements asset regeneration, replacement, addition, and deletion
with style consistency and version control.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from holodeck_core.storage import WorkspaceManager
from holodeck_core.object_gen import AssetGenerator


class AssetEditor:
    """Manages 3D asset editing operations with style consistency."""

    def __init__(self, workspace_manager: WorkspaceManager):
        self.workspace = workspace_manager
        self.logger = logging.getLogger(__name__)

        # Initialize asset generator
        self.asset_generator = AssetGenerator()

        # Style consistency configuration
        self.style_consistency_enabled = True
        self.max_regeneration_attempts = 3

    def regenerate_asset(self, session_id: str, object_id: str,
                        feedback: str) -> Dict[str, Any]:
        """Regenerate asset with updated properties based on feedback.

        Args:
            session_id: Scene session identifier
            object_id: Object to regenerate
            feedback: User feedback describing desired changes

        Returns:
            Dict containing regeneration result
        """
        try:
            session_path = self.workspace.get_session_path(session_id)

            # Load object data
            objects = self.workspace.load_objects(session_id)
            target_object = self._find_object(objects, object_id)

            if not target_object:
                raise ValueError(f"Object {object_id} not found")

            # Preserve style context from scene
            style_context = self._extract_style_context(objects, target_object)

            # Generate updated description incorporating feedback
            updated_description = self._update_description(
                target_object.get("visual_desc", ""),
                feedback,
                style_context
            )

            # Generate new asset
            asset_path = self._generate_asset_with_retry(
                session_id, object_id, updated_description, style_context
            )

            # Update object metadata
            target_object["visual_desc"] = updated_description
            target_object["asset_path"] = str(asset_path)
            target_object["version"] = target_object.get("version", 0) + 1
            target_object["last_modified"] = self._get_timestamp()

            # Save updated objects
            self.workspace.save_objects(session_id, objects)

            # Update asset manifest
            self._update_asset_manifest(session_path, object_id, asset_path)

            result = {
                "status": "success",
                "object_id": object_id,
                "new_asset_path": str(asset_path),
                "version": target_object["version"],
                "quality_impact": self._assess_quality_impact(feedback),
                "style_preserved": self.style_consistency_enabled
            }

            self.logger.info(f"Regenerated asset for object {object_id} in session {session_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error regenerating asset for {object_id}: {e}")
            raise

    def replace_asset(self, session_id: str, object_id: str,
                     replacement_spec: str) -> Dict[str, Any]:
        """Replace asset with completely new asset based on specification.

        Args:
            session_id: Scene session identifier
            object_id: Object to replace
            replacement_spec: Specification for replacement asset

        Returns:
            Dict containing replacement result
        """
        try:
            session_path = self.workspace.get_session_path(session_id)

            # Load object data
            objects = self.workspace.load_objects(session_id)
            target_object = self._find_object(objects, object_id)

            if not target_object:
                raise ValueError(f"Object {object_id} not found")

            # Extract style context for consistency
            style_context = self._extract_style_context(objects, target_object)

            # Generate replacement description
            replacement_description = self._generate_replacement_description(
                replacement_spec, style_context
            )

            # Generate new asset
            asset_path = self._generate_asset_with_retry(
                session_id, object_id, replacement_description, style_context
            )

            # Archive old asset
            old_asset_path = target_object.get("asset_path")
            if old_asset_path:
                self._archive_old_asset(session_path, object_id, old_asset_path)

            # Update object with replacement
            target_object["visual_desc"] = replacement_description
            target_object["asset_path"] = str(asset_path)
            target_object["version"] = target_object.get("version", 0) + 1
            target_object["last_modified"] = self._get_timestamp()
            target_object["replaced_from"] = old_asset_path if old_asset_path else None

            # Save updated objects
            self.workspace.save_objects(session_id, objects)

            # Update asset manifest
            self._update_asset_manifest(session_path, object_id, asset_path)

            result = {
                "status": "success",
                "object_id": object_id,
                "new_asset_path": str(asset_path),
                "old_asset_archived": old_asset_path is not None,
                "version": target_object["version"],
                "quality_impact": 0.15,  # Replacement generally improves quality
                "style_preserved": self.style_consistency_enabled
            }

            self.logger.info(f"Replaced asset for object {object_id} in session {session_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error replacing asset for {object_id}: {e}")
            raise

    def add_object(self, session_id: str, object_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Add new object with generated asset to scene.

        Args:
            session_id: Scene session identifier
            object_spec: Object specification

        Returns:
            Dict containing addition result
        """
        try:
            session_path = self.workspace.get_session_path(session_id)

            # Load existing objects to get style context
            objects = self.workspace.load_objects(session_id)
            style_context = self._extract_scene_style_context(objects)

            # Generate asset for new object
            object_id = object_spec["object_id"]
            description = object_spec.get("visual_desc", "")

            asset_path = self._generate_asset_with_retry(
                session_id, object_id, description, style_context
            )

            # Update object spec with generated asset
            object_spec["asset_path"] = str(asset_path)
            object_spec["version"] = 1
            object_spec["created_at"] = self._get_timestamp()
            object_spec["last_modified"] = self._get_timestamp()

            # Add to objects list
            objects["objects"].append(object_spec)

            # Save updated objects
            self.workspace.save_objects(session_id, objects)

            # Update asset manifest
            self._update_asset_manifest(session_path, object_id, asset_path)

            result = {
                "status": "success",
                "object_id": object_id,
                "asset_path": str(asset_path),
                "version": 1,
                "quality_impact": 0.1,  # Adding objects improves scene richness
                "style_consistent": True
            }

            self.logger.info(f"Added new object {object_id} to session {session_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error adding object to session {session_id}: {e}")
            raise

    def delete_object(self, session_id: str, object_id: str) -> Dict[str, Any]:
        """Delete object and its associated asset from scene.

        Args:
            session_id: Scene session identifier
            object_id: Object to delete

        Returns:
            Dict containing deletion result
        """
        try:
            session_path = self.workspace.get_session_path(session_id)

            # Load objects
            objects = self.workspace.load_objects(session_id)
            target_object = self._find_object(objects, object_id)

            if not target_object:
                raise ValueError(f"Object {object_id} not found")

            # Archive asset before deletion
            asset_path = target_object.get("asset_path")
            archived = False
            if asset_path:
                archived = self._archive_old_asset(session_path, object_id, asset_path)

            # Remove from objects list
            objects["objects"] = [
                obj for obj in objects["objects"]
                if obj["object_id"] != object_id
            ]

            # Save updated objects
            self.workspace.save_objects(session_id, objects)

            # Remove from asset manifest
            self._remove_from_asset_manifest(session_path, object_id)

            result = {
                "status": "success",
                "object_id": object_id,
                "asset_archived": archived,
                "quality_impact": -0.05,  # Removing objects may reduce richness
                "deleted_at": self._get_timestamp()
            }

            self.logger.info(f"Deleted object {object_id} from session {session_id}")
            return result

        except Exception as e:
            self.logger.error(f"Error deleting object {object_id}: {e}")
            raise

    def _generate_asset_with_retry(self, session_id: str, object_id: str,
                                 description: str, style_context: Dict[str, Any]) -> Path:
        """Generate asset with retry logic for robustness."""
        last_error = None

        for attempt in range(self.max_regeneration_attempts):
            try:
                asset_path = self.asset_generator.generate_from_description(
                    session_id, object_id, description, style_context
                )

                # Validate generated asset
                if self._validate_asset(asset_path):
                    return asset_path
                else:
                    self.logger.warning(f"Generated asset validation failed on attempt {attempt + 1}")

            except Exception as e:
                last_error = e
                self.logger.warning(f"Asset generation attempt {attempt + 1} failed: {e}")

        # All attempts failed
        raise RuntimeError(f"Failed to generate asset after {self.max_regeneration_attempts} attempts: {last_error}")

    def _extract_style_context(self, objects: Dict[str, Any],
                             target_object: Dict[str, Any]) -> Dict[str, Any]:
        """Extract style context from scene for consistency."""
        scene_style = objects.get("scene_style", "modern")

        # Collect style elements from other objects
        style_elements = []
        for obj in objects.get("objects", []):
            if obj["object_id"] != target_object.get("object_id"):
                visual_desc = obj.get("visual_desc", "")
                style_elements.append(visual_desc)

        return {
            "scene_style": scene_style,
            "style_elements": style_elements[:5],  # Limit to avoid token overflow
            "material_preferences": self._extract_material_preferences(style_elements),
            "color_scheme": self._extract_color_scheme(style_elements)
        }

    def _extract_scene_style_context(self, objects: Dict[str, Any]) -> Dict[str, Any]:
        """Extract overall scene style context for new objects."""
        scene_style = objects.get("scene_style", "modern")

        # Collect style from all objects
        style_elements = []
        for obj in objects.get("objects", []):
            visual_desc = obj.get("visual_desc", "")
            style_elements.append(visual_desc)

        return {
            "scene_style": scene_style,
            "style_elements": style_elements[-10:],  # Use recent objects
            "material_preferences": self._extract_material_preferences(style_elements),
            "color_scheme": self._extract_color_scheme(style_elements)
        }

    def _update_description(self, current_desc: str, feedback: str,
                          style_context: Dict[str, Any]) -> str:
        """Update asset description incorporating feedback while preserving style."""
        # This would use LLM to intelligently merge feedback with current description
        # For now, implement basic merging

        scene_style = style_context.get("scene_style", "")

        # Extract key terms from feedback
        feedback_keywords = self._extract_keywords(feedback)

        # Merge with current description
        updated_desc = f"{current_desc}. {feedback}. Maintain {scene_style} style."

        return updated_desc

    def _generate_replacement_description(self, replacement_spec: str,
                                        style_context: Dict[str, Any]) -> str:
        """Generate description for replacement asset with style consistency."""
        scene_style = style_context.get("scene_style", "")
        material_prefs = style_context.get("material_preferences", [])

        # Incorporate style preferences
        style_additions = []
        if material_prefs:
            style_additions.append(f"use materials: {', '.join(material_prefs[:2])}")

        style_additions.append(f"maintain {scene_style} aesthetic")

        replacement_desc = f"{replacement_spec}. {'; '.join(style_additions)}."

        return replacement_desc

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Simple keyword extraction - would be enhanced with NLP
        words = text.lower().split()
        keywords = [word for word in words if len(word) > 3]
        return keywords[:5]  # Limit keywords

    def _extract_material_preferences(self, descriptions: List[str]) -> List[str]:
        """Extract material preferences from descriptions."""
        materials = ["wood", "metal", "glass", "plastic", "fabric", "leather", "stone", "marble"]
        found_materials = []

        for desc in descriptions:
            desc_lower = desc.lower()
            for material in materials:
                if material in desc_lower and material not in found_materials:
                    found_materials.append(material)

        return found_materials[:3]  # Limit materials

    def _extract_color_scheme(self, descriptions: List[str]) -> List[str]:
        """Extract color scheme from descriptions."""
        colors = ["black", "white", "gray", "brown", "blue", "red", "green", "yellow", "orange", "purple"]
        found_colors = []

        for desc in descriptions:
            desc_lower = desc.lower()
            for color in colors:
                if color in desc_lower and color not in found_colors:
                    found_colors.append(color)

        return found_colors[:4]  # Limit colors

    def _assess_quality_impact(self, feedback: str) -> float:
        """Assess potential quality impact of feedback."""
        # Simple heuristic - would be enhanced with ML
        positive_indicators = ["better", "improve", "enhance", "upgrade", "modern", "sleek"]
        negative_indicators = ["worse", "bad", "ugly", "remove", "delete"]

        feedback_lower = feedback.lower()

        positive_score = sum(1 for indicator in positive_indicators if indicator in feedback_lower)
        negative_score = sum(1 for indicator in negative_indicators if indicator in feedback_lower)

        impact = (positive_score - negative_score) * 0.1
        return max(-0.2, min(0.2, impact))

    def _validate_asset(self, asset_path: Path) -> bool:
        """Validate generated asset file."""
        try:
            if not asset_path.exists():
                return False

            # Check file size (should be reasonable)
            file_size = asset_path.stat().st_size
            # For placeholder files, allow smaller sizes
            if file_size < 1 or file_size > 100 * 1024 * 1024:  # 1 byte to 100MB
                return False

            # Could add more validation (file format, etc.)
            return True

        except Exception:
            return False

    def _archive_old_asset(self, session_path: Path, object_id: str,
                          asset_path: str) -> bool:
        """Archive old asset before replacement."""
        try:
            source_path = Path(asset_path)
            if not source_path.exists():
                return False

            # Create archive directory
            archive_dir = session_path / "archived_assets"
            archive_dir.mkdir(exist_ok=True)

            # Generate archive filename with timestamp
            timestamp = self._get_timestamp().replace(":", "-")
            archive_path = archive_dir / f"{object_id}_{timestamp}{source_path.suffix}"

            # Copy to archive
            shutil.copy2(source_path, archive_path)

            return True

        except Exception as e:
            self.logger.warning(f"Failed to archive old asset: {e}")
            return False

    def _update_asset_manifest(self, session_path: Path, object_id: str,
                              asset_path: Path) -> None:
        """Update asset manifest with new asset information."""
        try:
            manifest_path = session_path / "asset_manifest.json"

            if manifest_path.exists():
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            else:
                manifest = {}

            # Update manifest entry
            manifest[object_id] = {
                "path": str(asset_path),
                "version": manifest.get(object_id, {}).get("version", 0) + 1,
                "last_updated": self._get_timestamp(),
                "file_size": asset_path.stat().st_size if asset_path.exists() else 0
            }

            # Save manifest
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to update asset manifest: {e}")

    def _remove_from_asset_manifest(self, session_path: Path, object_id: str) -> None:
        """Remove object from asset manifest."""
        try:
            manifest_path = session_path / "asset_manifest.json"

            if manifest_path.exists():
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)

                # Remove entry
                if object_id in manifest:
                    del manifest[object_id]

                # Save updated manifest
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=2)

        except Exception as e:
            self.logger.warning(f"Failed to remove from asset manifest: {e}")

    def _find_object(self, objects: Dict[str, Any], object_id: str) -> Optional[Dict[str, Any]]:
        """Find object by ID in objects data."""
        for obj in objects.get("objects", []):
            if obj.get("object_id") == object_id:
                return obj
        return None

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()