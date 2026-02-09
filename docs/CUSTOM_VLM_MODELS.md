# Custom VLM Models Support

## Overview

The Unified VLM Client now supports custom Vision-Language Model backends through URL + API Key + model name configuration. This allows you to integrate any OpenAI-compatible VLM API into your Holodeck pipeline.

## Features

✅ **Universal API Support**: Works with any OpenAI-compatible API endpoint
✅ **Flexible Configuration**: Multiple ways to configure custom models
✅ **Automatic Integration**: Seamlessly integrates with existing factory architecture
✅ **Fallback Support**: Robust error handling and fallback mechanisms
✅ **Environment Variables**: Easy configuration through environment variables
✅ **Full Feature Support**: Supports object extraction, vision processing, and scene analysis

## Quick Start

### Method 1: Direct Configuration

```python
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend

# Configure your custom model
custom_config = {
    "base_url": "https://api.your-provider.com/v1",
    "api_key": "your-api-key-here",
    "model_name": "your-model-name",
    "headers": {
        "X-Custom-Header": "custom-value"  # Optional additional headers
    }
}

# Create client with custom backend
vlm_client = UnifiedVLMClient(
    backend=VLMBackend.CUSTOM,
    custom_config=custom_config
)

# Use the client
scene_data = await vlm_client.extract_objects("A modern living room")
```

### Method 2: Environment Variables

```bash
# Set environment variables
export CUSTOM_VLM_BASE_URL="https://api.your-provider.com/v1"
export CUSTOM_VLM_API_KEY="your-api-key-here"
export CUSTOM_VLM_MODEL_NAME="your-model-name"
export CUSTOM_VLM_HEADERS='{"X-Custom-Header": "custom-value"}'
```

```python
import os
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend

# Load configuration from environment variables
def create_config_from_env():
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

# Create client
custom_config = create_config_from_env()
if custom_config:
    vlm_client = UnifiedVLMClient(
        backend=VLMBackend.CUSTOM,
        custom_config=custom_config
    )
```

### Method 3: Auto-Selection with Custom Priority

```python
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend

# Provide custom config and let the system auto-select the best backend
# Custom models have the highest priority
vlm_client = UnifiedVLMClient(
    backend=VLMBackend.AUTO,  # Will select CUSTOM if available
    custom_config={
        "base_url": "https://api.your-provider.com/v1",
        "api_key": "your-api-key-here",
        "model_name": "your-model-name"
    }
)
```

### Method 4: Factory Integration

```python
from holodeck_core.clients.factory import LLMClientFactory

# Set environment variable to enable custom model detection
os.environ["CUSTOM_VLM_CONFIG"] = "enabled"

# Create factory
factory = LLMClientFactory()

# Create VLM client through factory (will include custom models)
vlm_client = factory.create_client(
    client_name="unified_vlm",
    features=["object_extraction", "vision"]
)
```

## Configuration Options

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `base_url` | string | Base URL of the API endpoint | `https://api.openai.com/v1` |
| `api_key` | string | API key for authentication | `sk-xxxxxxxxxxxxxxxxxxxx` |
| `model_name` | string | Name of the model to use | `gpt-4-vision-preview` |

### Optional Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `headers` | dict | Additional HTTP headers | `{}` |

## API Compatibility

The custom VLM client expects your API to be compatible with the OpenAI Chat Completions API format:

### Request Format

```json
{
  "model": "your-model-name",
  "messages": [
    {
      "role": "system",
      "content": "System prompt for object extraction"
    },
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "User prompt"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "data:image/png;base64,..."
          }
        }
      ]
    }
  ],
  "max_tokens": 2048,
  "temperature": 0.1
}
```

### Expected Response Format

```json
{
  "choices": [
    {
      "message": {
        "content": "{\"scene_style\": \"modern\", \"objects\": [...]}"
      }
    }
  ]
}
```

The response content should be a JSON string containing:

```json
{
  "scene_style": "modern",
  "objects": [
    {
      "name": "object_name",
      "category": "furniture",
      "size": [1.0, 1.0, 1.0],
      "visual_description": "detailed description",
      "position": [0.0, 0.0, 0.0],
      "rotation": [0.0, 0.0, 0.0],
      "must_exist": true
    }
  ]
}
```

## Supported APIs

The custom VLM client works with any API that supports the OpenAI Chat Completions format, including:

- **OpenAI GPT-4 Vision** and compatible models
- **Azure OpenAI Service**
- **OpenRouter** and other OpenAI-compatible proxy services
- **Local LLM servers** with OpenAI-compatible APIs (e.g., LM Studio, Ollama)
- **Custom VLM deployments** with OpenAI-compatible endpoints

## Examples

### Example 1: OpenAI GPT-4 Vision

```python
custom_config = {
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your-openai-key",
    "model_name": "gpt-4-vision-preview",
    "headers": {}
}

vlm_client = UnifiedVLMClient(
    backend=VLMBackend.CUSTOM,
    custom_config=custom_config
)
```

### Example 2: Azure OpenAI

```python
custom_config = {
    "base_url": "https://your-resource.openai.azure.com/openai/deployments/your-deployment",
    "api_key": "your-azure-api-key",
    "model_name": "gpt-4-vision",
    "headers": {
        "api-key": "your-azure-api-key"
    }
}
```

### Example 3: Local LLM Server (LM Studio)

```python
custom_config = {
    "base_url": "http://localhost:1234/v1",
    "api_key": "not-needed-for-local",  # Often not required for local servers
    "model_name": "local-vision-model",
    "headers": {}
}
```

### Example 4: OpenRouter

```python
custom_config = {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "your-openrouter-key",
    "model_name": "openai/gpt-4-vision-preview",
    "headers": {
        "HTTP-Referer": "https://your-app.com",
        "X-Title": "Your App Name"
    }
}
```

## Integration with SceneAnalyzer

The custom VLM models work seamlessly with the SceneAnalyzer:

```python
from holodeck_core.scene_analysis.scene_analyzer import SceneAnalyzer

# Use factory mode (recommended) - will automatically use custom models if configured
analyzer = SceneAnalyzer(use_factory=True)

# Or use direct mode with custom VLM client
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend

custom_vlm = UnifiedVLMClient(
    backend=VLMBackend.CUSTOM,
    custom_config=custom_config
)

# Use the custom client directly
scene_data = await custom_vlm.extract_objects("A modern office space")
```

## Error Handling and Fallbacks

### Automatic Fallbacks

1. **API Connection Errors**: Falls back to alternative backends if available
2. **JSON Parsing Errors**: Returns structured fallback data
3. **Rate Limiting**: Respects API rate limits and retry mechanisms
4. **Model Errors**: Graceful degradation to simpler object extraction

### Custom Error Handling

```python
try:
    scene_data = await vlm_client.extract_objects(scene_text)
except Exception as e:
    print(f"Custom VLM extraction failed: {e}")
    # Implement your custom fallback logic here
```

## Testing Your Custom Model

### Connection Test

```python
# Test if your custom model is accessible
connection_ok = await vlm_client.test_connection()
if connection_ok:
    print("✓ Custom model is accessible")
else:
    print("✗ Custom model connection failed")
```

### Feature Support Test

```python
# Check what features your custom model supports
features = ["object_extraction", "vision", "scene_analysis"]
for feature in features:
    supported = await vlm_client.supports_feature(feature)
    print(f"{feature}: {'✓ Supported' if supported else '✗ Not supported'}")
```

### Backend Information

```python
# Get detailed information about the current backend
backend_info = vlm_client.get_backend_info()
print(f"Current backend: {backend_info['current_backend']}")
print(f"Available backends: {backend_info['available_backends']}")
print(f"Client type: {backend_info['client_type']}")
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `CUSTOM_VLM_BASE_URL` | Base URL of your API endpoint | Yes |
| `CUSTOM_VLM_API_KEY` | API key for authentication | Yes |
| `CUSTOM_VLM_MODEL_NAME` | Name of the model to use | Yes |
| `CUSTOM_VLM_HEADERS` | Additional headers (JSON format) | No |

Example:

```bash
export CUSTOM_VLM_BASE_URL="https://api.example.com/v1"
export CUSTOM_VLM_API_KEY="your-api-key"
export CUSTOM_VLM_MODEL_NAME="your-model"
export CUSTOM_VLM_HEADERS='{"X-Custom-Header": "value", "Authorization": "Bearer token"}'
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check if the base URL is correct
   - Verify the API key is valid
   - Ensure the endpoint is accessible from your environment

2. **Authentication Error**
   - Verify your API key format
   - Check if additional headers are required
   - Ensure the API key has the necessary permissions

3. **Model Not Found**
   - Verify the model name is correct
   - Check if the model is available in your API plan
   - Ensure the model supports vision capabilities

4. **JSON Parsing Error**
   - Check if your API returns valid JSON
   - Verify the response format matches expectations
   - Ensure the model is properly instructed to return JSON

### Debug Mode

Enable debug logging to see detailed API interactions:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("holodeck_core.scene_analysis.clients.unified_vlm")
logger.setLevel(logging.DEBUG)
```

## Best Practices

1. **Security**
   - Store API keys in environment variables, not in code
   - Use least-privilege API keys when possible
   - Rotate API keys regularly

2. **Performance**
   - Use appropriate timeout values for your API
   - Implement caching for repeated requests
   - Batch requests when possible

3. **Reliability**
   - Always implement error handling and fallbacks
   - Monitor API usage and costs
   - Test with various input scenarios

4. **Configuration**
   - Use environment variables for different deployment environments
   - Validate configuration before using the client
   - Document your custom model setup

## Migration from Existing Code

### From OpenAI Client

```python
# Before
from holodeck_core.scene_analysis.clients.openai_client import OpenAIClient
client = OpenAIClient(api_key="your-key")

# After (with custom configuration)
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend
client = UnifiedVLMClient(
    backend=VLMBackend.CUSTOM,
    custom_config={
        "base_url": "https://api.openai.com/v1",
        "api_key": "your-key",
        "model_name": "gpt-4-vision-preview"
    }
)
```

### From SiliconFlow Client

```python
# Before
from holodeck_core.scene_analysis.clients.siliconflow_client import SiliconFlowClient
client = SiliconFlowClient(api_key="your-key")

# After (with custom configuration)
from holodeck_core.scene_analysis.clients.unified_vlm import UnifiedVLMClient, VLMBackend
client = UnifiedVLMClient(
    backend=VLMBackend.CUSTOM,
    custom_config={
        "base_url": "https://api.siliconflow.cn/v1",
        "api_key": "your-key",
        "model_name": "zai-org/GLM-4.6V"
    }
)
```

## Advanced Usage

### Custom Headers and Authentication

```python
custom_config = {
    "base_url": "https://api.example.com/v1",
    "api_key": "your-api-key",
    "model_name": "your-model",
    "headers": {
        "X-API-Version": "2023-01-01",
        "X-Organization": "your-org",
        "Authorization": "Bearer your-token",  # Alternative auth method
        "Custom-Header": "custom-value"
    }
}
```

### Multiple Custom Models

```python
# Define multiple custom configurations
custom_models = {
    "primary": {
        "base_url": "https://api.primary.com/v1",
        "api_key": "primary-key",
        "model_name": "primary-model"
    },
    "fallback": {
        "base_url": "https://api.fallback.com/v1",
        "api_key": "fallback-key",
        "model_name": "fallback-model"
    }
}

# Use primary model, fallback on error
for model_name, config in custom_models.items():
    try:
        client = UnifiedVLMClient(
            backend=VLMBackend.CUSTOM,
            custom_config=config
        )
        scene_data = await client.extract_objects(scene_text)
        break  # Success, exit loop
    except Exception as e:
        print(f"{model_name} failed: {e}")
        continue
```

## Conclusion

The custom VLM model support provides a flexible and powerful way to integrate any OpenAI-compatible Vision-Language Model into your Holodeck pipeline. With multiple configuration options, robust error handling, and seamless integration with the existing architecture, you can easily extend Holodeck's capabilities to work with your preferred VLM providers.