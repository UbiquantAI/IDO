"""
Migration 0008: Add favorite column to knowledge table

Adds favorite column to support favoriting knowledge items
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0008"
    description = "Add favorite column to knowledge table"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add favorite column to knowledge table"""

        # Add favorite column
        try:
            cursor.execute(
                "ALTER TABLE knowledge ADD COLUMN favorite BOOLEAN DEFAULT 0"
            )
        except sqlite3.OperationalError as e:
            error_msg = str(e).lower()
            if "duplicate column" in error_msg or "already exists" in error_msg:
                # Column already exists, skip
                pass
            else:
                raise

        # Create index for favorite column
        try:
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_knowledge_favorite
                ON knowledge(favorite)
                """
            )
        except sqlite3.OperationalError:
            # Index might already exist, ignore
            pass

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported (SQLite doesn't support DROP COLUMN in older versions)
        """
        pass
