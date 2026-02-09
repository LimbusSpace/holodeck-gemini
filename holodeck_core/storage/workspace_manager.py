"""Workspace manager for unified access to session data and files.

Provides a unified interface for:
- Session management
- Object data access
- Constraint management
- File operations
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from .session_manager import SessionManager
from ..schemas import SessionRequest


class WorkspaceManager:
    """Unified workspace manager for scene editing operations."""

    def __init__(self, workspace_root: str = "workspace/sessions"):
        # 如果没有提供workspace_root，使用config的工作空间路径
        if workspace_root == "workspace/sessions":
            from holodeck_cli.config import config
            workspace_path = config.get_workspace_path()
            self.workspace_root = workspace_path / "sessions"
            self.session_manager = SessionManager(str(workspace_path))
        else:
            self.workspace_root = Path(workspace_root)
            self.session_manager = SessionManager(workspace_root)

        self.logger = logging.getLogger(__name__)

        # Ensure workspace directory exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def create_session(self, request_text: str, style: str = "modern") -> str:
        """Create a new session with request data."""
        # Create session request
        request = SessionRequest(
            text=request_text,
            style=style
        )

        # Create session (sync wrapper for async method)
        import asyncio
        session_id = asyncio.run(self.session_manager.create_session(request))

        # Create session directory
        session_path = self.get_session_path(session_id)
        session_path.mkdir(parents=True, exist_ok=True)

        # Save request data
        request_data = {
            "session_id": session_id,
            "text": request_text,
            "style": style,
            "constraints": {
                "max_objects": 25,
                "room_size_hint": [6, 4, 3]
            }
        }

        request_path = session_path / "request.json"
        with open(request_path, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2)

        self.logger.info(f"Created session {session_id}")
        return session_id

    def get_session_path(self, session_id: str) -> Path:
        """Get session directory path."""
        return self.workspace_root / session_id

    def load_objects(self, session_id: str) -> Dict[str, Any]:
        """Load objects data from session."""
        session_path = self.get_session_path(session_id)
        objects_path = session_path / "objects.json"

        if not objects_path.exists():
            raise FileNotFoundError(f"Objects file not found: {objects_path}")

        with open(objects_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_objects(self, session_id: str, objects_data: Dict[str, Any]) -> None:
        """Save objects data to session."""
        session_path = self.get_session_path(session_id)
        objects_path = session_path / "objects.json"

        with open(objects_path, 'w', encoding='utf-8') as f:
            json.dump(objects_data, f, indent=2)

    def load_constraints(self, session_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Load constraints data from session."""
        session_path = self.get_session_path(session_id)

        if version:
            constraints_path = session_path / f"constraints_{version}.json"
        else:
            # Find latest version
            constraint_files = list(session_path.glob("constraints_v*.json"))
            if constraint_files:
                constraints_path = max(constraint_files, key=lambda p: p.stat().st_mtime)
            else:
                constraints_path = session_path / "constraints_v1.json"

        if not constraints_path.exists():
            # Return default constraints
            return {
                "globals": {
                    "ground_only_default": True,
                    "collision_clearance_m": 0.02
                },
                "relations": []
            }

        with open(constraints_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_constraints(self, session_id: str, constraints_data: Dict[str, Any]) -> str:
        """Save constraints data and return version."""
        session_path = self.get_session_path(session_id)

        # Determine version number
        existing_versions = list(session_path.glob("constraints_v*.json"))
        version_num = len(existing_versions) + 1
        version = f"v{version_num}"

        constraints_path = session_path / f"constraints_{version}.json"

        with open(constraints_path, 'w', encoding='utf-8') as f:
            json.dump(constraints_data, f, indent=2)

        return version

    def load_layout_solution(self, session_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Load layout solution from session."""
        session_path = self.get_session_path(session_id)

        if version:
            solution_path = session_path / f"layout_solution_{version}.json"
        else:
            # Find latest version
            solution_files = list(session_path.glob("layout_solution_v*.json"))
            if solution_files:
                solution_path = max(solution_files, key=lambda p: p.stat().st_mtime)
            else:
                solution_path = session_path / "layout_solution_v1.json"

        if not solution_path.exists():
            raise FileNotFoundError(f"Layout solution not found: {solution_path}")

        with open(solution_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_layout_solution(self, session_id: str, solution: Any) -> str:
        """Save layout solution and return version."""
        session_path = self.get_session_path(session_id)

        # Determine version number
        existing_versions = list(session_path.glob("layout_solution_v*.json"))
        version_num = len(existing_versions) + 1
        version = f"v{version_num}"

        solution_path = session_path / f"layout_solution_{version}.json"

        with open(solution_path, 'w', encoding='utf-8') as f:
            json.dump(solution.model_dump() if hasattr(solution, 'model_dump') else solution, f, indent=2)

        return version

    def get_edit_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get edit history for session."""
        session_path = self.get_session_path(session_id)
        history_path = session_path / "edit_history.json"

        if not history_path.exists():
            return None

        with open(history_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def save_edit_history(self, session_id: str, history_data: Dict[str, Any]) -> None:
        """Save edit history for session."""
        session_path = self.get_session_path(session_id)
        history_path = session_path / "edit_history.json"

        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2)

    def list_sessions(self) -> List[str]:
        """List all session IDs."""
        import asyncio
        return asyncio.run(self.session_manager.list_sessions())

    def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        session_path = self.get_session_path(session_id)
        return session_path.exists()