"""
Migration 0004: Add Pomodoro-TODO association and Activity ratings

Changes:
1. Add associated_todo_id column to pomodoro_sessions table
2. Create activity_ratings table for multi-dimensional activity ratings
3. Add indexes for efficient querying
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0004"
    description = "Add Pomodoro-TODO association and Activity ratings"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add Pomodoro-TODO association and activity ratings tables"""

        # 1. Add associated_todo_id column to pomodoro_sessions
        try:
            cursor.execute(
                """
                ALTER TABLE pomodoro_sessions
                ADD COLUMN associated_todo_id TEXT
                """
            )
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "duplicate column" in error_msg or "already exists" in error_msg:
                # Column already exists, skip
                pass
            else:
                raise

        # 2. Create index for associated_todo_id
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_todo
                ON pomodoro_sessions(associated_todo_id)
                """
            )
        except Exception:
            # Index creation failures are usually safe to ignore
            pass

        # 3. Create activity_ratings table
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_ratings (
                    id TEXT PRIMARY KEY,
                    activity_id TEXT NOT NULL,
                    dimension TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                    note TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
                    UNIQUE(activity_id, dimension)
                )
                """
            )
        except Exception as e:
            # Table might already exist
            pass

        # 4. Create indexes for activity_ratings
        indexes_to_create = [
            (
                "idx_activity_ratings_activity",
                """
                CREATE INDEX IF NOT EXISTS idx_activity_ratings_activity
                ON activity_ratings(activity_id)
                """
            ),
            (
                "idx_activity_ratings_dimension",
                """
                CREATE INDEX IF NOT EXISTS idx_activity_ratings_dimension
                ON activity_ratings(dimension)
                """
            ),
        ]

        for index_name, sql in indexes_to_create:
            try:
                cursor.execute(sql)
            except Exception:
                # Index creation failures are usually safe to ignore
                pass

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported (SQLite doesn't support DROP COLUMN easily)

        To rollback, you would need to:
        1. Drop activity_ratings table
        2. Create new pomodoro_sessions table without associated_todo_id
        3. Copy data
        4. Drop old pomodoro_sessions table
        5. Rename new table
        """
        pass
