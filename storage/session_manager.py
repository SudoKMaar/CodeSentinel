"""
Session state management for pause/resume functionality.

This module provides persistent storage for analysis session state using JSON files,
enabling pause/resume capabilities for long-running analyses.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from models.data_models import SessionState, SessionStatus, AnalysisConfig


class SessionManager:
    """
    Manages session state persistence for analysis sessions.
    
    Provides:
    - Session creation and initialization
    - Save and restore operations for session state
    - Checkpoint mechanism for incremental progress tracking
    - Session cleanup for completed/expired sessions
    """
    
    def __init__(self, sessions_dir: str = ".sessions"):
        """
        Initialize the Session Manager.
        
        Args:
            sessions_dir: Directory path for storing session files
        """
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session(
        self,
        session_id: str,
        config: AnalysisConfig,
        pending_files: Optional[List[str]] = None
    ) -> SessionState:
        """
        Create a new analysis session.
        
        Args:
            session_id: Unique identifier for the session
            config: Analysis configuration
            pending_files: List of files to be analyzed
            
        Returns:
            Newly created SessionState
        """
        session_state = SessionState(
            session_id=session_id,
            status=SessionStatus.RUNNING,
            config=config,
            processed_files=[],
            pending_files=pending_files or [],
            partial_results={},
            checkpoint_time=datetime.now(timezone.utc)
        )
        
        self.save_session(session_state)
        return session_state
    
    def save_session(self, session_state: SessionState) -> None:
        """
        Save session state to disk.
        
        Args:
            session_state: The SessionState to persist
        """
        import time
        
        session_file = self._get_session_file_path(session_state.session_id)
        
        # Convert to JSON-serializable dict
        session_dict = session_state.model_dump(mode='json')
        
        # Write to temporary file first, then rename for atomic operation
        temp_file = session_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(session_dict, f, indent=2, ensure_ascii=False)
        
        # Atomic rename with retry for Windows file locking issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                temp_file.replace(session_file)
                break
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # Wait a bit and retry
                else:
                    raise
    
    def load_session(self, session_id: str) -> Optional[SessionState]:
        """
        Load session state from disk.
        
        Args:
            session_id: The session identifier
            
        Returns:
            SessionState if found, None otherwise
        """
        session_file = self._get_session_file_path(session_id)
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_dict = json.load(f)
            
            return SessionState.model_validate(session_dict)
        except (json.JSONDecodeError, ValueError) as e:
            # Log error and return None for corrupted files
            print(f"Error loading session {session_id}: {e}")
            return None
    
    def update_session_status(
        self,
        session_id: str,
        status: SessionStatus
    ) -> bool:
        """
        Update the status of a session.
        
        Args:
            session_id: The session identifier
            status: New status value
            
        Returns:
            True if updated successfully, False if session not found
        """
        session_state = self.load_session(session_id)
        if session_state is None:
            return False
        
        session_state.status = status
        session_state.checkpoint_time = datetime.now(timezone.utc)
        self.save_session(session_state)
        return True
    
    def checkpoint(
        self,
        session_id: str,
        processed_files: List[str],
        pending_files: List[str],
        partial_results: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a checkpoint for incremental progress tracking.
        
        Args:
            session_id: The session identifier
            processed_files: Files that have been processed
            pending_files: Files still pending processing
            partial_results: Optional partial analysis results
            
        Returns:
            True if checkpoint created successfully, False if session not found
        """
        session_state = self.load_session(session_id)
        if session_state is None:
            return False
        
        session_state.processed_files = processed_files
        session_state.pending_files = pending_files
        if partial_results is not None:
            session_state.partial_results.update(partial_results)
        session_state.checkpoint_time = datetime.now(timezone.utc)
        
        self.save_session(session_state)
        return True
    
    def pause_session(self, session_id: str) -> bool:
        """
        Pause an active session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if paused successfully, False if session not found or not running
        """
        session_state = self.load_session(session_id)
        if session_state is None:
            return False
        
        if session_state.status != SessionStatus.RUNNING:
            return False
        
        session_state.status = SessionStatus.PAUSED
        session_state.checkpoint_time = datetime.now(timezone.utc)
        self.save_session(session_state)
        return True
    
    def resume_session(self, session_id: str) -> Optional[SessionState]:
        """
        Resume a paused session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            SessionState if resumed successfully, None if session not found or not paused
        """
        session_state = self.load_session(session_id)
        if session_state is None:
            return None
        
        if session_state.status != SessionStatus.PAUSED:
            return None
        
        session_state.status = SessionStatus.RUNNING
        session_state.checkpoint_time = datetime.now(timezone.utc)
        self.save_session(session_state)
        return session_state
    
    def complete_session(self, session_id: str) -> bool:
        """
        Mark a session as completed.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if marked completed successfully, False if session not found
        """
        return self.update_session_status(session_id, SessionStatus.COMPLETED)
    
    def fail_session(self, session_id: str) -> bool:
        """
        Mark a session as failed.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if marked failed successfully, False if session not found
        """
        return self.update_session_status(session_id, SessionStatus.FAILED)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and its associated files.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if deleted successfully, False if session not found
        """
        session_file = self._get_session_file_path(session_id)
        
        if not session_file.exists():
            return False
        
        try:
            session_file.unlink()
            return True
        except OSError:
            return False
    
    def list_sessions(
        self,
        status_filter: Optional[SessionStatus] = None
    ) -> List[SessionState]:
        """
        List all sessions, optionally filtered by status.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            List of SessionState objects
        """
        sessions = []
        
        for session_file in self.sessions_dir.glob("*.json"):
            session_id = session_file.stem
            session_state = self.load_session(session_id)
            
            if session_state is None:
                continue
            
            if status_filter is None or session_state.status == status_filter:
                sessions.append(session_state)
        
        # Sort by checkpoint time (most recent first)
        sessions.sort(key=lambda s: s.checkpoint_time, reverse=True)
        return sessions
    
    def cleanup_completed_sessions(self, keep_recent: int = 10) -> int:
        """
        Clean up completed sessions, keeping only the most recent ones.
        
        Args:
            keep_recent: Number of recent completed sessions to keep
            
        Returns:
            Number of sessions deleted
        """
        completed_sessions = self.list_sessions(status_filter=SessionStatus.COMPLETED)
        
        # Keep only the most recent N sessions
        sessions_to_delete = completed_sessions[keep_recent:]
        
        deleted_count = 0
        for session in sessions_to_delete:
            if self.delete_session(session.session_id):
                deleted_count += 1
        
        return deleted_count
    
    def cleanup_expired_sessions(self, max_age_days: int = 30) -> int:
        """
        Clean up sessions older than the specified age.
        
        Args:
            max_age_days: Maximum age in days for sessions to keep
            
        Returns:
            Number of sessions deleted
        """
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_days * 24 * 60 * 60)
        
        deleted_count = 0
        for session_file in self.sessions_dir.glob("*.json"):
            # Check file modification time
            if session_file.stat().st_mtime < cutoff_time:
                session_id = session_file.stem
                if self.delete_session(session_id):
                    deleted_count += 1
        
        return deleted_count
    
    def cleanup_failed_sessions(self) -> int:
        """
        Clean up all failed sessions.
        
        Returns:
            Number of sessions deleted
        """
        failed_sessions = self.list_sessions(status_filter=SessionStatus.FAILED)
        
        deleted_count = 0
        for session in failed_sessions:
            if self.delete_session(session.session_id):
                deleted_count += 1
        
        return deleted_count
    
    def get_session_count(self, status_filter: Optional[SessionStatus] = None) -> int:
        """
        Get the count of sessions, optionally filtered by status.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            Number of sessions
        """
        return len(self.list_sessions(status_filter=status_filter))
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if session exists, False otherwise
        """
        return self._get_session_file_path(session_id).exists()
    
    def _get_session_file_path(self, session_id: str) -> Path:
        """
        Get the file path for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Path to the session file
        """
        # Sanitize session_id to prevent directory traversal
        safe_session_id = "".join(c for c in session_id if c.isalnum() or c in ('-', '_'))
        return self.sessions_dir / f"{safe_session_id}.json"
    
    def backup_session(self, session_id: str, backup_dir: Optional[str] = None) -> bool:
        """
        Create a backup of a session.
        
        Args:
            session_id: The session identifier
            backup_dir: Optional directory for backup (defaults to sessions_dir/backups)
            
        Returns:
            True if backup created successfully, False otherwise
        """
        session_file = self._get_session_file_path(session_id)
        
        if not session_file.exists():
            return False
        
        if backup_dir is None:
            backup_path = self.sessions_dir / "backups"
        else:
            backup_path = Path(backup_dir)
        
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Create backup with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"{session_id}_{timestamp}.json"
        
        try:
            shutil.copy2(session_file, backup_file)
            return True
        except OSError:
            return False
    
    def validate_session(self, session_id: str) -> tuple[bool, Optional[str]]:
        """
        Validate session state for consistency and recoverability.
        
        Args:
            session_id: The session identifier
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        session_state = self.load_session(session_id)
        
        if session_state is None:
            return False, "Session not found"
        
        # Check required fields
        if not session_state.session_id:
            return False, "Missing session_id"
        
        if not session_state.config:
            return False, "Missing config"
        
        if not session_state.config.target_path:
            return False, "Missing target_path in config"
        
        # Validate target path exists
        target_path = Path(session_state.config.target_path)
        if not target_path.exists():
            return False, f"Target path does not exist: {session_state.config.target_path}"
        
        # Check for data consistency
        processed_set = set(session_state.processed_files)
        pending_set = set(session_state.pending_files)
        
        # Files should not be in both processed and pending
        overlap = processed_set & pending_set
        if overlap:
            return False, f"Files in both processed and pending: {overlap}"
        
        # Validate status transitions
        valid_statuses = {SessionStatus.RUNNING, SessionStatus.PAUSED, SessionStatus.COMPLETED, SessionStatus.FAILED}
        if session_state.status not in valid_statuses:
            return False, f"Invalid status: {session_state.status}"
        
        return True, None
    
    def recover_session(self, session_id: str) -> Optional[SessionState]:
        """
        Attempt to recover a corrupted or invalid session.
        
        Performs:
        - Validation checks
        - Automatic backup creation
        - State correction where possible
        
        Args:
            session_id: The session identifier
        
        Returns:
            Recovered SessionState if successful, None otherwise
        """
        # First, try to load the session
        session_state = self.load_session(session_id)
        
        if session_state is None:
            return None
        
        # Create backup before attempting recovery
        self.backup_session(session_id)
        
        # Validate and attempt to fix issues
        is_valid, error_msg = self.validate_session(session_id)
        
        if is_valid:
            return session_state
        
        # Attempt recovery based on error type
        if "Files in both processed and pending" in (error_msg or ""):
            # Remove duplicates from pending (prefer processed)
            processed_set = set(session_state.processed_files)
            session_state.pending_files = [
                f for f in session_state.pending_files if f not in processed_set
            ]
            self.save_session(session_state)
            return session_state
        
        if "Target path does not exist" in (error_msg or ""):
            # Cannot recover if target path is gone
            return None
        
        if "Invalid status" in (error_msg or ""):
            # Reset to a valid status based on progress
            if session_state.pending_files:
                session_state.status = SessionStatus.PAUSED
            else:
                session_state.status = SessionStatus.COMPLETED
            self.save_session(session_state)
            return session_state
        
        # If we can't recover, return None
        return None
    
    def get_session_health(self, session_id: str) -> Dict[str, Any]:
        """
        Get health status and diagnostics for a session.
        
        Args:
            session_id: The session identifier
        
        Returns:
            Dictionary with health information
        """
        session_state = self.load_session(session_id)
        
        if session_state is None:
            return {
                'exists': False,
                'valid': False,
                'error': 'Session not found'
            }
        
        is_valid, error_msg = self.validate_session(session_id)
        
        # Calculate progress
        total_files = len(session_state.processed_files) + len(session_state.pending_files)
        progress = 0.0
        if total_files > 0:
            progress = len(session_state.processed_files) / total_files
        
        # Check file existence
        missing_files = []
        for file_path in session_state.processed_files + session_state.pending_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        return {
            'exists': True,
            'valid': is_valid,
            'error': error_msg,
            'status': session_state.status,
            'progress': progress,
            'processed_count': len(session_state.processed_files),
            'pending_count': len(session_state.pending_files),
            'missing_files': missing_files,
            'last_checkpoint': session_state.checkpoint_time.isoformat()
        }
