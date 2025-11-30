"""
Memory Bank for long-term storage of project patterns.

This module provides persistent storage for learned patterns, project conventions,
and historical analysis data using SQLite.
"""

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from models.data_models import ProjectPattern, PatternType


class MemoryBank:
    """
    Long-term storage for project patterns and conventions.
    
    Uses SQLite for persistent storage with support for:
    - CRUD operations on patterns
    - Similarity-based pattern retrieval
    - Confidence scoring and updates based on feedback
    - Database migrations
    """
    
    def __init__(self, db_path: str = "memory_bank.db"):
        """
        Initialize the Memory Bank.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._initialize_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _initialize_database(self) -> None:
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Create patterns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    examples TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    last_updated TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    feedback_count INTEGER DEFAULT 0,
                    positive_feedback INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes for efficient querying
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_id 
                ON patterns(project_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pattern_type 
                ON patterns(pattern_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_confidence 
                ON patterns(confidence DESC)
            """)
            
            # Create schema version table for migrations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            
            # Set initial schema version if not exists
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            if cursor.fetchone() is None:
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (1, datetime.now(timezone.utc).isoformat())
                )
    
    def store_pattern(self, pattern: ProjectPattern) -> None:
        """
        Store a new pattern or update an existing one.
        
        Args:
            pattern: The ProjectPattern to store
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if pattern already exists
            cursor.execute(
                "SELECT pattern_id FROM patterns WHERE pattern_id = ?",
                (pattern.pattern_id,)
            )
            exists = cursor.fetchone() is not None
            
            examples_json = json.dumps(pattern.examples)
            
            if exists:
                # Update existing pattern
                cursor.execute("""
                    UPDATE patterns
                    SET project_id = ?,
                        pattern_type = ?,
                        description = ?,
                        examples = ?,
                        confidence = ?,
                        last_updated = ?
                    WHERE pattern_id = ?
                """, (
                    pattern.project_id,
                    pattern.pattern_type.value if isinstance(pattern.pattern_type, PatternType) else pattern.pattern_type,
                    pattern.description,
                    examples_json,
                    pattern.confidence,
                    pattern.last_updated.isoformat(),
                    pattern.pattern_id
                ))
            else:
                # Insert new pattern
                cursor.execute("""
                    INSERT INTO patterns (
                        pattern_id, project_id, pattern_type, description,
                        examples, confidence, last_updated, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.pattern_id,
                    pattern.project_id,
                    pattern.pattern_type.value if isinstance(pattern.pattern_type, PatternType) else pattern.pattern_type,
                    pattern.description,
                    examples_json,
                    pattern.confidence,
                    pattern.last_updated.isoformat(),
                    datetime.now(timezone.utc).isoformat()
                ))
    
    def retrieve_pattern(self, pattern_id: str) -> Optional[ProjectPattern]:
        """
        Retrieve a specific pattern by ID.
        
        Args:
            pattern_id: The unique pattern identifier
            
        Returns:
            The ProjectPattern if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM patterns WHERE pattern_id = ?",
                (pattern_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
            
            return self._row_to_pattern(row)
    
    def retrieve_patterns(
        self,
        project_id: str,
        pattern_type: Optional[PatternType] = None,
        min_confidence: float = 0.0,
        limit: Optional[int] = None
    ) -> List[ProjectPattern]:
        """
        Retrieve patterns for a project with optional filtering.
        
        Args:
            project_id: The project identifier
            pattern_type: Optional pattern type filter
            min_confidence: Minimum confidence threshold (0.0-1.0)
            limit: Maximum number of patterns to return
            
        Returns:
            List of matching ProjectPatterns, ordered by confidence (descending)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM patterns
                WHERE project_id = ? AND confidence >= ?
            """
            params: List[Any] = [project_id, min_confidence]
            
            if pattern_type is not None:
                query += " AND pattern_type = ?"
                params.append(pattern_type.value if isinstance(pattern_type, PatternType) else pattern_type)
            
            query += " ORDER BY confidence DESC"
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_pattern(row) for row in rows]
    
    def search_patterns_by_description(
        self,
        project_id: str,
        search_term: str,
        min_confidence: float = 0.0,
        limit: Optional[int] = None
    ) -> List[ProjectPattern]:
        """
        Search patterns by description text (similarity search).
        
        Args:
            project_id: The project identifier
            search_term: Text to search for in descriptions
            min_confidence: Minimum confidence threshold
            limit: Maximum number of patterns to return
            
        Returns:
            List of matching ProjectPatterns, ordered by confidence
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM patterns
                WHERE project_id = ?
                AND confidence >= ?
                AND (description LIKE ? OR examples LIKE ?)
                ORDER BY confidence DESC
            """
            params: List[Any] = [
                project_id,
                min_confidence,
                f"%{search_term}%",
                f"%{search_term}%"
            ]
            
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_pattern(row) for row in rows]
    
    def update_pattern_confidence(
        self,
        pattern_id: str,
        feedback_positive: bool
    ) -> None:
        """
        Update pattern confidence based on user feedback.
        
        Uses a simple feedback-based scoring algorithm:
        - Positive feedback increases confidence
        - Negative feedback decreases confidence
        - Confidence is bounded between 0.0 and 1.0
        
        Args:
            pattern_id: The pattern to update
            feedback_positive: True for positive feedback, False for negative
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current pattern data
            cursor.execute("""
                SELECT confidence, feedback_count, positive_feedback
                FROM patterns
                WHERE pattern_id = ?
            """, (pattern_id,))
            
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Pattern {pattern_id} not found")
            
            current_confidence = row["confidence"]
            feedback_count = row["feedback_count"]
            positive_feedback = row["positive_feedback"]
            
            # Update feedback counters
            feedback_count += 1
            if feedback_positive:
                positive_feedback += 1
            
            # Calculate new confidence using weighted average
            # New confidence = (positive_feedback / total_feedback) * 0.7 + current_confidence * 0.3
            feedback_ratio = positive_feedback / feedback_count
            new_confidence = feedback_ratio * 0.7 + current_confidence * 0.3
            
            # Ensure confidence stays in valid range
            new_confidence = max(0.0, min(1.0, new_confidence))
            
            # Update the pattern
            cursor.execute("""
                UPDATE patterns
                SET confidence = ?,
                    feedback_count = ?,
                    positive_feedback = ?,
                    last_updated = ?
                WHERE pattern_id = ?
            """, (
                new_confidence,
                feedback_count,
                positive_feedback,
                datetime.now(timezone.utc).isoformat(),
                pattern_id
            ))
    
    def delete_pattern(self, pattern_id: str) -> bool:
        """
        Delete a pattern from the database.
        
        Args:
            pattern_id: The pattern to delete
            
        Returns:
            True if pattern was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM patterns WHERE pattern_id = ?", (pattern_id,))
            return cursor.rowcount > 0
    
    def get_all_projects(self) -> List[str]:
        """
        Get a list of all project IDs in the database.
        
        Returns:
            List of unique project IDs
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT project_id FROM patterns ORDER BY project_id")
            return [row["project_id"] for row in cursor.fetchall()]
    
    def get_pattern_count(self, project_id: Optional[str] = None) -> int:
        """
        Get the count of patterns, optionally filtered by project.
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            Number of patterns
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if project_id is None:
                cursor.execute("SELECT COUNT(*) as count FROM patterns")
            else:
                cursor.execute(
                    "SELECT COUNT(*) as count FROM patterns WHERE project_id = ?",
                    (project_id,)
                )
            
            return cursor.fetchone()["count"]
    
    def _row_to_pattern(self, row: sqlite3.Row) -> ProjectPattern:
        """Convert a database row to a ProjectPattern object."""
        return ProjectPattern(
            pattern_id=row["pattern_id"],
            project_id=row["project_id"],
            pattern_type=PatternType(row["pattern_type"]),
            description=row["description"],
            examples=json.loads(row["examples"]),
            confidence=row["confidence"],
            last_updated=datetime.fromisoformat(row["last_updated"])
        )
    
    def migrate_to_version(self, target_version: int) -> None:
        """
        Apply database migrations up to the target version.
        
        Args:
            target_version: The schema version to migrate to
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get current version
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            current_version = row["version"] if row else 0
            
            if current_version >= target_version:
                return  # Already at or beyond target version
            
            # Apply migrations sequentially
            for version in range(current_version + 1, target_version + 1):
                self._apply_migration(cursor, version)
                cursor.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (version, datetime.now(timezone.utc).isoformat())
                )
    
    def _apply_migration(self, cursor: sqlite3.Cursor, version: int) -> None:
        """
        Apply a specific migration version.
        
        Args:
            cursor: Database cursor
            version: Migration version to apply
        """
        # Migration definitions
        migrations = {
            # Version 1 is the initial schema (already applied in _initialize_database)
            # Future migrations can be added here
            # Example:
            # 2: "ALTER TABLE patterns ADD COLUMN new_field TEXT",
        }
        
        if version in migrations:
            cursor.execute(migrations[version])
    
    def get_schema_version(self) -> int:
        """
        Get the current database schema version.
        
        Returns:
            Current schema version number
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            return row["version"] if row else 0
    
    def clear_project_patterns(self, project_id: str) -> int:
        """
        Delete all patterns for a specific project.
        
        Args:
            project_id: The project whose patterns should be deleted
            
        Returns:
            Number of patterns deleted
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM patterns WHERE project_id = ?", (project_id,))
            return cursor.rowcount
