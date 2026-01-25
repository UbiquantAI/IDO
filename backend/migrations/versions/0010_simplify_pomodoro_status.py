"""
Migration 0010: Simplify Pomodoro status values

Simplifies status and processing_status values by merging similar states:
- status: 'interrupted' and 'too_short' → 'abandoned'
- processing_status: 'skipped' → 'failed'

This reduces state complexity from 10 combinations to 7 combinations.
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0010"
    description = "Simplify Pomodoro status values"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Merge similar status values to simplify state management"""

        # Merge 'interrupted' and 'too_short' into 'abandoned'
        cursor.execute(
            """
            UPDATE pomodoro_sessions
            SET status = 'abandoned'
            WHERE status IN ('interrupted', 'too_short')
            """
        )

        # Merge 'skipped' into 'failed'
        cursor.execute(
            """
            UPDATE pomodoro_sessions
            SET processing_status = 'failed'
            WHERE processing_status = 'skipped'
            """
        )

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported - cannot reliably restore original status values
        """
        pass
