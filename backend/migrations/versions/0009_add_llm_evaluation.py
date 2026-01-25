"""
Migration 0009: Add LLM evaluation fields to pomodoro_sessions

Adds llm_evaluation_result and llm_evaluation_computed_at columns
to support caching LLM focus evaluations
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0009"
    description = "Add LLM evaluation fields to pomodoro_sessions"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add LLM evaluation columns to pomodoro_sessions table"""

        # Add llm_evaluation_result column
        try:
            cursor.execute(
                """
                ALTER TABLE pomodoro_sessions
                ADD COLUMN llm_evaluation_result TEXT
                """
            )
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "duplicate column" in error_msg or "already exists" in error_msg:
                # Column already exists, skip
                pass
            else:
                raise

        # Add llm_evaluation_computed_at column
        try:
            cursor.execute(
                """
                ALTER TABLE pomodoro_sessions
                ADD COLUMN llm_evaluation_computed_at TEXT
                """
            )
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "duplicate column" in error_msg or "already exists" in error_msg:
                # Column already exists, skip
                pass
            else:
                raise

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported (SQLite doesn't support DROP COLUMN in older versions)
        """
        pass
