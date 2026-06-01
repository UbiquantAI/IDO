"""
Migration 0003: Add Pomodoro feature

Adds columns to existing tables for Pomodoro session tracking:
- pomodoro_session_id to raw_records, actions, events, activities
- user_intent and pomodoro_status to activities

Also creates indexes for efficient querying
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0003"
    description = "Add Pomodoro feature columns and indexes"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add Pomodoro-related columns and indexes"""

        # Column additions
        columns_to_add = [
            (
                "raw_records",
                "pomodoro_session_id",
                "ALTER TABLE raw_records ADD COLUMN pomodoro_session_id TEXT",
            ),
            (
                "actions",
                "pomodoro_session_id",
                "ALTER TABLE actions ADD COLUMN pomodoro_session_id TEXT",
            ),
            (
                "events",
                "pomodoro_session_id",
                "ALTER TABLE events ADD COLUMN pomodoro_session_id TEXT",
            ),
            (
                "activities",
                "pomodoro_session_id",
                "ALTER TABLE activities ADD COLUMN pomodoro_session_id TEXT",
            ),
            (
                "activities",
                "user_intent",
                "ALTER TABLE activities ADD COLUMN user_intent TEXT",
            ),
            (
                "activities",
                "pomodoro_status",
                "ALTER TABLE activities ADD COLUMN pomodoro_status TEXT",
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

        # Index creation
        indexes_to_create = [
            (
                "idx_raw_records_pomodoro_session",
                """
                CREATE INDEX IF NOT EXISTS idx_raw_records_pomodoro_session
                ON raw_records(pomodoro_session_id)
                """,
            ),
            (
                "idx_actions_pomodoro_session",
                """
                CREATE INDEX IF NOT EXISTS idx_actions_pomodoro_session
                ON actions(pomodoro_session_id)
                """,
            ),
            (
                "idx_events_pomodoro_session",
                """
                CREATE INDEX IF NOT EXISTS idx_events_pomodoro_session
                ON events(pomodoro_session_id)
                """,
            ),
            (
                "idx_activities_pomodoro_session",
                """
                CREATE INDEX IF NOT EXISTS idx_activities_pomodoro_session
                ON activities(pomodoro_session_id)
                """,
            ),
            (
                "idx_activities_pomodoro_status",
                """
                CREATE INDEX IF NOT EXISTS idx_activities_pomodoro_status
                ON activities(pomodoro_status)
                """,
            ),
        ]

        for index_name, sql in indexes_to_create:
            try:
                cursor.execute(sql)
            except Exception as e:
                # Index creation failures are usually safe to ignore
                # (index might already exist)
                pass

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported (SQLite doesn't support DROP COLUMN easily)

        To rollback, you would need to:
        1. Create new tables without the columns
        2. Copy data
        3. Drop old tables
        4. Rename new tables
        """
        pass
