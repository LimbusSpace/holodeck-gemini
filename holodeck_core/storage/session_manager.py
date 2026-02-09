"""Session management implementation."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from ..schemas import Session, SessionStatus, SessionRequest
from .file_storage import FileStorage


class SessionManager:
    """Manages session lifecycle and persistence."""

    def __init__(self, workspace_root: str = "workspace/sessions"):
        """Initialize session manager."""
        self.storage = FileStorage(workspace_root)

    async def create_session(self, request: SessionRequest) -> str:
        """Create a new session."""
        # Generate unique session ID with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        unique_id = str(uuid.uuid4())[:8]
        session_id = f"{timestamp}_{unique_id}"

        # Create session object
        session = Session(
            session_id=session_id,
            request=request,
            status=SessionStatus.INIT
        )

        # Save session
        await self.storage.write_session(session)

        return session_id

    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load session by ID."""
        data = await self.storage.read_session(session_id)
        if not data:
            return None

        return Session(**data)

    async def update_session_status(self, session_id: str, status: SessionStatus) -> bool:
        """Update session status."""
        session = await self.load_session(session_id)
        if not session:
            return False

        session.status = status
        session.updated_at = datetime.now(timezone.utc)
        await self.storage.write_session(session)
        return True

    async def update_session_metadata(self, session_id: str, metadata: dict) -> bool:
        """Update session metadata."""
        session = await self.load_session(session_id)
        if not session:
            return False

        session.metadata.update(metadata)
        session.updated_at = datetime.now(timezone.utc)
        await self.storage.write_session(session)
        return True

    async def list_sessions(self) -> List[str]:
        """List all session IDs."""
        return await self.storage.list_sessions()

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return await self.storage.delete_session(session_id)

    async def get_session_path(self, session_id: str) -> Optional[str]:
        """Get session directory path."""
        session_dir = self.storage.workspace_root / session_id
        if session_dir.exists():
            return str(session_dir)
        return None

    async def is_session_valid(self, session_id: str) -> bool:
        """Check if session exists and is valid."""
        session = await self.load_session(session_id)
        return session is not None

    async def create_snapshot(self, session_id: str, note: str) -> str:
        """Create a snapshot of session state."""
        session = await self.load_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Create snapshot name
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"snapshot_{timestamp}"

        # Add snapshot info to metadata
        if "snapshots" not in session.metadata:
            session.metadata["snapshots"] = []

        snapshot_info = {
            "name": snapshot_name,
            "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": session.status.value
        }
        session.metadata["snapshots"].append(snapshot_info)

        await self.storage.write_session(session)
        return snapshot_name