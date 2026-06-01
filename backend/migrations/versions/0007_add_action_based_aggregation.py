"""
Migration 0007: Add action-based aggregation support to activities

Adds columns to activities table to support direct action→activity aggregation:
- source_action_ids: JSON array of action IDs (alternative to source_event_ids)
- aggregation_mode: Flag to indicate 'event_based' or 'action_based' aggregation

This migration enables the unified action-based architecture where both Normal Mode
and Pomodoro Mode can aggregate actions directly into activities, bypassing the
Events layer for better temporal continuity.
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0007"
    description = "Add action-based aggregation support to activities"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add action-based aggregation columns to activities table"""

        # Column additions
        columns_to_add = [
            (
                "activities",
                "source_action_ids",
                "ALTER TABLE activities ADD COLUMN source_action_ids TEXT",
            ),
            (
                "activities",
                "aggregation_mode",
                "ALTER TABLE activities ADD COLUMN aggregation_mode TEXT DEFAULT 'action_based'",
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

        # Set existing activities to event_based mode (they have source_event_ids)
        update_sql = """
        UPDATE activities
        SET aggregation_mode = 'event_based'
        WHERE aggregation_mode IS NULL AND source_event_ids IS NOT NULL
        """
        try:
            cursor.execute(update_sql)
        except Exception:
            # If update fails, it's not critical - new activities will default to action_based
            pass

        # Add index for aggregation_mode for efficient querying
        index_sql = """
        CREATE INDEX IF NOT EXISTS idx_activities_aggregation_mode
        ON activities(aggregation_mode)
        """
        try:
            cursor.execute(index_sql)
        except Exception:
            # Index creation failures are usually safe to ignore
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
