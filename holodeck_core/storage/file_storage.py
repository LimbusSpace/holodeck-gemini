"""File system storage utilities."""

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
import aiofiles
import aiofiles.os

from ..schemas import Session


class FileStorage:
    """File system storage handler for sessions."""

    def __init__(self, workspace_root: str = "workspace/sessions"):
        """Initialize storage with workspace root."""
        self.workspace_root = Path(workspace_root)

    async def ensure_session_dir(self, session_id: str) -> Path:
        """Ensure session directory exists."""
        session_dir = self.workspace_root / session_id
        await aiofiles.os.makedirs(session_dir, exist_ok=True)
        return session_dir

    async def write_json(self, session_id: str, filename: str, data: Any) -> Path:
        """Write data to JSON file."""
        session_dir = await self.ensure_session_dir(session_id)
        filepath = session_dir / filename

        async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False, default=str))

        return filepath

    async def read_json(self, session_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Read data from JSON file."""
        filepath = self.workspace_root / session_id / filename

        if not filepath.exists():
            return None

        async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)

    async def write_session(self, session: Session) -> Path:
        """Write session data to file."""
        return await self.write_json(session.session_id, "session.json", session.dict())

    async def read_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Read session data from file."""
        return await self.read_json(session_id, "session.json")

    async def save_image(self, session_id: str, filename: str, image_data: bytes) -> Path:
        """Save binary image data."""
        session_dir = await self.ensure_session_dir(session_id)
        filepath = session_dir / filename

        async with aiofiles.open(filepath, 'wb') as f:
            await f.write(image_data)

        return filepath

    async def list_sessions(self) -> list[str]:
        """List all session IDs."""
        if not self.workspace_root.exists():
            return []

        sessions = []
        for item in self.workspace_root.iterdir():
            if item.is_dir():
                sessions.append(item.name)

        return sorted(sessions)

    async def delete_session(self, session_id: str) -> bool:
        """Delete entire session directory."""
        session_dir = self.workspace_root / session_id

        if not session_dir.exists():
            return False

        shutil.rmtree(session_dir)
        return True