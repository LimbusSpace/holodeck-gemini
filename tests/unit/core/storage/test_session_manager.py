# pylint: skip-file
"""Test session manager functionality."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from holodeck_core.storage import SessionManager
from holodeck_core.schemas import SessionRequest, SessionStatus


@pytest.mark.unit
@pytest.mark.asyncio
class TestSessionManager:
    """Test session manager."""

    @pytest.fixture
    def session_manager(self):
        """Create a temporary session manager for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir) / "workspace" / "sessions"
            manager = SessionManager(str(workspace))
            yield manager

    async def test_create_session(self, session_manager):
        """Test session creation."""
        request = SessionRequest(
            text="A test scene with a table",
            style="modern"
        )
        session_id = await session_manager.create_session(request)

        assert session_id is not None
        assert isinstance(session_id, str)
        # Check that it follows expected format
        assert "_" in session_id

    async def test_load_session(self, session_manager):
        """Test loading a session."""
        request = SessionRequest(text="Test scene")
        session_id = await session_manager.create_session(request)

        # Load the session
        session = await session_manager.load_session(session_id)

        assert session is not None
        assert session.session_id == session_id
        assert session.request.text == "Test scene"
        assert session.status == SessionStatus.INIT

    async def test_load_nonexistent_session(self, session_manager):
        """Test loading a session that doesn't exist."""
        session = await session_manager.load_session("nonexistent_id")
        assert session is None

    async def test_update_session_status(self, session_manager):
        """Test updating session status."""
        request = SessionRequest(text="Test scene")
        session_id = await session_manager.create_session(request)

        # Update status
        success = await session_manager.update_session_status(
            session_id, SessionStatus.GENERATING
        )
        assert success is True

        # Verify update
        session = await session_manager.load_session(session_id)
        assert session.status == SessionStatus.GENERATING

    async def test_update_status_nonexistent(self, session_manager):
        """Test updating status of nonexistent session."""
        success = await session_manager.update_session_status(
            "nonexistent", SessionStatus.COMPLETED
        )
        assert success is False

    async def test_update_session_metadata(self, session_manager):
        """Test updating session metadata."""
        request = SessionRequest(text="Test scene")
        session_id = await session_manager.create_session(request)

        # Update metadata
        metadata = {"author": "test_user", "version": "1.0"}
        success = await session_manager.update_session_metadata(session_id, metadata)
        assert success is True

        # Verify update
        session = await session_manager.load_session(session_id)
        assert session.metadata["author"] == "test_user"
        assert session.metadata["version"] == "1.0"

    async def test_list_sessions(self, session_manager):
        """Test listing sessions."""
        # Initially empty
        sessions = await session_manager.list_sessions()
        assert len(sessions) == 0

        # Create some sessions
        request1 = SessionRequest(text="Scene 1")
        request2 = SessionRequest(text="Scene 2")

        id1 = await session_manager.create_session(request1)
        id2 = await session_manager.create_session(request2)

        sessions = await session_manager.list_sessions()
        assert len(sessions) == 2
        assert id1 in sessions
        assert id2 in sessions

    async def test_delete_session(self, session_manager):
        """Test deleting a session."""
        request = SessionRequest(text="Test scene")
        session_id = await session_manager.create_session(request)

        # Verify it exists
        session = await session_manager.load_session(session_id)
        assert session is not None

        # Delete it
        success = await session_manager.delete_session(session_id)
        assert success is True

        # Verify it's gone
        session = await session_manager.load_session(session_id)
        assert session is None

    async def test_delete_nonexistent_session(self, session_manager):
        """Test deleting a session that doesn't exist."""
        success = await session_manager.delete_session("nonexistent")
        assert success is False

    async def test_get_session_path(self, session_manager):
        """Test getting session path."""
        request = SessionRequest(text="Test scene")
        session_id = await session_manager.create_session(request)

        path = await session_manager.get_session_path(session_id)
        assert path is not None
        assert session_id in path
        assert Path(path).exists()

    async def test_is_session_valid(self, session_manager):
        """Test checking if session is valid."""
        # Nonexistent session
        assert await session_manager.is_session_valid("nonexistent") is False

        # Create session
        request = SessionRequest(text="Test scene")
        session_id = await session_manager.create_session(request)

        # Valid session
        assert await session_manager.is_session_valid(session_id) is True

    async def test_create_snapshot(self, session_manager):
        """Test creating session snapshot."""
        request = SessionRequest(text="Test scene")
        session_id = await session_manager.create_session(request)

        # Create snapshot
        snapshot_name = await session_manager.create_snapshot(
            session_id, "Initial state"
        )

        assert snapshot_name is not None
        assert "snapshot_" in snapshot_name

        # Check session metadata
        session = await session_manager.load_session(session_id)
        assert "snapshots" in session.metadata
        assert len(session.metadata["snapshots"]) == 1

        snapshot = session.metadata["snapshots"][0]
        assert snapshot["name"] == snapshot_name
        assert snapshot["note"] == "Initial state"

    async def test_snapshot_nonexistent_session(self, session_manager):
        """Test creating snapshot for nonexistent session."""
        with pytest.raises(ValueError, match="Session nonexistent not found"):
            await session_manager.create_snapshot("nonexistent", "Test")