"""
Image manager
Manages screenshot memory cache, thumbnail generation, compression and persistence strategies
"""

import base64
import io
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.logger import get_logger
from core.paths import ensure_dir, get_data_dir
from PIL import Image

logger = get_logger(__name__)


class ImageManager:
    """Image manager - Manages screenshot memory cache and persistence"""

    def __init__(
        self,
        memory_cache_size: int = 500,  # Maximum number of images to keep in memory (default increased to 500, can be overridden by configuration)
        thumbnail_size: Tuple[int, int] = (1280, 720),  # Default landscape baseline (unused in dynamic scaling but kept for backward compat)
        thumbnail_quality: int = 75,  # Thumbnail quality
        max_age_hours: int = 24,  # Maximum retention time for temporary files
        base_dir: Optional[
            str
        ] = None,  # Screenshot storage root directory (override config)
        enable_memory_first: bool = True,  # Enable memory-first storage strategy
        memory_ttl: int = 180,  # TTL for memory-only images (seconds) - Updated to 180s to meet recommended minimum
    ):
        # Try to read custom path from configuration
        try:
            from core.settings import get_settings

            configured = get_settings().get(
                "image.memory_cache_size", memory_cache_size
            )
            # Override default value if configuration exists and is numeric
            memory_cache_size = (
                int(configured) if configured is not None else memory_cache_size
            )
        except Exception as e:
            logger.debug(
                f"Failed to read config image.memory_cache_size, using default value: {e}"
            )

        self.memory_cache_size = memory_cache_size
        self.thumbnail_size = thumbnail_size
        self.thumbnail_quality = thumbnail_quality
        self.max_age_hours = max_age_hours
        self.scale_threshold = 1440  # Scale when any side exceeds this threshold
        self.scale_factor = 0.75  # When scaling is needed, scale to 75% of original size

        # Memory-first storage configuration
        self.enable_memory_first = enable_memory_first
        self.memory_ttl = memory_ttl

        # Determine storage directory (supports user configuration)
        self.base_dir = self._resolve_base_dir(base_dir)
        self.thumbnails_dir = ensure_dir(self.base_dir / "thumbnails")

        # Memory cache: hash -> (base64_data, timestamp)
        self._memory_cache: OrderedDict[str, Tuple[str, datetime]] = OrderedDict()

        # Image metadata: hash -> (timestamp, is_persisted)
        self._image_metadata: dict[str, Tuple[datetime, bool]] = {}

        # Persistence statistics tracking
        self.persistence_stats = {
            "total_persist_attempts": 0,
            "successful_persists": 0,
            "failed_persists": 0,
            "cache_misses": 0,
            "already_persisted": 0,
        }

        self._ensure_directories()

        logger.debug(
            f"ImageManager initialized: cache_size={memory_cache_size}, "
            f"default_thumbnail_size={thumbnail_size}, "
            f"scale_threshold={self.scale_threshold}, "
            f"scale_factor={self.scale_factor}, "
            f"quality={thumbnail_quality}, base_dir={self.base_dir}"
        )

        # Validation: Warn if TTL seems too low for reliable persistence
        if self.memory_ttl < 120:
            logger.warning(
                f"Memory TTL ({self.memory_ttl}s) is low and may cause image persistence failures. "
                f"Recommended: ≥180s for reliable persistence. "
                f"Increase 'image.memory_ttl_multiplier' in config.toml to fix."
            )

    def _select_thumbnail_size(self, img: Image.Image) -> Tuple[int, int]:
        """Choose target size based on orientation and resolution"""
        width, height = img.size
        # Orientation awareness is implicit; we scale both sides equally
        if width > self.scale_threshold or height > self.scale_threshold:
            return (
                max(1, int(width * self.scale_factor)),
                max(1, int(height * self.scale_factor)),
            )
        return width, height

    def _resolve_base_dir(self, override: Optional[str]) -> Path:
        """Parse screenshot root directory based on configuration or override parameter"""
        candidates: List[Path] = []

        if override:
            candidates.append(Path(override).expanduser())

        # Try to read custom path from configuration
        try:
            from core.settings import get_settings

            config_path = get_settings().get("image_storage_path", "")
            if config_path:
                candidates.append(Path(config_path).expanduser())
        except Exception:
            logger.debug("Could not read image_storage_path from settings")

        # Use configured data directory as fallback
        candidates.append(get_data_dir() / "screenshots")

        # Use first valid candidate
        for candidate in candidates:
            if candidate.exists() or candidate.parent.exists():
                return ensure_dir(candidate)

        # If none exist, use the data directory (it will be created)
        return ensure_dir(candidates[-1])

    def _ensure_directories(self):
        """Ensure required directories exist"""
        ensure_dir(self.thumbnails_dir)

    def get_from_cache(self, img_hash: str) -> Optional[str]:
        """Get image from memory cache

        Args:
            img_hash: Image hash value

        Returns:
            base64-encoded image data, return None if not found
        """
        try:
            data, timestamp = self._memory_cache.get(img_hash, (None, None))
            if data:
                # Update access time (move to end)
                self._memory_cache.move_to_end(img_hash)
                return data
        except Exception as e:
            logger.error(f"Failed to get image from cache: {e}")
        return None

    def get_multiple_from_cache(self, img_hashes: List[str]) -> Dict[str, str]:
        """Batch retrieve images from memory cache

        Args:
            img_hashes: List of image hash values

        Returns:
            dict: {hash: base64_data}
        """
        result = {}
        for img_hash in img_hashes:
            data = self.get_from_cache(img_hash)
            if data:
                result[img_hash] = data
        return result

    def add_to_cache(self, img_hash: str, img_data: str) -> None:
        """Add image to memory cache with TTL cleanup

        Args:
            img_hash: Image hash value
            img_data: base64-encoded image data
        """
        try:
            now = datetime.now()

            # Perform TTL cleanup before adding new image
            if self.enable_memory_first:
                self.cleanup_expired_memory_images()

            self._memory_cache[img_hash] = (img_data, now)

            # LRU eviction if cache is full
            while len(self._memory_cache) > self.memory_cache_size:
                evicted_hash, _ = self._memory_cache.popitem(last=False)

                # Clean metadata for evicted image
                if evicted_hash in self._image_metadata:
                    metadata = self._image_metadata[evicted_hash]
                    if not metadata[1]:  # Not persisted
                        logger.warning(
                            f"LRU evicted memory-only image: {evicted_hash[:8]}... "
                            f"(never persisted to disk)"
                        )
                    del self._image_metadata[evicted_hash]

            logger.debug(f"Added image to cache: {img_hash[:8]}...")
        except Exception as e:
            logger.error(f"Failed to add image to cache: {e}")

    def load_thumbnail_base64(self, img_hash: str) -> Optional[str]:
        """Load thumbnail and return base64 data

        Args:
            img_hash: Image hash value

        Returns:
            base64-encoded thumbnail data, return None if not found
        """
        try:
            thumbnail_path = self.thumbnails_dir / f"{img_hash}.jpg"
            if thumbnail_path.exists():
                with open(thumbnail_path, "rb") as f:
                    img_bytes = f.read()
                    return base64.b64encode(img_bytes).decode("utf-8")
        except Exception as e:
            logger.debug(f"Failed to load thumbnail: {e}")
        return None

    def save_thumbnail(self, img_hash: str, thumbnail_bytes: bytes) -> None:
        """Save thumbnail to disk

        Args:
            img_hash: Image hash value
            thumbnail_bytes: Thumbnail image bytes
        """
        try:
            thumbnail_path = self.thumbnails_dir / f"{img_hash}.jpg"
            with open(thumbnail_path, "wb") as f:
                f.write(thumbnail_bytes)
            logger.debug(f"Saved thumbnail: {thumbnail_path}")
        except Exception as e:
            logger.error(f"Failed to save thumbnail: {e}")

    def _create_thumbnail(self, img_bytes: bytes) -> bytes:
        """Create thumbnail from image bytes

        Args:
            img_bytes: Original image bytes

        Returns:
            Thumbnail image bytes
        """
        try:
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")

            target_size = self._select_thumbnail_size(img)
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            thumb_bytes = io.BytesIO()
            img.save(
                thumb_bytes,
                format="JPEG",
                quality=self.thumbnail_quality,
                optimize=True,
            )
            return thumb_bytes.getvalue()
        except Exception as e:
            logger.error(f"Failed to create thumbnail: {e}")
            return img_bytes  # Return original if thumbnail creation fails

    def process_image_for_cache(self, img_hash: str, img_bytes: bytes) -> None:
        """Process image: create thumbnail and store both in memory and disk for reliability

        Args:
            img_hash: Image hash value
            img_bytes: Original image bytes
        """
        try:
            # Create thumbnail
            thumbnail_bytes = self._create_thumbnail(img_bytes)
            thumbnail_base64 = base64.b64encode(thumbnail_bytes).decode("utf-8")

            # Always store in memory for fast access
            self.add_to_cache(img_hash, thumbnail_base64)

            # Always persist to disk immediately to prevent image loss
            # This ensures images are never lost even if:
            # 1. Memory cache is full and LRU evicts them
            # 2. TTL cleanup removes them
            # 3. System crashes before action persistence
            self.save_thumbnail(img_hash, thumbnail_bytes)
            self._image_metadata[img_hash] = (datetime.now(), True)  # Mark as persisted

            logger.debug(f"Stored image in memory AND disk: {img_hash[:8]}...")
        except Exception as e:
            logger.error(f"Failed to process image for cache: {e}")

    def persist_image(self, img_hash: str) -> bool:
        """Persist a memory-only image to disk

        Args:
            img_hash: Image hash to persist

        Returns:
            True if persisted successfully, False otherwise
        """
        try:
            self.persistence_stats["total_persist_attempts"] += 1

            # Check if already persisted
            metadata = self._image_metadata.get(img_hash)
            if metadata and metadata[1]:  # is_persisted = True
                self.persistence_stats["already_persisted"] += 1
                logger.debug(f"Image already persisted: {img_hash[:8]}...")
                return True

            # Check if exists on disk already
            thumbnail_path = self.thumbnails_dir / f"{img_hash}.jpg"
            if thumbnail_path.exists():
                self.persistence_stats["already_persisted"] += 1
                # Update metadata
                self._image_metadata[img_hash] = (datetime.now(), True)
                logger.debug(f"Image already on disk: {img_hash[:8]}...")
                return True

            # Get from memory cache
            img_data = self.get_from_cache(img_hash)
            if not img_data:
                self.persistence_stats["failed_persists"] += 1
                self.persistence_stats["cache_misses"] += 1
                logger.warning(
                    f"Image not found in memory cache (likely evicted): {img_hash[:8]}... "
                    f"Cannot persist to disk."
                )
                return False

            # Decode and save to disk
            img_bytes = base64.b64decode(img_data)
            self.save_thumbnail(img_hash, img_bytes)

            # Update metadata
            self._image_metadata[img_hash] = (datetime.now(), True)
            self.persistence_stats["successful_persists"] += 1

            logger.debug(f"Persisted image to disk: {img_hash[:8]}...")
            return True

        except Exception as e:
            self.persistence_stats["failed_persists"] += 1
            logger.error(f"Failed to persist image {img_hash[:8]}: {e}")
            return False

    def persist_images_batch(self, img_hashes: list[str]) -> dict[str, bool]:
        """Persist multiple images in batch

        Args:
            img_hashes: List of image hashes to persist

        Returns:
            Dict mapping hash to success status
        """
        results = {}
        success_count = 0

        for img_hash in img_hashes:
            success = self.persist_image(img_hash)
            results[img_hash] = success
            if success:
                success_count += 1

        logger.info(
            f"Batch persist completed: {success_count}/{len(img_hashes)} images persisted"
        )

        return results

    def cleanup_expired_memory_images(self) -> int:
        """Clean up memory-only images that exceed TTL

        Returns:
            Number of images evicted
        """
        if not self.enable_memory_first:
            return 0

        try:
            now = datetime.now()
            cutoff_time = now - timedelta(seconds=self.memory_ttl)

            evicted_count = 0
            hashes_to_remove = []

            for img_hash, (timestamp, is_persisted) in self._image_metadata.items():
                # Only evict memory-only images
                if not is_persisted and timestamp < cutoff_time:
                    hashes_to_remove.append(img_hash)

            # Remove from memory cache
            for img_hash in hashes_to_remove:
                if img_hash in self._memory_cache:
                    del self._memory_cache[img_hash]
                    evicted_count += 1

                # Clean metadata
                if img_hash in self._image_metadata:
                    del self._image_metadata[img_hash]

            if evicted_count > 0:
                logger.info(
                    f"TTL cleanup: evicted {evicted_count} memory-only images "
                    f"(TTL={self.memory_ttl}s)"
                )

            return evicted_count

        except Exception as e:
            logger.error(f"Failed to cleanup expired memory images: {e}")
            return 0

    def cleanup_batch_screenshots(self, img_hashes: list[str]) -> int:
        """Clean up specific screenshots from memory (batch cleanup after action generation)

        This is called after actions are saved to immediately free memory-only images
        that were not used in the final actions.

        Args:
            img_hashes: List of image hashes to remove from memory

        Returns:
            Number of images removed
        """
        if not self.enable_memory_first:
            return 0

        try:
            removed_count = 0

            for img_hash in img_hashes:
                # Check if this image is memory-only (not persisted)
                metadata = self._image_metadata.get(img_hash)
                if metadata and not metadata[1]:  # is_persisted = False
                    # Remove from memory cache
                    if img_hash in self._memory_cache:
                        del self._memory_cache[img_hash]
                        removed_count += 1

                    # Remove from metadata
                    if img_hash in self._image_metadata:
                        del self._image_metadata[img_hash]

            return removed_count

        except Exception as e:
            logger.error(f"Failed to cleanup batch screenshots: {e}")
            return 0

    def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up old temporary files

        Args:
            max_age_hours: Maximum file retention time (hours), None uses default value

        Returns:
            Number of cleaned files
        """
        try:
            max_age = max_age_hours or self.max_age_hours
            cutoff_time = datetime.now() - timedelta(hours=max_age)
            cutoff_timestamp = cutoff_time.timestamp()

            cleaned_count = 0
            total_size = 0

            for file_path in self.thumbnails_dir.glob("*"):
                if not file_path.is_file():
                    continue

                if file_path.stat().st_mtime < cutoff_timestamp:
                    file_size = file_path.stat().st_size
                    file_path.unlink(missing_ok=True)
                    cleaned_count += 1
                    total_size += file_size
                    logger.debug(f"Deleted old file: {file_path.name}")

            if cleaned_count > 0:
                logger.debug(
                    f"Cleaned up {cleaned_count} old files, "
                    f"Released space: {total_size / 1024 / 1024:.2f}MB"
                )

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to clean up old files: {e}")
            return 0

    def cleanup_orphaned_images(self, get_referenced_hashes_func, safety_window_minutes: int = 30) -> int:
        """
        Clean up images that are not referenced by any action and are older than the safety window.

        This is more aggressive than cleanup_old_files and should be used to remove
        screenshots that were never associated with any action.

        Args:
            get_referenced_hashes_func: Function that returns a set of all image hashes
                                       referenced in action_images table
            safety_window_minutes: Keep files younger than this many minutes
                                  to avoid deleting images being processed (default: 30)

        Returns:
            Number of cleaned files
        """
        try:
            # Get all referenced hashes from database
            referenced_hashes = get_referenced_hashes_func()
            if not isinstance(referenced_hashes, set):
                referenced_hashes = set(referenced_hashes)

            cutoff_time = datetime.now() - timedelta(minutes=safety_window_minutes)
            cutoff_timestamp = cutoff_time.timestamp()

            cleaned_count = 0
            total_size = 0

            for file_path in self.thumbnails_dir.glob("*.jpg"):
                if not file_path.is_file():
                    continue

                # Extract hash from filename (remove .jpg extension)
                file_hash = file_path.stem

                # Skip if file is within safety window
                if file_path.stat().st_mtime >= cutoff_timestamp:
                    continue

                # Delete if not referenced by any action
                if file_hash not in referenced_hashes:
                    file_size = file_path.stat().st_size
                    file_path.unlink(missing_ok=True)
                    cleaned_count += 1
                    total_size += file_size
                    logger.debug(f"Deleted orphaned image: {file_path.name}")

            if cleaned_count > 0:
                logger.info(
                    f"Cleaned up {cleaned_count} orphaned images, "
                    f"released space: {total_size / 1024 / 1024:.2f}MB"
                )

            return cleaned_count

        except Exception as e:
            logger.error(f"Failed to clean up orphaned images: {e}", exc_info=True)
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            # Memory cache stats
            memory_count = len(self._memory_cache)
            memory_size_mb = (
                sum(len(data[0]) for data in self._memory_cache.values()) / 1024 / 1024
            )

            # Disk stats
            disk_count = 0
            disk_size = 0
            if self.thumbnails_dir.exists():
                for file_path in self.thumbnails_dir.glob("*"):
                    if file_path.is_file():
                        disk_count += 1
                        disk_size += file_path.stat().st_size

            # Memory-first stats
            memory_only_count = 0
            persisted_count = 0

            for _, (_, is_persisted) in self._image_metadata.items():
                if is_persisted:
                    persisted_count += 1
                else:
                    memory_only_count += 1

            # Calculate persistence success rate
            total_attempts = self.persistence_stats["total_persist_attempts"]
            success_rate = (
                self.persistence_stats["successful_persists"] / total_attempts
                if total_attempts > 0
                else 1.0
            )

            return {
                "memory_cache_count": memory_count,
                "memory_cache_limit": self.memory_cache_size,
                "memory_cache_size_mb": round(memory_size_mb, 2),
                "disk_thumbnail_count": disk_count,
                "disk_total_size_mb": disk_size / 1024 / 1024,
                "thumbnail_size": self.thumbnail_size,
                "scale_threshold": self.scale_threshold,
                "scale_factor": self.scale_factor,
                "thumbnail_quality": self.thumbnail_quality,
                # Memory-first stats
                "memory_first_enabled": self.enable_memory_first,
                "memory_ttl_seconds": self.memory_ttl,
                "memory_only_images": memory_only_count,
                "persisted_images_in_cache": persisted_count,
                # Persistence stats
                "persistence_success_rate": round(success_rate, 4),
                "persistence_stats": self.persistence_stats,
            }

        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Backward compatible alias used by handlers"""
        return self.get_stats()

    def clear_memory_cache(self) -> int:
        """Clear in-memory cache and return number of removed entries"""
        cleared = len(self._memory_cache)
        self._memory_cache.clear()
        logger.debug("Cleared image memory cache", extra={"count": cleared})
        return cleared

    def estimate_compression_savings(self, img_bytes: bytes) -> Dict[str, Any]:
        """
        Estimate space savings after compression

        Args:
            img_bytes: Original image byte data

        Returns:
            Dictionary containing original size, thumbnail size, and savings ratio
        """
        try:
            original_size = len(img_bytes)

            # Create temporary thumbnail to estimate size
            img = Image.open(io.BytesIO(img_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")

            target_size = self._select_thumbnail_size(img)
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # Compress to memory
            thumb_bytes = io.BytesIO()
            img.save(
                thumb_bytes,
                format="JPEG",
                quality=self.thumbnail_quality,
                optimize=True,
            )
            thumbnail_size = len(thumb_bytes.getvalue())

            savings_ratio = (1 - thumbnail_size / original_size) * 100

            return {
                "original_size_kb": original_size / 1024,
                "thumbnail_size_kb": thumbnail_size / 1024,
                "savings_ratio": savings_ratio,
                "space_saved_kb": (original_size - thumbnail_size) / 1024,
            }

        except Exception as e:
            logger.error(f"Failed to estimate compression savings: {e}")
            return {}

    def update_storage_path(self, new_base_dir: str) -> None:
        """Update screenshot storage path (respond to configuration changes)"""
        if not new_base_dir:
            return

        try:
            resolved = ensure_dir(Path(new_base_dir).expanduser())
            if resolved == self.base_dir:
                return

            self.base_dir = resolved
            self.thumbnails_dir = ensure_dir(self.base_dir / "thumbnails")

            logger.debug(f"Screenshot storage directory updated: {self.base_dir}")
        except Exception as exc:
            logger.error(f"Failed to update screenshot storage directory: {exc}")


# Global singleton
_image_manager: Optional[ImageManager] = None


def get_image_manager() -> ImageManager:
    """Get image manager singleton"""
    global _image_manager
    if _image_manager is None:
        _image_manager = init_image_manager()
    return _image_manager


def init_image_manager(**kwargs) -> ImageManager:
    """Initialize image manager (can customize parameters)"""
    global _image_manager

    # Calculate TTL from config if not provided
    if "memory_ttl" not in kwargs or "enable_memory_first" not in kwargs:
        try:
            from config.loader import get_config

            config = get_config().load()

            # Access nested config values correctly
            image_config = config.get("image", {})
            monitoring_config = config.get("monitoring", {})

            enable_memory_first = image_config.get("enable_memory_first", True)
            processing_interval = monitoring_config.get("processing_interval", 30)
            multiplier = image_config.get("memory_ttl_multiplier", 2.5)
            ttl_min = image_config.get("memory_ttl_min", 60)
            ttl_max = image_config.get("memory_ttl_max", 300)

            # Calculate dynamic TTL
            calculated_ttl = int(processing_interval * multiplier)
            memory_ttl = max(ttl_min, min(ttl_max, calculated_ttl))

            logger.debug(
                f"ImageManager config: processing_interval={processing_interval}, "
                f"multiplier={multiplier}, ttl_min={ttl_min}, ttl_max={ttl_max}, "
                f"calculated_ttl={calculated_ttl}, final_memory_ttl={memory_ttl}"
            )

            if "enable_memory_first" not in kwargs:
                kwargs["enable_memory_first"] = enable_memory_first
            if "memory_ttl" not in kwargs:
                kwargs["memory_ttl"] = memory_ttl

            logger.info(
                f"ImageManager: memory_first={enable_memory_first}, "
                f"TTL={memory_ttl}s (processing_interval={processing_interval}s * multiplier={multiplier})"
            )
        except Exception as e:
            logger.warning(f"Failed to calculate memory TTL from config: {e}", exc_info=True)

    _image_manager = ImageManager(**kwargs)
    return _image_manager
