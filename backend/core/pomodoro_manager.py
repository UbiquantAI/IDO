"""
Pomodoro Manager - Manages Pomodoro session lifecycle

Responsibilities:
1. Start/stop Pomodoro sessions
2. Coordinate with PipelineCoordinator (enter/exit Pomodoro mode)
3. Trigger deferred batch processing after session completion
4. Track session metadata and handle orphaned sessions
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from core.db import get_db
from core.logger import get_logger
from core.models import RawRecord, RecordType

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
        # Allow starting if processing has been running for more than 15 minutes (likely stuck)
        processing_sessions = await self.db.pomodoro_sessions.get_by_processing_status(
            "processing", limit=1
        )
        if processing_sessions:
            session = processing_sessions[0]
            processing_started_at = session.get("processing_started_at")

            if processing_started_at:
                try:
                    started_time = datetime.fromisoformat(processing_started_at)
                    elapsed_minutes = (datetime.now() - started_time).total_seconds() / 60

                    if elapsed_minutes < 15:
                        # Still within reasonable time, block new session
                        raise ValueError(
                            "Previous Pomodoro session is still being analyzed. "
                            "Please wait for completion before starting a new session."
                        )
                    else:
                        # Processing stuck for > 15 minutes, force complete it
                        logger.warning(
                            f"Force completing stuck session {session['id']} "
                            f"(processing for {elapsed_minutes:.1f} minutes)"
                        )
                        await self.db.pomodoro_sessions.update(
                            session_id=session["id"],
                            processing_status="failed",
                            processing_error="Processing timeout - forced completion",
                        )
                except Exception as e:
                    logger.error(f"Error checking processing session timestamp: {e}")
                    # If we can't parse timestamp, allow starting new session
            else:
                # No timestamp, likely stuck - force complete it
                logger.warning(f"Force completing session {session['id']} (no timestamp)")
                await self.db.pomodoro_sessions.update(
                    session_id=session["id"],
                    processing_status="failed",
                    processing_error="No processing timestamp - forced completion",
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

                # Trigger aggregation with phase_id
                asyncio.create_task(
                    self._aggregate_work_phase_activities(
                        session_id=session_id,
                        work_phase=current_round,
                        phase_start_time=phase_start_time,
                        phase_end_time=phase_end_time,
                        phase_id=phase_id,
                    )
                )

                # Flush ImageConsumer BEFORE stopping perception
                # This ensures all buffered screenshots from work phase are processed
                perception_manager = self.coordinator.perception_manager
                if perception_manager and perception_manager.image_consumer:
                    remaining = perception_manager.image_consumer.flush()
                    logger.info(
                        f"Flushed {len(remaining)} buffered screenshots on work→break transition "
                        f"(session_id={session_id}, work_phase={current_round})"
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
            # SIMPLIFIED: Treat too-short sessions as 'abandoned'
            if elapsed_duration < 2:
                logger.warning(
                    f"Pomodoro session {session_id} too short ({elapsed_duration:.1f}min), marking as abandoned"
                )
                await self.db.pomodoro_sessions.update(
                    session_id=session_id,
                    end_time=end_time.isoformat(),
                    actual_duration_minutes=int(elapsed_duration),
                    status="abandoned",
                    processing_status="failed",  # No analysis for too-short sessions
                )

                # Exit pomodoro mode
                await self.coordinator.exit_pomodoro_mode()

                self.is_active = False
                self.current_session = None

                return {
                    "session_id": session_id,
                    "processing_job_id": None,
                    "raw_records_count": 0,
                    "message": "Session too short, marked as abandoned",
                }

            # Get session data
            session = await self.db.pomodoro_sessions.get_by_id(session_id)

            # ★ Calculate actual work duration FIRST (before modifying completed_rounds) ★
            # For completed rounds: use full work_duration
            # For current incomplete work phase: use actual elapsed time from phase_start_time to end_time
            if session:
                completed_rounds = session.get("completed_rounds", 0)
                work_duration = session.get("work_duration_minutes", 25)
                current_phase = session.get("current_phase", "work")

                # Calculate time for completed rounds
                actual_work_minutes = completed_rounds * work_duration

                # If ending during work phase, add actual time worked in current phase
                current_phase_minutes = 0
                if current_phase == "work":
                    phase_start_time_str = session.get("phase_start_time")
                    if phase_start_time_str:
                        phase_start_time = datetime.fromisoformat(phase_start_time_str)
                        # Calculate actual time worked in current phase (in minutes)
                        current_phase_minutes = (end_time - phase_start_time).total_seconds() / 60
                        actual_work_minutes += int(current_phase_minutes)

                        logger.info(
                            f"Session duration: elapsed={elapsed_duration:.1f}min, "
                            f"actual_work={actual_work_minutes}min "
                            f"({completed_rounds} completed rounds × {work_duration}min + "
                            f"{int(current_phase_minutes)}min in current phase)"
                        )
                    else:
                        # Fallback: if no phase_start_time, use full work_duration for current phase
                        current_phase_minutes = work_duration
                        actual_work_minutes += work_duration
                        logger.warning(
                            f"No phase_start_time found for current work phase, "
                            f"using full work_duration ({work_duration}min)"
                        )
                else:
                    logger.info(
                        f"Session duration: elapsed={elapsed_duration:.1f}min, "
                        f"actual_work={actual_work_minutes}min (based on {completed_rounds} completed rounds)"
                    )

                # ========== PARALLEL PHASE PROCESSING ==========
                # Identify all work phases that occurred during session
                current_round = session.get("current_round", 1)

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
                # Don't await tasks - let them run in background
                # ========== END PARALLEL PHASE PROCESSING ==========
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

            # IMPORTANT: Flush ImageConsumer BEFORE exiting Pomodoro mode
            # This ensures all buffered screenshots are processed
            perception_manager = self.coordinator.perception_manager
            if perception_manager and perception_manager.image_consumer:
                remaining = perception_manager.image_consumer.flush()
                logger.info(
                    f"Flushed {len(remaining)} buffered screenshots on session end "
                    f"(session_id={session_id})"
                )

            # Exit pomodoro mode (this will also flush in PerceptionManager.clear_pomodoro_session)
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
                    timeout=600  # 10 minutes: 5 min wait + ~5 min LLM evaluation
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

    async def _wait_and_trigger_llm_evaluation(self, session_id: str) -> None:
        """
        Wait for all work phases to complete successfully, then trigger LLM evaluation.

        This ensures AI analysis only runs after all activity data is ready.
        For initial generation, retries are automatic. For subsequent failures,
        users can manually retry.

        Args:
            session_id: Pomodoro session ID
        """
        MAX_WAIT_TIME = 300  # 5 minutes max wait
        POLL_INTERVAL = 3  # Check every 3 seconds

        try:
            logger.info(f"Waiting for all work phases to complete for session {session_id}")

            # Get session info
            session = await self.db.pomodoro_sessions.get_by_id(session_id)
            if not session:
                logger.warning(f"Session {session_id} not found, skipping LLM evaluation wait")
                return

            total_rounds = session.get("total_rounds", 4)
            waited_time = 0

            # Wait for all phases to reach terminal state (completed or failed)
            while waited_time < MAX_WAIT_TIME:
                phases = await self.db.work_phases.get_by_session(session_id)

                # Check if all expected work phases exist and have terminal status
                completed_phases = [p for p in phases if p["status"] == "completed"]
                failed_phases = [p for p in phases if p["status"] == "failed"]
                terminal_phases = completed_phases + failed_phases

                if len(terminal_phases) >= total_rounds:
                    # All phases have reached terminal state
                    logger.info(
                        f"All {total_rounds} work phases reached terminal state: "
                        f"completed={len(completed_phases)}, failed={len(failed_phases)}"
                    )
                    break

                # Still waiting for phases to complete
                logger.debug(
                    f"Waiting for work phases: {len(terminal_phases)}/{total_rounds} complete, "
                    f"waited {waited_time}s"
                )

                await asyncio.sleep(POLL_INTERVAL)
                waited_time += POLL_INTERVAL

            if waited_time >= MAX_WAIT_TIME:
                logger.warning(
                    f"Timeout waiting for work phases to complete ({MAX_WAIT_TIME}s), "
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
        activities: List[Dict[str, Any]],
        session: Dict[str, Any],
        focus_evaluator: Any,
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
        session: Dict[str, Any],
        phase_number: int
    ) -> Tuple[datetime, datetime]:
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
        phase_id: Optional[str] = None,
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
        MAX_RETRIES = 1  # Simplified: only 1 retry
        RETRY_DELAY = 10  # seconds

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
            for attempt in range(MAX_RETRIES + 1):
                try:
                    # Update status to processing
                    await self.db.work_phases.update_status(
                        phase_id, "processing", None, attempt
                    )

                    logger.info(
                        f"Processing work phase: session={session_id}, "
                        f"phase={work_phase}, attempt={attempt + 1}/{MAX_RETRIES + 1}"
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
                    from core.events import emit_pomodoro_work_phase_completed

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

                    if attempt < MAX_RETRIES:
                        # Schedule retry after 10 seconds
                        new_retry_count = await self.db.work_phases.increment_retry_count(
                            phase_id
                        )

                        await self.db.work_phases.update_status(
                            phase_id, "pending", error_message, new_retry_count
                        )

                        logger.info(
                            f"Retrying work phase in {RETRY_DELAY}s "
                            f"(retry {new_retry_count}/{MAX_RETRIES})"
                        )

                        await asyncio.sleep(RETRY_DELAY)
                    else:
                        # All retries exhausted - mark as failed
                        # User can manually retry via API
                        await self.db.work_phases.update_status(
                            phase_id, "failed", error_message, MAX_RETRIES
                        )

                        logger.error(
                            f"✗ Work phase aggregation failed after {MAX_RETRIES + 1} attempts: "
                            f"session={session_id}, phase={work_phase}, error={error_message}"
                        )

                        # Emit failure event
                        from core.events import emit_pomodoro_work_phase_failed
                        emit_pomodoro_work_phase_failed(session_id, work_phase, error_message)

                        return  # Don't raise - allow other phases to continue

        except Exception as e:
            # Outer exception handler (should rarely trigger)
            logger.error(
                f"Unexpected error in work phase aggregation: {e}", exc_info=True
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
