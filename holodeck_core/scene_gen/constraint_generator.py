"""
Constraint Generator - From Natural Language to Spatial Constraints

This module generates spatial constraints from scene descriptions and failure traces.
Provides VLM integration layer for automatic constraint generation.
"""

from typing import List, Dict, Optional, Any
import json
import base64
import aiohttp
import os
import re

SYSTEM_PROMPT = """You are a spatial relationship analyzer.
Generate valid JSON constraints based on scene descriptions,
object information and the reference image.

Output the constraints in a strict sequence:
once an object has appeared as a target,
it must not later appear as a source.

For each object, output all of its source-type constraints
in true consecutive order in the list - they must be
physically adjacent without any other constraints interleaved."""

USER_PROMPT_TEMPLATE = """You are a spatial relationship analyzer. Given a scene description
and a list of objects with their IDs, generate spatial constraints between the objects.

Scene Description:
{description}

Available Objects:
{objects_text}

Generate spatial constraints in the following JSON format:
[
    {{"type": "relative", "relation": "right of|left of|in front of|behind|side of|on|above", "source": "object_id", "target": "object_id"}},
    {{"type": "distance", "relation": "near|far", "source": "object_id", "target": "object_id"}},
    {{"type": "rotation", "relation": "face to", "source": "object_id", "target": "object_id"}}
]

Guidelines:
1. Only include meaningful spatial relationships that match the description
2. Use the exact object IDs from the available objects list
3. Focus on the most important spatial relationships
4. Avoid redundant relationships
5. Return only valid JSON, no additional text
6. For example, if "a chair to the right of a table", relation = right of, source = chair, target = table
7. An object should either be on the ground (default) or on/above another object
8. Use "on" for resting on surface. Use "above" for floating/suspended.

Generate the constraints:"""


class ConstraintGenerator:
    """Generates constraints from scene descriptions and failure traces."""

    @staticmethod
    def generate_constraints_from_text(
        scene_description: str,
        objects: List[Any],
        previous_trace: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Generate constraints from scene text description (sync fallback)."""
        return type('ConstraintSet', (), {'relations': []})()

    @staticmethod
    async def generate_constraints_with_vlm(
        scene_description: str,
        objects: List[Dict[str, Any]],
        ref_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate constraints using VLM with Prompt 6 format.

        Args:
            scene_description: Scene description text
            objects: List of object dicts with id, name, visual_description
            ref_image_path: Optional path to reference image

        Returns:
            Dict with 'relations' key containing constraint list
        """
        # Build objects text
        objects_text = "\n".join(
            f"- {obj.get('id', obj.get('object_id', f'obj_{i}'))}: {obj.get('name', 'unknown')}"
            for i, obj in enumerate(objects)
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            description=scene_description,
            objects_text=objects_text
        )

        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        # Add image if provided
        image_b64 = None
        if ref_image_path and os.path.exists(ref_image_path):
            with open(ref_image_path, 'rb') as f:
                image_b64 = base64.b64encode(f.read()).decode('utf-8')
            messages[1] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}}
                ]
            }

        # Call VLM API
        base_url = os.getenv("CUSTOM_VLM_BASE_URL", "").rstrip('/')
        api_key = os.getenv("CUSTOM_VLM_API_KEY", "")
        model_name = os.getenv("CUSTOM_VLM_MODEL_NAME", "")

        if not all([base_url, api_key, model_name]):
            return {"relations": []}

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.1
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        return {"relations": []}

                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]

                    # Parse JSON from response
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', content)
                    if json_match:
                        json_str = json_match.group(1).strip()
                    else:
                        json_match = re.search(r'\[[\s\S]*\]', content)
                        json_str = json_match.group(0) if json_match else "[]"

                    constraints = json.loads(json_str)
                    return {"relations": constraints if isinstance(constraints, list) else []}

        except Exception:
            return {"relations": []}

    @staticmethod
    def relationships_to_constraints(
        relationships: List[Dict[str, Any]],
        object_mapping: Dict[str, str]
    ) -> List[Any]:
        """Convert parsed relationships to spatial constraints."""
        constraints = []

        # Placeholder implementation
        # Would map relationship types to actual constraint objects
        for rel in relationships:
            # Creates constraint stub
            constraint = type('SpatialConstraint', (), {
                'type': rel.get('type'),
                'source': rel.get('source'),
                'target': rel.get('target'),
                'priority': rel.get('priority', 'secondary')
            })()
            constraints.append(constraint)

        return constraints

    @staticmethod
    def regenerate_after_failure(
        original_constraints: Any,
        trace: Dict[str, Any],
        adjustment_strategy: str = "relax"
    ) -> Any:
        """Regenerate constraints after a failure with trace feedback."""
        modified_relations = []

        if not hasattr(original_constraints, 'relations'):
            return original_constraints

        for constraint in original_constraints.relations:
            # If constraint involves the failed object, modify it
            if (getattr(constraint, 'source', None) == trace.get('failed_object_id') or
                getattr(constraint, 'target', None) in trace.get('placed_objects', [])):

                if adjustment_strategy == "relax":
                    # Make constraint softer
                    constraint.priority = "secondary"
                elif adjustment_strategy == "remove":
                    # Skip constraint
                    continue
                else:
                    # Keep as is
                    pass

            modified_relations.append(constraint)

        return type('ConstraintSet', (), {'relations': modified_relations})()

def generate_constraints_from_scene(
    scene_description: str,
    objects: List[Any],
    previous_trace: Optional[Dict[str, Any]] = None
) -> Any:
    """Generate constraints from a scene description."""
    return ConstraintGenerator.generate_constraints_from_text(
        scene_description, objects, previous_trace
    )