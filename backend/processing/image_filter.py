"""
Unified image filtering and optimization
Integrates deduplication, content analysis, and compression into a single preprocessing stage

Supports coding scene detection for adaptive thresholds:
- Coding scenes (IDEs, terminals) use more permissive thresholds
- This helps capture small but meaningful changes during coding
"""

import base64
import io
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.logger import get_logger
from core.models import RawRecord, RecordType
from perception.image_manager import get_image_manager
from processing.coding_detector import get_coding_detector

logger = get_logger(__name__)

# Try to import imagehash and PIL
try:
    import imagehash
    from PIL import Image

    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    logger.warning(
        "imagehash or PIL library not installed, image filtering will be limited"
    )


class ImageFilter:
    """
    Unified image filter - preprocesses all screenshots before accumulation

    Responsibilities:
    1. Deduplication (multi-hash similarity detection)
    2. Content analysis (skip static/blank screens)
    3. Compression (resolution optimization)
    4. Store optimized base64 in record.data for later use
    """

    def __init__(
        self,
        # Deduplication settings
        enable_deduplication: bool = True,
        similarity_threshold: float = 0.92,
        hash_cache_size: int = 10,
        hash_algorithms: Optional[List[str]] = None,
        enable_adaptive_threshold: bool = True,
        # Content analysis settings
        enable_content_analysis: bool = True,
        # Compression settings
        enable_compression: bool = True,
        # Periodic sampling settings
        min_sample_interval: float = 30.0,
    ):
        """
        Initialize unified image filter

        Args:
            enable_deduplication: Enable multi-hash deduplication
            similarity_threshold: Similarity threshold (0-1, default 0.92)
            hash_cache_size: Number of hashes to cache (default 10)
            hash_algorithms: Hash algorithms to use (default: ['phash', 'dhash', 'average_hash'])
            enable_adaptive_threshold: Enable scene-adaptive thresholds
            enable_content_analysis: Enable content analysis (skip static screens)
            enable_compression: Enable image compression
            min_sample_interval: Minimum seconds between kept samples in static scenes (default 30)
        """
        self.enable_deduplication = enable_deduplication and IMAGEHASH_AVAILABLE
        self.similarity_threshold = similarity_threshold
        self.hash_cache_size = hash_cache_size
        self.enable_adaptive_threshold = enable_adaptive_threshold
        self.enable_content_analysis = enable_content_analysis
        self.enable_compression = enable_compression
        self.min_sample_interval = min_sample_interval
        self.last_kept_timestamp: Optional[datetime] = None

        # Initialize hash algorithms with weights
        if hash_algorithms is None:
            hash_algorithms = ['phash', 'dhash', 'average_hash']
        self.hash_algorithms = self._init_hash_algorithms(hash_algorithms)

        # Hash cache: deque of (timestamp, multi_hash_dict) tuples
        self.hash_cache: deque = deque(maxlen=hash_cache_size)

        self.image_manager = get_image_manager()
        self.coding_detector = get_coding_detector()

        # Initialize components
        self._init_content_analyzer()
        self._init_compressor()

        # Statistics
        self.stats = {
            "total_processed": 0,
            "duplicates_skipped": 0,
            "content_filtered": 0,
            "compressed": 0,
            "total_passed": 0,
        }

        logger.debug(
            f"ImageFilter initialized: dedup={enable_deduplication}, "
            f"content_analysis={enable_content_analysis}, compression={enable_compression}"
        )

    def _init_hash_algorithms(
        self, algorithms: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Initialize hash algorithms with default weights

        Returns:
            Dict mapping algorithm name to {weight, hash_func}
        """
        # Default weights (normalized to sum to 1.0)
        default_weights = {
            'phash': 0.5,  # Perceptual hash - best for structure
            'dhash': 0.3,  # Difference hash - good for gradients
            'average_hash': 0.2,  # Average hash - fast but less precise
        }

        result = {}
        total_weight = 0.0

        for algo in algorithms:
            if algo in default_weights:
                weight = default_weights[algo]
                result[algo] = {
                    'weight': weight,
                    'hash_func': getattr(imagehash, algo) if IMAGEHASH_AVAILABLE else None,
                }
                total_weight += weight

        # Normalize weights to sum to 1.0
        if total_weight > 0:
            for algo in result:
                result[algo]['weight'] /= total_weight

        return result

    def _init_content_analyzer(self):
        """Initialize content analyzer"""
        if not self.enable_content_analysis:
            self.content_analyzer = None
            return

        try:
            from processing.image.analysis import ImageAnalyzer
            self.content_analyzer = ImageAnalyzer()
            logger.debug("Content analyzer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize content analyzer: {e}")
            self.content_analyzer = None

    def _init_compressor(self):
        """Initialize image compressor"""
        if not self.enable_compression:
            self.compressor = None
            return

        try:
            from processing.image.processing import ImageCompressor
            self.compressor = ImageCompressor()
            logger.debug("Image compressor initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize compressor: {e}")
            self.compressor = None

    def filter_screenshots(self, records: List[RawRecord]) -> List[RawRecord]:
        """
        Filter and optimize screenshots in a single pass

        Process:
        1. Load image once
        2. Check deduplication
        3. Check content quality
        4. Compress
        5. Store optimized base64 in record.data

        Args:
            records: List of raw records

        Returns:
            Filtered records with optimized image data
        """
        filtered = []

        for record in records:
            # Non-screenshot records pass through
            if record.type != RecordType.SCREENSHOT_RECORD:
                filtered.append(record)
                continue

            self.stats["total_processed"] += 1

            # Load image once
            img_bytes = self._load_image_bytes(record)
            if not img_bytes:
                # Can't load image, keep record as-is
                filtered.append(record)
                continue

            # Step 1: Deduplication check
            if self.enable_deduplication:
                is_duplicate, similarity = self._check_duplicate(img_bytes, record)
                if is_duplicate:
                    self.stats["duplicates_skipped"] += 1
                    logger.debug(
                        f"Skipping duplicate screenshot: similarity={similarity:.3f}"
                    )
                    continue

            # Step 2: Content analysis
            if self.enable_content_analysis and self.content_analyzer:
                # Check if this is a coding scene for relaxed thresholds
                is_coding = self.coding_detector.is_coding_record(record.data)
                has_content, reason = self.content_analyzer.has_significant_content(
                    img_bytes,
                    is_coding_scene=is_coding,
                )
                if not has_content:
                    self.stats["content_filtered"] += 1
                    logger.debug(f"Skipping screenshot: {reason}")
                    continue

            # Step 3: Compression
            optimized_bytes = img_bytes
            if self.enable_compression and self.compressor:
                try:
                    compressed_bytes, meta = self.compressor.compress(img_bytes)
                    if compressed_bytes:
                        optimized_bytes = compressed_bytes
                        self.stats["compressed"] += 1

                        # Log compression stats
                        original_size = len(img_bytes)
                        final_size = len(compressed_bytes)
                        ratio = (1 - final_size / original_size) * 100
                        logger.debug(
                            f"Compressed: {original_size}→{final_size} bytes ({ratio:.1f}% reduction)"
                        )
                except Exception as e:
                    logger.debug(f"Compression failed, using original: {e}")

            # Step 4: Store optimized base64 in record.data
            optimized_base64 = base64.b64encode(optimized_bytes).decode('utf-8')
            if record.data is None:
                record.data = {}
            record.data["optimized_img_data"] = optimized_base64

            filtered.append(record)
            self.stats["total_passed"] += 1

        if self.stats["total_processed"] > 0:
            logger.debug(
                f"ImageFilter: {len(records)}→{len(filtered)} records "
                f"(duplicates: {self.stats['duplicates_skipped']}, "
                f"content filtered: {self.stats['content_filtered']})"
            )

        return filtered

    def _load_image_bytes(self, record: RawRecord) -> Optional[bytes]:
        """Load image bytes from record"""
        try:
            data = record.data or {}

            # Try embedded base64
            img_data = data.get("img_data")
            if img_data:
                return base64.b64decode(img_data)

            # Try hash-based lookup
            img_hash = data.get("hash")
            if not img_hash:
                return None

            # Try memory cache
            cached = self.image_manager.get_from_cache(img_hash)
            if cached:
                return base64.b64decode(cached)

            # Try thumbnail
            thumbnail = self.image_manager.load_thumbnail_base64(img_hash)
            if thumbnail:
                return base64.b64decode(thumbnail)

            return None
        except Exception as e:
            logger.debug(f"Failed to load image bytes: {e}")
            return None

    def _check_duplicate(
        self, img_bytes: bytes, record: RawRecord
    ) -> Tuple[bool, float]:
        """
        Check if image is duplicate using multi-hash similarity

        Returns:
            (is_duplicate, max_similarity)
        """
        if not IMAGEHASH_AVAILABLE:
            return False, 0.0

        try:
            # Periodic sampling: force keep at least one sample every min_sample_interval
            # This ensures time coverage even in static scenes (reading, watching)
            force_keep = False
            if self.last_kept_timestamp is not None:
                elapsed = (record.timestamp - self.last_kept_timestamp).total_seconds()
                if elapsed >= self.min_sample_interval:
                    force_keep = True
                    logger.debug(
                        f"Periodic sampling: keeping screenshot after {elapsed:.1f}s "
                        f"(interval: {self.min_sample_interval}s)"
                    )

            # Load PIL Image
            img = Image.open(io.BytesIO(img_bytes))

            # Compute multi-hash
            multi_hash = self._compute_multi_hash(img)
            if multi_hash is None:
                return False, 0.0

            # Check similarity with cached hashes
            max_similarity = 0.0
            scene_type = 'normal'

            if self.hash_cache:
                # Compare with all cached hashes
                for cached_timestamp, cached_hash in self.hash_cache:
                    similarity = self._calculate_similarity(multi_hash, cached_hash)
                    max_similarity = max(max_similarity, similarity)

                # Detect scene type and get adaptive threshold
                # Pass record to check for coding scene
                scene_type = self._detect_scene_type(max_similarity, record)
                adaptive_threshold = self._get_adaptive_threshold(scene_type)

                # Check if duplicate (but respect periodic sampling)
                if max_similarity >= adaptive_threshold and not force_keep:
                    return True, max_similarity

            # Not duplicate (or force kept), add to cache and update timestamp
            self.hash_cache.append((record.timestamp, multi_hash))
            self.last_kept_timestamp = record.timestamp
            return False, max_similarity

        except Exception as e:
            logger.debug(f"Duplicate check failed: {e}")
            return False, 0.0

    def _compute_multi_hash(self, img: Image.Image) -> Optional[Dict[str, Any]]:
        """Compute multi-hash for image"""
        if not IMAGEHASH_AVAILABLE:
            return None

        try:
            result = {}
            for algo_name, algo_info in self.hash_algorithms.items():
                hash_func = algo_info['hash_func']
                weight = algo_info['weight']

                if hash_func:
                    hash_value = hash_func(img)
                    result[algo_name] = {
                        'hash': hash_value,
                        'weight': weight,
                    }

            return result if result else None
        except Exception as e:
            logger.debug(f"Failed to compute multi-hash: {e}")
            return None

    def _calculate_similarity(
        self, hash1: Dict[str, Any], hash2: Dict[str, Any]
    ) -> float:
        """
        Calculate weighted similarity between two multi-hash dicts

        Returns similarity score (0-1)
        """
        if not hash1 or not hash2:
            return 0.0

        total_similarity = 0.0
        total_weight = 0.0

        for algo_name in hash1:
            if algo_name not in hash2:
                continue

            h1 = hash1[algo_name]['hash']
            h2 = hash2[algo_name]['hash']
            weight = hash1[algo_name]['weight']

            # Calculate Hamming distance and convert to similarity
            hash_diff = h1 - h2
            similarity = 1.0 - (hash_diff / 64.0)  # 64 bits in hash

            total_similarity += similarity * weight
            total_weight += weight

        return total_similarity / total_weight if total_weight > 0 else 0.0

    def _detect_scene_type(
        self, similarity: float, record: Optional[RawRecord] = None
    ) -> str:
        """
        Detect scene type based on similarity and active window context.

        Scene types:
        - 'coding': IDEs, terminals, code editors (more permissive threshold)
        - 'static': Almost identical content (aggressive deduplication)
        - 'video': High similarity with motion (preserve key frames)
        - 'normal': Regular interactive content (default threshold)
        """
        # Check for coding scene first (highest priority)
        if record and record.data:
            if self.coding_detector.is_coding_record(record.data):
                return 'coding'

        # Similarity-based detection
        if similarity >= 0.99:
            return 'static'  # Almost identical (documents, reading)
        elif similarity >= 0.95:
            return 'video'  # High similarity (video playback)
        else:
            return 'normal'  # Regular interactive content

    def _get_adaptive_threshold(self, scene_type: str) -> float:
        """
        Get adaptive threshold based on scene type.

        Thresholds:
        - coding: 0.92 (more permissive, capture small code changes)
        - static: 0.85 (aggressive deduplication for static content)
        - video: 0.98 (preserve key frames)
        - normal: configured threshold (default 0.88)
        """
        if not self.enable_adaptive_threshold:
            return self.similarity_threshold

        if scene_type == 'coding':
            # More permissive for coding - capture cursor movement, typing
            return 0.92
        elif scene_type == 'static':
            return 0.85  # Aggressive deduplication for static content
        elif scene_type == 'video':
            return 0.98  # Preserve key frames in video
        else:
            return self.similarity_threshold  # Use configured threshold

    def get_stats(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        return self.stats.copy()

    def reset_state(self):
        """Reset deduplication state (clears hash cache and periodic sampling)"""
        self.hash_cache.clear()
        self.last_kept_timestamp = None
        self.stats = {
            "total_processed": 0,
            "duplicates_skipped": 0,
            "content_filtered": 0,
            "compressed": 0,
            "total_passed": 0,
        }
        logger.debug("ImageFilter state reset")

    def check_duplicate(
        self, record: RawRecord, compare_with_cache: bool = True
    ) -> Tuple[bool, float]:
        """
        Check if a screenshot record is duplicate (public method for external use)

        Args:
            record: Screenshot record to check
            compare_with_cache: Whether to compare with hash cache

        Returns:
            Tuple of (is_duplicate, similarity_score)
        """
        if not compare_with_cache or not self.enable_deduplication:
            return False, 0.0

        img_bytes = self._load_image_bytes(record)
        if not img_bytes:
            return False, 0.0

        return self._check_duplicate(img_bytes, record)
