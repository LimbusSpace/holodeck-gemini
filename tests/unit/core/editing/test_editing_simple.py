"""
Simple editing functionality tests using pytest framework
"""

import json
import logging
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from holodeck_core.editing import EditEngine, FeedbackParser
from holodeck_core.schemas import EditHistory, EditOperation


@pytest.mark.unit
class TestEditingSimple:
    """Test basic editing functionality"""
    
    def test_feedback_parser_initialization(self):
        """Test FeedbackParser initialization"""
        parser = FeedbackParser()
        assert parser is not None

    def test_edit_engine_initialization(self):
        """Test EditEngine initialization"""
        engine = EditEngine()
        assert engine is not None

    def test_parse_simple_feedback(self):
        """Test parsing simple feedback"""
        parser = FeedbackParser()
        feedback = "Move the chair closer to the table"
        
        result = parser.parse_feedback(feedback)
        assert result is not None
        assert "focus_object" in result
        assert "operations" in result

    def test_edit_history_creation(self):
        """Test EditHistory creation"""
        history = EditHistory()
        assert history.operations == []
        assert history.session_id is None

    def test_edit_operation_creation(self):
        """Test EditOperation creation"""
        operation = EditOperation(
            operation_type="move",
            target_object="chair_001",
            parameters={"distance": 0.5}
        )
        assert operation.operation_type == "move"
        assert operation.target_object == "chair_001"
        assert operation.parameters["distance"] == 0.5
