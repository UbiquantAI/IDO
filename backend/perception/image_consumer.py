"""
Image Consumer - Batch screenshot buffering for Pomodoro mode

Accumulates screenshot metadata and generates RawRecords in batches
when threshold is reached (count-based OR time-based).

This component provides:
1. Dual buffer architecture (accumulating + processing)
2. State machine for batch lifecycle management
3. Timeout protection for long-running LLM calls
4. Hybrid threshold triggering (count + time)
"""

import uuid
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from core.logger import get_logger
from core.models import RawRecord, RecordType

logger = get_logger(__name__)


class BatchState(Enum):
    """Batch processing state"""
    IDLE = "idle"  # No processing, ready to accept new batch
    READY_TO_PROCESS = "ready_to_process"  # Batch prepared, about to trigger
    PROCESSING = "processing"  # Batch being processed by LLM


@dataclass
class ScreenshotMetadata:
    """Lightweight screenshot metadata for buffering"""
    img_hash: str
    timestamp: datetime
    monitor_index: int
    monitor_info: Dict[str, Any]
    active_window: Optional[Dict[str, Any]]
    screenshot_path: str
    width: int
    height: int


class ImageConsumer:
    """
    Screenshot buffering and batch RawRecord generation for Pomodoro mode

    Uses dual-buffer architecture to isolate accumulating screenshots
    from those being processed by LLM, preventing data confusion during
    HTTP timeouts.

    Batch Triggering:
    - COUNT threshold: 50 screenshots (default)
    - TIME threshold: 60 seconds elapsed (default)
    - OVERFLOW protection: 200 screenshots max (safety limit)

    State Machine:
    IDLE → READY_TO_PROCESS → PROCESSING → IDLE
    """

    def __init__(
        self,
        count_threshold: int = 50,
        time_threshold: float = 60.0,
        max_buffer_size: int = 200,
        processing_timeout: float = 720.0,
        on_batch_ready: Optional[Callable[[List[RawRecord], Callable[[bool], None]], None]] = None,
        image_manager: Optional[Any] = None,
    ):
        """
        Initialize ImageConsumer

        Args:
            count_threshold: Trigger batch when this many screenshots accumulated
            time_threshold: Trigger batch after this many seconds elapsed
            max_buffer_size: Emergency flush when buffer exceeds this size
            processing_timeout: Timeout for batch processing (default: 12 minutes)
            on_batch_ready: Callback to invoke with generated RawRecords batch
                           Signature: (records: List[RawRecord], on_completed: Callable[[bool], None]) -> None
            image_manager: Reference to ImageManager for cache validation
        """
        self.count_threshold = count_threshold
        self.time_threshold = time_threshold
        self.max_buffer_size = max_buffer_size
        self.processing_timeout = processing_timeout
        self.on_batch_ready = on_batch_ready
        self.image_manager = image_manager

        # Dual buffer architecture
        self._accumulating_buffer: List[ScreenshotMetadata] = []
        self._processing_buffer: Optional[List[ScreenshotMetadata]] = None

        # State machine
        self._batch_state: BatchState = BatchState.IDLE
        self._processing_batch_id: Optional[str] = None
        self._processing_start_time: Optional[datetime] = None

        # Track first screenshot time for time threshold
        self._first_screenshot_time: Optional[datetime] = None

        # Statistics
        self.stats: Dict[str, int] = {
            "total_screenshots_consumed": 0,
            "batches_generated": 0,
            "total_records_generated": 0,
            "cache_misses": 0,
            "timeout_resets": 0,
            "overflow_flushes": 0,
            "concurrent_trigger_attempts": 0,
            "count_triggers": 0,
            "time_triggers": 0,
        }

        logger.info(
            f"ImageConsumer initialized: count_threshold={count_threshold}, "
            f"time_threshold={time_threshold}s, max_buffer={max_buffer_size}, "
            f"processing_timeout={processing_timeout}s"
        )

    def consume_screenshot(
        self,
        img_hash: str,
        timestamp: datetime,
        monitor_index: int,
        monitor_info: Dict[str, Any],
        active_window: Optional[Dict[str, Any]],
        screenshot_path: str,
        width: int = 0,
        height: int = 0,
    ) -> None:
        """
        Consume a screenshot (store metadata for later batch processing)

        Lightweight storage - only metadata (~1KB), actual image in ImageManager cache.

        Args:
            img_hash: Perceptual hash of the screenshot
            timestamp: Capture timestamp
            monitor_index: Monitor index
            monitor_info: Monitor information dict
            active_window: Active window information (optional)
            screenshot_path: Virtual path to screenshot
            width: Screenshot width
            height: Screenshot height
        """
        metadata = ScreenshotMetadata(
            img_hash=img_hash,
            timestamp=timestamp,
            monitor_index=monitor_index,
            monitor_info=monitor_info,
            active_window=active_window,
            screenshot_path=screenshot_path,
            width=width,
            height=height,
        )

        # Always add to accumulating buffer (even when processing)
        self._accumulating_buffer.append(metadata)
        self.stats["total_screenshots_consumed"] += 1

        # Track first screenshot time for time threshold
        if self._first_screenshot_time is None:
            self._first_screenshot_time = timestamp

        # Log state for debugging
        if self._batch_state == BatchState.PROCESSING:
            logger.debug(
                f"Screenshot queued (batch {self._processing_batch_id} processing): "
                f"accumulating={len(self._accumulating_buffer)}"
            )

        # Check overflow protection
        if len(self._accumulating_buffer) >= self.max_buffer_size:
            logger.warning(
                f"Buffer overflow detected ({len(self._accumulating_buffer)} >= {self.max_buffer_size}), "
                f"force flushing"
            )
            self.stats["overflow_flushes"] += 1
            self._trigger_batch_generation("overflow")
            return

        # Check if should trigger batch
        should_trigger, reason = self._should_trigger_batch()
        if should_trigger and reason:  # Ensure reason is not None
            self._trigger_batch_generation(reason)

    def _should_trigger_batch(self) -> tuple[bool, Optional[str]]:
        """
        Check if batch should be triggered

        Returns:
            (should_trigger, reason)
            reason: "count" | "time" | None
        """
        # Don't trigger if already processing
        if self._batch_state == BatchState.PROCESSING:
            return False, None

        # Check count threshold
        if len(self._accumulating_buffer) >= self.count_threshold:
            return True, "count"

        # Check time threshold
        if self._first_screenshot_time:
            elapsed = (datetime.now() - self._first_screenshot_time).total_seconds()
            if elapsed >= self.time_threshold:
                return True, "time"

        return False, None

    def _trigger_batch_generation(self, reason: str) -> None:
        """
        Trigger batch generation (state transition)

        Args:
            reason: Trigger reason ("count", "time", "overflow", "manual")
        """
        if self._batch_state == BatchState.PROCESSING:
            logger.warning(
                f"Cannot trigger new batch (reason: {reason}): "
                f"previous batch {self._processing_batch_id} still processing"
            )
            self.stats["concurrent_trigger_attempts"] += 1
            return

        if len(self._accumulating_buffer) == 0:
            logger.debug("No screenshots to process, skipping batch generation")
            return

        # Update trigger stats
        if reason == "count":
            self.stats["count_triggers"] += 1
        elif reason == "time":
            self.stats["time_triggers"] += 1

        # State: IDLE → READY_TO_PROCESS
        self._batch_state = BatchState.READY_TO_PROCESS

        # Move accumulating buffer to processing buffer
        self._processing_buffer = self._accumulating_buffer
        self._accumulating_buffer = []
        self._first_screenshot_time = None  # Reset time tracker

        # Generate batch ID and record start time
        self._processing_batch_id = str(uuid.uuid4())
        self._processing_start_time = datetime.now()

        batch_size = len(self._processing_buffer)
        logger.info(
            f"Triggering batch generation: batch_id={self._processing_batch_id[:8]}, "
            f"size={batch_size}, reason={reason}"
        )

        # Generate RawRecords from metadata
        try:
            records = self._generate_raw_records_batch(self._processing_buffer)

            # State: READY_TO_PROCESS → PROCESSING
            self._batch_state = BatchState.PROCESSING

            logger.debug(
                f"Batch {self._processing_batch_id[:8]} ready: "
                f"{len(records)}/{batch_size} records generated"
            )

            # Invoke callback with completion handler
            if self.on_batch_ready:
                self.on_batch_ready(records, self._on_batch_completed)
            else:
                logger.warning("No on_batch_ready callback registered, auto-completing")
                self._on_batch_completed(True)

        except Exception as e:
            logger.error(f"Failed to generate batch {self._processing_batch_id[:8]}: {e}", exc_info=True)
            # Reset state on failure
            self._processing_buffer = None
            self._batch_state = BatchState.IDLE
            self._processing_batch_id = None
            self._processing_start_time = None

    def _generate_raw_records_batch(self, metadata_list: List[ScreenshotMetadata]) -> List[RawRecord]:
        """
        Generate RawRecords from buffered screenshot metadata

        Args:
            metadata_list: List of screenshot metadata

        Returns:
            List of RawRecord objects ready for processing
        """
        records = []
        failed_count = 0

        for meta in metadata_list:
            # Verify image still in cache (if image_manager available)
            if self.image_manager:
                if not self.image_manager.get_from_cache(meta.img_hash):
                    logger.warning(
                        f"Image {meta.img_hash[:8]} evicted from cache before batch processing, "
                        f"skipping this screenshot"
                    )
                    failed_count += 1
                    self.stats["cache_misses"] += 1
                    continue

            # Create RawRecord from metadata
            screenshot_data = {
                "action": "capture",
                "width": meta.width,
                "height": meta.height,
                "format": "JPEG",
                "hash": meta.img_hash,
                "monitor": meta.monitor_info,
                "monitor_index": meta.monitor_index,
                "timestamp": meta.timestamp.isoformat(),
                "screenshotPath": meta.screenshot_path,
            }

            if meta.active_window:
                screenshot_data["active_window"] = meta.active_window

            record = RawRecord(
                timestamp=meta.timestamp,
                type=RecordType.SCREENSHOT_RECORD,
                data=screenshot_data,
                screenshot_path=meta.screenshot_path,
            )

            records.append(record)

        if failed_count > 0:
            logger.warning(
                f"Lost {failed_count}/{len(metadata_list)} screenshots due to cache eviction. "
                f"Consider increasing image.memory_cache_size in config."
            )

        self.stats["batches_generated"] += 1
        self.stats["total_records_generated"] += len(records)

        return records

    def _on_batch_completed(self, success: bool) -> None:
        """
        Batch processing completion callback

        Args:
            success: Whether batch processing succeeded
        """
        if not self._processing_start_time:
            logger.warning("Batch completion called but no processing start time recorded")
            return

        elapsed = (datetime.now() - self._processing_start_time).total_seconds()
        batch_id_short = self._processing_batch_id[:8] if self._processing_batch_id else "unknown"

        if success:
            logger.info(f"Batch {batch_id_short} completed successfully in {elapsed:.1f}s")
        else:
            logger.error(f"Batch {batch_id_short} failed after {elapsed:.1f}s")

        # Clear processing buffer
        self._processing_buffer = None
        self._processing_batch_id = None
        self._processing_start_time = None

        # State: PROCESSING → IDLE
        self._batch_state = BatchState.IDLE

        logger.debug(
            f"State reset to IDLE, accumulating buffer size: {len(self._accumulating_buffer)}"
        )

    def check_processing_timeout(self) -> bool:
        """
        Check if currently processing batch has timed out

        Should be called periodically (e.g., on each screenshot event).

        Returns:
            True if timeout detected and state was reset
        """
        if self._batch_state != BatchState.PROCESSING:
            return False

        if not self._processing_start_time:
            return False

        elapsed = (datetime.now() - self._processing_start_time).total_seconds()

        if elapsed > self.processing_timeout:
            batch_id_short = self._processing_batch_id[:8] if self._processing_batch_id else "unknown"
            logger.error(
                f"Batch {batch_id_short} processing timeout detected: "
                f"{elapsed:.1f}s > {self.processing_timeout}s, forcing reset"
            )

            # Force reset state (discard timed-out batch)
            self._processing_buffer = None
            self._processing_batch_id = None
            self._processing_start_time = None
            self._batch_state = BatchState.IDLE

            self.stats["timeout_resets"] += 1

            logger.warning(
                f"State reset due to timeout, accumulating buffer size: {len(self._accumulating_buffer)}"
            )

            return True

        return False

    def flush(self) -> List[RawRecord]:
        """
        Force flush all buffered screenshots (called on Pomodoro end)

        Flushes both accumulating and processing buffers.

        Returns:
            List of RawRecord objects from both buffers
        """
        records = []

        # Flush processing buffer if exists
        if self._processing_buffer:
            logger.info(
                f"Flushing processing buffer: batch_id={self._processing_batch_id[:8] if self._processing_batch_id else 'none'}, "
                f"size={len(self._processing_buffer)}"
            )
            processing_records = self._generate_raw_records_batch(self._processing_buffer)
            records.extend(processing_records)

            # Clear processing state
            self._processing_buffer = None
            self._processing_batch_id = None
            self._processing_start_time = None
            self._batch_state = BatchState.IDLE

        # Flush accumulating buffer
        if self._accumulating_buffer:
            logger.info(
                f"Flushing accumulating buffer: size={len(self._accumulating_buffer)}"
            )
            accumulating_records = self._generate_raw_records_batch(self._accumulating_buffer)
            records.extend(accumulating_records)

            # Clear accumulating buffer
            self._accumulating_buffer = []
            self._first_screenshot_time = None

        if records:
            logger.info(f"Flushed total {len(records)} records from both buffers")
        else:
            logger.debug("No buffered screenshots to flush")

        return records

    def get_stats(self) -> Dict[str, Any]:
        """
        Get consumer statistics

        Returns:
            Dictionary with statistics including buffer sizes
        """
        return {
            **self.stats,
            "accumulating_buffer_size": len(self._accumulating_buffer),
            "processing_buffer_size": len(self._processing_buffer) if self._processing_buffer else 0,
            "batch_state": self._batch_state.value,
            "processing_batch_id": self._processing_batch_id,
            "processing_elapsed_seconds": (
                (datetime.now() - self._processing_start_time).total_seconds()
                if self._processing_start_time else None
            ),
        }
