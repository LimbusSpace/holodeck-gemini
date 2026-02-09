"""
Unified VLM Client Factory Architecture Demo

This script demonstrates how to use the new unified VLM client architecture
with factory pattern integration.
"""

import asyncio
import os
from holodeck_core.clients.factory import LLMClientFactory
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend
from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer


async def demo_factory_architecture():
    """Demonstrate the factory architecture for VLM clients"""

    print("=== Unified VLM Client Factory Architecture Demo ===\n")

    # 1. Factory-based approach (recommended)
    print("1. Factory-based approach (recommended):")
    print("-" * 50)

    try:
        # Create LLM factory
        llm_factory = LLMClientFactory()
        print(f"Available LLM clients: {llm_factory.get_available_clients()}")

        # Create unified VLM client through factory
        vlm_client = llm_factory.create_client(
            client_name="unified_vlm",
            features=["object_extraction", "vision"]
        )
        print(f"Created VLM client: {type(vlm_client).__name__}")

        # Get backend information
        if hasattr(vlm_client, 'get_backend_info'):
            backend_info = vlm_client.get_backend_info()
            print(f"Backend info: {backend_info}")

        # Test connection (if API keys are configured)
        try:
            connection_ok = await vlm_client.test_connection()
            print(f"Connection test: {'✓ Success' if connection_ok else '✗ Failed'}")
        except Exception as e:
            print(f"Connection test skipped (no API keys): {e}")

    except Exception as e:
        print(f"Factory approach failed: {e}")
        print("This is expected if no API keys are configured")

    print("\n" + "=" * 60 + "\n")

    # 2. Direct instantiation approach (backward compatible)
    print("2. Direct instantiation approach (backward compatible):")
    print("-" * 50)

    try:
        # Create UnifiedVLMClient directly
        vlm_client = UnifiedVLMClient(backend=VLMBackend.AUTO)
        print(f"Created VLM client: {type(vlm_client).__name__}")
        print(f"Backend: {vlm_client.backend}")

        # Initialize the client
        await vlm_client.initialize()
        print("Client initialized successfully")

    except Exception as e:
        print(f"Direct approach failed: {e}")
        print("This is expected if no API keys are configured")

    print("\n" + "=" * 60 + "\n")

    # 3. SceneAnalyzer with factory mode
    print("3. SceneAnalyzer with factory mode:")
    print("-" * 50)

    try:
        # Create SceneAnalyzer using factory mode (recommended)
        analyzer = SceneAnalyzer(use_factory=True)
        print(f"SceneAnalyzer created with factory mode: {analyzer.use_factory}")

        # Create SceneAnalyzer using traditional mode (backward compatible)
        analyzer_traditional = SceneAnalyzer(api_key="demo_key", use_factory=False)
        print(f"Traditional SceneAnalyzer created: {not analyzer_traditional.use_factory}")

    except Exception as e:
        print(f"SceneAnalyzer demo failed: {e}")

    print("\n" + "=" * 60 + "\n")

    # 4. Feature support demonstration
    print("4. Feature support demonstration:")
    print("-" * 50)

    try:
        # Check what features are supported
        factory = LLMClientFactory()

        vlm_features = ["object_extraction", "vision", "scene_analysis"]
        for feature in vlm_features:
            supported = factory._supports_features("unified_vlm", [feature])
            print(f"  {feature}: {'✓ Supported' if supported else '✗ Not supported'}")

        # Check configuration status
        configured = factory._is_client_configured("unified_vlm")
        print(f"\nVLM client configured: {'✓ Yes' if configured else '✗ No'}")
        if not configured:
            print("  (Configure OPENAI_API_KEY or SILICONFLOW_API_KEY to enable)")

    except Exception as e:
        print(f"Feature check failed: {e}")

    print("\n" + "=" * 60 + "\n")

    print("Demo completed successfully!")
    print("\nKey benefits of the new architecture:")
    print("  • Automatic backend selection based on availability")
    print("  • Unified interface for multiple VLM providers")
    print("  • Factory pattern for easy client management")
    print("  • Backward compatibility with existing code")
    print("  • Feature detection and capability checking")
    print("  • Fallback mechanisms for robustness")


async def demo_object_extraction():
    """Demonstrate object extraction functionality (if configured)"""

    print("\n=== Object Extraction Demo ===\n")

    # Check if any VLM backend is configured
    if not (os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")):
        print("No VLM API keys configured. Skipping object extraction demo.")
        print("To enable this demo, set OPENAI_API_KEY or SILICONFLOW_API_KEY environment variables.")
        return

    try:
        # Create client through factory
        factory = LLMClientFactory()
        vlm_client = factory.create_client(
            client_name="unified_vlm",
            features=["object_extraction", "vision"]
        )

        # Test scene description
        test_scene = "A modern living room with a blue sofa, coffee table, and floor lamp"

        print(f"Extracting objects from: '{test_scene}'")

        # Extract objects
        scene_data = await vlm_client.extract_objects(test_scene)

        print(f"Extracted {len(scene_data.objects)} objects:")
        for obj in scene_data.objects:
            print(f"  - {obj.name} ({obj.object_id})")

        print(f"\nScene style: {scene_data.scene_style}")

    except Exception as e:
        print(f"Object extraction demo failed: {e}")


async def main():
    """Main demo function"""
    await demo_factory_architecture()

    # Only run object extraction demo if API keys are available
    if os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY"):
        await demo_object_extraction()
    else:
        print("\nSkipping object extraction demo (no API keys configured)")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())