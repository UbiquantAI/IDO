"""
Tauri event sending manager
Used to send event notifications from backend to frontend
"""

from typing import Any, Dict, List, Optional

from pydantic import RootModel

try:
    from pytauri import AppHandle, Emitter
except ImportError:  # pragma: no cover - May not be available in non-Tauri environments (like offline scripts, tests)
    AppHandle = Any  # type: ignore[assignment]
    Emitter = None  # type: ignore[assignment]
from core._event_state import event_state
from core.logger import get_logger

logger = get_logger(__name__)


class _RawEventPayload(RootModel[Dict[str, Any]]):
    """Wraps event payload for JSON serialization through PyTauri."""


def register_emit_handler(app_handle: AppHandle):
    """Register Tauri AppHandle for sending events through PyTauri Emitter."""
    if Emitter is None:
        logger.warning(
            "PyTauri not installed, event notification functionality unavailable"
        )
        return

    event_state.app_handle = app_handle
    logger.debug("Registered Tauri AppHandle for event sending")


def _emit(event_name: str, payload: Dict[str, Any]) -> bool:
    """Send events to frontend through PyTauri."""
    if Emitter is None:
        logger.debug(
            f"[events] PyTauri Emitter unavailable, skipping event sending: {event_name}"
        )
        return False

    if event_state.app_handle is None:
        logger.warning(
            f"[events] AppHandle not registered, cannot send event: {event_name}"
        )
        return False

    try:
        Emitter.emit(event_state.app_handle, event_name, _RawEventPayload(payload))
        return True
    except Exception as exc:  # pragma: no cover - runtime exception logging
        logger.error(f"❌ [events] Event sending failed: {event_name} : {exc}", exc_info=True)
        return False


def emit_activity_created(activity_data: Dict[str, Any]) -> bool:
    """
    Send "activity created" event to frontend

    Args:
        activity_data: Activity data dictionary, containing:
            - id: Activity ID
            - description: Activity description
            - startTime: Start time
            - endTime: End time
            - version: Version number
            - createdAt: Creation time

    Returns:
        True if sent successfully, False otherwise
    """
    logger.debug(
        "[emit_activity_created] Attempting to send activity creation event, AppHandle registered: %s",
        event_state.app_handle is not None,
    )

    payload = {
        "type": "activity_created",
        "data": activity_data,
        "timestamp": activity_data.get("createdAt"),
    }

    success = _emit("activity-created", payload)
    if success:
        logger.debug(
            f"✅ [emit_activity_created] Successfully sent activity creation event: {activity_data.get('id')}"
        )
    return success


def emit_activity_updated(activity_data: Dict[str, Any]) -> bool:
    """
    Send "activity updated" event to frontend

    Args:
        activity_data: Updated activity data, should contain:
            - id: Activity ID
            - description: Activity description
            - startTime: Start time
            - endTime: End time
            - version: Version number
            - createdAt: Creation time

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "type": "activity_updated",
        "data": activity_data,
        "timestamp": activity_data.get("createdAt"),
    }

    success = _emit("activity-updated", payload)
    if success:
        logger.debug(f"✅ Activity update event sent: {activity_data.get('id')}")
    return success


def emit_activity_deleted(activity_id: str, timestamp: Optional[str] = None) -> bool:
    """
    Send "activity deleted" event to frontend

    Args:
        activity_id: ID of the deleted activity
        timestamp: Deletion timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "activity_deleted",
        "data": {"id": activity_id, "deletedAt": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }

    success = _emit("activity-deleted", payload)
    if success:
        logger.debug(f"✅ Activity deletion event sent: {activity_id}")
    return success


def emit_event_deleted(event_id: str, timestamp: Optional[str] = None) -> bool:
    """
    Send "event deleted" event to frontend

    Args:
        event_id: ID of the deleted event
        timestamp: Deletion timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "event_deleted",
        "data": {"id": event_id, "deletedAt": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }

    success = _emit("event-deleted", payload)
    if success:
        logger.debug(f"✅ Event deletion event sent: {event_id}")
    return success


def emit_bulk_update_completed(
    updated_count: int, timestamp: Optional[str] = None
) -> bool:
    """
    Send "bulk update completed" event to frontend
    Used to notify frontend that multiple activities have been batch updated

    Args:
        updated_count: Number of updated activities
        timestamp: Operation timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "bulk_update_completed",
        "data": {"updatedCount": updated_count, "timestamp": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }

    success = _emit("bulk-update-completed", payload)
    if success:
        logger.debug(
            f"✅ Bulk update completion event sent: {updated_count} activities"
        )
    return success


def emit_monitors_changed(
    monitors: List[Dict[str, Any]], timestamp: Optional[str] = None
) -> bool:
    """
    Send \"monitors changed\" event to frontend when connected displays change.
    Also notifies the perception manager to update monitor bounds.
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "monitors_changed",
        "data": {"monitors": monitors, "count": len(monitors)},
        "timestamp": resolved_timestamp,
    }
    success = _emit("monitors-changed", payload)
    if success:
        logger.debug("✅ Monitors changed event sent")

    # Notify perception manager to update monitor tracker bounds
    try:
        from core.coordinator import get_coordinator
        coordinator = get_coordinator()
        if coordinator and coordinator.perception_manager:
            coordinator.perception_manager.handle_monitors_changed()
            logger.debug("✓ Perception manager notified of monitor changes")
    except Exception as e:
        logger.error(f"Failed to notify perception manager of monitor changes: {e}")

    return success


def emit_agent_task_update(
    task_id: str,
    status: str,
    progress: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send "Agent task update" event to frontend

    Args:
        task_id: Task ID
        status: Task status (todo/processing/done/failed)
        progress: Task progress (optional)
        result: Task result (optional)
        error: Error information (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "taskId": task_id,
        "status": status,
    }

    if progress is not None:
        payload["progress"] = progress
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error

    success = _emit("agent-task-update", payload)
    if success:
        logger.debug(f"✅ Agent task update event sent: {task_id} -> {status}")
    return success


def emit_chat_message_chunk(
    conversation_id: str,
    chunk: str,
    done: bool = False,
    message_id: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send "chat message chunk" event to frontend (for streaming output)

    Args:
        conversation_id: Conversation ID
        chunk: Text chunk content
        done: Whether completed (True indicates streaming output ended)
        message_id: Message ID (optional, provided when completed)

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "conversationId": conversation_id,
        "chunk": chunk,
        "done": done,
    }

    if message_id is not None:
        payload["messageId"] = message_id

    success = _emit("chat-message-chunk", payload)
    if success and done:
        logger.debug(f"✅ Chat message completion event sent: {conversation_id}")
    return success


def emit_activity_merged(
    merged_activity_id: str,
    original_activity_ids: List[str],
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send "activity merged" event to frontend

    Args:
        merged_activity_id: ID of the newly created merged activity
        original_activity_ids: IDs of the original activities that were merged
        timestamp: Merge timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "activity_merged",
        "data": {
            "merged_activity_id": merged_activity_id,
            "original_activity_ids": original_activity_ids,
        },
        "timestamp": resolved_timestamp,
    }

    success = _emit("activity-merged", payload)
    if success:
        logger.debug(
            f"✅ Activity merge event sent: {len(original_activity_ids)} -> {merged_activity_id}"
        )
    return success


def emit_activity_split(
    original_activity_id: str,
    new_activity_ids: List[str],
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send "activity split" event to frontend

    Args:
        original_activity_id: ID of the original activity that was split
        new_activity_ids: IDs of the new activities created from split
        timestamp: Split timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "activity_split",
        "data": {
            "original_activity_id": original_activity_id,
            "new_activity_ids": new_activity_ids,
        },
        "timestamp": resolved_timestamp,
    }

    success = _emit("activity-split", payload)
    if success:
        logger.debug(
            f"✅ Activity split event sent: {original_activity_id} -> {len(new_activity_ids)}"
        )
    return success


def emit_knowledge_created(knowledge_data: Dict[str, Any]) -> bool:
    """
    Send "knowledge created" event to frontend

    Args:
        knowledge_data: Knowledge data dictionary, containing:
            - id: Knowledge ID
            - title: Knowledge title
            - description: Knowledge description
            - keywords: Keywords list
            - created_at: Creation time
            - source_action_id: Source action ID (optional)
            - type: Type ("original" or "combined")

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    payload = {
        "type": "knowledge_created",
        "data": knowledge_data,
        "timestamp": knowledge_data.get("created_at") or datetime.now().isoformat(),
    }
    success = _emit("knowledge-created", payload)
    if success:
        logger.debug(f"✅ Knowledge creation event sent: {knowledge_data.get('id')}")
    return success


def emit_knowledge_updated(knowledge_data: Dict[str, Any]) -> bool:
    """
    Send "knowledge updated" event to frontend

    Args:
        knowledge_data: Updated knowledge data, should contain:
            - id: Knowledge ID
            - title: Knowledge title
            - description: Knowledge description
            - keywords: Keywords list
            - created_at: Creation time
            - merged_from_ids: Merged from IDs (optional)
            - type: Type ("original" or "combined")

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    payload = {
        "type": "knowledge_updated",
        "data": knowledge_data,
        "timestamp": knowledge_data.get("created_at") or datetime.now().isoformat(),
    }
    success = _emit("knowledge-updated", payload)
    if success:
        logger.debug(f"✅ Knowledge update event sent: {knowledge_data.get('id')}")
    return success


def emit_knowledge_deleted(knowledge_id: str, timestamp: Optional[str] = None) -> bool:
    """
    Send "knowledge deleted" event to frontend

    Args:
        knowledge_id: ID of the deleted knowledge
        timestamp: Deletion timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "knowledge_deleted",
        "data": {"id": knowledge_id, "deletedAt": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }
    success = _emit("knowledge-deleted", payload)
    if success:
        logger.debug(f"✅ Knowledge deletion event sent: {knowledge_id}")
    return success


def emit_todo_created(todo_data: Dict[str, Any]) -> bool:
    """
    Send "todo created" event to frontend

    Args:
        todo_data: TODO data dictionary, containing:
            - id: TODO ID
            - title: TODO title
            - description: TODO description
            - keywords: Keywords list
            - completed: Completion status
            - scheduled_date: Scheduled date (optional)
            - scheduled_time: Scheduled time (optional)
            - scheduled_end_time: Scheduled end time (optional)
            - recurrence_rule: Recurrence rule (optional)
            - created_at: Creation time
            - type: Type ("original" or "combined")

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    payload = {
        "type": "todo_created",
        "data": todo_data,
        "timestamp": todo_data.get("created_at") or datetime.now().isoformat(),
    }
    success = _emit("todo-created", payload)
    if success:
        logger.debug(f"✅ TODO creation event sent: {todo_data.get('id')}")
    return success


def emit_todo_updated(todo_data: Dict[str, Any]) -> bool:
    """
    Send "todo updated" event to frontend

    Args:
        todo_data: Updated TODO data, should contain:
            - id: TODO ID
            - title: TODO title
            - description: TODO description
            - keywords: Keywords list
            - completed: Completion status
            - scheduled_date: Scheduled date (optional)
            - scheduled_time: Scheduled time (optional)
            - scheduled_end_time: Scheduled end time (optional)
            - recurrence_rule: Recurrence rule (optional)
            - created_at: Creation time
            - merged_from_ids: Merged from IDs (optional)
            - type: Type ("original" or "combined")

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    payload = {
        "type": "todo_updated",
        "data": todo_data,
        "timestamp": todo_data.get("created_at") or datetime.now().isoformat(),
    }
    success = _emit("todo-updated", payload)
    if success:
        logger.debug(f"✅ TODO update event sent: {todo_data.get('id')}")
    return success


def emit_todo_deleted(todo_id: str, timestamp: Optional[str] = None) -> bool:
    """
    Send "todo deleted" event to frontend

    Args:
        todo_id: ID of the deleted TODO
        timestamp: Deletion timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "todo_deleted",
        "data": {"id": todo_id, "deletedAt": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }
    success = _emit("todo-deleted", payload)
    if success:
        logger.debug(f"✅ TODO deletion event sent: {todo_id}")
    return success



def emit_pomodoro_processing_progress(
    session_id: str, job_id: str, processed: int
) -> bool:
    """
    Send Pomodoro processing progress event to frontend

    Args:
        session_id: Pomodoro session ID
        job_id: Processing job ID
        processed: Number of records processed

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "session_id": session_id,
        "job_id": job_id,
        "processed": processed,
    }

    logger.debug(
        f"[emit_pomodoro_processing_progress] Session: {session_id}, "
        f"Job: {job_id}, Processed: {processed}"
    )
    return _emit("pomodoro-processing-progress", payload)


def emit_pomodoro_processing_complete(
    session_id: str, job_id: str, total_processed: int
) -> bool:
    """
    Send Pomodoro processing completion event to frontend

    Args:
        session_id: Pomodoro session ID
        job_id: Processing job ID
        total_processed: Total number of records processed

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "session_id": session_id,
        "job_id": job_id,
        "total_processed": total_processed,
    }

    logger.debug(
        f"[emit_pomodoro_processing_complete] Session: {session_id}, "
        f"Job: {job_id}, Total: {total_processed}"
    )
    return _emit("pomodoro-processing-complete", payload)


def emit_pomodoro_processing_failed(
    session_id: str, job_id: str, error: str
) -> bool:
    """
    Send Pomodoro processing failure event to frontend

    Args:
        session_id: Pomodoro session ID
        job_id: Processing job ID
        error: Error message

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "session_id": session_id,
        "job_id": job_id,
        "error": error,
    }

    logger.debug(
        f"[emit_pomodoro_processing_failed] Session: {session_id}, "
        f"Job: {job_id}, Error: {error}"
    )
    return _emit("pomodoro-processing-failed", payload)


def emit_pomodoro_phase_switched(
    session_id: str,
    new_phase: str,
    current_round: int,
    total_rounds: int,
    completed_rounds: int,
) -> bool:
    """
    Send Pomodoro phase switch event to frontend

    Emitted when session automatically switches between work/break phases.

    Args:
        session_id: Pomodoro session ID
        new_phase: New phase ('work', 'break', or 'completed')
        current_round: Current round number (1-based)
        total_rounds: Total number of rounds
        completed_rounds: Number of completed work rounds

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "session_id": session_id,
        "new_phase": new_phase,
        "current_round": current_round,
        "total_rounds": total_rounds,
        "completed_rounds": completed_rounds,
    }

    logger.debug(
        f"[emit_pomodoro_phase_switched] Session: {session_id}, "
        f"Phase: {new_phase}, Round: {current_round}/{total_rounds}, "
        f"Completed: {completed_rounds}"
    )
    return _emit("pomodoro-phase-switched", payload)


def emit_pomodoro_work_phase_completed(
    session_id: str,
    work_phase: int,
    activity_count: int,
) -> bool:
    """
    Send Pomodoro work phase completed event to frontend

    Emitted when a work phase completes and activities have been generated.
    Allows frontend to display notifications and refresh session detail views.

    Args:
        session_id: Pomodoro session ID
        work_phase: Work phase number (1-based)
        activity_count: Number of activities created/updated for this work phase

    Returns:
        True if sent successfully, False otherwise
    """
    payload = {
        "session_id": session_id,
        "work_phase": work_phase,
        "activity_count": activity_count,
    }

    logger.debug(
        f"[emit_pomodoro_work_phase_completed] Session: {session_id}, "
        f"Phase: {work_phase}, Activities: {activity_count}"
    )
    return _emit("pomodoro-work-phase-completed", payload)


def emit_pomodoro_session_deleted(
    session_id: str,
    timestamp: Optional[str] = None,
) -> bool:
    """
    Send Pomodoro session deleted event to frontend

    Emitted when a session is deleted. Frontend should refresh session list
    and clear any selected session state.

    Args:
        session_id: Pomodoro session ID
        timestamp: Deletion timestamp

    Returns:
        True if sent successfully, False otherwise
    """
    from datetime import datetime

    resolved_timestamp = timestamp or datetime.now().isoformat()
    payload = {
        "type": "session_deleted",
        "data": {"id": session_id, "deletedAt": resolved_timestamp},
        "timestamp": resolved_timestamp,
    }

    success = _emit("session-deleted", payload)
    if success:
        logger.debug(f"✅ Pomodoro session deletion event sent: {session_id}")
    return success
