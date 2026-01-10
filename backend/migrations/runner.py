"""
Migration runner - Manages database schema versioning

Responsibilities:
1. Create schema_migrations table if not exists
2. Discover all migration files
3. Determine which migrations need to run
4. Execute migrations in order
5. Record successful migrations
"""

import importlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Type

from core.logger import get_logger

from .base import BaseMigration

logger = get_logger(__name__)


class MigrationRunner:
    """
    Database migration runner with version tracking

    Usage:
        runner = MigrationRunner(db_path)
        runner.run_migrations()
    """

    SCHEMA_MIGRATIONS_TABLE = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """

    def __init__(self, db_path: Path):
        """
        Initialize migration runner

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.migrations: Dict[str, Type[BaseMigration]] = {}

    def _ensure_schema_migrations_table(self, cursor: sqlite3.Cursor) -> None:
        """
        Create schema_migrations table if it doesn't exist

        Args:
            cursor: Database cursor
        """
        cursor.execute(self.SCHEMA_MIGRATIONS_TABLE)
        logger.debug("✓ schema_migrations table ready")

    def _get_applied_versions(self, cursor: sqlite3.Cursor) -> set:
        """
        Get set of already-applied migration versions

        Args:
            cursor: Database cursor

        Returns:
            Set of version strings
        """
        cursor.execute("SELECT version FROM schema_migrations")
        rows = cursor.fetchall()
        return {row[0] for row in rows}

    def _discover_migrations(self) -> List[Type[BaseMigration]]:
        """
        Discover all migration classes from versions directory

        Returns:
            List of migration classes sorted by version
        """
        migrations_dir = Path(__file__).parent / "versions"

        if not migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {migrations_dir}")
            return []

        discovered = []

        # Import all Python files in versions directory
        for migration_file in sorted(migrations_dir.glob("*.py")):
            if migration_file.name.startswith("_"):
                continue  # Skip __init__.py and other private files

            module_name = f"migrations.versions.{migration_file.stem}"

            try:
                module = importlib.import_module(module_name)

                # Find migration class in module
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check if it's a migration class
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseMigration)
                        and attr is not BaseMigration
                    ):
                        discovered.append(attr)
                        logger.debug(f"Discovered migration: {attr.version} - {attr.description}")

            except Exception as e:
                logger.error(f"Failed to load migration {migration_file}: {e}", exc_info=True)

        # Sort by version
        discovered.sort(key=lambda m: m.version)

        return discovered

    def _record_migration(
        self, cursor: sqlite3.Cursor, migration: BaseMigration
    ) -> None:
        """
        Record successful migration in schema_migrations table

        Args:
            cursor: Database cursor
            migration: Migration instance
        """
        cursor.execute(
            """
            INSERT INTO schema_migrations (version, description, applied_at)
            VALUES (?, ?, ?)
            """,
            (
                migration.version,
                migration.description,
                datetime.now().isoformat(),
            ),
        )
        logger.info(f"✓ Recorded migration: {migration.version}")

    def run_migrations(self) -> int:
        """
        Run all pending migrations

        Returns:
            Number of migrations executed
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Ensure tracking table exists
            self._ensure_schema_migrations_table(cursor)
            conn.commit()

            # Get applied versions
            applied_versions = self._get_applied_versions(cursor)
            logger.debug(f"Applied migrations: {applied_versions}")

            # Discover all migrations
            all_migrations = self._discover_migrations()

            if not all_migrations:
                logger.info("No migrations found")
                conn.close()
                return 0

            # Filter to pending migrations
            pending_migrations = [
                m for m in all_migrations if m.version not in applied_versions
            ]

            if not pending_migrations:
                logger.info("✓ All migrations up to date")
                conn.close()
                return 0

            logger.info(f"Found {len(pending_migrations)} pending migration(s)")

            # Execute each pending migration
            executed_count = 0
            for migration_class in pending_migrations:
                migration = migration_class()

                logger.info(f"Running migration {migration.version}: {migration.description}")

                try:
                    # Execute migration
                    migration.up(cursor)

                    # Record success
                    self._record_migration(cursor, migration)
                    conn.commit()

                    executed_count += 1
                    logger.info(f"✓ Migration {migration.version} completed successfully")

                except Exception as e:
                    logger.error(
                        f"✗ Migration {migration.version} failed: {e}",
                        exc_info=True,
                    )
                    conn.rollback()
                    raise

            conn.close()

            logger.info(f"✓ Successfully executed {executed_count} migration(s)")
            return executed_count

        except Exception as e:
            logger.error(f"Migration runner failed: {e}", exc_info=True)
            raise

    def get_migration_status(self) -> Dict[str, Any]:
        """
        Get current migration status

        Returns:
            Dictionary with migration status information
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Ensure tracking table exists
            self._ensure_schema_migrations_table(cursor)

            # Get applied migrations
            cursor.execute(
                """
                SELECT version, description, applied_at
                FROM schema_migrations
                ORDER BY version
                """
            )
            applied = [dict(row) for row in cursor.fetchall()]

            # Discover all migrations
            all_migrations = self._discover_migrations()

            applied_versions = {m["version"] for m in applied}
            pending = [
                {"version": m.version, "description": m.description}
                for m in all_migrations
                if m.version not in applied_versions
            ]

            conn.close()

            return {
                "applied_count": len(applied),
                "pending_count": len(pending),
                "applied": applied,
                "pending": pending,
            }

        except Exception as e:
            logger.error(f"Failed to get migration status: {e}", exc_info=True)
            raise
