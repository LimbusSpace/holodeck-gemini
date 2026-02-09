# -*- coding: utf-8 -*-
"""Asset Decision Engine - determines generation vs retrieval path."""

import re


class AssetDecisionEngine:
    """Evaluates whether an object should be generated or retrieved."""

    # Keywords indicating high generation necessity
    HIGH_SCORE_KEYWORDS = [
        "定制", "custom", "独特", "unique", "特殊", "special",
        "赛博朋克", "cyberpunk", "蒸汽朋克", "steampunk",
        "未来", "futuristic", "科幻", "sci-fi",
        "艺术", "artistic", "手工", "handmade",
        "复古", "vintage", "古董", "antique",
    ]

    # Keywords indicating low generation necessity (common objects)
    LOW_SCORE_KEYWORDS = [
        "普通", "ordinary", "标准", "standard", "常见", "common",
        "简单", "simple", "基本", "basic", "通用", "generic",
    ]

    def __init__(self):
        self.anchor_weights = {}  # Reserved for world memory sync

    def evaluate(self, object_desc: str) -> float:
        """Evaluate generation necessity score (0-1)."""
        return self._rule_based_score(object_desc)

    def _rule_based_score(self, desc: str) -> float:
        """Rule-based scoring for quick filtering."""
        desc_lower = desc.lower()
        score = 0.5  # Default neutral score

        # Check high-score keywords
        for kw in self.HIGH_SCORE_KEYWORDS:
            if kw in desc_lower:
                score += 0.15

        # Check low-score keywords
        for kw in self.LOW_SCORE_KEYWORDS:
            if kw in desc_lower:
                score -= 0.15

        # Apply anchor weights if available
        for anchor, weight in self.anchor_weights.items():
            if anchor in desc_lower:
                score += weight

        return max(0.0, min(1.0, score))
