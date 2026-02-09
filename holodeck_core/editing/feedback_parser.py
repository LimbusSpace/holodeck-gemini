"""Feedback parsing module for interpreting user editing requests.

Implements natural language understanding for scene editing feedback,
converting user text into structured edit operations.
"""

import json
import logging
import re
from typing import Dict, Any, Optional, List

from holodeck_core.schemas.constraints import SpatialConstraint
from holodeck_core.storage import WorkspaceManager


class FeedbackParser:
    """Parses user feedback into structured edit operations."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Spatial relationship keywords
        self.spatial_keywords = {
            "left": ["left", "to the left", "on the left", "left side"],
            "right": ["right", "to the right", "on the right", "right side"],
            "front": ["front", "in front", "before"],
            "behind": ["behind", "back", "after"],
            "above": ["above", "on top", "over"],
            "below": ["below", "under", "underneath", "beneath"],
            "near": ["near", "close to", "next to", "beside", "by"],
            "far": ["far from", "away from", "distant from"],
            "on": ["on", "on top of", "placed on"]
        }

        # Edit type keywords
        self.edit_keywords = {
            "add": ["add", "new", "create", "include", "insert"],
            "delete": ["delete", "remove", "take out", "get rid of", "eliminate"],
            "replace": ["replace", "swap", "change to", "different", "alternative"],
            "asset": ["texture", "material", "color", "style", "appearance", "look", "visual"],
            "layout": ["move", "position", "place", "relocate", "arrange", "layout"]
        }

        # Object category keywords
        self.object_categories = {
            "furniture": ["chair", "table", "desk", "bed", "sofa", "couch", "stool", "bench"],
            "lighting": ["lamp", "light", "chandelier", "sconce", "lamppost"],
            "decoration": ["painting", "art", "vase", "statue", "ornament", "decoration"],
            "electronics": ["tv", "television", "monitor", "computer", "speaker", "device"],
            "storage": ["shelf", "cabinet", "drawer", "bookcase", "wardrobe"]
        }

    def parse_feedback(self, session_id: str, feedback_text: str) -> Dict[str, Any]:
        """Parse user feedback into structured edit operation.

        Args:
            session_id: Scene session identifier
            feedback_text: User feedback text

        Returns:
            Dict containing parsed edit information
        """
        try:
            # Load scene objects for reference
            workspace = WorkspaceManager()
            objects = workspace.load_objects(session_id)

            # Normalize feedback text
            normalized_feedback = self._normalize_text(feedback_text)

            # Identify focus object
            focus_object_id = self._identify_focus_object(normalized_feedback, objects)

            # Determine edit type
            edit_type = self._determine_edit_type(normalized_feedback, focus_object_id)

            # Generate interpreted intent
            interpreted_intent = self._generate_interpreted_intent(
                normalized_feedback, focus_object_id, edit_type
            )

            # Calculate confidence score
            confidence_score = self._calculate_confidence(
                normalized_feedback, focus_object_id, edit_type
            )

            # Generate constraints for layout edits
            delta_constraints = []
            if edit_type == "layout" and focus_object_id:
                delta_constraints = self._generate_spatial_constraints(
                    normalized_feedback, focus_object_id, objects
                )

            # Identify assets to regenerate
            assets_to_regenerate = []
            if edit_type in ["asset", "replace"] and focus_object_id:
                assets_to_regenerate = [focus_object_id]

            result = {
                "focus_object_id": focus_object_id,
                "edit_type": edit_type,
                "interpreted_intent": interpreted_intent,
                "confidence_score": confidence_score,
                "delta_constraints": delta_constraints,
                "removed_constraints": [],  # Could be extended for constraint removal
                "assets_to_regenerate": assets_to_regenerate
            }

            self.logger.debug(f"Parsed feedback: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing feedback: {e}")
            # Return safe defaults
            return {
                "focus_object_id": None,
                "edit_type": "layout",
                "interpreted_intent": feedback_text,
                "confidence_score": 0.0,
                "delta_constraints": [],
                "removed_constraints": [],
                "assets_to_regenerate": []
            }

    def parse_object_specification(self, spec_text: str) -> Dict[str, Any]:
        """Parse object specification text into object data structure.

        Args:
            spec_text: Object specification text

        Returns:
            Dict containing object data
        """
        try:
            # Extract object name and properties
            normalized_spec = self._normalize_text(spec_text)

            # Identify object category
            category = self._identify_object_category(normalized_spec)

            # Extract size hints
            size_hints = self._extract_size_hints(normalized_spec)

            # Generate object ID
            import uuid
            object_id = f"obj_{uuid.uuid4().hex[:8]}"

            # Create object structure
            object_data = {
                "object_id": object_id,
                "name": self._extract_object_name(normalized_spec),
                "category": category,
                "size_m": size_hints,
                "initial_pose": {"pos": [0, 0, 0], "rot_euler": [0, 0, 0]},
                "visual_desc": spec_text,
                "must_exist": True,
                "version": 1
            }

            return object_data

        except Exception as e:
            self.logger.error(f"Error parsing object specification: {e}")
            # Return default object
            import uuid
            return {
                "object_id": f"obj_{uuid.uuid4().hex[:8]}",
                "name": "unknown",
                "category": "furniture",
                "size_m": [1.0, 1.0, 1.0],
                "initial_pose": {"pos": [0, 0, 0], "rot_euler": [0, 0, 0]},
                "visual_desc": spec_text,
                "must_exist": True,
                "version": 1
            }

    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing."""
        # Convert to lowercase and remove extra whitespace
        normalized = re.sub(r'\s+', ' ', text.lower().strip())
        return normalized

    def _identify_focus_object(self, feedback: str, objects: Dict[str, Any]) -> Optional[str]:
        """Identify the focus object from feedback text."""
        scene_objects = objects.get("objects", [])

        # First, try exact name matching
        for obj in scene_objects:
            obj_name = obj.get("name", "").lower()
            if obj_name in feedback:
                return obj.get("object_id")

        # Then try category matching
        for obj in scene_objects:
            obj_category = obj.get("category", "").lower()
            if obj_category in feedback:
                return obj.get("object_id")

        # Finally, try visual description keywords
        for obj in scene_objects:
            visual_desc = obj.get("visual_desc", "").lower()
            desc_words = visual_desc.split()
            for word in desc_words:
                if len(word) > 3 and word in feedback:
                    return obj.get("object_id")

        return None

    def _determine_edit_type(self, feedback: str, focus_object_id: Optional[str]) -> str:
        """Determine the type of edit operation."""
        # Score each edit type based on keyword matches
        scores = {}

        for edit_type, keywords in self.edit_keywords.items():
            score = sum(1 for keyword in keywords if keyword in feedback)
            scores[edit_type] = score

        # If no object identified, add operation is likely
        if not focus_object_id:
            scores["add"] = scores.get("add", 0) + 2

        # Return the edit type with highest score
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        # Default to layout if no clear indication
        return "layout"

    def _generate_interpreted_intent(self, feedback: str, focus_object_id: Optional[str],
                                   edit_type: str) -> str:
        """Generate AI-interpreted intent from feedback."""
        if edit_type == "add":
            return f"Add new object based on: {feedback}"
        elif edit_type == "delete":
            return f"Remove object {focus_object_id}"
        elif edit_type == "replace":
            return f"Replace {focus_object_id} with different version"
        elif edit_type == "asset":
            return f"Update {focus_object_id} appearance: {feedback}"
        elif edit_type == "layout":
            return f"Reposition {focus_object_id}: {feedback}"
        else:
            return f"Edit scene: {feedback}"

    def _calculate_confidence(self, feedback: str, focus_object_id: Optional[str],
                            edit_type: str) -> float:
        """Calculate confidence score for the interpretation."""
        confidence = 0.5  # Base confidence

        # Increase confidence if focus object identified
        if focus_object_id:
            confidence += 0.2

        # Increase confidence based on keyword matches
        keyword_matches = 0
        for keywords in self.edit_keywords.values():
            keyword_matches += sum(1 for keyword in keywords if keyword in feedback)

        confidence += min(0.3, keyword_matches * 0.1)

        # Decrease confidence for ambiguous feedback
        if len(feedback.split()) < 3:
            confidence -= 0.2

        return max(0.0, min(1.0, confidence))

    def _generate_spatial_constraints(self, feedback: str, focus_object_id: str,
                                    objects: Dict[str, Any]) -> List[SpatialConstraint]:
        """Generate spatial constraints from feedback text."""
        constraints = []
        scene_objects = objects.get("objects", [])

        # Find reference objects mentioned in feedback
        reference_objects = []
        for obj in scene_objects:
            obj_name = obj.get("name", "").lower()
            if obj_name in feedback and obj["object_id"] != focus_object_id:
                reference_objects.append(obj)

        # Generate constraints based on spatial keywords
        for ref_obj in reference_objects:
            ref_id = ref_obj["object_id"]

            # Check for each spatial relationship
            for relation_type, keywords in self.spatial_keywords.items():
                if any(keyword in feedback for keyword in keywords):
                    constraint = self._create_spatial_constraint(
                        relation_type, focus_object_id, ref_id, feedback
                    )
                    if constraint:
                        constraints.append(constraint)
                    break  # Only one constraint per reference object

        return constraints

    def _create_spatial_constraint(self, relation_type: str, object_a: str,
                                 object_b: str, feedback: str) -> Optional[SpatialConstraint]:
        """Create a specific spatial constraint."""
        try:
            # Map simple relation types to proper enum values
            type_mapping = {
                "left": ("relative", "left of"),
                "right": ("relative", "right of"),
                "front": ("relative", "in front of"),
                "behind": ("relative", "behind"),
                "above": ("vertical", "above"),
                "below": ("vertical", "below"),
                "on": ("vertical", "on"),
                "near": ("distance", "near"),
                "far": ("distance", "far")
            }

            if relation_type not in type_mapping:
                self.logger.warning(f"Unknown relation type: {relation_type}")
                return None

            constraint_type, relation = type_mapping[relation_type]

            constraint_params = {
                "type": constraint_type,
                "relation": relation,
                "source": object_a,
                "target": object_b
            }

            # Extract distance thresholds for near/far relationships
            if relation_type in ["near", "far"]:
                # Look for distance specifications
                distance_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m|meter|meters)', feedback)
                if distance_match:
                    constraint_params["threshold_m"] = float(distance_match.group(1))
                else:
                    constraint_params["threshold_m"] = 1.0 if relation_type == "near" else 3.0

            # Extract angle tolerances for directional relationships
            if relation_type in ["left", "right", "front", "behind"]:
                angle_match = re.search(r'(\d+)\s*deg', feedback)
                if angle_match:
                    constraint_params["deg_tolerance"] = int(angle_match.group(1))
                else:
                    constraint_params["deg_tolerance"] = 15

            return SpatialConstraint(**constraint_params)

        except Exception as e:
            self.logger.warning(f"Error creating spatial constraint: {e}")
            return None

    def _identify_object_category(self, spec_text: str) -> str:
        """Identify object category from specification text."""
        category_scores = {}

        for category, keywords in self.object_categories.items():
            score = sum(1 for keyword in keywords if keyword in spec_text)
            category_scores[category] = score

        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]

        return "furniture"  # Default category

    def _extract_size_hints(self, spec_text: str) -> List[float]:
        """Extract size hints from specification text."""
        # Look for explicit size mentions
        size_patterns = [
            r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*by\s*(\d+(?:\.\d+)?)\s*by\s*(\d+(?:\.\d+)?)'
        ]

        for pattern in size_patterns:
            match = re.search(pattern, spec_text)
            if match:
                return [float(x) for x in match.groups()]

        # Default sizes based on category
        category = self._identify_object_category(spec_text)
        default_sizes = {
            "furniture": [1.0, 1.0, 1.0],
            "lighting": [0.3, 0.3, 0.8],
            "decoration": [0.2, 0.2, 0.3],
            "electronics": [0.5, 0.4, 0.1],
            "storage": [0.8, 0.4, 1.2]
        }

        return default_sizes.get(category, [1.0, 1.0, 1.0])

    def _extract_object_name(self, spec_text: str) -> str:
        """Extract object name from specification text."""
        # Look for the first noun that could be an object name
        words = spec_text.split()

        # Check against known object categories
        for category, keywords in self.object_categories.items():
            for keyword in keywords:
                if keyword in words:
                    return keyword

        # Return first meaningful word
        for word in words:
            if len(word) > 2 and word not in ["add", "new", "create", "the", "a", "an"]:
                return word

        return "object"