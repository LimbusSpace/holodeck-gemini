"""Image management utilities.

Handles saving, organizing, and managing generated images in the workspace.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ImageManager:
    """Manages generated images in workspace structure."""

    def __init__(self, workspace_root: str = "workspace"):
        """Initialize image manager.

        Args:
            workspace_root: Root directory for workspace
        """
        self.workspace_root = Path(workspace_root)
        self.sessions_dir = self.workspace_root / "sessions"

    def get_session_dir(self, session_id: str) -> Path:
        """Get the directory for a specific session.

        Args:
            session_id: Unique session identifier

        Returns:
            Path to session directory
        """
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def save_scene_reference(
        self,
        session_id: str,
        image_path: str,
        prompt: str,
        style: str,
        generation_time: float
    ) -> Dict[str, Any]:
        """Save scene reference image to session workspace.

        Args:
            session_id: Session identifier
            image_path: Path to generated image
            prompt: Original prompt used
            style: Artistic style
            generation_time: Generation time in seconds

        Returns:
            Dictionary with image metadata
        """
        session_dir = self.get_session_dir(session_id)
        target_path = session_dir / "scene_ref.png"

        # Copy image to session directory
        shutil.copy2(image_path, target_path)
        logger.info(f"Saved scene reference image to {target_path}")

        metadata = {
            "image_path": str(target_path.relative_to(self.workspace_root)),
            "prompt_used": prompt,
            "style": style,
            "generation_time": generation_time,
            "created_at": datetime.now().isoformat()
        }

        return metadata

    def save_object_card(
        self,
        session_id: str,
        object_id: str,
        object_name: str,
        image_path: str,
        prompt: str,
        generation_time: float,
        qc_status: str = "pending"
    ) -> Dict[str, Any]:
        """Save object card image to session workspace.

        Args:
            session_id: Session identifier
            object_id: Unique object identifier
            object_name: Human-readable object name
            image_path: Path to generated image
            prompt: Prompt used for generation
            generation_time: Generation time in seconds
            qc_status: Quality control status

        Returns:
            Dictionary with object card metadata
        """
        session_dir = self.get_session_dir(session_id)
        object_cards_dir = session_dir / "object_cards"
        object_cards_dir.mkdir(exist_ok=True)

        target_path = object_cards_dir / f"{object_id}.png"

        # Copy image to session directory
        shutil.copy2(image_path, target_path)
        logger.info(f"Saved object card to {target_path}")

        metadata = {
            "object_id": object_id,
            "object_name": object_name,
            "card_image_path": str(target_path.relative_to(self.workspace_root)),
            "prompt_used": prompt,
            "generation_time": generation_time,
            "qc_status": qc_status,
            "created_at": datetime.now().isoformat()
        }

        return metadata

    def clean_temp_images(self, temp_dir: str = None) -> None:
        """Clean up temporary images after processing.

        Args:
            temp_dir: Temporary directory to clean (defailts to workspace/temp)
        """
        if temp_dir is None:
            temp_dir = self.workspace_root / "temp"

        temp_path = Path(temp_dir)
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)
            logger.info(f"Cleaned temporary directory: {temp_path}")

    def get_image_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics about images in a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with image statistics
        """
        session_dir = self.get_session_dir(session_id)
        stats = {
            "session_id": session_id,
            "scene_ref_exists": False,
            "object_card_count": 0,
            "total_size_mb": 0.0
        }

        # Check scene reference
        scene_ref = session_dir / "scene_ref.png"
        if scene_ref.exists():
            stats["scene_ref_exists"] = True
            stats["total_size_mb"] += scene_ref.stat().st_size / (1024 * 1024)

        # Count object cards
        object_cards_dir = session_dir / "object_cards"
        if object_cards_dir.exists():
            object_cards = list(object_cards_dir.glob("*.png"))
            stats["object_card_count"] = len(object_cards)
            for card_path in object_cards:
                stats["total_size_mb"] += card_path.stat().st_size / (1024 * 1024)

        return stats

    def validate_image_structure(self, session_id: str) -> Dict[str, Any]:
        """Validate that the session has the expected image structure.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with validation results
        """
        session_dir = self.get_session_dir(session_id)
        validation = {
            "valid": True,
            "issues": []
        }

        # Check scene reference image
        scene_ref = session_dir / "scene_ref.png"
        if not scene_ref.exists():
            validation["valid"] = False
            validation["issues"].append("Missing scene reference image (scene_ref.png)")

        # Check object cards directory and structure
        object_cards_dir = session_dir / "object_cards"
        if not object_cards_dir.exists():
            validation["valid"] = False
            validation["issues"].append("Missing object_cards directory")
        else:
            object_files = list(object_cards_dir.glob("*.png"))
            if not object_files:
                validation["valid"] = False
                validation["issues"].append("No object cards found")

        return validation