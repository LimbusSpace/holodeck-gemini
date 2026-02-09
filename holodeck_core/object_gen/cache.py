"""Image hash cache system for 3D asset generation.

Implements a dual-layer caching system (session + global) to avoid regenerating
the same 3D assets from identical object cards.
"""

import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class ImageHashCache:
    """Dual-layer cache system (session-level + global-level) for 3D assets."""

    def __init__(self, workspace_root: str = "workspace"):
        """Initialize cache system.

        Args:
            workspace_root: Root workspace directory
        """
        self.workspace_root = Path(workspace_root)
        self.session_cache: Dict[str, Dict] = {}  # In-memory session cache
        self.global_cache: Dict[str, Dict] = {}   # In-memory global cache

        # Cache TTL (days)
        self.session_ttl = None  # Lives for session duration
        self.global_ttl_days = int(os.getenv("HOLODECK_GLOBAL_CACHE_TTL_DAYS", "30"))

        # Cache size limits (optional)
        self.max_cache_size_mb = int(os.getenv("HOLODECK_MAX_CACHE_SIZE_MB", "10240"))  # 10GB

    def calculate_image_hash(self, image_path: str) -> str:
        """Calculate SHA256 hash of image file.

        Args:
            image_path: Path to image file

        Returns:
            64-character hex string
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        sha256_hash = hashlib.sha256()
        with open(image_path, "rb") as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _get_session_cache_dir(self, session_id: str) -> Path:
        """Get session cache directory path."""
        return self.workspace_root / "sessions" / session_id / "cache"

    def _get_global_cache_dir(self) -> Path:
        """Get global cache directory path."""
        return self.workspace_root / "caches" / "generated_assets"

    def _get_session_cache_file(self, session_id: str) -> Path:
        """Get session cache file path."""
        return self._get_session_cache_dir(session_id) / "image_hashes.json"

    def _get_global_cache_file(self) -> Path:
        """Get global cache manifest path."""
        return self._get_global_cache_dir() / "manifest.json"

    def _load_cache_file(self, cache_path: Path) -> Dict:
        """Load cache from JSON file."""
        if not cache_path.exists():
            return {}

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)

            # Filter expired entries for global cache
            if cache_path.name == "manifest.json":
                current_time = time.time()
                expired_keys = []
                ttl_seconds = self.global_ttl_days * 24 * 3600

                for key, entry in cache.items():
                    timestamp = entry.get('timestamp', 0)
                    if current_time - timestamp > ttl_seconds:
                        expired_keys.append(key)

                # Remove expired entries
                for key in expired_keys:
                    del cache[key]
                    # Also remove the actual GLB file if exists
                    glb_path = self._get_global_cache_dir() / f"{key}.glb"
                    if glb_path.exists():
                        glb_path.unlink()

                if expired_keys:
                    self._save_cache_file(cache_path, cache)
                    logger.info(f"Cleaned up {len(expired_keys)} expired global cache entries")

            return cache
        except Exception as e:
            logger.error(f"Failed to load cache file {cache_path}: {e}")
            return {}

    def _save_cache_file(self, cache_path: Path, cache: Dict):
        """Save cache to JSON file."""
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save cache file {cache_path}: {e}")

    def generate_cache_key(self, image_hash: str, **params) -> str:
        """Generate cache key from image hash and parameters.

        Args:
            image_hash: SHA256 hash of the image
            **params: Generation parameters (e.g., foreground_ratio, texture_resolution)

        Returns:
            Cache key string
        """
        # Sort params for consistent key generation
        param_str = "_".join(f"{k}_{v}" for k, v in sorted(params.items()))
        return f"{image_hash}_{param_str}" if param_str else image_hash

    def lookup_cache(self, image_path: str, session_id: str, **params) -> Optional[Tuple[str, Dict]]:
        """Check if asset exists in cache.

        Priority: Session cache -> Global cache

        Args:
            image_path: Path to source image
            session_id: Current session ID
            **params: Generation parameters

        Returns:
            Tuple of (glb_path, metadata) if found, None otherwise
        """
        # Calculate image hash
        try:
            image_hash = self.calculate_image_hash(image_path)
        except Exception as e:
            logger.error(f"Failed to calculate image hash: {e}")
            return None

        cache_key = self.generate_cache_key(image_hash, **params)

        # First check session cache (faster, session-specific)
        if session_id:
            session_cache_file = self._get_session_cache_file(session_id)
            session_cache = self._load_cache_file(session_cache_file)

            if cache_key in session_cache:
                entry = session_cache[cache_key]
                cache_path = session_cache_file.parent / entry["relative_path"]
                if cache_path.exists():
                    logger.info(f"Session cache hit for {session_id[:8]}: {cache_key[:16]}...")
                    return str(cache_path), entry["metadata"]
                # Clean up stale entry if file doesn't exist
                del session_cache[cache_key]
                self._save_cache_file(session_cache_file, session_cache)

        # Then check global cache (cross-session reuse)
        global_cache_file = self._get_global_cache_file()
        global_cache = self._load_cache_file(global_cache_file)

        if cache_key in global_cache:
            entry = global_cache[cache_key]
            cache_path = self._get_global_cache_dir() / f"{cache_key}.glb"
            if cache_path.exists():
                logger.info(f"Global cache hit: {cache_key[:16]}...")

                # Also copy to session cache for faster future access
                if session_id:
                    self._add_to_session_cache(
                        session_id, cache_key, cache_path, entry["metadata"]
                    )

                return str(cache_path), entry["metadata"]
            # Clean up stale entry if file doesn't exist
            del global_cache[cache_key]
            self._save_cache_file(global_cache_file, global_cache)

        logger.debug(f"Cache miss: {cache_key[:16]}...")
        return None

    def store_in_cache(
        self,
        image_path: str,
        glb_path: str,
        metadata: Dict,
        session_id: str,
        **params
    ) -> None:
        """Store generated asset in both cache layers.

        Args:
            image_path: Path to source image
            glb_path: Path to generated GLB file
            metadata: Generation metadata
            session_id: Current session ID
            **params: Generation parameters
        """
        try:
            image_hash = self.calculate_image_hash(image_path)
        except Exception as e:
            logger.error(f"Failed to calculate image hash for caching: {e}")
            return

        cache_key = self.generate_cache_key(image_hash, **params)
        glb_source = Path(glb_path)

        # Store in session cache
        if session_id:
            self._add_to_session_cache(session_id, cache_key, glb_source, metadata)

        # Store in global cache
        self._add_to_global_cache(cache_key, glb_source, metadata)

        logger.info(f"Stored in cache: {cache_key[:16]}...")

        # Check cache size and cleanup if needed
        self._cleanup_cache_if_needed()

    def _add_to_session_cache(
        self,
        session_id: str,
        cache_key: str,
        glb_source: Path,
        metadata: Dict
    ) -> None:
        """Add entry to session cache."""
        session_cache_file = self._get_session_cache_file(session_id)
        session_cache = self._load_cache_file(session_cache_file)

        Session_cache_dir = session_cache_file.parent

        # Copy GLB to session cache if not already there
        relative_path = f"assets/{Path(glb_source).name}"
        glb_dest = Session_cache_dir / relative_path
        glb_dest.parent.mkdir(parents=True, exist_ok=True)

        if not glb_dest.exists() and glb_source != glb_dest:
            import shutil
            shutil.copy2(glb_source, glb_dest)

        # Update cache entry
        session_cache[cache_key] = {
            "relative_path": relative_path,
            "metadata": metadata,
            "timestamp": time.time()
        }

        self._save_cache_file(session_cache_file, session_cache)

    def _add_to_global_cache(
        self,
        cache_key: str,
        glb_source: Path,
        metadata: Dict
    ) -> None:
        """Add entry to global cache."""
        global_cache_dir = self._get_global_cache_dir()
        global_cache_file = self._get_global_cache_file()
        global_cache = self._load_cache_file(global_cache_file)

        # Copy GLB to global cache if not already there
        glb_dest = global_cache_dir / f"{cache_key}.glb"
        glb_dest.parent.mkdir(parents=True, exist_ok=True)

        if not glb_dest.exists() and glb_source != glb_dest:
            import shutil
            shutil.copy2(glb_source, glb_dest)

        # Update cache entry
        global_cache[cache_key] = {
            "metadata": metadata,
            "timestamp": time.time(),
            "usage_count": global_cache.get(cache_key, {}).get("usage_count", 0) + 1
        }

        self._save_cache_file(global_cache_file, global_cache)

    def _cleanup_cache_if_needed(self) -> None:
        """Clean up global cache if size exceeds limit."""
        if self.max_cache_size_mb <= 0:
            return  # No limit

        global_cache_dir = self._get_global_cache_dir()
        global_cache_file = self._get_global_cache_file()
        global_cache = self._load_cache_file(global_cache_file)

        # Calculate total cache size
        total_size_mb = 0
        for file in global_cache_dir.glob("*.glb"):
            total_size_mb += file.stat().st_size / (1024 * 1024)

        if total_size_mb <= self.max_cache_size_mb:
            return

        logger.info(f"Cache size {total_size_mb:.1f}MB exceeds limit {self.max_cache_size_mb}MB, cleaning up...")

        # Sort entries by timestamp and usage count
        entries = []
        for cache_key, entry in global_cache.items():
            entries.append((
                entry.get("timestamp", 0),
                entry.get("usage_count", 0),
                cache_key,
                entry
            ))

        # Sort by oldest first, then lowest usage
        entries.sort()

        # Remove oldest entries until under limit
        target_size_mb = self.max_cache_size_mb * 0.8  # Leave some headroom
        removed_count = 0

        for timestamp, usage_count, cache_key, entry in entries:
            glb_path = global_cache_dir / f"{cache_key}.glb"
            if glb_path.exists():
                file_size_mb = glb_path.stat().st_size / (1024 * 1024)
                glb_path.unlink()
                total_size_mb -= file_size_mb
                del global_cache[cache_key]
                removed_count += 1

            if total_size_mb <= target_size_mb:
                break

        self._save_cache_file(global_cache_file, global_cache)
        logger.info(f"Cache cleanup completed: removed {removed_count} old entries")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        global_cache_dir = self._get_global_cache_dir()
        global_cache_file = self._get_global_cache_file()
        global_cache = self._load_cache_file(global_cache_file)

        # Calculate global cache stats
        total_mb = sum(
            f.stat().st_size / (1024 * 1024)
            for f in global_cache_dir.glob("*.glb")
        )

        return {
            "global_entries": len(global_cache),
            "global_size_mb": round(total_mb, 2),
            "global_limit_mb": self.max_cache_size_mb,
            "ttl_days": self.global_ttl_days
        }