"""Prompt templates aligned with HOLODECK 2.0 paper."""

import os
import yaml
from pathlib import Path
from typing import Any, Dict


class PromptManager:
    """Manages prompt templates for Scene Analysis."""

    def __init__(self):
        """Initialize prompt manager."""
        self.templates = {}
        self._load_templates()

    def _load_templates(self):
        """Load prompt templates from YAML files."""
        prompt_dir = Path(__file__).parent

        # Load each template file
        template_files = {
            "scene_reference": "scene_reference.yaml",
            "object_extraction": "object_extraction.yaml",
            "card_generation": "card_generation.yaml",
            "qc_evaluation": "qc_evaluation.yaml",
            "background_extraction": "background_extraction.yaml"
        }

        for template_name, filename in template_files.items():
            filepath = prompt_dir / filename
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    template_data = yaml.safe_load(f)
                    self.templates[template_name] = template_data
            else:
                # Use inline templates as fallback
                self.templates[template_name] = self._get_fallback_template(template_name)

    def get_prompt(self, template_name: str, variables: Dict[str, Any] = None) -> str:
        """Get formatted prompt template.

        Args:
            template_name: Name of the template
            variables: Variables to format into the template

        Returns:
            Formatted prompt string
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")

        template = self.templates[template_name]

        if isinstance(template, dict) and "template" in template:
            prompt = template["template"]
        elif isinstance(template, str):
            prompt = template
        else:
            prompt = str(template)

        # Format variables
        if variables:
            try:
                prompt = prompt.format(**variables)
            except KeyError as e:
                raise ValueError(f"Missing variable for template '{template_name}': {e}")

        return prompt

    def _get_fallback_template(self, template_name: str) -> Dict[str, str]:
        """Get fallback template if file doesn't exist."""
        templates = {
            "scene_reference": {
                "template": """Generate a 3D scene reference image for: "{text}"

Style: {style}

Requirements:
- 3-D view: x->right, y->backward, z->up
- Well-lit, no extra objects
- No humans or animals
- Consistent style across objects"""
            },
            "object_extraction": {
                "template": """Based on scene description and reference image, extract visible objects.

Scene Description: "{scene_text}"
Reference Image: [attached]

CRITICAL CONSTRAINTS:
1. Origin (0,0,0) at centre of floor/ground
2. Size range: [0.1, 5.0] metres
3. MAIN objects only - ignore small decorative items
4. NO background elements:
   - No walls, windows, ceiling, sky, roads, terrain
   - No curtains, carpets as separate objects
5. NO components/parts:
   - No handles, knobs, drawers, legs as separate objects
   - No faucets when bathtub present
6. Output ONLY valid JSON schema"""
            },
            "card_generation": {
                "template": """Generate ONE PNG image of an isolated front-view {object_name}
with transparent background.

Style: consistent with reference scene
Description: {visual_desc}

Requirements:
- Single object only
- Front view, centered
- Transparent background (PNG)
- No shadows/reflections"""
            },
            "qc_evaluation": {
                "template": """Analyze these object cards and identify redundant components.

Rule: If card A shows a component that is already part of card B,
mark card A for deletion.

Output format:
{{
  "delete_cards": ["faucet_001.png"],
  "keep_cards": ["bathtub_001.png", ...]
}}"""
            },
            "background_extraction": {
                "template": """Replace the entire image with ONE seamless, tileable PNG
of the main floor/ground texture.

Instructions:
- Ignore all objects, walls, ceiling
- Extract ONLY the floor/ground pattern
- Make it homogeneous and repeating smoothly
- NO transparency - solid texture only
- Must be tileable/seamless"""
            }
        }

        return templates.get(template_name, {"template": "Template not found"})