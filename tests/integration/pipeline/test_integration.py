"""Integration tests for the complete workflow."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from holodeck_core.storage import SessionManager
from holodeck_core.schemas import SessionRequest


@pytest.mark.integration
@pytest.mark.asyncio
class TestIntegrationWorkflow:
    """Test the end-to-end workflow."""

    async def test_bedroom_workflow(self):
        """Test complete bedroom scene workflow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup
            workspace = Path(tmp_dir) / "workspace" / "sessions"
            manager = SessionManager(str(workspace))

            # Step 1: Create session
            request = SessionRequest(
                text="A cozy modern bedroom with a king bed, two nightstands with lamps, and a full-length mirror.",
                style="modern minimalist"
            )
            session_id = await manager.create_session(request)

            # Verify session
            assert session_id is not None
            session = await manager.load_session(session_id)
            assert session is not None
            assert session.request.text == request.text
            assert session.request.style == request.style

    def test_examples_scenes(self):
        """Verify example scene configurations."""
        from config.examples.scenes import SCENARIOS

        assert "examples" in SCENARIOS
        assert len(SCENARIOS["examples"]) == 5

        # Check each scene has required fields
        for scene in SCENARIOS["examples"]:
            assert "name" in scene
            assert "description" in scene
            assert "text" in scene
            assert "expected_objects" in scene
            assert scene["expected_objects"] >= 1
            assert scene["expected_objects"] <= 25

    def test_style_validations(self):
        """Test style options."""
        from config.examples.scenes import SCENARIOS

        styles = SCENARIOS["styles"]
        assert len(styles) == 10
        assert "realistic" in styles
        assert "modern minimalist" in styles


@pytest.mark.integration
class TestPluginStructure:
    """Test plugin structure integrity."""

    def test_plugin_json(self):
        """Verify plugin configuration."""
        plugin_path = Path(".claude-plugin/plugin.json")
        assert plugin_path.exists()

        import json
        with open(plugin_path) as f:
            config = json.load(f)

        assert config["name"] == "holodeck"
        assert "mcpServers" in config
        assert "holodeck-tools" in config["mcpServers"]

    def test_commands_directory(self):
        """Verify commands exist."""
        commands = Path("commands")
        assert commands.exists()

        required_commands = [
            "holodeck_build.md",
            "holodeck_edit.md",
            "holodeck_replay.md"
        ]

        for cmd in required_commands:
            assert (commands / cmd).exists()

    def test_skills_directory(self):
        """Verify skills structure."""
        skills = Path("skills")
        assert skills.exists()

        required_skills = [
            "holodeck-build",
            "holodeck-edit",
            "holodeck-debug"
        ]

        for skill in required_skills:
            skill_dir = skills / skill
            assert skill_dir.exists()
            assert (skill_dir / "SKILL.md").exists()
            # Read and verify basic structure
            with open(skill_dir / "SKILL.md") as f:
                content = f.read()
                assert "name:" in content
                assert "description:" in content