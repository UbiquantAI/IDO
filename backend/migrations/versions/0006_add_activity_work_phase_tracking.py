"""
Migration 0006: Add work phase tracking and focus score to activities

Adds columns to activities table for better Pomodoro session tracking:
- pomodoro_work_phase: Track which work round (1-4) generated the activity
- focus_score: Pre-calculated focus metric (0.0-1.0) for each activity

Also creates index for efficient querying by session and work phase
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0006"
    description = "Add work phase tracking and focus score to activities"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add work phase and focus score columns to activities table"""

        # Column additions
        columns_to_add = [
            (
                "activities",
                "pomodoro_work_phase",
                "ALTER TABLE activities ADD COLUMN pomodoro_work_phase INTEGER",
            ),
            (
                "activities",
                "focus_score",
                "ALTER TABLE activities ADD COLUMN focus_score REAL DEFAULT 0.5",
            ),
        ]

        for table, column, sql in columns_to_add:
            try:
                cursor.execute(sql)
            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                if "duplicate column" in error_msg or "already exists" in error_msg:
                    # Column already exists, skip
                    pass
                else:
                    raise

        # Index creation for efficient querying
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_activities_pomodoro_work_phase
        ON activities(pomodoro_session_id, pomodoro_work_phase)
        """
        try:
            cursor.execute(index_sql)
        except Exception:
            # Index creation failures are usually safe to ignore
            # (index might already exist)
            pass

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported (SQLite doesn't support DROP COLUMN easily)

        To rollback, you would need to:
        1. Create new table without the columns
        2. Copy data
        3. Drop old table
        4. Rename new table
        """
        pass
