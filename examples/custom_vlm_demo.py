"""
Custom VLM Model Demo

This script demonstrates how to use custom VLM models via URL + API Key + model name
with the unified VLM client architecture.
"""

import asyncio
import json
import os
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend
from holodeck_core.clients.factory import LLMClientFactory


async def demo_custom_model():
    """Demonstrate custom VLM model usage"""

    print("=== Custom VLM Model Demo ===\n")

    # Example 1: Direct instantiation with custom model
    print("1. Direct instantiation with custom model:")
    print("-" * 50)

    # Custom model configuration
    custom_config = {
        "base_url": "https://api.openai.com/v1",  # Example: OpenAI compatible API
        "api_key": "your-api-key-here",
        "model_name": "gpt-4-vision-preview",
        "headers": {
            # Additional headers if needed
        }
    }

    try:
        # Create client with custom backend
        vlm_client = UnifiedVLMClient(
            backend=VLMBackend.CUSTOM,
            custom_config=custom_config
        )

        print(f"Created custom VLM client for model: {custom_config['model_name']}")
        print(f"Base URL: {custom_config['base_url']}")

        # Initialize the client
        await vlm_client.initialize()
        print("Client initialized successfully")

        # Test connection (this will fail without real API key, but shows the flow)
        try:
            connection_ok = await vlm_client.test_connection()
            print(f"Connection test: {'✓ Success' if connection_ok else '✗ Failed'}")
        except Exception as e:
            print(f"Connection test failed (expected without real API key): {e}")

    except Exception as e:
        print(f"Custom model demo failed: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 2: Auto-selection with custom model
    print("2. Auto-selection with custom model:")
    print("-" * 50)

    try:
        # Create client with auto backend but custom config provided
        vlm_client = UnifiedVLMClient(
            backend=VLMBackend.AUTO,
            custom_config=custom_config
        )

        print(f"Created VLM client with auto-selection and custom config")

        # Initialize - should select custom backend if available
        await vlm_client.initialize()

        backend_info = vlm_client.get_backend_info()
        print(f"Selected backend: {backend_info['current_backend']}")

    except Exception as e:
        print(f"Auto-selection demo failed: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 3: Environment variable configuration
    print("3. Environment variable configuration:")
    print("-" * 50)

    # Example of how to configure via environment variables
    env_config_example = {
        "CUSTOM_VLM_BASE_URL": "https://api.example.com/v1",
        "CUSTOM_VLM_API_KEY": "your-api-key",
        "CUSTOM_VLM_MODEL_NAME": "custom-model-v1",
        "CUSTOM_VLM_HEADERS": '{"X-Custom-Header": "value"}'  # JSON string
    }

    print("Environment variable configuration example:")
    for key, value in env_config_example.items():
        print(f"  {key}={value}")

    # Function to create config from environment variables
    def create_config_from_env():
        """Create custom config from environment variables"""
        base_url = os.getenv("CUSTOM_VLM_BASE_URL")
        api_key = os.getenv("CUSTOM_VLM_API_KEY")
        model_name = os.getenv("CUSTOM_VLM_MODEL_NAME")
        headers_str = os.getenv("CUSTOM_VLM_HEADERS", "{}")

        if not all([base_url, api_key, model_name]):
            return None

        try:
            headers = json.loads(headers_str)
        except json.JSONDecodeError:
            headers = {}

        return {
            "base_url": base_url,
            "api_key": api_key,
            "model_name": model_name,
            "headers": headers
        }

    # Test environment-based configuration
    env_config = create_config_from_env()
    if env_config:
        print(f"✓ Environment configuration loaded")
        try:
            vlm_client = UnifiedVLMClient(
                backend=VLMBackend.CUSTOM,
                custom_config=env_config
            )
            print("✓ Client created with environment configuration")
        except Exception as e:
            print(f"✗ Environment configuration failed: {e}")
    else:
        print("✗ No environment configuration found (this is expected)")

    print("\n" + "=" * 60 + "\n")

    # Example 4: Factory integration with custom models
    print("4. Factory integration with custom models:")
    print("-" * 50)

    try:
        # Set environment variable for factory detection
        os.environ["CUSTOM_VLM_CONFIG"] = "enabled"

        factory = LLMClientFactory()

        # Check if unified_vlm is configured (should now include custom)
        configured = factory._is_client_configured("unified_vlm")
        print(f"Unified VLM configured (including custom): {'✓ Yes' if configured else '✗ No'}")

        # Create client through factory with custom config
        vlm_client = factory.create_client(
            client_name="unified_vlm",
            features=["object_extraction", "vision"]
        )
        print(f"✓ Created VLM client through factory: {type(vlm_client).__name__}")

    except Exception as e:
        print(f"Factory integration demo failed: {e}")

    print("\n" + "=" * 60 + "\n")

    # Example 5: Object extraction with custom model (simulated)
    print("5. Object extraction with custom model (simulated):")
    print("-" * 50)

    # Simulated API response for demo purposes
    simulated_response = {
        "scene_style": "modern minimalist",
        "objects": [
            {
                "name": "ergonomic_office_chair",
                "category": "furniture",
                "size": [0.6, 0.6, 1.2],
                "visual_description": "Black ergonomic office chair with lumbar support",
                "position": [1.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "must_exist": True
            },
            {
                "name": "wooden_desk",
                "category": "furniture",
                "size": [1.2, 0.6, 0.75],
                "visual_description": "Light wood desk with clean lines",
                "position": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0],
                "must_exist": True
            }
        ]
    }

    print("Simulated custom model response:")
    print(json.dumps(simulated_response, indent=2))

    print("\n" + "=" * 60 + "\n")

    print("Demo completed successfully!")
    print("\nCustom VLM model usage patterns:")
    print("  1. Direct instantiation with custom_config parameter")
    print("  2. Auto-selection when custom config is provided")
    print("  3. Environment variable configuration")
    print("  4. Factory integration with custom models")
    print("\nTo use your own custom model:")
    print("  1. Prepare your API endpoint URL")
    print("  2. Get your API key")
    print("  3. Know your model name")
    print("  4. Configure using any of the methods above")


async def demo_real_custom_extraction():
    """Demonstrate real object extraction with custom model (if configured)"""

    print("\n=== Real Custom Model Extraction Demo ===\n")

    # Check if custom model is configured via environment variables
    custom_config = None
    if all([
        os.getenv("CUSTOM_VLM_BASE_URL"),
        os.getenv("CUSTOM_VLM_API_KEY"),
        os.getenv("CUSTOM_VLM_MODEL_NAME")
    ]):
        custom_config = {
            "base_url": os.getenv("CUSTOM_VLM_BASE_URL"),
            "api_key": os.getenv("CUSTOM_VLM_API_KEY"),
            "model_name": os.getenv("CUSTOM_VLM_MODEL_NAME"),
            "headers": json.loads(os.getenv("CUSTOM_VLM_HEADERS", "{}"))
        }

    if not custom_config:
        print("Custom model not configured via environment variables.")
        print("To enable this demo, set the following environment variables:")
        print("  - CUSTOM_VLM_BASE_URL")
        print("  - CUSTOM_VLM_API_KEY")
        print("  - CUSTOM_VLM_MODEL_NAME")
        print("  - CUSTOM_VLM_HEADERS (optional, JSON format)")
        return

    try:
        # Create client with custom model
        vlm_client = UnifiedVLMClient(
            backend=VLMBackend.CUSTOM,
            custom_config=custom_config
        )

        # Test scene description
        test_scene = "A modern office with a desk, chair, computer monitor, and bookshelf"

        print(f"Extracting objects from: '{test_scene}'")

        # Extract objects
        scene_data = await vlm_client.extract_objects(test_scene)

        print(f"✓ Extracted {len(scene_data.objects)} objects:")
        for obj in scene_data.objects:
            print(f"  - {obj.name} ({obj.category})")

        print(f"\nScene style: {scene_data.scene_style}")

    except Exception as e:
        print(f"Real extraction demo failed: {e}")


async def main():
    """Main demo function"""
    await demo_custom_model()

    # Only run real extraction if custom model is configured
    if all([
        os.getenv("CUSTOM_VLM_BASE_URL"),
        os.getenv("CUSTOM_VLM_API_KEY"),
        os.getenv("CUSTOM_VLM_MODEL_NAME")
    ]):
        await demo_real_custom_extraction()
    else:
        print("\nSkipping real extraction demo (custom model not configured)")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())