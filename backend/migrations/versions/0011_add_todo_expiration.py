"""
Migration 0011: Add todo expiration and source tracking

Adds expiration and source tracking columns to todos table:
- expires_at: Expiration timestamp for AI-generated todos (default 3 days)
- source_type: 'ai' or 'manual' to track todo origin

This enables automatic cleanup of expired AI-generated todos.
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0011"
    description = "Add todo expiration and source tracking"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add expires_at and source_type columns to todos table"""

        # Add expires_at column (NULL means no expiration)
        cursor.execute(
            """
            ALTER TABLE todos ADD COLUMN expires_at TEXT
            """
        )

        # Add source_type column (default 'ai' for existing records)
        cursor.execute(
            """
            ALTER TABLE todos ADD COLUMN source_type TEXT DEFAULT 'ai'
            """

        )

        # Update existing records to have source_type = 'ai'
        cursor.execute(
            """
            UPDATE todos SET source_type = 'ai' WHERE source_type IS NULL
            """
        )

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported - cannot reliably restore original schema
        """
        pass
