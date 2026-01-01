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
        self,
        user_intent: str,
        duration_minutes: int = 25,
        associated_todo_id: Optional[str] = None,
        work_duration_minutes: int = 25,
        break_duration_minutes: int = 5,
        total_rounds: int = 4,
    ) -> str:
        """
        Start a new Pomodoro session with rounds

        Actions:
        1. Create pomodoro_sessions record
        2. Signal coordinator to enter "pomodoro mode"
        3. Start phase timer for automatic work/break switching
        4. Coordinator disables continuous processing
        5. PerceptionManager captures during work phase only

        Args:
            user_intent: User's description of what they plan to work on
            duration_minutes: Total planned duration (calculated from rounds)
            associated_todo_id: Optional TODO ID to associate with this session
            work_duration_minutes: Duration of each work phase (default: 25)
            break_duration_minutes: Duration of each break phase (default: 5)
            total_rounds: Total number of work rounds (default: 4)

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

        # Calculate total duration: (work + break) * rounds - last break
        total_duration = (work_duration_minutes + break_duration_minutes) * total_rounds - break_duration_minutes

        try:
            # Save to database
            await self.db.pomodoro_sessions.create(
                session_id=session_id,
                user_intent=user_intent,
                planned_duration_minutes=total_duration,
                start_time=start_time.isoformat(),
                status="active",
                associated_todo_id=associated_todo_id,
                work_duration_minutes=work_duration_minutes,
                break_duration_minutes=break_duration_minutes,
                total_rounds=total_rounds,
            )

            # Create session object
            self.current_session = PomodoroSession(
                session_id=session_id,
                user_intent=user_intent,
                duration_minutes=total_duration,
                start_time=start_time,
            )
            self.is_active = True

            # Signal coordinator to enter pomodoro mode (work phase)
            await self.coordinator.enter_pomodoro_mode(session_id)

            # Start phase timer for automatic switching
            self._start_phase_timer(session_id, work_duration_minutes)

            logger.info(
                f"✓ Pomodoro session started: {session_id}, "
                f"intent='{user_intent}', rounds={total_rounds}, "
                f"work={work_duration_minutes}min, break={break_duration_minutes}min"
            )

            return session_id

        except Exception as e:
            logger.error(f"Failed to start Pomodoro session: {e}", exc_info=True)
            # Cleanup on failure
            self.is_active = False
            self.current_session = None
            raise

    def _start_phase_timer(self, session_id: str, duration_minutes: int) -> None:
        """
        Start a timer for current phase

        When timer expires, automatically switch to next phase.

        Args:
            session_id: Session ID
            duration_minutes: Duration of current phase in minutes
        """
        # Cancel any existing timer for this session
        if session_id in self._processing_tasks:
            self._processing_tasks[session_id].cancel()

        # Create async task for phase timer
        async def phase_timer():
            try:
                # Wait for phase duration
                await asyncio.sleep(duration_minutes * 60)

                # Switch to next phase
                await self._auto_switch_phase(session_id)

            except asyncio.CancelledError:
                logger.debug(f"Phase timer cancelled for session {session_id}")
            except Exception as e:
                logger.error(
                    f"Error in phase timer for session {session_id}: {e}",
                    exc_info=True,
                )

        # Store task reference
        task = asyncio.create_task(phase_timer())
        self._processing_tasks[session_id] = task

    async def _auto_switch_phase(self, session_id: str) -> None:
        """
        Automatically switch to next phase when current phase completes

        Phase transitions:
        - work → break: Stop perception, start break timer
        - break → work: Start perception, start work timer
        - If all rounds completed: End session

        Args:
            session_id: Session ID
        """
        try:
            # Get current session state
            session = await self.db.pomodoro_sessions.get_by_id(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for phase switch")
                return

            current_phase = session.get("current_phase", "work")
            current_round = session.get("current_round", 1)
            total_rounds = session.get("total_rounds", 4)
            work_duration = session.get("work_duration_minutes", 25)
            break_duration = session.get("break_duration_minutes", 5)

            logger.info(
                f"Auto-switching phase for session {session_id}: "
                f"current_phase={current_phase}, round={current_round}/{total_rounds}"
            )

            # Determine next phase
            if current_phase == "work":
                # Work phase completed, switch to break
                new_phase = "break"
                next_duration = break_duration

                # ★ Trigger activity aggregation for completed work phase (async, non-blocking) ★
                phase_start_time_str = session.get("phase_start_time")
                if phase_start_time_str:
                    phase_start_time = datetime.fromisoformat(phase_start_time_str)
                else:
                    # Fallback to session start time if phase start time not available
                    phase_start_time = datetime.fromisoformat(session.get("start_time", datetime.now().isoformat()))
                phase_end_time = datetime.now()

                # Run aggregation in background, don't block phase transition
                asyncio.create_task(
                    self._aggregate_work_phase_activities(
                        session_id=session_id,
                        work_phase=current_round,
                        phase_start_time=phase_start_time,
                        phase_end_time=phase_end_time,
                    )
                )

                # Stop perception during break
                await self.coordinator.exit_pomodoro_mode()

            elif current_phase == "break":
                # Break completed, switch to next work round
                new_phase = "work"
                next_duration = work_duration

                # Resume perception for work phase
                await self.coordinator.enter_pomodoro_mode(session_id)

            else:
                logger.warning(f"Unknown phase '{current_phase}' for session {session_id}")
                return

            # Update session phase in database (this increments completed_rounds for work→break)
            phase_start_time = datetime.now().isoformat()
            updated_session = await self.db.pomodoro_sessions.switch_phase(
                session_id, new_phase, phase_start_time
            )

            # Check if session completed after phase switch (all rounds done)
            if updated_session.get("status") == "completed":
                # All rounds completed, end session
                await self._complete_session(session_id)
                return

            # Start timer for next phase
            self._start_phase_timer(session_id, next_duration)

            # Emit phase switch event to frontend
            from core.events import emit_pomodoro_phase_switched

            emit_pomodoro_phase_switched(
                session_id=session_id,
                new_phase=new_phase,
                current_round=updated_session.get("current_round", current_round),
                total_rounds=total_rounds,
                completed_rounds=updated_session.get("completed_rounds", 0),
            )

            logger.info(
                f"✓ Switched to {new_phase} phase for session {session_id}, "
                f"duration={next_duration}min"
            )

        except Exception as e:
            logger.error(
                f"Failed to auto-switch phase for session {session_id}: {e}",
                exc_info=True,
            )

    async def _complete_session(self, session_id: str) -> None:
        """
        Complete a Pomodoro session after all rounds finished

        Args:
            session_id: Session ID
        """
        try:
            logger.info(f"Completing Pomodoro session {session_id}: all rounds finished")

            # Mark session as completed
            end_time = datetime.now()
            session = await self.db.pomodoro_sessions.get_by_id(session_id)

            if session:
                # Calculate actual work duration based on completed rounds
                completed_rounds = session.get("completed_rounds", 0)
                work_duration = session.get("work_duration_minutes", 25)
                actual_work_minutes = completed_rounds * work_duration

                logger.info(
                    f"Session completed: {completed_rounds} rounds × {work_duration}min = {actual_work_minutes}min"
                )

                await self.db.pomodoro_sessions.update(
                    session_id,
                    status="completed",
                    end_time=end_time.isoformat(),
                    actual_duration_minutes=actual_work_minutes,
                    current_phase="completed",
                )

            # Cleanup
            self.is_active = False
            self.current_session = None

            # Cancel phase timer
            if session_id in self._processing_tasks:
                self._processing_tasks[session_id].cancel()
                del self._processing_tasks[session_id]

            # Exit pomodoro mode
            await self.coordinator.exit_pomodoro_mode()

            # Trigger batch processing
            await self._trigger_batch_processing(session_id)

            logger.info(f"✓ Session {session_id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to complete session {session_id}: {e}", exc_info=True)

    async def end_pomodoro(self, status: str = "completed") -> Dict[str, Any]:
        """
        End current Pomodoro session (manual termination)

        Actions:
        1. Cancel phase timer
        2. Update pomodoro_sessions record
        3. Signal coordinator to exit "pomodoro mode"
        4. Trigger deferred batch processing
        5. Return processing job ID

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
        elapsed_duration = (end_time - self.current_session.start_time).total_seconds() / 60

        # Cancel phase timer if running
        if session_id in self._processing_tasks:
            self._processing_tasks[session_id].cancel()
            del self._processing_tasks[session_id]
            logger.debug(f"Cancelled phase timer for manual end of session {session_id}")

        try:
            # Check if session is too short (< 2 minutes)
            if elapsed_duration < 2:
                logger.warning(
                    f"Pomodoro session {session_id} too short ({elapsed_duration:.1f}min), skipping analysis"
                )
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    end_time=end_time.isoformat(),
                    actual_duration_minutes=int(elapsed_duration),
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

            # ★ NEW: If ending during work phase, aggregate activities for current work phase ★
            session = await self.db.pomodoro_sessions.get_by_id(session_id)
            if session and session.get("current_phase") == "work":
                current_round = session.get("current_round", 1)
                phase_start_time_str = session.get("phase_start_time")

                if phase_start_time_str:
                    phase_start_time = datetime.fromisoformat(phase_start_time_str)
                else:
                    # Fallback to session start if phase start time not available
                    phase_start_time = datetime.fromisoformat(
                        session.get("start_time", datetime.now().isoformat())
                    )

                logger.info(
                    f"Manual session end during work phase {current_round}, "
                    f"triggering activity aggregation (async)"
                )

                # Increment completed_rounds to reflect this work phase (before async call)
                completed_rounds = session.get("completed_rounds", 0) + 1
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    completed_rounds=completed_rounds,
                )

                # Trigger activity aggregation in background (non-blocking)
                asyncio.create_task(
                    self._aggregate_work_phase_activities(
                        session_id=session_id,
                        work_phase=current_round,
                        phase_start_time=phase_start_time,
                        phase_end_time=end_time,
                    )
                )

            # ★ Calculate actual work duration based on completed rounds (not elapsed time) ★
            # This ensures statistics reflect pure focus time, excluding breaks
            if session:
                completed_rounds = session.get("completed_rounds", 0)
                # If we just ended during a work phase, include it
                if session.get("current_phase") == "work":
                    completed_rounds = session.get("completed_rounds", 0) + 1

                work_duration = session.get("work_duration_minutes", 25)
                actual_work_minutes = completed_rounds * work_duration

                logger.info(
                    f"Session duration: elapsed={elapsed_duration:.1f}min, "
                    f"actual_work={actual_work_minutes}min (based on {completed_rounds} completed rounds)"
                )
            else:
                # Fallback: use elapsed time if we can't get session data
                actual_work_minutes = int(elapsed_duration)

            # Update database
            await self.db.pomodoro_sessions.update(
                session_id=session_id,
                end_time=end_time.isoformat(),
                actual_duration_minutes=actual_work_minutes,
                status=status,
                processing_status="pending",
            )

            # Exit pomodoro mode
            await self.coordinator.exit_pomodoro_mode()

            # Count raw records for this session
            raw_count = await self.db.raw_records.count_by_session(session_id)

            logger.info(
                f"✓ Pomodoro session ended: {session_id}, "
                f"status={status}, elapsed={elapsed_duration:.1f}min, "
                f"actual_work={actual_work_minutes}min, records={raw_count}"
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

            # Trigger LLM focus evaluation (async, non-blocking)
            await self._compute_and_cache_llm_evaluation(session_id)

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

    async def _compute_and_cache_llm_evaluation(self, session_id: str) -> None:
        """
        Compute LLM focus evaluation and cache to database

        Called after batch processing completes to pre-compute evaluation.
        Failures are logged but don't block session completion.

        Args:
            session_id: Pomodoro session ID
        """
        try:
            logger.info(f"Computing LLM focus evaluation for session {session_id}")

            # Get session and activities
            session = await self.db.pomodoro_sessions.get_by_id(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found for LLM evaluation")
                return

            activities = await self.db.activities.get_by_pomodoro_session(session_id)

            if not activities:
                logger.info(f"No activities for session {session_id}, skipping LLM evaluation")
                return

            # Compute LLM evaluation
            from llm.focus_evaluator import get_focus_evaluator

            focus_evaluator = get_focus_evaluator()
            llm_result = await focus_evaluator.evaluate_focus(
                activities=activities,
                session_info=session,
            )

            # Cache result to database
            await self.db.pomodoro_sessions.update_llm_evaluation(
                session_id, llm_result
            )

            logger.info(
                f"✓ LLM evaluation cached for session {session_id}: "
                f"score={llm_result.get('focus_score')}, "
                f"level={llm_result.get('focus_level')}"
            )

        except Exception as e:
            # Don't crash session completion if LLM evaluation fails
            logger.error(
                f"Failed to compute LLM evaluation for session {session_id}: {e}",
                exc_info=True,
            )
            # Continue gracefully - evaluation can be computed on-demand later

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

                # Calculate actual work duration based on completed rounds
                completed_rounds = session.get("completed_rounds", 0)
                # If session was interrupted during a work phase, include it
                if session.get("current_phase") == "work":
                    completed_rounds += 1

                work_duration = session.get("work_duration_minutes", 25)
                actual_work_minutes = completed_rounds * work_duration

                # Auto-end as 'interrupted'
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    end_time=datetime.now().isoformat(),
                    actual_duration_minutes=actual_work_minutes,
                    status="interrupted",
                    processing_status="pending",
                )

                # Trigger batch processing
                await self._trigger_batch_processing(session_id)

                logger.info(
                    f"✓ Recovered orphaned session: {session_id}, "
                    f"actual_work={actual_work_minutes}min, triggering analysis"
                )

            return len(orphaned)

        except Exception as e:
            logger.error(f"Failed to check orphaned sessions: {e}", exc_info=True)
            return 0

    async def get_current_session_info(self) -> Optional[Dict[str, Any]]:
        """
        Get current session information with rounds and phase data

        Returns:
            Session info dict or None if no active session
        """
        if not self.is_active or not self.current_session:
            return None

        # Fetch full session info from database to get all fields
        session_record = await self.db.pomodoro_sessions.get_by_id(
            self.current_session.id
        )

        if not session_record:
            return None

        now = datetime.now()
        elapsed_minutes = (
            now - self.current_session.start_time
        ).total_seconds() / 60

        # Get phase information
        current_phase = session_record.get("current_phase", "work")
        phase_start_time_str = session_record.get("phase_start_time")
        work_duration = session_record.get("work_duration_minutes", 25)
        break_duration = session_record.get("break_duration_minutes", 5)

        # Calculate remaining time in current phase
        remaining_phase_seconds = None
        if phase_start_time_str:
            try:
                phase_start = datetime.fromisoformat(phase_start_time_str)
                phase_elapsed = (now - phase_start).total_seconds()

                # Determine phase duration
                phase_duration_seconds = (
                    work_duration * 60
                    if current_phase == "work"
                    else break_duration * 60
                )

                remaining_phase_seconds = max(
                    0, int(phase_duration_seconds - phase_elapsed)
                )
            except Exception as e:
                logger.warning(f"Failed to calculate remaining time: {e}")

        session_info = {
            "session_id": self.current_session.id,
            "user_intent": self.current_session.user_intent,
            "start_time": self.current_session.start_time.isoformat(),
            "elapsed_minutes": int(elapsed_minutes),
            "planned_duration_minutes": self.current_session.duration_minutes,
            "associated_todo_id": session_record.get("associated_todo_id"),
            "associated_todo_title": None,
            # Rounds data
            "work_duration_minutes": work_duration,
            "break_duration_minutes": break_duration,
            "total_rounds": session_record.get("total_rounds", 4),
            "current_round": session_record.get("current_round", 1),
            "current_phase": current_phase,
            "phase_start_time": phase_start_time_str,
            "completed_rounds": session_record.get("completed_rounds", 0),
            "remaining_phase_seconds": remaining_phase_seconds,
        }

        # If there's an associated TODO, fetch its title
        todo_id = session_info["associated_todo_id"]
        if todo_id:
            try:
                # Ensure todo_id is a string for type safety
                todo_id_str = str(todo_id) if not isinstance(todo_id, str) else todo_id
                todo = await self.db.todos.get_by_id(todo_id_str)
                if todo and not todo.get("deleted"):
                    session_info["associated_todo_title"] = todo.get("title")
            except Exception as e:
                logger.warning(
                    f"Failed to fetch TODO title for session {self.current_session.id}: {e}"
                )

        return session_info

    async def _aggregate_work_phase_activities(
        self,
        session_id: str,
        work_phase: int,
        phase_start_time: datetime,
        phase_end_time: datetime,
    ) -> None:
        """
        Trigger SessionAgent to aggregate activities for a completed work phase

        This method is called when a work phase ends (work → break transition).
        It delegates to SessionAgent.aggregate_work_phase() to create activities
        and emits an event to notify the frontend.

        Args:
            session_id: Pomodoro session ID
            work_phase: Work phase number (1-based)
            phase_start_time: When this work phase started
            phase_end_time: When this work phase ended
        """
        try:
            logger.info(
                f"Triggering work phase aggregation: session={session_id}, "
                f"phase={work_phase}, "
                f"duration={(phase_end_time - phase_start_time).total_seconds() / 60:.1f}min"
            )

            # Get SessionAgent from coordinator
            session_agent = self.coordinator.session_agent
            if not session_agent:
                logger.warning(
                    "SessionAgent not available for work phase aggregation. "
                    "Activities will not be generated for this work phase."
                )
                return

            # Trigger activity aggregation
            activities = await session_agent.aggregate_work_phase(
                session_id=session_id,
                work_phase=work_phase,
                phase_start_time=phase_start_time,
                phase_end_time=phase_end_time,
            )

            activity_count = len(activities)
            logger.info(
                f"Work phase aggregation completed: {activity_count} activities "
                f"created/updated for phase {work_phase}"
            )

            # Emit event to frontend to notify work phase completion
            from core.events import emit_pomodoro_work_phase_completed

            emit_pomodoro_work_phase_completed(
                session_id=session_id,
                work_phase=work_phase,
                activity_count=activity_count,
            )

        except Exception as e:
            # Don't crash the session flow if aggregation fails
            # Log error but allow phase switch to proceed
            logger.error(
                f"Failed to aggregate work phase activities "
                f"(session: {session_id}, phase: {work_phase}): {e}",
                exc_info=True,
            )

    def get_current_session_id(self) -> Optional[str]:
        """
        Get current active Pomodoro session ID

        Returns:
            Session ID if a Pomodoro session is active, None otherwise
        """
        if self.is_active and self.current_session:
            return self.current_session.id
        return None
