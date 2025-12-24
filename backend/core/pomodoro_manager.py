"""
Pomodoro Manager - Manages Pomodoro session lifecycle

Responsibilities:
1. Start/stop Pomodoro sessions
2. Coordinate with PipelineCoordinator (enter/exit Pomodoro mode)
3. Trigger deferred batch processing after session completion
4. Track session metadata and handle orphaned sessions
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from core.db import get_db
from core.logger import get_logger
from core.models import RawRecord

logger = get_logger(__name__)


class PomodoroSession:
    """Pomodoro session data class"""

    def __init__(
        self,
        session_id: str,
        user_intent: str,
        duration_minutes: int,
        start_time: datetime,
    ):
        self.id = session_id
        self.user_intent = user_intent
        self.duration_minutes = duration_minutes
        self.start_time = start_time


class PomodoroManager:
    """
    Pomodoro session manager

    Handles Pomodoro lifecycle and coordinates with coordinator
    """

    def __init__(self, coordinator):
        """
        Initialize Pomodoro manager

        Args:
            coordinator: Reference to PipelineCoordinator instance
        """
        self.coordinator = coordinator
        self.db = get_db()
        self.current_session: Optional[PomodoroSession] = None
        self.is_active = False
        self._processing_tasks: Dict[str, asyncio.Task] = {}

    async def start_pomodoro(
        self, user_intent: str, duration_minutes: int = 25
    ) -> str:
        """
        Start a new Pomodoro session

        Actions:
        1. Create pomodoro_sessions record
        2. Signal coordinator to enter "pomodoro mode"
        3. Coordinator disables continuous processing
        4. PerceptionManager continues capturing but tags records
        5. RawRecords get persisted to DB with session_id

        Args:
            user_intent: User's description of what they plan to work on
            duration_minutes: Planned duration (default: 25 minutes)

        Returns:
            session_id

        Raises:
            ValueError: If a Pomodoro session is already active
        """
        if self.is_active:
            raise ValueError("A Pomodoro session is already active")

        # Check if previous session is still processing
        processing_sessions = await self.db.pomodoro_sessions.get_by_processing_status(
            "processing", limit=1
        )
        if processing_sessions:
            raise ValueError(
                "Previous Pomodoro session is still being analyzed. "
                "Please wait for completion before starting a new session."
            )

        session_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            # Save to database
            await self.db.pomodoro_sessions.create(
                session_id=session_id,
                user_intent=user_intent,
                planned_duration_minutes=duration_minutes,
                start_time=start_time.isoformat(),
                status="active",
            )

            # Create session object
            self.current_session = PomodoroSession(
                session_id=session_id,
                user_intent=user_intent,
                duration_minutes=duration_minutes,
                start_time=start_time,
            )
            self.is_active = True

            # Signal coordinator to enter pomodoro mode
            await self.coordinator.enter_pomodoro_mode(session_id)

            logger.info(
                f"✓ Pomodoro session started: {session_id}, "
                f"intent='{user_intent}', duration={duration_minutes}min"
            )

            return session_id

        except Exception as e:
            logger.error(f"Failed to start Pomodoro session: {e}", exc_info=True)
            # Cleanup on failure
            self.is_active = False
            self.current_session = None
            raise

    async def end_pomodoro(self, status: str = "completed") -> Dict[str, Any]:
        """
        End current Pomodoro session

        Actions:
        1. Update pomodoro_sessions record
        2. Signal coordinator to exit "pomodoro mode"
        3. Trigger deferred batch processing
        4. Return processing job ID

        Args:
            status: Session status ('completed', 'abandoned', 'interrupted')

        Returns:
            {
                "session_id": str,
                "processing_job_id": str,
                "raw_records_count": int
            }

        Raises:
            ValueError: If no active Pomodoro session
        """
        if not self.is_active or not self.current_session:
            raise ValueError("No active Pomodoro session")

        session_id = self.current_session.id
        end_time = datetime.now()
        duration = (end_time - self.current_session.start_time).total_seconds() / 60

        try:
            # Check if session is too short (< 2 minutes)
            if duration < 2:
                logger.warning(
                    f"Pomodoro session {session_id} too short ({duration:.1f}min), skipping analysis"
                )
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    end_time=end_time.isoformat(),
                    actual_duration_minutes=int(duration),
                    status="too_short",
                    processing_status="skipped",
                )

                # Exit pomodoro mode
                await self.coordinator.exit_pomodoro_mode()

                self.is_active = False
                self.current_session = None

                return {
                    "session_id": session_id,
                    "processing_job_id": None,
                    "raw_records_count": 0,
                    "message": "Session too short, data discarded",
                }

            # Update database
            await self.db.pomodoro_sessions.update(
                session_id=session_id,
                end_time=end_time.isoformat(),
                actual_duration_minutes=int(duration),
                status=status,
                processing_status="pending",
            )

            # Exit pomodoro mode
            await self.coordinator.exit_pomodoro_mode()

            # Count raw records for this session
            raw_count = await self.db.raw_records.count_by_session(session_id)

            logger.info(
                f"✓ Pomodoro session ended: {session_id}, "
                f"status={status}, duration={duration:.1f}min, records={raw_count}"
            )

            # Trigger batch processing in background
            job_id = await self._trigger_batch_processing(session_id)

            self.is_active = False
            self.current_session = None

            return {
                "session_id": session_id,
                "processing_job_id": job_id,
                "raw_records_count": raw_count,
            }

        except Exception as e:
            logger.error(f"Failed to end Pomodoro session: {e}", exc_info=True)
            raise

    async def _trigger_batch_processing(self, session_id: str) -> str:
        """
        Trigger background batch processing for Pomodoro session

        Creates async task that:
        1. Loads all RawRecords with pomodoro_session_id
        2. Processes through normal pipeline (deferred)
        3. Updates processing_status as it progresses
        4. Emits events for frontend to track progress

        Args:
            session_id: Pomodoro session ID

        Returns:
            job_id: Processing job identifier
        """
        job_id = str(uuid.uuid4())

        # Create background task
        task = asyncio.create_task(self._process_pomodoro_batch(session_id, job_id))

        # Store task reference
        self._processing_tasks[job_id] = task

        logger.debug(f"✓ Batch processing triggered: job={job_id}, session={session_id}")

        return job_id

    async def _process_pomodoro_batch(self, session_id: str, job_id: str):
        """
        Background task to process Pomodoro session data

        Steps:
        1. Update status to 'processing'
        2. Load RawRecords in chunks (to avoid memory issues)
        3. Process through pipeline
        4. Update status to 'completed'
        5. Emit completion event

        Args:
            session_id: Pomodoro session ID
            job_id: Processing job ID
        """
        try:
            await self.db.pomodoro_sessions.update(
                session_id=session_id,
                processing_status="processing",
                processing_started_at=datetime.now().isoformat(),
            )

            logger.info(f"→ Processing Pomodoro session: {session_id}")

            # Load raw records in chunks
            chunk_size = 100
            offset = 0
            total_processed = 0

            while True:
                records = await self.db.raw_records.get_by_session(
                    session_id=session_id,
                    limit=chunk_size,
                    offset=offset,
                )

                if not records:
                    break

                # Convert DB records back to RawRecord objects
                raw_records = []
                for r in records:
                    try:
                        import json

                        raw_record = RawRecord(
                            timestamp=datetime.fromisoformat(r["timestamp"]),
                            type=r["type"],
                            data=json.loads(r["data"]),
                        )
                        raw_records.append(raw_record)
                    except Exception as e:
                        logger.warning(f"Failed to parse raw record {r['id']}: {e}")

                # Process through pipeline
                if raw_records:
                    await self.coordinator.processing_pipeline.process_raw_records(
                        raw_records
                    )

                total_processed += len(records)
                offset += chunk_size

                # Emit progress event
                self._emit_progress_event(session_id, job_id, total_processed)

            # Update status
            await self.db.pomodoro_sessions.update(
                session_id=session_id,
                processing_status="completed",
                processing_completed_at=datetime.now().isoformat(),
            )

            logger.info(
                f"✓ Pomodoro session processed: {session_id}, records={total_processed}"
            )

            # Emit completion event
            self._emit_completion_event(session_id, job_id, total_processed)

            # Cleanup task reference
            self._processing_tasks.pop(job_id, None)

        except Exception as e:
            logger.error(
                f"✗ Pomodoro batch processing failed: {e}", exc_info=True
            )
            await self.db.pomodoro_sessions.update(
                session_id=session_id,
                processing_status="failed",
                processing_error=str(e),
            )

            # Emit failure event
            self._emit_failure_event(session_id, job_id, str(e))

            # Cleanup task reference
            self._processing_tasks.pop(job_id, None)

    def _emit_progress_event(
        self, session_id: str, job_id: str, processed: int
    ) -> None:
        """Emit progress event for frontend"""
        try:
            from core.events import emit_pomodoro_processing_progress

            emit_pomodoro_processing_progress(session_id, job_id, processed)
        except Exception as e:
            logger.debug(f"Failed to emit progress event: {e}")

    def _emit_completion_event(
        self, session_id: str, job_id: str, total_processed: int
    ) -> None:
        """Emit completion event for frontend"""
        try:
            from core.events import emit_pomodoro_processing_complete

            emit_pomodoro_processing_complete(session_id, job_id, total_processed)
        except Exception as e:
            logger.debug(f"Failed to emit completion event: {e}")

    def _emit_failure_event(
        self, session_id: str, job_id: str, error: str
    ) -> None:
        """Emit failure event for frontend"""
        try:
            from core.events import emit_pomodoro_processing_failed

            emit_pomodoro_processing_failed(session_id, job_id, error)
        except Exception as e:
            logger.debug(f"Failed to emit failure event: {e}")

    async def check_orphaned_sessions(self) -> int:
        """
        Check for orphaned sessions from previous runs

        Orphaned sessions are active sessions that were not properly closed
        (e.g., due to app crash or system shutdown).

        This should be called on application startup.

        Returns:
            Number of orphaned sessions found and recovered
        """
        try:
            orphaned = await self.db.pomodoro_sessions.get_by_status("active")

            if not orphaned:
                return 0

            logger.warning(f"Found {len(orphaned)} orphaned Pomodoro session(s)")

            for session in orphaned:
                session_id = session["id"]

                # Auto-end as 'interrupted'
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    end_time=datetime.now().isoformat(),
                    status="interrupted",
                    processing_status="pending",
                )

                # Trigger batch processing
                await self._trigger_batch_processing(session_id)

                logger.info(
                    f"✓ Recovered orphaned session: {session_id}, triggering analysis"
                )

            return len(orphaned)

        except Exception as e:
            logger.error(f"Failed to check orphaned sessions: {e}", exc_info=True)
            return 0

    async def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current session information

        Returns:
            Session info dict or None if no active session
        """
        if not self.is_active or not self.current_session:
            return None

        elapsed_minutes = (
            datetime.now() - self.current_session.start_time
        ).total_seconds() / 60

        return {
            "session_id": self.current_session.id,
            "user_intent": self.current_session.user_intent,
            "start_time": self.current_session.start_time.isoformat(),
            "elapsed_minutes": int(elapsed_minutes),
            "planned_duration_minutes": self.current_session.duration_minutes,
        }
