"""Test ComfyUI integration functionality."""

import os
import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import mcp.types as types

# Skip tests if required dependencies are not available
try:
    import websocket
    import requests
    from holodeck_core.image_generation import ComfyUIClient, ImageManager
    from holodeck_core.schemas import SceneRefImage, ObjectCard
    DEPS_AVAILABLE = True
except ImportError as e:
    print(f"Skipping ComfyUI tests due to missing dependencies: {e}")
    DEPS_AVAILABLE = False


@pytest.mark.skipif(not DEPS_AVAILABLE, reason="ComfyUI dependencies not available")
@pytest.mark.integration
class TestComfyUIClient:
    """Test ComfyUIClient functionality."""

    @pytest.fixture
    def client(self):
        """Create test client instance."""
        return ComfyUIClient(
            server_address="127.0.0.1:8188",
            client_id="test-client-123"
        )

    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.server_address == "127.0.0.1:8188"
        assert client.client_id == "test-client-123"
        assert client.timeout == 30
        assert client.base_url == "http://127.0.0.1:8188"

    def test_make_request_url(self, client):
        """Test URL construction."""
        url = client._make_request_url("prompt")
        assert url == "http://127.0.0.1:8188/prompt"

        url = client._make_request_url("history/test123")
        assert url == "http://127.0.0.1:8188/history/test123"

    @patch('requests.get')
    def test_test_connection_success(self, mock_get, client):
        """Test successful connection test."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Run in sync context for test
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(client.test_connection())

        assert result is True
        mock_get.assert_called_once_with("http://127.0.0.1:8188/system_stats", timeout=5)

    @patch('requests.get')
    def test_test_connection_failure(self, mock_get, client):
        """Test failed connection test."""
        mock_get.side_effect = Exception("Connection error")

        # Run in sync context for test
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(client.test_connection())

        assert result is False

    def test_get_server_info(self, client):
        """Test getting server information."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"status": "ok"}
            mock_get.return_value = mock_response

            info = client.get_server_info()
            assert info == {"status": "ok"}
            mock_get.assert_called_once_with("http://127.0.0.1:8188/system_stats", timeout=5)


@pytest.mark.skipif(not DEPS_AVAILABLE, reason="ComfyUI dependencies not available")
@pytest.mark.integration
class TestWorkflowManagement:
    """Test workflow template management."""

    def test_workflow_injection(self):
        """Test prompt injection into workflow."""
        from holodeck_core.image_generation.workflows import (
            SCENE_REF_WORKFLOW,
            OBJECT_CARD_WORKFLOW,
            inject_prompt,
            set_resolution,
            set_seed
        )

        # Test prompt injection
        workflow = SCENE_REF_WORKFLOW.copy()
        prompt = "A modern bedroom with soft lighting"
        modified = inject_prompt(workflow, prompt)

        # Find the text encode node and check injection
        found_prompt = False
        for node_id, node_data in modified.items():
            if node_data.get("class_type") == "CLIPTextEncode":
                if "text" in node_data["inputs"]:
                    text_input = node_data["inputs"]["text"]
                    if isinstance(text_input, list) and text_input:
                        if prompt in text_input[0]:
                            found_prompt = True
                            break
                    else:
                        if prompt in text_input:
                            found_prompt = True
                            break
        assert found_prompt, "Prompt not injected into workflow"

    def test_resolution_setting(self):
        """Test resolution modification in workflow."""
        from holodeck_core.image_generation.workflows import SCENE_REF_WORKFLOW, set_resolution

        workflow = SCENE_REF_WORKFLOW.copy()
        modified = set_resolution(workflow, 800, 600)

        # Find the latent image node and check resolution
        found_resolution = False
        for node_id, node_data in modified.items():
            if node_data.get("class_type") == "EmptyLatentImage":
                if (
                    node_data["inputs"]["width"] == 800
                    and node_data["inputs"]["height"] == 600
                ):
                    found_resolution = True
                    break
        assert found_resolution, "Resolution not set correctly"

    def test_seed_setting(self):
        """Test seed modification in workflow."""
        from holodeck_core.image_generation.workflows import SCENE_REF_WORKFLOW, set_seed

        workflow = SCENE_REF_WORKFLOW.copy()
        modified = set_seed(workflow, 999)

        # Find the sampler node and check seed
        found_seed = False
        for node_id, node_data in modified.items():
            if node_data.get("class_type") == "KSampler":
                if node_data["inputs"]["seed"] == 999:
                    found_seed = True
                    break
        assert found_seed, "Seed not set correctly"

    def test_object_card_workflow_creation(self):
        """Test creating workflow for specific object."""
        from holodeck_core.image_generation.workflows import create_object_card_workflow

        workflow = create_object_card_workflow(" Wooden Chair",
                                            "Generate a {name} with wooden texture")

        # Verify the prompt contains the object name and template
        workflow_json = str(workflow)
        assert "Wooden Chair" in workflow_json
        assert "wooden texture" in workflow_json


@pytest.mark.skipif(not DEPS_AVAILABLE, reason="ComfyUI dependencies not available")
@pytest.mark.integration
class TestImageManager:
    """Test image management functionality."""

    @pytest.fixture
    def manager(self):
        """Create test image manager with temporary workspace."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir) / "workspace"
            workspace.mkdir()
            yield ImageManager(str(workspace))

    def test_session_directory_creation(self, manager):
        """Test session directory creation."""
        session_id = "test-session-123"
        session_dir = manager.get_session_dir(session_id)

        assert session_dir.exists()
        assert session_dir.name == session_id
        assert session_dir.parent == manager.sessions_dir

    def test_scene_reference_saving(self, manager):
        """Test saving scene reference image."""
        session_id = "test-session"
        manager.get_session_dir(session_id)

        # Create a dummy image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            image_path = tmp_file.name

        metadata = manager.save_scene_reference(
            session_id=session_id,
            image_path=image_path,
            prompt="A cozy bedroom",
            style="realistic",
            generation_time=5.5
        )

        assert metadata["image_path"] == f"sessions{os.sep}{session_id}{os.sep}scene_ref.png"
        assert metadata["prompt_used"] == "A cozy bedroom"
        assert metadata["style"] == "realistic"
        assert metadata["generation_time"] == 5.5
        assert "created_at" in metadata

        # Verify file was copied
        scene_ref_path = manager.sessions_dir / session_id / "scene_ref.png"
        assert scene_ref_path.exists()

        # Clean up
        Path(image_path).unlink()

    def test_object_card_saving(self, manager):
        """Test saving object card image."""
        session_id = "test-session"
        manager.get_session_dir(session_id)

        # Create a dummy image file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
            image_path = tmp_file.name

        metadata = manager.save_object_card(
            session_id=session_id,
            object_id="chair1",
            object_name="Wooden Chair",
            image_path=image_path,
            prompt="Generate a wooden chair",
            generation_time=3.2
        )

        assert metadata["object_id"] == "chair1"
        assert metadata["object_name"] == "Wooden Chair"
        assert metadata["card_image_path"] == f"sessions{os.sep}{session_id}{os.sep}object_cards{os.sep}chair1.png"
        assert metadata["prompt_used"] == "Generate a wooden chair"
        assert metadata["generation_time"] == 3.2
        assert metadata["qc_status"] == "pending"

        # Verify file was copied
        object_card_path = manager.sessions_dir / session_id / "object_cards" / "chair1.png"
        assert object_card_path.exists()

        # Clean up
        Path(image_path).unlink()

    def test_image_stats(self, manager):
        """Test getting image statistics."""
        session_id = "test-session"
        session_dir = manager.get_session_dir(session_id)

        # Create dummy files
        scene_ref = session_dir / "scene_ref.png"
        object_cards_dir = session_dir / "object_cards"
        object_cards_dir.mkdir()

        with open(scene_ref, 'wb') as f:
            f.write(b'dummy' * 1024)  # 1KB

        with open(object_cards_dir / "card1.png", 'wb') as f:
            f.write(b'card' * 2048)  # 2KB

        stats = manager.get_image_stats(session_id)

        assert stats["session_id"] == session_id
        assert stats["scene_ref_exists"] is True
        assert stats["object_card_count"] == 1
        assert stats["total_size_mb"] > 0  # Should be > 0

    def test_image_structure_validation(self, manager):
        """Test image structure validation."""
        session_id = "test-session"
        session_dir = manager.get_session_dir(session_id)

        # Test empty session
        validation = manager.validate_image_structure(session_id)
        assert not validation["valid"]
        assert any("Missing scene reference image" in issue for issue in validation["issues"])

        # Create scene reference
        scene_ref = session_dir / "scene_ref.png"
        scene_ref.touch()

        validation = manager.validate_image_structure(session_id)
        assert not validation["valid"]
        assert any("Missing object_cards directory" in issue for issue in validation["issues"])

        # Create object cards directory
        object_cards_dir = session_dir / "object_cards"
        object_cards_dir.mkdir()

        validation = manager.validate_image_structure(session_id)
        assert not validation["valid"]
        assert any("No object cards found" in issue for issue in validation["issues"])

        # Create an object card
        (object_cards_dir / "card1.png").touch()

        validation = manager.validate_image_structure(session_id)
        assert validation["valid"]
        assert len(validation["issues"]) == 0

    def test_temp_cleanup(self, manager):
        """Test temporary image cleanup."""
        # Create temp directory
        temp_dir = manager.workspace_root / "temp"
        temp_dir.mkdir(exist_ok=True)

        # Create some dummy files
        (temp_dir / "temp1.png").touch()
        (temp_dir / "temp2.png").touch()

        assert temp_dir.exists()

        # Clean up
        manager.clean_temp_images(str(temp_dir))

        assert not temp_dir.exists()


@pytest.mark.skipif(not DEPS_AVAILABLE, reason="ComfyUI dependencies not available")
@pytest.mark.integration
class TestIntegrationWorkflow:
    """Test end-to-end integration workflow."""

    @pytest.mark.asyncio
    async def test_mock_generation_workflow(self):
        """Test generation workflow with mocked ComfyUI."""
        with patch('holodeck_core.image_generation.comfyui_client.ComfyUIClient') as MockClient:
            # Setup mock client
            mock_client = MockClient()
            mock_client.test_connection = AsyncMock(return_value=True)
            mock_client.generate_image = AsyncMock(
                return_value=(
                    "/path/to/image.png",
                    {"generation_time": 3.5}
                )
            )

            # Test workflow
            manager = ImageManager()
            session_id = "test-session"

            # Test scene generation
            prompt = "A modern bedroom"
            image_path, metadata = await mock_client.generate_image(
                prompt=prompt,
                workflow_type="scene_ref"
            )

            assert image_path == "/path/to/image.png"
            assert metadata["generation_time"] == 3.5

            # Verify it was saved properly
            mock_client.generate_image.assert_called_once_with(
                prompt="A modern bedroom. Render in realistic style. 3-D view: x->right, y->backward, z->up. Well-lit, no extra objects.",
                workflow_type="scene_ref"
            )

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in generation workflow."""
        with patch('holodeck_core.image_generation.comfyui_client.ComfyUIClient') as MockClient:
            mock_client = MockClient()
            mock_client.test_connection = AsyncMock(return_value=False)

            # Should return error message when ComfyUI is not connected
            from servers.holodeck_mcp.tools.scene_analysis_tools import SceneAnalysisTools

            tools = SceneAnalysisTools()

            # This should return an error response instead of raising
            result = await tools_comfyui_integration.test_connection_error_handling(tools)

            assert "Error: Cannot connect to ComfyUI" in result

    @pytest.mark.asyncio
    async def test_batch_generation_success(self):
        """Test successful batch generation of object cards."""
        with patch('holodeck_core.image_generation.comfyui_client.ComfyUIClient') as MockClient:
            mock_client = MockClient()
            mock_client.test_connection = AsyncMock(return_value=True)

            # Mock successful generation for each object
            mock_client.generate_image = AsyncMock(
                side_effect=[
                    ("/path/to/chair.png", {"generation_time": 2.5}),
                    ("/path/to/table.png", {"generation_time": 3.0}),
                ]
            )

            from servers.holodeck_mcp.tools.scene_analysis_tools import SceneAnalysisTools

            tools = SceneAnalysisTools()

            # Mock objects list
            objects = [
                {"object_id": "chair1", "name": "Wooden Chair"},
                {"object_id": "table1", "name": "Oak Table"}
            ]

            result = await test_batch_generation_worker(tools, "test_session", objects)

            assert "3/3 object cards" in result
            assert "batch_" in result

            # Verify all cards were generated
            assert mock_client.generate_image.call_count == 2


# Helper functions for async testing
async def tools_comfyui_integration_test_connection_error_handling(tools):
    """Helper to test connection error handling."""
    session_id = "test-session"
    text = "Test scene"
    style = "realistic"

    arguments = {
        "session_id": session_id,
        "text": text,
        "style": style
    }

    # This mimics the actual tool call
    if not await tools.comfyui_client.test_connection():
        return [types.TextContent(
            type="text",
            text="Error: Cannot connect to ComfyUI server at 127.0.0.1:8188. Please ensure ComfyUI is running."
        )]


async def test_batch_generation_worker(tools, session_id, objects):
    """Helper to test batch generation."""
    arguments = {
        "session_id": session_id,
        "objects": objects
    }

    # This would normally call the actual method
    cards = []
    total_generation_time = 0.0

    for i, obj in enumerate(objects):
        object_id = obj.get("object_id", f"object_{i}")
        object_name = obj.get("name", "Unknown Object")

        prompt = (
            f"Please generate ONE PNG image of an isolated front-view {object_name} "
            f"with a transparent background, in realistic style"
        )

        try:
            image_path, metadata = await tools.comfyui_client.generate_image(
                prompt=prompt,
                workflow_type="object_card"
            )

            total_generation_time += metadata.get("generation_time", 0.0)
            cards.append({"object_name": object_name, "success": True})
        except:
            cards.append({"object_name": object_name, "success": False})

    return [types.TextContent(
        type="text",
        text=f"Generated {len([c for c in cards if c['success']])}/{len(cards)} object cards"
    )]