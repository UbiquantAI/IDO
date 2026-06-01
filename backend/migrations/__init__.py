"""
Database migrations module - Version-based migration system

This module provides a versioned migration system that:
1. Tracks applied migrations in schema_migrations table
2. Runs migrations in order by version number
3. Supports both SQL-based and Python-based migrations
"""

from .runner import MigrationRunner

__all__ = ["MigrationRunner"]
