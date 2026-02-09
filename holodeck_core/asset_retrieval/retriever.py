# -*- coding: utf-8 -*-
"""Asset Retriever - searches local cache using CLIP embeddings."""

import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

# Lazy load CLIP to avoid import overhead
_clip_model = None
_clip_processor = None


def _load_clip():
    """Lazy load CLIP model."""
    global _clip_model, _clip_processor
    if _clip_model is None:
        try:
            from transformers import CLIPModel, CLIPProcessor
            _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            logger.info("CLIP model loaded")
        except Exception as e:
            logger.warning(f"Failed to load CLIP: {e}")
    return _clip_model, _clip_processor


class AssetRetriever:
    """Retrieves assets from local cache using CLIP semantic matching."""

    def __init__(self, cache_dir: Optional[Path] = None, similarity_threshold: float = 0.25):
        self.cache_dir = cache_dir or Path("workspace/asset_cache")
        self.index_path = self.cache_dir / "clip_index.json"
        self.similarity_threshold = similarity_threshold
        self._index: List[Dict[str, Any]] = []
        self._embeddings: Optional[np.ndarray] = None
        self._load_index()

    def _load_index(self):
        """Load pre-computed CLIP index."""
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text())
                self._index = data.get("assets", [])
                if data.get("embeddings"):
                    self._embeddings = np.array(data["embeddings"], dtype=np.float32)
                logger.info(f"Loaded CLIP index with {len(self._index)} assets")
            except Exception as e:
                logger.warning(f"Failed to load CLIP index: {e}")

    def build_index(self):
        """Build CLIP index from local assets."""
        if not self.cache_dir.exists():
            return

        model, processor = _load_clip()
        if model is None:
            return

        import torch
        assets = []
        texts = []

        for glb_file in self.cache_dir.glob("**/*.glb"):
            name = glb_file.stem.replace("_", " ").replace("-", " ")
            assets.append({"name": name, "path": str(glb_file)})
            texts.append(name)

        if not texts:
            return

        # Compute embeddings
        with torch.no_grad():
            inputs = processor(text=texts, return_tensors="pt", padding=True, truncation=True)
            embeddings = model.get_text_features(**inputs).numpy()
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        self._index = assets
        self._embeddings = embeddings

        # Save index
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps({
            "assets": assets,
            "embeddings": embeddings.tolist()
        }, indent=2))
        logger.info(f"Built CLIP index with {len(assets)} assets")

    def search(self, description: str) -> Optional[Dict[str, Any]]:
        """Search for asset matching description using CLIP."""
        if not self._index or self._embeddings is None:
            return self._fallback_search(description)

        model, processor = _load_clip()
        if model is None:
            return self._fallback_search(description)

        import torch
        with torch.no_grad():
            inputs = processor(text=[description], return_tensors="pt", padding=True, truncation=True)
            query_emb = model.get_text_features(**inputs).numpy()
            query_emb = query_emb / np.linalg.norm(query_emb)

        # Cosine similarity
        similarities = (self._embeddings @ query_emb.T).flatten()
        best_idx = int(np.argmax(similarities))
        best_score = float(similarities[best_idx])

        if best_score >= self.similarity_threshold:
            asset = self._index[best_idx]
            logger.info(f"CLIP match: '{asset['name']}' (score={best_score:.3f})")
            return {"path": asset["path"], "source": "local", "score": best_score}

        return None

    def _fallback_search(self, description: str) -> Optional[Dict[str, Any]]:
        """Fallback to keyword matching if CLIP unavailable."""
        desc_lower = description.lower()
        for asset in self._index:
            name = asset.get("name", "").lower()
            if name in desc_lower or desc_lower in name:
                return {"path": asset["path"], "source": "local"}
        return None
