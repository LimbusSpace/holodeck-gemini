"""
Example demonstrating custom VLM configuration using environment variables
for URL + API Key + model name, integrated with standardized prompt templates.
"""

import asyncio
import os
from pathlib import Path

# Add the project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend


def setup_environment_variables():
    """Setup environment variables for custom VLM configuration."""
    # In production, these would be set in your environment
    # For this example, we'll set them programmatically

    os.environ["CUSTOM_VLM_BASE_URL"] = "https://api.example.com/v1"
    os.environ["CUSTOM_VLM_API_KEY"] = "your-custom-api-key"
    os.environ["CUSTOM_VLM_MODEL_NAME"] = "your-custom-model"

    print("✅ Environment variables set:")
    print(f"   CUSTOM_VLM_BASE_URL: {os.environ.get('CUSTOM_VLM_BASE_URL')}")
    print(f"   CUSTOM_VLM_API_KEY: {os.environ.get('CUSTOM_VLM_API_KEY')[:8]}... (hidden)")
    print(f"   CUSTOM_VLM_MODEL_NAME: {os.environ.get('CUSTOM_VLM_MODEL_NAME')}")
    print()


async def demonstrate_custom_vlm_with_env_vars():
    """Demonstrate custom VLM usage with environment variables and standardized prompts."""
    print("=== Custom VLM with Environment Variables Example ===\n")

    # Setup environment variables
    setup_environment_variables()

    try:
        # Example 1: Auto backend selection (will pick CUSTOM if env vars are set)
        print("1. Auto backend selection with environment variables...")
        client_auto = UnifiedVLMClient(backend=VLMBackend.AUTO)

        if await client_auto.test_connection():
            print("✅ Auto backend connection successful")

            # Get backend info
            backend_info = client_auto.get_backend_info()
            print(f"   Selected backend: {backend_info['current_backend']}")
            print(f"   Client type: {backend_info['client_type']}")
        else:
            print("❌ Auto backend connection failed")
        print()

        # Example 2: Explicit custom backend (reads from environment variables)
        print("2. Explicit custom backend with environment variables...")
        client_custom = UnifiedVLMClient(backend=VLMBackend.CUSTOM)

        if await client_custom.test_connection():
            print("✅ Custom backend connection successful")

            # Test reference image generation
            print("   Testing reference image generation...")
            try:
                reference_image = await client_custom.generate_reference_image(
                    description="A modern living room with sofa, coffee table, and TV",
                    style="realistic",
                    language="en"
                )
                print(f"   ✅ Generated reference image: {len(reference_image)} bytes")

                # Save image
                with open("custom_reference_image.png", "wb") as f:
                    f.write(reference_image)
                print("   ✅ Saved as 'custom_reference_image.png'")

            except Exception as e:
                print(f"   ❌ Reference image generation failed: {e}")

            # Test object image generation
            print("   Testing object image generation...")
            try:
                object_image = await client_custom.generate_object_image(
                    obj_name="modern sofa",
                    style="realistic",
                    reference_context="A modern living room with sofa, coffee table, and TV",
                    language="en"
                )
                print(f"   ✅ Generated object image: {len(object_image)} bytes")

                # Save image
                with open("custom_sofa_isolated.png", "wb") as f:
                    f.write(object_image)
                print("   ✅ Saved as 'custom_sofa_isolated.png'")

            except Exception as e:
                print(f"   ❌ Object image generation failed: {e}")

        else:
            print("❌ Custom backend connection failed")
        print()

        # Example 3: Multilingual support with custom backend
        print("3. Multilingual support with custom backend...")

        # English prompt
        try:
            ref_en = await client_custom.generate_reference_image(
                description="A cozy bedroom with bed and nightstand",
                style="realistic",
                language="en"
            )
            print(f"   ✅ English reference image: {len(ref_en)} bytes")
        except Exception as e:
            print(f"   ❌ English reference image failed: {e}")

        # Chinese prompt
        try:
            ref_zh = await client_custom.generate_reference_image(
                description="一个舒适的卧室，配有床和床头柜",
                style="写实",
                language="zh"
            )
            print(f"   ✅ Chinese reference image: {len(ref_zh)} bytes")
        except Exception as e:
            print(f"   ❌ Chinese reference image failed: {e}")

        # Auto-detection
        try:
            ref_auto = await client_custom.generate_reference_image(
                description="A modern 现代厨房 kitchen with island 岛台",
                style="realistic"
                # language=None (auto-detection)
            )
            print(f"   ✅ Auto-detected reference image: {len(ref_auto)} bytes")
        except Exception as e:
            print(f"   ❌ Auto-detected reference image failed: {e}")

        print()

        # Example 4: Backend information
        print("4. Backend configuration information...")
        backend_info = client_custom.get_backend_info()
        print(f"   Current backend: {backend_info['current_backend']}")
        print(f"   Requested backend: {backend_info['requested_backend']}")
        print(f"   Available backends: {backend_info['available_backends']}")
        print(f"   Configured backends: {backend_info['configured_backends']}")
        print(f"   Client type: {backend_info['client_type']}")
        print()

        print("=== Example completed successfully! ===")

    except Exception as e:
        print(f"❌ Error: {e}")


def demonstrate_environment_variable_usage():
    """Show different ways to use environment variables."""
    print("=== Environment Variable Usage Patterns ===\n")

    print("Pattern 1: Set environment variables before running")
    print("```bash")
    print("export CUSTOM_VLM_BASE_URL=https://api.example.com/v1")
    print("export CUSTOM_VLM_API_KEY=your-api-key")
    print("export CUSTOM_VLM_MODEL_NAME=your-model-name")
    print("python your_script.py")
    print("```")
    print()

    print("Pattern 2: Use .env file")
    print("```env")
    print("CUSTOM_VLM_BASE_URL=https://api.example.com/v1")
    print("CUSTOM_VLM_API_KEY=your-api-key")
    print("CUSTOM_VLM_MODEL_NAME=your-model-name")
    print("```")
    print()

    print("Pattern 3: Set programmatically (as shown in this example)")
    print("```python")
    print("os.environ['CUSTOM_VLM_BASE_URL'] = 'https://api.example.com/v1'")
    print("os.environ['CUSTOM_VLM_API_KEY'] = 'your-api-key'")
    print("os.environ['CUSTOM_VLM_MODEL_NAME'] = 'your-model-name'")
    print("```")
    print()

    print("Pattern 4: Docker environment variables")
    print("```dockerfile")
    print("ENV CUSTOM_VLM_BASE_URL=https://api.example.com/v1")
    print("ENV CUSTOM_VLM_API_KEY=your-api-key")
    print("ENV CUSTOM_VLM_MODEL_NAME=your-model-name")
    print("```")
    print()


if __name__ == "__main__":
    # Show usage patterns
    demonstrate_environment_variable_usage()

    # Run the main demonstration
    asyncio.run(demonstrate_custom_vlm_with_env_vars())