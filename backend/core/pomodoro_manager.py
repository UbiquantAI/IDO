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
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from core.db import get_db
from core.events import (
    emit_pomodoro_phase_switched,
    emit_pomodoro_processing_complete,
    emit_pomodoro_processing_failed,
    emit_pomodoro_processing_progress,
    emit_pomodoro_work_phase_completed,
    emit_pomodoro_work_phase_failed,
)
from core.logger import get_logger

if TYPE_CHECKING:
    from llm.focus_evaluator import FocusEvaluator

logger = get_logger(__name__)


class _Constants:
    """Pomodoro manager constants to eliminate magic numbers"""

    # Session timing
    PROCESSING_STUCK_THRESHOLD_MINUTES = 15
    MIN_SESSION_DURATION_MINUTES = 2

    # Processing timeouts
    MAX_PHASE_WAIT_SECONDS = 300  # 5 minutes
    TOTAL_PROCESSING_TIMEOUT_SECONDS = 600  # 10 minutes
    POLL_INTERVAL_SECONDS = 3

    # Retry configuration
    MAX_RETRIES = 1
    RETRY_DELAY_SECONDS = 10

    # Default Pomodoro settings
    DEFAULT_WORK_DURATION_MINUTES = 25
    DEFAULT_BREAK_DURATION_MINUTES = 5
    DEFAULT_TOTAL_ROUNDS = 4


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
        self.current_session: PomodoroSession | None = None
        self.is_active = False
        self._processing_tasks: dict[str, asyncio.Task] = {}

    # ============================================================
    # Helper Methods - Session State Management
    # ============================================================

    def _clear_session_state(self) -> None:
        """Clear current session state (unified cleanup)"""
        self.is_active = False
        self.current_session = None

    def _cancel_phase_timer(self, session_id: str) -> None:
        """Cancel phase timer for a session if running"""
        if session_id in self._processing_tasks:
            self._processing_tasks[session_id].cancel()
            del self._processing_tasks[session_id]
            logger.debug(f"Cancelled phase timer for session {session_id}")

    def _get_session_defaults(self, session: dict[str, Any]) -> tuple[int, int, int]:
        """
        Get session configuration with defaults

        Returns:
            Tuple of (work_duration, break_duration, total_rounds)
        """
        return (
            session.get("work_duration_minutes", _Constants.DEFAULT_WORK_DURATION_MINUTES),
            session.get("break_duration_minutes", _Constants.DEFAULT_BREAK_DURATION_MINUTES),
            session.get("total_rounds", _Constants.DEFAULT_TOTAL_ROUNDS),
        )

    # ============================================================
    # Helper Methods - Time Calculations
    # ============================================================

    def _calculate_elapsed_minutes(self, end_time: datetime) -> float:
        """Calculate elapsed minutes from session start"""
        if not self.current_session:
            return 0.0
        return (end_time - self.current_session.start_time).total_seconds() / 60

    async def _calculate_actual_work_minutes(
        self,
        session: dict[str, Any],
        end_time: datetime,
    ) -> int:
        """
        Calculate actual work duration in minutes

        For completed rounds: use full work_duration
        For current incomplete work phase: use actual elapsed time

        Args:
            session: Session record from database
            end_time: Session end time

        Returns:
            Actual work minutes (integer)
        """
        completed_rounds = session.get("completed_rounds", 0)
        work_duration, _, _ = self._get_session_defaults(session)
        current_phase = session.get("current_phase", "work")

        # Calculate time for completed rounds
        actual_work_minutes = completed_rounds * work_duration

        # If ending during work phase, add actual time worked in current phase
        if current_phase == "work":
            phase_start_time_str = session.get("phase_start_time")
            if phase_start_time_str:
                phase_start_time = datetime.fromisoformat(phase_start_time_str)
                current_phase_minutes = (end_time - phase_start_time).total_seconds() / 60
                actual_work_minutes += int(current_phase_minutes)
                logger.debug(
                    f"Adding {int(current_phase_minutes)}min from current work phase"
                )
            else:
                # Fallback: use full work_duration for current phase
                actual_work_minutes += work_duration
                logger.warning("No phase_start_time found, using full work_duration")

        return actual_work_minutes

    # ============================================================
    # Helper Methods - Event Emission
    # ============================================================

    def _emit_phase_completion_event(
        self,
        session_id: str,
        session: dict[str, Any] | None = None,
        phase: str = "completed",
    ) -> None:
        """
        Emit phase switched event (unified helper)

        Args:
            session_id: Session ID
            session: Optional session dict for round info
            phase: Phase name (default: "completed")
        """
        current_round = 1
        total_rounds = _Constants.DEFAULT_TOTAL_ROUNDS
        completed_rounds = 0

        if session:
            current_round = session.get("current_round", 1)
            total_rounds = session.get("total_rounds", _Constants.DEFAULT_TOTAL_ROUNDS)
            completed_rounds = session.get("completed_rounds", 0)

        emit_pomodoro_phase_switched(
            session_id=session_id,
            new_phase=phase,
            current_round=current_round,
            total_rounds=total_rounds,
            completed_rounds=completed_rounds,
        )
        logger.debug(f"Emitted phase event: session={session_id}, phase={phase}")

    def _emit_progress_event(
        self, session_id: str, job_id: str, processed: int
    ) -> None:
        """Emit progress event for frontend"""
        try:
            emit_pomodoro_processing_progress(session_id, job_id, processed)
        except Exception as e:
            logger.debug(f"Failed to emit progress event: {e}")

    def _emit_completion_event(
        self, session_id: str, job_id: str, total_processed: int
    ) -> None:
        """Emit completion event for frontend"""
        try:
            emit_pomodoro_processing_complete(session_id, job_id, total_processed)
        except Exception as e:
            logger.debug(f"Failed to emit completion event: {e}")

    def _emit_failure_event(
        self, session_id: str, job_id: str, error: str
    ) -> None:
        """Emit failure event for frontend"""
        try:
            emit_pomodoro_processing_failed(session_id, job_id, error)
        except Exception as e:
            logger.debug(f"Failed to emit failure event: {e}")

    # ============================================================
    # Helper Methods - Processing Status Checks
    # ============================================================

    async def _check_and_handle_stuck_processing(self) -> None:
        """
        Check for orphaned ACTIVE sessions only (not processing status)

        Processing status is now independent and should NOT block new sessions.
        Only check for truly orphaned active sessions from app crashes.

        Background processing runs independently and doesn't prevent new sessions.
        """
        # ✅ NEW: Only check status="active" (orphaned sessions from crashes)
        # Processing status is independent and doesn't block new sessions
        active_sessions = await self.db.pomodoro_sessions.get_by_status("active")
        if not active_sessions:
            return

        # Orphaned active session found - clean it up
        for session in active_sessions:
            session_id = session["id"]
            logger.warning(
                f"Found orphaned active session {session_id}, "
                f"marking as abandoned (app restart detected)"
            )

            # Force end the orphaned session
            # This code path only triggers on app restart after crash
            await self.db.pomodoro_sessions.update(
                session_id=session_id,
                status="abandoned",
                processing_status="failed",
                processing_error="Session orphaned (app restart detected)",
            )

    def _classify_aggregation_error(self, error: Exception) -> str:
        """
        Classify aggregation errors for better user feedback.

        Returns:
            - 'no_actions_found': No user activity during phase
            - 'llm_clustering_failed': LLM API call failed
            - 'supervisor_validation_failed': Activity validation failed
            - 'database_save_failed': Database operation failed
            - 'unknown_error': Unclassified error
        """
        error_str = str(error).lower()

        if "no actions found" in error_str or "no action" in error_str:
            return "no_actions_found"
        elif "clustering" in error_str or "llm" in error_str or "api" in error_str:
            return "llm_clustering_failed"
        elif "supervisor" in error_str or "validation" in error_str:
            return "supervisor_validation_failed"
        elif "database" in error_str or "sql" in error_str:
            return "database_save_failed"
        else:
            return "unknown_error"

    # ============================================================
    # Main Public Methods
    # ============================================================

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

        # Check for stuck processing sessions
        await self._check_and_handle_stuck_processing()

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

            # Emit phase switch event to notify frontend that work phase started
            emit_pomodoro_phase_switched(
                session_id=session_id,
                new_phase="work",
                current_round=1,
                total_rounds=total_rounds,
                completed_rounds=0,
            )

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
            work_duration, break_duration, total_rounds = self._get_session_defaults(session)

            logger.info(
                f"Auto-switching phase for session {session_id}: "
                f"current_phase={current_phase}, round={current_round}/{total_rounds}"
            )

            # Determine next phase
            if current_phase == "work":
                # Work phase completed, switch to break
                new_phase = "break"
                next_duration = break_duration

                # Calculate phase timing
                phase_start_time_str = session.get("phase_start_time")
                if phase_start_time_str:
                    phase_start_time = datetime.fromisoformat(phase_start_time_str)
                else:
                    # Fallback to session start time if phase start time not available
                    phase_start_time = datetime.fromisoformat(
                        session.get("start_time", datetime.now().isoformat())
                    )
                phase_end_time = datetime.now()

                # ★ NEW: Create phase record BEFORE triggering aggregation ★
                phase_id = await self.db.work_phases.create(
                    session_id=session_id,
                    phase_number=current_round,
                    phase_start_time=phase_start_time.isoformat(),
                    phase_end_time=phase_end_time.isoformat(),
                    status="pending",
                )

                logger.info(
                    f"Created phase record: session={session_id}, "
                    f"phase={current_round}, id={phase_id}"
                )

                # ★ FORCE SETTLEMENT: Process all pending records before phase ends ★
                # This ensures no actions are lost during phase transition
                logger.info(
                    f"Force settling all pending records for work phase {current_round}"
                )
                settlement_result = await self.force_settlement(session_id)
                if settlement_result.get("success"):
                    logger.info(
                        f"✓ Force settlement successful: "
                        f"{settlement_result['records_processed']['total']} records processed, "
                        f"{settlement_result['events_generated']} events, "
                        f"{settlement_result['activities_generated']} activities"
                    )
                else:
                    logger.warning(
                        f"Force settlement had issues but continuing: "
                        f"{settlement_result.get('error', 'Unknown error')}"
                    )

                # ★ CRITICAL: Stop perception AFTER force settlement ★
                # This ensures no new records are captured while we're aggregating
                # Stop perception during break
                await self.coordinator.exit_pomodoro_mode()

                # ★ Trigger aggregation AFTER stopping perception ★
                # This guarantees all captured records have been processed
                asyncio.create_task(
                    self._aggregate_work_phase_activities(
                        session_id=session_id,
                        work_phase=current_round,
                        phase_start_time=phase_start_time,
                        phase_end_time=phase_end_time,
                        phase_id=phase_id,
                    )
                )

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

                # Emit completion event to frontend (so desktop clock can switch to normal mode)
                self._emit_phase_completion_event(session_id, session, "completed")
                logger.info(f"Emitted completion event for session {session_id}")

            # Cleanup
            self._clear_session_state()
            self._cancel_phase_timer(session_id)

            # Exit pomodoro mode
            await self.coordinator.exit_pomodoro_mode()

            # Trigger batch processing
            await self._trigger_batch_processing(session_id)

            logger.info(f"✓ Session {session_id} completed successfully")

        except Exception as e:
            logger.error(f"Failed to complete session {session_id}: {e}", exc_info=True)

    # ============================================================
    # Helper Methods - End Pomodoro Workflow
    # ============================================================

    async def _handle_too_short_session(
        self,
        session_id: str,
        end_time: datetime,
        elapsed_minutes: float,
    ) -> dict[str, Any]:
        """
        Handle sessions that are too short (< 2 minutes) - immediate return

        Args:
            session_id: Session ID
            end_time: Session end time
            elapsed_minutes: Elapsed duration in minutes

        Returns:
            Response dict for too-short session
        """
        logger.warning(
            f"Pomodoro session {session_id} too short ({elapsed_minutes:.1f}min), marking as abandoned"
        )

        # Update database (fast)
        await self.db.pomodoro_sessions.update(
            session_id=session_id,
            end_time=end_time.isoformat(),
            actual_duration_minutes=int(elapsed_minutes),
            status="abandoned",
            processing_status="failed",
        )

        # Emit completion event IMMEDIATELY for frontend/clock to reset state
        self._emit_phase_completion_event(session_id)
        logger.info(f"Emitted completion event for abandoned session {session_id}")

        # Exit pomodoro mode and cleanup
        await self.coordinator.exit_pomodoro_mode()
        self._clear_session_state()

        return {
            "session_id": session_id,
            "status": "abandoned",
            "actual_work_minutes": 0,
            "raw_records_count": 0,  # ✅ Added back for compatibility
            "message": "Session too short, marked as abandoned",
        }

    async def _process_incomplete_phases(
        self,
        session_id: str,
        session: dict[str, Any],
        end_time: datetime,
    ) -> None:
        """
        Process all work phases that occurred during session (parallel processing)

        CRITICAL: This is a background task that must not crash.
        All errors are isolated and logged.

        Args:
            session_id: Session ID
            session: Session record from database
            end_time: Session end time
        """
        try:
            current_phase = session.get("current_phase", "work")
            current_round = session.get("current_round", 1)
            completed_rounds = session.get("completed_rounds", 0)

            # Identify all work phases to process
            work_phases_to_process = list(range(1, completed_rounds + 1))

            # Include current work phase if session ended during work
            if current_phase == "work" and current_round not in work_phases_to_process:
                work_phases_to_process.append(current_round)
                # Increment completed_rounds to reflect this work phase
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    completed_rounds=completed_rounds + 1,
                )

            logger.info(
                f"Session termination: processing {len(work_phases_to_process)} work phases "
                f"in parallel: {work_phases_to_process}"
            )

            # Create phase records and trigger parallel aggregation
            aggregation_tasks = []
            for phase_num in work_phases_to_process:
                # Use unified time window calculation
                phase_start, phase_end = await self._get_phase_time_window(session, phase_num)

                # Use actual end time for last phase (if ending during work)
                if phase_num == max(work_phases_to_process) and current_phase == "work":
                    phase_end = min(phase_end, end_time)

                # Check if phase record already exists
                existing_phase = await self.db.work_phases.get_by_session_and_phase(
                    session_id, phase_num
                )

                # Skip if already completed or processing
                if existing_phase and existing_phase["status"] in ("completed", "processing"):
                    logger.info(
                        f"Phase {phase_num} already {existing_phase['status']}, skipping"
                    )
                    continue

                # Create or get phase record
                if existing_phase:
                    phase_id = existing_phase["id"]
                else:
                    phase_id = await self.db.work_phases.create(
                        session_id=session_id,
                        phase_number=phase_num,
                        phase_start_time=phase_start.isoformat(),
                        phase_end_time=phase_end.isoformat(),
                        status="pending",
                    )

                # Create parallel task (don't await)
                task = asyncio.create_task(
                    self._aggregate_work_phase_activities(
                        session_id=session_id,
                        work_phase=phase_num,
                        phase_start_time=phase_start,
                        phase_end_time=phase_end,
                        phase_id=phase_id,
                    )
                )
                aggregation_tasks.append(task)

            logger.info(
                f"Triggered parallel aggregation for {len(aggregation_tasks)} work phases"
            )

        except Exception as e:
            # ✅ Isolate all errors to prevent crash
            logger.error(
                f"Error processing incomplete phases for session {session_id}: {e}",
                exc_info=True,
            )
            # Don't re-raise - this is a background task

    async def _update_session_metadata(
        self,
        session_id: str,
        end_time: datetime,
        actual_work_minutes: int,
        status: str,
    ) -> None:
        """
        Update session metadata in database (fast, non-blocking)

        Args:
            session_id: Session ID
            end_time: Session end time
            actual_work_minutes: Actual work duration in minutes
            status: Session status
        """
        await self.db.pomodoro_sessions.update(
            session_id=session_id,
            end_time=end_time.isoformat(),
            actual_duration_minutes=actual_work_minutes,
            status=status,
            processing_status="pending",
        )

    async def _background_finalize_session(
        self,
        session_id: str,
    ) -> None:
        """
        Background task: force settlement, cleanup, trigger processing

        CRITICAL: This task MUST NEVER crash or block new sessions.
        All errors are logged but do not propagate.

        This runs asynchronously after user-facing state has been updated.

        Args:
            session_id: Session ID
        """
        try:
            logger.info(f"Starting background finalization for session {session_id}")

            # Force settlement: process all pending records
            # ✅ Isolate settlement errors to prevent crash
            try:
                logger.info("Force settling all pending records for session end")
                settlement_result = await self.force_settlement(session_id)
                if settlement_result.get("success"):
                    logger.info(
                        f"✓ Force settlement successful: "
                        f"{settlement_result['records_processed']['total']} records processed, "
                        f"{settlement_result['events_generated']} events, "
                        f"{settlement_result['activities_generated']} activities"
                    )
                else:
                    logger.warning(
                        f"Force settlement had issues but continuing: "
                        f"{settlement_result.get('error', 'Unknown error')}"
                    )
            except Exception as e:
                # ✅ Isolate settlement errors
                logger.error(f"Force settlement failed: {e}", exc_info=True)

            # Trigger batch processing
            # ✅ Isolate batch processing errors to prevent crash
            try:
                await self._trigger_batch_processing(session_id)
            except Exception as e:
                # ✅ Isolate batch processing errors
                logger.error(f"Batch processing failed: {e}", exc_info=True)

            logger.info(f"✓ Background finalization completed for session {session_id}")

        except Exception as e:
            # ✅ Catch-all for any unexpected errors
            logger.error(
                f"Unexpected error in background finalization: {e}",
                exc_info=True,
            )
            # Mark processing as failed so it doesn't appear stuck
            try:
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    processing_status="failed",
                    processing_error=f"Background finalization error: {str(e)}",
                )
            except:
                # Even DB update failure shouldn't crash
                pass

    # ============================================================
    # Public Methods - Session Control
    # ============================================================

    async def end_pomodoro(self, status: str = "completed") -> dict[str, Any]:
        """
        End current Pomodoro session (manual termination)

        IMPORTANT: This method returns IMMEDIATELY after updating user-facing state.
        All heavy processing (settlement, aggregation) happens in background.

        Workflow:
        1. ✅ Validate session (fast)
        2. ✅ Cancel phase timer (fast)
        3. ✅ Update database metadata (fast)
        4. ✅ Flush perception buffers (fast)
        5. ✅ Emit completion event (fast)
        6. ✅ Exit pomodoro mode (fast)
        7. ✅ Clear local state (fast)
        8. ✅ Return immediately to user
        9. 🔄 Start background processing (async, non-blocking)

        Args:
            status: Session status ('completed', 'abandoned', 'interrupted')

        Returns:
            {
                "session_id": str,
                "status": str,
                "actual_work_minutes": int
            }

        Raises:
            ValueError: If no active Pomodoro session
        """
        if not self.is_active or not self.current_session:
            raise ValueError("No active Pomodoro session")

        session_id = self.current_session.id
        end_time = datetime.now()
        elapsed_duration = self._calculate_elapsed_minutes(end_time)

        # Cancel phase timer if running
        self._cancel_phase_timer(session_id)

        try:
            # Check if session is too short (< 2 minutes)
            if elapsed_duration < _Constants.MIN_SESSION_DURATION_MINUTES:
                return await self._handle_too_short_session(
                    session_id, end_time, elapsed_duration
                )

            # ========== FAST PATH: Immediate user-facing updates ==========

            # Get session data
            session = await self.db.pomodoro_sessions.get_by_id(session_id)

            # Calculate actual work duration
            actual_work_minutes = (
                await self._calculate_actual_work_minutes(session, end_time)
                if session
                else int(elapsed_duration)
            )

            # Update database metadata (fast, no heavy processing)
            await self._update_session_metadata(
                session_id, end_time, actual_work_minutes, status
            )

            # Flush ImageConsumer buffer (fast)
            perception_manager = self.coordinator.perception_manager
            if perception_manager and perception_manager.image_consumer:
                remaining = perception_manager.image_consumer.flush()
                logger.debug(f"Flushed {len(remaining)} buffered screenshots")

            # Emit completion event IMMEDIATELY for frontend/clock
            self._emit_phase_completion_event(session_id, session, "completed")
            logger.info(f"Emitted completion event for session {session_id}")

            # Exit pomodoro mode (stops perception)
            await self.coordinator.exit_pomodoro_mode()

            # Clear local state
            self._clear_session_state()

            logger.info(
                f"✓ Pomodoro session ended (immediate response): {session_id}, "
                f"status={status}, elapsed={elapsed_duration:.1f}min, "
                f"actual_work={actual_work_minutes}min"
            )

            # ========== BACKGROUND PATH: Heavy processing (non-blocking) ==========

            # Trigger background tasks asynchronously
            if session:
                # Process incomplete work phases (parallel, background)
                asyncio.create_task(
                    self._process_incomplete_phases(session_id, session, end_time)
                )

            # Trigger background finalization (settlement + batch processing)
            asyncio.create_task(self._background_finalize_session(session_id))

            logger.debug(f"Background processing started for session {session_id}")

            # ========== IMMEDIATE RETURN ==========

            # Count raw records for compatibility with frontend/handler
            raw_count = await self.db.raw_records.count_by_session(session_id)

            return {
                "session_id": session_id,
                "status": status,
                "actual_work_minutes": actual_work_minutes,
                "raw_records_count": raw_count,  # ✅ Added back for compatibility
                "message": "Session ended successfully. Background processing started.",
            }

        except Exception as e:
            logger.error(f"Failed to end Pomodoro session: {e}", exc_info=True)
            # Ensure state is cleaned up even on error
            self._clear_session_state()
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
        SIMPLIFIED: Wait for all work phases to complete and trigger LLM evaluation

        NOTE: Batch processing of raw records is removed. All data processing
        now happens through phase-level aggregation in _aggregate_work_phase_activities.

        Steps:
        1. Update status to 'processing'
        2. Wait for all work phases to complete (max 5 minutes)
        3. Trigger LLM evaluation (with timeout protection)
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

            logger.info(f"→ Waiting for work phases to complete: {session_id}")

            # Wrap entire processing in timeout (max 10 minutes total)
            # This prevents processing from hanging indefinitely
            try:
                await asyncio.wait_for(
                    self._wait_and_trigger_llm_evaluation(session_id),
                    timeout=_Constants.TOTAL_PROCESSING_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                logger.error(
                    f"Processing timeout (10 minutes) for session {session_id}, "
                    f"marking as failed"
                )
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    processing_status="failed",
                    processing_error="Processing timeout (10 minutes exceeded)",
                )
                self._emit_failure_event(session_id, job_id, "Processing timeout")
                self._processing_tasks.pop(job_id, None)
                return

            # Update status
            await self.db.pomodoro_sessions.update(
                session_id=session_id,
                processing_status="completed",
                processing_completed_at=datetime.now().isoformat(),
            )

            logger.info(f"✓ Pomodoro session completed: {session_id}")

            # Emit completion event
            self._emit_completion_event(session_id, job_id, 0)

            # Cleanup task reference
            self._processing_tasks.pop(job_id, None)

        except Exception as e:
            logger.error(
                f"✗ Pomodoro session completion failed: {e}", exc_info=True
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



    async def _wait_and_trigger_llm_evaluation(self, session_id: str) -> None:
        """
        Wait for all work phases to complete successfully, then trigger LLM evaluation.

        This ensures AI analysis only runs after all activity data is ready.
        For initial generation, retries are automatic. For subsequent failures,
        users can manually retry.

        Args:
            session_id: Pomodoro session ID
        """
        try:
            logger.info(f"Waiting for all work phases to complete for session {session_id}")

            # Get session info
            session = await self.db.pomodoro_sessions.get_by_id(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found, skipping LLM evaluation wait")
                return

            # Check if session is still active/pending (not already ended)
            session_status = session.get("processing_status", "pending")
            if session_status not in ("pending", "processing"):
                logger.info(
                    f"Session {session_id} status is '{session_status}', skipping LLM evaluation wait"
                )
                return

            # Use completed_rounds instead of total_rounds
            # When user ends session early, only completed_rounds phases are created
            completed_rounds = session.get("completed_rounds", 0)
            if completed_rounds == 0:
                # No work phases completed, skip waiting
                logger.info(
                    f"No completed work phases for session {session_id}, "
                    f"proceeding directly to LLM evaluation"
                )
                await self._compute_and_cache_llm_evaluation(session_id, is_first_attempt=True)
                return

            expected_phases = completed_rounds
            waited_time = 0

            # Wait for all completed phases to reach terminal state (completed or failed)
            while waited_time < _Constants.MAX_PHASE_WAIT_SECONDS:
                # Re-check session status in case it was ended during wait
                session = await self.db.pomodoro_sessions.get_by_id(session_id)
                if session:
                    current_status = session.get("processing_status", "pending")
                    if current_status not in ("pending", "processing"):
                        logger.info(
                            f"Session {session_id} status changed to '{current_status}', "
                            f"stopping LLM evaluation wait"
                        )
                        return

                phases = await self.db.work_phases.get_by_session(session_id)

                # Check if all expected work phases exist and have terminal status
                completed_phases = [p for p in phases if p["status"] == "completed"]
                failed_phases = [p for p in phases if p["status"] == "failed"]
                terminal_phases = completed_phases + failed_phases

                if len(terminal_phases) >= expected_phases:
                    # All expected phases have reached terminal state
                    logger.info(
                        f"All {expected_phases} work phases reached terminal state: "
                        f"completed={len(completed_phases)}, failed={len(failed_phases)}"
                    )
                    break

                # Still waiting for phases to complete
                logger.debug(
                    f"Waiting for work phases: {len(terminal_phases)}/{expected_phases} complete, "
                    f"waited {waited_time}s"
                )

                await asyncio.sleep(_Constants.POLL_INTERVAL_SECONDS)
                waited_time += _Constants.POLL_INTERVAL_SECONDS

            if waited_time >= _Constants.MAX_PHASE_WAIT_SECONDS:
                logger.warning(
                    f"Timeout waiting for work phases to complete ({_Constants.MAX_PHASE_WAIT_SECONDS}s), "
                    f"proceeding with LLM evaluation anyway"
                )

            # Now trigger LLM evaluation
            await self._compute_and_cache_llm_evaluation(session_id, is_first_attempt=True)

        except Exception as e:
            logger.error(
                f"Error waiting for phases before LLM evaluation: {e}",
                exc_info=True
            )
            # Continue to try LLM evaluation anyway
            await self._compute_and_cache_llm_evaluation(session_id, is_first_attempt=True)

    async def _compute_and_cache_llm_evaluation(
        self, session_id: str, is_first_attempt: bool = False
    ) -> None:
        """
        Compute LLM focus evaluation and cache to database

        Called after all work phases complete to pre-compute evaluation.
        Failures are logged but don't block session completion.

        This method now also updates individual activity focus_scores for
        better data granularity and frontend display.

        Args:
            session_id: Pomodoro session ID
            is_first_attempt: Whether this is the first automatic attempt
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

            # Compute LLM evaluation (session-level)
            from llm.focus_evaluator import get_focus_evaluator

            focus_evaluator = get_focus_evaluator()
            llm_result = await focus_evaluator.evaluate_focus(
                activities=activities,
                session_info=session,
            )

            # Cache session-level result to database
            await self.db.pomodoro_sessions.update_llm_evaluation(
                session_id, llm_result
            )

            logger.info(
                f"✓ LLM evaluation cached for session {session_id}: "
                f"score={llm_result.get('focus_score')}, "
                f"level={llm_result.get('focus_level')}"
            )

            # Update individual activity focus scores for better granularity
            await self._update_activity_focus_scores(
                session_id, activities, session, focus_evaluator
            )

        except Exception as e:
            # Don't crash session completion if LLM evaluation fails
            logger.error(
                f"Failed to compute LLM evaluation for session {session_id}: {e}",
                exc_info=True,
            )
            # Continue gracefully - evaluation can be computed on-demand later

    async def _update_activity_focus_scores(
        self,
        session_id: str,
        activities: list[dict[str, Any]],
        session: dict[str, Any],
        focus_evaluator: "FocusEvaluator",
    ) -> None:
        """
        Update focus scores for individual activities

        This provides better granularity than session-level scores and enables
        per-activity focus analysis in the frontend.

        Args:
            session_id: Pomodoro session ID
            activities: List of activity dictionaries
            session: Session dictionary with user_intent and related_todos
            focus_evaluator: FocusEvaluator instance
        """
        try:
            logger.debug(f"Updating focus scores for {len(activities)} activities")

            # Prepare session context for evaluation
            session_context = {
                "user_intent": session.get("user_intent"),
                "related_todos": session.get("related_todos", []),
            }

            # Evaluate and update each activity
            activity_scores = []
            for activity in activities:
                try:
                    # Evaluate single activity focus
                    activity_eval = await focus_evaluator.evaluate_activity_focus(
                        activity=activity,
                        session_context=session_context,
                    )

                    focus_score = activity_eval.get("focus_score", 50.0)
                    activity_scores.append({
                        "activity_id": activity["id"],
                        "focus_score": focus_score,
                    })

                    logger.debug(
                        f"Activity '{activity.get('title', 'Untitled')[:30]}' "
                        f"focus_score: {focus_score}"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to evaluate activity {activity.get('id')}: {e}, "
                        f"using default score"
                    )
                    # Use default score on failure
                    activity_scores.append({
                        "activity_id": activity["id"],
                        "focus_score": 50.0,
                    })

            # Batch update all activity focus scores
            if activity_scores:
                updated_count = await self.db.activities.batch_update_focus_scores(
                    activity_scores
                )
                logger.info(
                    f"✓ Updated focus_scores for {updated_count} activities "
                    f"in session {session_id}"
                )

        except Exception as e:
            logger.error(
                f"Failed to update activity focus scores for session {session_id}: {e}",
                exc_info=True,
            )
            # Non-critical error, continue gracefully

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
                recovery_time = datetime.now()

                # Calculate actual work duration
                completed_rounds = session.get("completed_rounds", 0)
                work_duration = session.get("work_duration_minutes", 25)
                actual_work_minutes = completed_rounds * work_duration

                # If session was interrupted during a work phase, add actual time worked
                if session.get("current_phase") == "work":
                    phase_start_time_str = session.get("phase_start_time")
                    if phase_start_time_str:
                        try:
                            phase_start_time = datetime.fromisoformat(phase_start_time_str)
                            # Calculate actual time worked in interrupted phase (in minutes)
                            current_phase_minutes = (recovery_time - phase_start_time).total_seconds() / 60
                            actual_work_minutes += int(current_phase_minutes)
                            logger.info(
                                f"Orphaned session {session_id} interrupted during work phase: "
                                f"adding {int(current_phase_minutes)}min to total"
                            )
                        except Exception as e:
                            # Fallback: if phase_start_time parsing fails, use full work_duration
                            actual_work_minutes += work_duration
                            logger.warning(
                                f"Failed to parse phase_start_time for orphaned session {session_id}, "
                                f"using full work_duration: {e}"
                            )
                    else:
                        # Fallback: if no phase_start_time, use full work_duration
                        actual_work_minutes += work_duration
                        logger.warning(
                            f"No phase_start_time for orphaned session {session_id}, "
                            f"using full work_duration ({work_duration}min)"
                        )

                # Auto-end as 'abandoned' (SIMPLIFIED: interrupted → abandoned)
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    end_time=recovery_time.isoformat(),
                    actual_duration_minutes=actual_work_minutes,
                    status="abandoned",
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

    async def get_current_session_info(self) -> dict[str, Any] | None:
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

    def _classify_aggregation_error(self, error: Exception) -> str:
        """
        Classify aggregation errors for better user feedback.

        Returns:
            - 'no_actions_found': No user activity during phase
            - 'llm_clustering_failed': LLM API call failed
            - 'supervisor_validation_failed': Activity validation failed
            - 'database_save_failed': Database operation failed
            - 'unknown_error': Unclassified error
        """
        error_str = str(error).lower()

        if "no actions found" in error_str or "no action" in error_str:
            return "no_actions_found"
        elif "clustering" in error_str or "llm" in error_str or "api" in error_str:
            return "llm_clustering_failed"
        elif "supervisor" in error_str or "validation" in error_str:
            return "supervisor_validation_failed"
        elif "database" in error_str or "sql" in error_str:
            return "database_save_failed"
        else:
            return "unknown_error"

    async def _get_phase_time_window(
        self,
        session: dict[str, Any],
        phase_number: int
    ) -> tuple[datetime, datetime]:
        """
        Unified phase time window calculation logic

        IMPORTANT: Uses user-configured durations from session record, NOT hardcoded defaults.

        Priority:
        1. Use actual times from work_phases table (if phase completed)
        2. Calculate from session start + user-configured durations (fallback)

        Args:
            session: Session record dict from database
            phase_number: Phase number (1-based)

        Returns:
            Tuple of (phase_start_time, phase_end_time)
        """
        try:
            # Try to get actual phase record from database (most accurate)
            phase_record = await self.db.work_phases.get_by_session_and_phase(
                session['id'], phase_number
            )

            if phase_record and phase_record.get('phase_start_time'):
                # Use actual recorded times (preferred)
                start_time = datetime.fromisoformat(phase_record['phase_start_time'])
                end_time_str = phase_record.get('phase_end_time')
                end_time = datetime.fromisoformat(end_time_str) if end_time_str else datetime.now()

                logger.debug(
                    f"Using actual phase times from DB: session={session['id']}, "
                    f"phase={phase_number}, start={start_time.isoformat()}, end={end_time.isoformat()}"
                )

                return (start_time, end_time)

        except Exception as e:
            logger.warning(f"Failed to query phase record from DB: {e}")

        # Fallback: Calculate from session start + user-configured durations
        # ⚠️ CRITICAL: Use user-configured durations, NOT hardcoded values
        session_start = datetime.fromisoformat(session['start_time'])
        work_duration = session.get('work_duration_minutes', 25)  # User-configured
        break_duration = session.get('break_duration_minutes', 5)  # User-configured

        # Calculate offset for this phase
        # Phase 1: offset = 0
        # Phase 2: offset = work_duration + break_duration
        # Phase 3: offset = 2 * (work_duration + break_duration)
        offset_minutes = (phase_number - 1) * (work_duration + break_duration)

        start_time = session_start + timedelta(minutes=offset_minutes)
        end_time = start_time + timedelta(minutes=work_duration)

        logger.debug(
            f"Calculated phase times: session={session['id']}, phase={phase_number}, "
            f"work_duration={work_duration}min, break_duration={break_duration}min, "
            f"start={start_time.isoformat()}, end={end_time.isoformat()}"
        )

        return (start_time, end_time)

    async def _aggregate_work_phase_activities(
        self,
        session_id: str,
        work_phase: int,
        phase_start_time: datetime,
        phase_end_time: datetime,
        phase_id: str | None = None,
    ) -> None:
        """
        Aggregate actions into activities for a work phase WITH SIMPLIFIED RETRY.

        Retry Strategy:
        - Attempt 1: Immediate
        - Attempt 2: After 10 seconds
        - After 2 attempts: Mark as 'failed' (user can manually retry)

        Args:
            session_id: Session ID
            work_phase: Phase number (1-4)
            phase_start_time: Phase start time
            phase_end_time: Phase end time
            phase_id: Existing phase record ID (optional)
        """
        try:
            # Get or create phase record
            if not phase_id:
                existing_phase = await self.db.work_phases.get_by_session_and_phase(
                    session_id, work_phase
                )
                if existing_phase:
                    phase_id = existing_phase["id"]
                else:
                    phase_id = await self.db.work_phases.create(
                        session_id=session_id,
                        phase_number=work_phase,
                        phase_start_time=phase_start_time.isoformat(),
                        phase_end_time=phase_end_time.isoformat(),
                        status="pending",
                    )

            # SIMPLIFIED RETRY LOOP: Only 1 retry
            for attempt in range(_Constants.MAX_RETRIES + 1):
                try:
                    # Update status to processing
                    await self.db.work_phases.update_status(
                        phase_id, "processing", None, attempt
                    )

                    logger.info(
                        f"Processing work phase: session={session_id}, "
                        f"phase={work_phase}, attempt={attempt + 1}/{_Constants.MAX_RETRIES + 1}"
                    )

                    # Get SessionAgent from coordinator
                    session_agent = self.coordinator.session_agent
                    if not session_agent:
                        raise ValueError("SessionAgent not available")

                    # Delegate to SessionAgent for actual aggregation
                    activities = await session_agent.aggregate_work_phase(
                        session_id=session_id,
                        work_phase=work_phase,
                        phase_start_time=phase_start_time,
                        phase_end_time=phase_end_time,
                    )

                    # Validate result
                    if not activities:
                        raise ValueError("No actions found for work phase")

                    # SUCCESS - Mark completed
                    await self.db.work_phases.mark_completed(phase_id, len(activities))

                    logger.info(
                        f"✓ Work phase aggregation completed: "
                        f"session={session_id}, phase={work_phase}, "
                        f"activities={len(activities)}"
                    )

                    # Emit success event
                    emit_pomodoro_work_phase_completed(session_id, work_phase, len(activities))

                    return  # Exit retry loop on success

                except Exception as e:
                    # Classify error for better reporting
                    error_type = self._classify_aggregation_error(e)
                    error_message = f"{error_type}: {str(e)}"

                    logger.warning(
                        f"Work phase aggregation attempt {attempt + 1} failed: "
                        f"{error_message}"
                    )

                    if attempt < _Constants.MAX_RETRIES:
                        # Schedule retry after 10 seconds
                        new_retry_count = await self.db.work_phases.increment_retry_count(
                            phase_id
                        )

                        await self.db.work_phases.update_status(
                            phase_id, "pending", error_message, new_retry_count
                        )

                        logger.info(
                            f"Retrying work phase in {_Constants.RETRY_DELAY_SECONDS}s "
                            f"(retry {new_retry_count}/{_Constants.MAX_RETRIES})"
                        )

                        await asyncio.sleep(_Constants.RETRY_DELAY_SECONDS)
                    else:
                        # All retries exhausted - mark as failed
                        # User can manually retry via API
                        await self.db.work_phases.update_status(
                            phase_id, "failed", error_message, _Constants.MAX_RETRIES
                        )

                        logger.error(
                            f"✗ Work phase aggregation failed after {_Constants.MAX_RETRIES + 1} attempts: "
                            f"session={session_id}, phase={work_phase}, error={error_message}"
                        )

                        # Emit failure event
                        emit_pomodoro_work_phase_failed(session_id, work_phase, error_message)

                        return  # Don't raise - allow other phases to continue

        except Exception as e:
            # Outer exception handler (should rarely trigger)
            logger.error(
                f"Unexpected error in work phase aggregation: {e}", exc_info=True
            )

    def get_current_session_id(self) -> str | None:
        """
        Get current active Pomodoro session ID

        Returns:
            Session ID if a Pomodoro session is active, None otherwise
        """
        if self.is_active and self.current_session:
            return self.current_session.id
        return None

    async def force_settlement(self, session_id: str) -> dict[str, Any]:
        """
        Force settlement of all pending records for phase completion

        This method ensures no data loss by:
        1. Flushing ImageConsumer buffered screenshots
        2. Collecting all unprocessed records from storage
        3. Immediately processing them through the pipeline

        Called during phase transitions to guarantee all captured actions
        are processed into events before the phase ends.

        Args:
            session_id: Pomodoro session ID

        Returns:
            Dict with settlement results including counts of processed records
        """
        logger.info(f"Starting force settlement for session: {session_id}")

        all_records = []
        records_count = {
            "image_consumer": 0,
            "storage": 0,
            "event_buffer": 0,
            "total": 0
        }

        try:
            # Step 1: Flush ImageConsumer buffered screenshots
            perception_manager = self.coordinator.perception_manager
            if perception_manager and perception_manager.image_consumer:
                logger.debug("Flushing ImageConsumer buffer...")
                buffered_records = perception_manager.image_consumer.flush()
                if buffered_records:
                    all_records.extend(buffered_records)
                    records_count["image_consumer"] = len(buffered_records)
                    logger.info(f"Flushed {len(buffered_records)} records from ImageConsumer")

            # Step 2: Get all records from SlidingWindowStorage
            if perception_manager and perception_manager.storage:
                logger.debug("Collecting records from SlidingWindowStorage...")
                storage_records = perception_manager.storage.get_records()
                if storage_records:
                    all_records.extend(storage_records)
                    records_count["storage"] = len(storage_records)
                    logger.info(f"Collected {len(storage_records)} records from SlidingWindowStorage")

            # Step 3: Get all events from EventBuffer
            if perception_manager and perception_manager.event_buffer:
                logger.debug("Collecting events from EventBuffer...")
                event_records = perception_manager.event_buffer.get_all()
                if event_records:
                    all_records.extend(event_records)
                    records_count["event_buffer"] = len(event_records)
                    logger.info(f"Collected {len(event_records)} events from EventBuffer")

            records_count["total"] = len(all_records)

            # Step 4: Sort records by timestamp to ensure correct processing order
            all_records.sort(key=lambda r: r.timestamp)

            # Step 5: Force process all records immediately
            if all_records:
                logger.info(
                    f"Force processing {len(all_records)} total records for phase settlement"
                )
                result = await self.coordinator.force_process_records(all_records)

                events_count = len(result.get("events", []))
                activities_count = len(result.get("activities", []))

                logger.info(
                    f"✓ Force settlement completed: "
                    f"{records_count['total']} records → {events_count} events → {activities_count} activities"
                )

                return {
                    "success": True,
                    "records_processed": records_count,
                    "events_generated": events_count,
                    "activities_generated": activities_count,
                    "result": result
                }
            else:
                logger.info("No pending records to settle")
                return {
                    "success": True,
                    "records_processed": records_count,
                    "events_generated": 0,
                    "activities_generated": 0,
                    "message": "No pending records"
                }

        except Exception as e:
            logger.error(f"Force settlement failed for session {session_id}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "records_processed": records_count
            }
