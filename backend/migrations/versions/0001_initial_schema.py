"""
Migration 0001: Initial database schema

Creates all base tables and indexes for the iDO application
"""

import sqlite3

from migrations.base import BaseMigration


class Migration(BaseMigration):
    version = "0001"
    description = "Initial database schema with all base tables"

    def up(self, cursor: sqlite3.Cursor) -> None:
        """Create all initial tables and indexes"""
        from core.sqls import schema

        # Create all tables
        for table_sql in schema.ALL_TABLES:
            cursor.execute(table_sql)

        # Create all indexes
        for index_sql in schema.ALL_INDEXES:
            cursor.execute(index_sql)

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback not supported for initial schema
        Would require dropping all tables
        """
        pass
