"""
Migration 0002: Add knowledge extraction columns to actions table

Adds columns to support knowledge extraction feature
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0002"
    description = "Add knowledge extraction columns to actions and knowledge tables"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Add columns for knowledge extraction feature"""

        # List of column additions (with error handling for already-exists)
        columns_to_add = [
            (
                "actions",
                "extract_knowledge",
                "ALTER TABLE actions ADD COLUMN extract_knowledge BOOLEAN DEFAULT 0",
            ),
            (
                "actions",
                "knowledge_extracted",
                "ALTER TABLE actions ADD COLUMN knowledge_extracted BOOLEAN DEFAULT 0",
            ),
            (
                "knowledge",
                "source_action_id",
                "ALTER TABLE knowledge ADD COLUMN source_action_id TEXT",
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

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported (SQLite doesn't support DROP COLUMN in older versions)
        """
        pass
