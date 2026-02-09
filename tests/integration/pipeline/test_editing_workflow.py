"""
Editing workflow integration tests using pytest framework
"""

import json
import logging
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from holodeck_core.editing import EditEngine, FeedbackParser, ConstraintManager
from holodeck_core.storage import SessionManager, WorkspaceManager
from holodeck_core.schemas import SessionRequest, EditHistory


@pytest.fixture
def workspace():
    """Create a temporary workspace for testing"""
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)
        workspace = WorkspaceManager(workspace_path)
        yield workspace


@pytest.fixture
def session_manager(workspace):
    """Create a session manager for testing"""
    manager = SessionManager(workspace.sessions_path)
    yield manager


@pytest.mark.integration
class TestEditingWorkflow:
    """Test complete editing workflow"""

    def test_session_creation(self, session_manager):
        """Test session creation for editing"""
        request = SessionRequest(
            text="A modern bedroom with a bed and nightstand",
            style="modern"
        )
        
        session_id = session_manager.create_session(request)
        assert session_id is not None
        
    def test_feedback_parsing_workflow(self):
        """Test feedback parsing in workflow"""
        parser = FeedbackParser()

        # Test various feedback types
        feedbacks = [
            "Move the chair closer to the desk",
            "Replace the red lamp with a blue one",
            "Add a bookshelf next to the bed",
            "Remove the small table"
        ]
        
        for feedback in feedbacks:
            result = parser.parse_feedback(feedback)
            assert result is not None
            assert "focus_object" in result
            assert "operations" in result
            assert len(result["operations"]) > 0

    def test_constraint_manager_workflow(self):
        """Test constraint manager in editing workflow"""
        manager = ConstraintManager()
        
        # Test constraint creation
        constraints = manager.generate_constraints_from_feedback(
            "Move chair closer to table",
            {"chair": "obj_001", "table": "obj_002"}
        )

        assert constraints is not None
        assert len(constraints) > 0

    def test_edit_engine_workflow(self, workspace):
        """Test edit engine in complete workflow"""
        engine = EditEngine(workspace)
        
        # Test edit application
        edit_data = {
            "session_id": "test_session",
            "feedback": "Move chair closer to table",
            "focus_object": "chair_001",
            "operations": [
                {
                    "type": "move",
                    "target": "chair_001",
                    "parameters": {"distance": 0.5}
                }
            ]
        }
        
        result = engine.apply_edit(edit_data)
        assert result is not None
        assert "success" in result
