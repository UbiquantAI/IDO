"""
Base migration class

All migrations should inherit from this base class
"""

import sqlite3
from abc import ABC, abstractmethod
from typing import Optional


class BaseMigration(ABC):
    """
    Base class for database migrations

    Each migration must:
    1. Define a unique version string (e.g., "0001", "0002")
    2. Provide a description
    3. Implement the up() method
    4. Optionally implement the down() method for rollbacks
    """

    # Must be overridden in subclass
    version: str = ""
    description: str = ""

    @abstractmethod
    def up(self, cursor: sqlite3.Cursor) -> None:
        """
        Execute migration (upgrade database)

        Args:
            cursor: SQLite cursor for executing SQL commands
        """
        pass

    def down(self, cursor: sqlite3.Cursor) -> None:
        """
        Rollback migration (downgrade database)

        Args:
            cursor: SQLite cursor for executing SQL commands

        Note:
            This is optional. Many migrations cannot be safely rolled back.
            If not implemented, rollback will be skipped with a warning.
        """
        pass

    def __repr__(self) -> str:
        return f"<Migration {self.version}: {self.description}>"
