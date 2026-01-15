"""
Migration 0005: Add Pomodoro rounds and phase management

Adds support for multi-round Pomodoro sessions with work/break phases:
- work_duration_minutes: Duration of work phase (default 25)
- break_duration_minutes: Duration of break phase (default 5)
- total_rounds: Total number of work rounds to complete (default 4)
- current_round: Current round number (1-based)
- current_phase: Current phase (work/break/completed)
- phase_start_time: When current phase started
- completed_rounds: Number of completed work rounds
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0005"
    description = "Add Pomodoro rounds and phase management"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add Pomodoro rounds-related columns and work phases table"""

        # Create pomodoro_work_phases table
        try:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS pomodoro_work_phases (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    phase_number INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    processing_error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    phase_start_time TEXT NOT NULL,
                    phase_end_time TEXT,
                    activity_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES pomodoro_sessions(id) ON DELETE CASCADE,
                    CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
                    UNIQUE(session_id, phase_number)
                )
                """
            )
        except Exception:
            # Table might already exist
            pass

        # Column additions for round management
        columns_to_add = [
            (
                "pomodoro_sessions",
                "work_duration_minutes",
                "ALTER TABLE pomodoro_sessions ADD COLUMN work_duration_minutes INTEGER DEFAULT 25",
            ),
            (
                "pomodoro_sessions",
                "break_duration_minutes",
                "ALTER TABLE pomodoro_sessions ADD COLUMN break_duration_minutes INTEGER DEFAULT 5",
            ),
            (
                "pomodoro_sessions",
                "total_rounds",
                "ALTER TABLE pomodoro_sessions ADD COLUMN total_rounds INTEGER DEFAULT 4",
            ),
            (
                "pomodoro_sessions",
                "current_round",
                "ALTER TABLE pomodoro_sessions ADD COLUMN current_round INTEGER DEFAULT 1",
            ),
            (
                "pomodoro_sessions",
                "current_phase",
                "ALTER TABLE pomodoro_sessions ADD COLUMN current_phase TEXT DEFAULT 'work'",
            ),
            (
                "pomodoro_sessions",
                "phase_start_time",
                "ALTER TABLE pomodoro_sessions ADD COLUMN phase_start_time TEXT",
            ),
            (
                "pomodoro_sessions",
                "completed_rounds",
                "ALTER TABLE pomodoro_sessions ADD COLUMN completed_rounds INTEGER DEFAULT 0",
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

        # Add index for current_phase for efficient querying
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_pomodoro_sessions_phase
                ON pomodoro_sessions(current_phase)
                """
            )
        except Exception:
            # Index creation failures are usually safe to ignore
            pass

        # Create indexes for pomodoro_work_phases table
        indexes_to_create = [
            """
            CREATE INDEX IF NOT EXISTS idx_work_phases_session
            ON pomodoro_work_phases(session_id, phase_number)
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_work_phases_status
            ON pomodoro_work_phases(status)
            """,
        ]

        for index_sql in indexes_to_create:
            try:
                cursor.execute(index_sql)
            except Exception:
                # Index creation failures are usually safe to ignore
                pass

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported (SQLite doesn't support DROP COLUMN easily)

        To rollback, you would need to:
        1. Create new pomodoro_sessions table without the new columns
        2. Copy data
        3. Drop old table
        4. Rename new table
        """
        pass
