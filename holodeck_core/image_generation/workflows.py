"""ComfyUI workflow templates for image generation.

Contains predefined workflows for scene reference images and object cards.
"""

from typing import Dict, Any

# Scene reference image workflow
# Based on the working workflow from comfyui文生图.json
SCENE_REF_WORKFLOW: Dict[str, Any] = {
    "79": {
        "inputs": {
            "unet_name": "z_image_turbo_bf16.safetensors",
            "weight_dtype": "default"
        },
        "class_type": "UNETLoader"
    },
    "80": {
        "inputs": {
            "clip_name": "qwen_3_4b.safetensors",
            "type": "qwen_image",
            "device": "default"
        },
        "class_type": "CLIPLoader"
    },
    "81": {
        "inputs": {
            "seed": 42,
            "steps": 10,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1,
            "model": ["79", 0],
            "positive": ["85", 0],
            "negative": ["93", 0],
            "latent_image": ["84", 0]
        },
        "class_type": "KSampler"
    },
    "82": {
        "inputs": {
            "samples": ["81", 0],
            "vae": ["86", 0]
        },
        "class_type": "VAEDecode"
    },
    "83": {
        "inputs": {
            "filename_prefix": "scene_ref",
            "images": ["82", 0]
        },
        "class_type": "SaveImage"
    },
    "84": {
        "inputs": {
            "width": 1024,
            "height": 1024,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "85": {
        "inputs": {
            "text": "A cozy bedroom with modern minimalist style. Render in realistic style. 3-D view: x->right, y->backward, z->up. Well-lit, no extra objects.",
            "clip": ["80", 0]
        },
        "class_type": "CLIPTextEncode"
    },
    "86": {
        "inputs": {
            "vae_name": "ae.safetensors"
        },
        "class_type": "VAELoader"
    },
    "93": {
        "inputs": {
            "conditioning": ["85", 0]
        },
        "class_type": "ConditioningZeroOut"
    }
}

# Object card workflow
# Similar structure but adjusted for object generation
OBJECT_CARD_WORKFLOW: Dict[str, Any] = {
    "79": {
        "inputs": {
            "unet_name": "z_image_turbo_bf16.safetensors",
            "weight_dtype": "default"
        },
        "class_type": "UNETLoader"
    },
    "80": {
        "inputs": {
            "clip_name": "qwen_3_4b.safetensors",
            "type": "qwen_image",
            "device": "default"
        },
        "class_type": "CLIPLoader"
    },
    "81": {
        "inputs": {
            "seed": 42,
            "steps": 10,
            "cfg": 1,
            "sampler_name": "euler",
            "scheduler": "simple",
            "denoise": 1,
            "model": ["79", 0],
            "positive": ["85", 0],
            "negative": ["93", 0],
            "latent_image": ["84", 0]
        },
        "class_type": "KSampler"
    },
    "82": {
        "inputs": {
            "samples": ["81", 0],
            "vae": ["86", 0]
        },
        "class_type": "VAEDecode"
    },
    "83": {
        "inputs": {
            "filename_prefix": "object_card",
            "images": ["82", 0]
        },
        "class_type": "SaveImage"
    },
    "84": {
        "inputs": {
            "width": 1024,
            "height": 1024,
            "batch_size": 1
        },
        "class_type": "EmptyLatentImage"
    },
    "85": {
        "inputs": {
            "text": "Please generate ONE PNG image of an isolated front-view King Bed with a transparent background, in realistic style, with shapes and style similar to the reference scene.",
            "clip": ["80", 0]
        },
        "class_type": "CLIPTextEncode"
    },
    "86": {
        "inputs": {
            "vae_name": "ae.safetensors"
        },
        "class_type": "VAELoader"
    },
    "93": {
        "inputs": {
            "conditioning": ["85", 0]
        },
        "class_type": "ConditioningZeroOut"
    }
}

# Utility functions for workflow manipulation
def inject_prompt(workflow: Dict[str, Any], prompt: str) -> Dict[str, Any]:
    """Inject prompt into the workflow's text encoding node.

    Args:
        workflow: ComfyUI workflow dictionary
        prompt: Text prompt to inject

    Returns:
        Modified workflow with prompt injected
    """
    modified = workflow.copy()

    # Find CLIPTextEncode node and inject prompt
    for node_id, node_data in modified.items():
        if node_data.get("class_type") == "CLIPTextEncode":
            # Skip negative prompt nodes (empty text initially)
            if "text" in node_data["inputs"]:
                current_text = node_data["inputs"]["text"]
                # Check if it's a list (ComfyUI API format)
                if isinstance(current_text, list):
                    if len(current_text) > 0 and isinstance(current_text[0], str):
                        # This is likely the positive prompt
                        node_data["inputs"]["text"] = [prompt]
                else:
                    # It's a string
                    if current_text.strip():
                        node_data["inputs"]["text"] = prompt

    return modified

def set_resolution(workflow: Dict[str, Any], width: int, height: int) -> Dict[str, Any]:
    """Set image resolution in the workflow.

    Args:
        workflow: ComfyUI workflow dictionary
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Modified workflow with new resolution
    """
    modified = workflow.copy()

    # Find EmptyLatentImage node and set dimensions
    for node_id, node_data in modified.items():
        if node_data.get("class_type") == "EmptyLatentImage":
            node_data["inputs"]["width"] = width
            node_data["inputs"]["height"] = height
            break

    return modified

def set_seed(workflow: Dict[str, Any], seed: int) -> Dict[str, Any]:
    """Set random seed in the workflow.

    Args:
        workflow: ComfyUI workflow dictionary
        seed: Random seed value

    Returns:
        Modified workflow with new seed
    """
    modified = workflow.copy()

    # Find KSampler node and set seed
    for node_id, node_data in modified.items():
        if node_data.get("class_type") == "KSampler":
            node_data["inputs"]["seed"] = seed
            break

    return modified

def create_object_card_workflow(object_name: str, prompt_template: str = None) -> Dict[str, Any]:
    """Create a modified object card workflow for a specific object.

    Args:
        object_name: Name of the object
        prompt_template: Custom prompt template (uses {name} placeholder)

    Returns:
        Modified workflow for the specific object
    """
    workflow = OBJECT_CARD_WORKFLOW.copy()

    # Replace object name in prompt
    if prompt_template:
        prompt = prompt_template.format(name=object_name)
    else:
        prompt = (
            f"Please generate ONE PNG image of an isolated front-view {object_name} "
            f"with a transparent background, in realistic style, "
            f"with shapes and style similar to the reference scene."
        )

    return inject_prompt(workflow, prompt)