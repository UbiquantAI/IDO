"""
Todos Repository - Handles all todo-related database operations
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.logger import get_logger

from .base import BaseRepository

logger = get_logger(__name__)

# Default expiration for AI-generated todos (3 days)
DEFAULT_TODO_EXPIRATION_DAYS = 3


class TodosRepository(BaseRepository):
    """Repository for managing todos in the database"""

    def __init__(self, db_path: Path):
        super().__init__(db_path)

    async def save(
        self,
        todo_id: str,
        title: str,
        description: str,
        keywords: List[str],
        *,
        completed: bool = False,
        scheduled_date: Optional[str] = None,
        scheduled_time: Optional[str] = None,
        scheduled_end_time: Optional[str] = None,
        recurrence_rule: Optional[Dict[str, Any]] = None,
        created_at: Optional[str] = None,
        expires_at: Optional[str] = None,
        source_type: str = "ai",
    ) -> None:
        """Save or update a todo

        Args:
            todo_id: Unique todo identifier
            title: Todo title
            description: Todo description
            keywords: List of keywords/tags
            completed: Whether todo is completed
            scheduled_date: Optional scheduled date (YYYY-MM-DD)
            scheduled_time: Optional scheduled time (HH:MM)
            scheduled_end_time: Optional scheduled end time (HH:MM)
            recurrence_rule: Optional recurrence configuration
            created_at: Custom creation timestamp (ISO format)
            expires_at: Custom expiration timestamp (ISO format), auto-calculated for AI todos if not provided
            source_type: 'ai' or 'manual' - defaults to 'ai'
        """
        try:
            created = created_at or datetime.now().isoformat()

            # Calculate expiration for AI-generated todos if not provided
            calculated_expires_at = expires_at
            if source_type == "ai" and expires_at is None:
                expiration_time = datetime.fromisoformat(created) + timedelta(days=DEFAULT_TODO_EXPIRATION_DAYS)
                calculated_expires_at = expiration_time.isoformat()

            with self._get_conn() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO todos (
                        id, title, description, keywords,
                        created_at, completed, deleted,
                        scheduled_date, scheduled_time, scheduled_end_time, recurrence_rule,
                        expires_at, source_type
                    ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        todo_id,
                        title,
                        description,
                        json.dumps(keywords, ensure_ascii=False),
                        created,
                        int(completed),
                        scheduled_date,
                        scheduled_time,
                        scheduled_end_time,
                        json.dumps(recurrence_rule) if recurrence_rule else None,
                        calculated_expires_at,
                        source_type,
                    ),
                )
                conn.commit()
                logger.debug(f"Saved todo: {todo_id} (source: {source_type}, expires: {calculated_expires_at})")

                # Send event to frontend
                from core.events import emit_todo_created

                emit_todo_created(
                    {
                        "id": todo_id,
                        "title": title,
                        "description": description,
                        "keywords": keywords,
                        "completed": completed,
                        "scheduled_date": scheduled_date,
                        "scheduled_time": scheduled_time,
                        "scheduled_end_time": scheduled_end_time,
                        "recurrence_rule": recurrence_rule,
                        "created_at": created,
                        "expires_at": calculated_expires_at,
                        "source_type": source_type,
                        "type": "original",
                    }
                )
        except Exception as e:
            logger.error(f"Failed to save todo {todo_id}: {e}", exc_info=True)
            raise


    async def get_by_id(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single todo by ID

        Args:
            todo_id: Todo ID

        Returns:
            Todo dict or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, title, description, keywords,
                           created_at, completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule, expires_at, source_type
                    FROM todos
                    WHERE id = ?
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    return {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "created_at": row["created_at"],
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "scheduled_date": row["scheduled_date"],
                        "scheduled_time": row["scheduled_time"],
                        "scheduled_end_time": row["scheduled_end_time"],
                        "recurrence_rule": json.loads(row["recurrence_rule"])
                        if row["recurrence_rule"]
                        else None,
                        "expires_at": row["expires_at"],
                        "source_type": row["source_type"] or "ai",
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to get todo by ID {todo_id}: {e}", exc_info=True)
            return None

    async def get_list(
        self, include_completed: bool = False, include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get todo list (from todos table)

        Args:
            include_completed: Whether to include completed todos
            include_expired: Whether to include expired AI todos (default False)

        Returns:
            List of todo dictionaries
        """
        try:
            now_iso = datetime.now().isoformat()

            if include_completed:
                if include_expired:
                    query = """
                        SELECT id, title, description, keywords,
                               created_at, completed, deleted, scheduled_date, scheduled_time,
                               scheduled_end_time, recurrence_rule, expires_at, source_type
                        FROM todos
                        WHERE deleted = 0
                        ORDER BY completed ASC, created_at DESC
                    """
                else:
                    query = """
                        SELECT id, title, description, keywords,
                               created_at, completed, deleted, scheduled_date, scheduled_time,
                               scheduled_end_time, recurrence_rule, expires_at, source_type
                        FROM todos
                        WHERE deleted = 0
                          AND (source_type = 'manual' OR expires_at IS NULL OR expires_at > ?)
                        ORDER BY completed ASC, created_at DESC
                    """
            else:
                if include_expired:
                    query = """
                        SELECT id, title, description, keywords,
                               created_at, completed, deleted, scheduled_date, scheduled_time,
                               scheduled_end_time, recurrence_rule, expires_at, source_type
                        FROM todos
                        WHERE deleted = 0 AND completed = 0
                        ORDER BY created_at DESC
                    """
                else:
                    query = """
                        SELECT id, title, description, keywords,
                               created_at, completed, deleted, scheduled_date, scheduled_time,
                               scheduled_end_time, recurrence_rule, expires_at, source_type
                        FROM todos
                        WHERE deleted = 0 AND completed = 0
                          AND (source_type = 'manual' OR expires_at IS NULL OR expires_at > ?)
                        ORDER BY created_at DESC
                    """

            with self._get_conn() as conn:
                if include_completed and include_expired:
                    cursor = conn.execute(query)
                else:
                    cursor = conn.execute(query, (now_iso,))
                rows = cursor.fetchall()

            todo_list: List[Dict[str, Any]] = []
            for row in rows:
                todo_list.append(
                    {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "created_at": row["created_at"],
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "scheduled_date": row["scheduled_date"],
                        "scheduled_time": row["scheduled_time"],
                        "scheduled_end_time": row["scheduled_end_time"],
                        "recurrence_rule": json.loads(row["recurrence_rule"])
                        if row["recurrence_rule"]
                        else None,
                        "expires_at": row["expires_at"],
                        "source_type": row["source_type"] or "ai",
                    }
                )

            return todo_list

        except Exception as e:
            logger.error(f"Failed to get todo list: {e}", exc_info=True)
            return []

    async def schedule(
        self,
        todo_id: str,
        scheduled_date: str,
        scheduled_time: Optional[str] = None,
        scheduled_end_time: Optional[str] = None,
        recurrence_rule: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Schedule todo to a specific date and optional time window

        Scheduling a todo clears its expiration time, as the todo is now in
        an active/scheduled state and should not expire.

        Args:
            todo_id: Todo ID
            scheduled_date: Scheduled date in YYYY-MM-DD format
            scheduled_time: Optional scheduled time in HH:MM format
            scheduled_end_time: Optional scheduled end time in HH:MM format
            recurrence_rule: Optional recurrence configuration dict

        Returns:
            Updated todo dict or None if not found
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                recurrence_json = json.dumps(recurrence_rule) if recurrence_rule else None

                # Clear expires_at when scheduling (todo is now active)
                cursor.execute(
                    """
                    UPDATE todos
                    SET scheduled_date = ?, scheduled_time = ?,
                        scheduled_end_time = ?, recurrence_rule = ?, expires_at = NULL
                    WHERE id = ? AND deleted = 0
                    """,
                    (
                        scheduled_date,
                        scheduled_time,
                        scheduled_end_time,
                        recurrence_json,
                        todo_id,
                    ),
                )
                conn.commit()

                cursor.execute(
                    """
                    SELECT id, title, description, keywords,
                           created_at, completed, deleted, scheduled_date, scheduled_time,
                           scheduled_end_time, recurrence_rule, expires_at, source_type
                    FROM todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    updated_todo = {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "created_at": row["created_at"],
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "scheduled_date": row["scheduled_date"],
                        "scheduled_time": row["scheduled_time"],
                        "scheduled_end_time": row["scheduled_end_time"],
                        "recurrence_rule": json.loads(row["recurrence_rule"])
                        if row["recurrence_rule"]
                        else None,
                        "expires_at": row["expires_at"],
                        "source_type": row["source_type"] or "ai",
                    }

                    # Send event to frontend
                    from core.events import emit_todo_updated

                    emit_todo_updated(updated_todo)

                    return updated_todo

                return None

        except Exception as e:
            logger.error(f"Failed to schedule todo: {e}", exc_info=True)
            return None

    async def unschedule(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Clear scheduling info for a todo

        Note: When unscheduling, we do NOT restore the expiration time.
        The todo remains without expiration since the user has explicitly
        interacted with it (scheduled then unscheduled).
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    UPDATE todos
                    SET scheduled_date = NULL,
                        scheduled_time = NULL,
                        scheduled_end_time = NULL,
                        recurrence_rule = NULL
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                conn.commit()

                cursor.execute(
                    """
                    SELECT id, title, description, keywords,
                           created_at, completed, deleted, scheduled_date,
                           expires_at, source_type
                    FROM todos
                    WHERE id = ? AND deleted = 0
                    """,
                    (todo_id,),
                )
                row = cursor.fetchone()

                if row:
                    updated_todo = {
                        "id": row["id"],
                        "title": row["title"],
                        "description": row["description"],
                        "keywords": json.loads(row["keywords"])
                        if row["keywords"]
                        else [],
                        "created_at": row["created_at"],
                        "completed": bool(row["completed"]),
                        "deleted": bool(row["deleted"]),
                        "scheduled_date": row["scheduled_date"],
                        "expires_at": row["expires_at"],
                        "source_type": row["source_type"] or "ai",
                    }

                    # Send event to frontend
                    from core.events import emit_todo_updated

                    emit_todo_updated(updated_todo)

                    return updated_todo

                return None

        except Exception as e:
            logger.error(f"Failed to unschedule todo: {e}", exc_info=True)
            return None

    async def complete(self, todo_id: str) -> None:
        """Mark a todo as completed"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE todos SET completed = 1 WHERE id = ?", (todo_id,)
                )
                conn.commit()
                logger.debug(f"Completed todo: {todo_id}")

                # Send event to frontend
                from core.events import emit_todo_updated

                emit_todo_updated({"id": todo_id, "completed": True})
        except Exception as e:
            logger.error(f"Failed to complete todo {todo_id}: {e}", exc_info=True)
            raise

    async def delete(self, todo_id: str) -> None:
        """Soft delete a todo"""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE todos SET deleted = 1 WHERE id = ?", (todo_id,)
                )
                conn.commit()
                logger.debug(f"Deleted todo: {todo_id}")

                # Send event to frontend
                from core.events import emit_todo_deleted

                emit_todo_deleted(todo_id)
        except Exception as e:
            logger.error(f"Failed to delete todo {todo_id}: {e}", exc_info=True)
            raise

    async def delete_batch(self, todo_ids: List[str]) -> int:
        """Soft delete multiple todos"""
        if not todo_ids:
            return 0

        try:
            placeholders = ",".join("?" for _ in todo_ids)
            with self._get_conn() as conn:
                cursor = conn.execute(
                    f"""
                    UPDATE todos
                    SET deleted = 1
                    WHERE deleted = 0 AND id IN ({placeholders})
                    """,
                    todo_ids,
                )
                conn.commit()
                return cursor.rowcount

        except Exception as e:
            logger.error(f"Failed to batch delete todos: {e}", exc_info=True)
            return 0

    async def delete_by_date_range(self, start_iso: str, end_iso: str) -> int:
        """Soft delete todos in a time window"""
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE todos
                    SET deleted = 1
                    WHERE deleted = 0
                      AND created_at >= ?
                      AND created_at <= ?
                    """,
                    (start_iso, end_iso),
                )
                deleted_count = cursor.rowcount
                conn.commit()

            return deleted_count

        except Exception as e:
            logger.error(
                f"Failed to delete todos between {start_iso} and {end_iso}: {e}",
                exc_info=True,
            )
            return 0

    async def delete_expired(self) -> int:
        """
        Soft delete expired AI-generated todos

        Removes todos that:
        - Are AI-generated (source_type = 'ai')
        - Have an expires_at timestamp in the past
        - Are not already deleted
        - Are not completed

        Returns:
            Number of todos soft-deleted
        """
        try:
            now_iso = datetime.now().isoformat()

            with self._get_conn() as conn:
                cursor = conn.execute(
                    """
                    UPDATE todos
                    SET deleted = 1
                    WHERE deleted = 0
                      AND completed = 0
                      AND source_type = 'ai'
                      AND expires_at IS NOT NULL
                      AND expires_at < ?
                    """,
                    (now_iso,),
                )
                deleted_count = cursor.rowcount
                conn.commit()

            if deleted_count > 0:
                logger.info(f"Soft-deleted {deleted_count} expired AI todos")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete expired todos: {e}", exc_info=True)
            return 0

    async def delete_soft_deleted_permanent(self) -> int:
        """
        Permanently delete all soft-deleted todos

        This is a cleanup operation that removes todos that have been
        soft-deleted (deleted = 1) from the database.

        Returns:
            Number of todos permanently deleted
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM todos WHERE deleted = 1"
                )
                deleted_count = cursor.rowcount
                conn.commit()

            if deleted_count > 0:
                logger.info(f"Permanently deleted {deleted_count} soft-deleted todos")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to permanently delete soft-deleted todos: {e}", exc_info=True)
            return 0
