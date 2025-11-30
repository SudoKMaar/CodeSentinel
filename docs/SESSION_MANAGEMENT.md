# Session State Management

## Overview

The Session State Management module provides persistent storage for analysis session state, enabling pause/resume capabilities for long-running code analyses. This is essential for managing system resources and allowing users to interrupt and continue analyses as needed.

## Features

- **Session Creation**: Initialize new analysis sessions with configuration and file lists
- **Save/Restore**: Persist session state to JSON files with atomic writes
- **Checkpointing**: Track incremental progress during analysis
- **Pause/Resume**: Pause running sessions and resume them later
- **Session Cleanup**: Automatically clean up completed, expired, or failed sessions
- **Session Listing**: Query and filter sessions by status
- **Backup Support**: Create backups of session state

## Architecture

### Storage Format

Sessions are stored as JSON files in a configurable directory (default: `.sessions/`). Each session file is named using the sanitized session ID (alphanumeric, hyphens, and underscores only).

### Data Model

The `SessionState` model includes:
- `session_id`: Unique identifier
- `status`: Current status (running, paused, completed, failed)
- `config`: Analysis configuration
- `processed_files`: List of already-processed files
- `pending_files`: List of files awaiting processing
- `partial_results`: Dictionary of intermediate results
- `checkpoint_time`: Timestamp of last checkpoint

## Usage

### Basic Usage

```python
from storage.session_manager import SessionManager
from models.data_models import AnalysisConfig, AnalysisDepth

# Initialize the session manager
session_manager = SessionManager(sessions_dir=".sessions")

# Create a new session
config = AnalysisConfig(
    target_path="./src",
    file_patterns=["*.py"],
    analysis_depth=AnalysisDepth.STANDARD
)

session_state = session_manager.create_session(
    session_id="analysis-001",
    config=config,
    pending_files=["file1.py", "file2.py", "file3.py"]
)
```

### Checkpointing Progress

```python
# Update progress during analysis
session_manager.checkpoint(
    session_id="analysis-001",
    processed_files=["file1.py", "file2.py"],
    pending_files=["file3.py"],
    partial_results={
        "file1.py": {"issues": 3, "quality_score": 85.0},
        "file2.py": {"issues": 1, "quality_score": 92.0}
    }
)
```

### Pause and Resume

```python
# Pause an active session
session_manager.pause_session("analysis-001")

# Later, resume the session
resumed_state = session_manager.resume_session("analysis-001")
if resumed_state:
    # Continue processing from where we left off
    remaining_files = resumed_state.pending_files
    # ... continue analysis
```

### Session Cleanup

```python
# Clean up completed sessions (keep 10 most recent)
deleted = session_manager.cleanup_completed_sessions(keep_recent=10)

# Clean up sessions older than 30 days
deleted = session_manager.cleanup_expired_sessions(max_age_days=30)

# Clean up all failed sessions
deleted = session_manager.cleanup_failed_sessions()
```

### Listing Sessions

```python
# List all sessions
all_sessions = session_manager.list_sessions()

# List only paused sessions
paused_sessions = session_manager.list_sessions(
    status_filter=SessionStatus.PAUSED
)

# Get session count
total = session_manager.get_session_count()
running = session_manager.get_session_count(SessionStatus.RUNNING)
```

## Implementation Details

### Atomic Writes

Session state is written atomically using a temporary file and rename operation. This ensures that session files are never left in a corrupted state, even if the process is interrupted during a write.

### Session ID Sanitization

Session IDs are sanitized to prevent directory traversal attacks. Only alphanumeric characters, hyphens, and underscores are allowed in the filename.

### Error Handling

- Corrupted session files return `None` when loaded
- Missing sessions return `None` or `False` as appropriate
- All file operations use proper exception handling

## Testing

The implementation includes comprehensive property-based tests using Hypothesis:

- **Property 17: Pause-Resume Round-Trip** - Validates that saving and loading preserves all session state
- Additional properties test session creation, pause/resume, checkpointing, listing, and deletion

Run tests with:
```bash
pytest tests/test_session_manager.py -v
```

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 7.1**: Session state persistence for pause/resume
- **Requirement 7.3**: Resume from last checkpoint
- **Requirement 7.4**: Skip already-processed files on resume

## Example

See `examples/session_manager_demo.py` for a complete working example demonstrating all features.

## API Reference

### SessionManager

#### `__init__(sessions_dir: str = ".sessions")`
Initialize the session manager with a directory for storing session files.

#### `create_session(session_id: str, config: AnalysisConfig, pending_files: Optional[List[str]] = None) -> SessionState`
Create a new analysis session.

#### `save_session(session_state: SessionState) -> None`
Save session state to disk (atomic operation).

#### `load_session(session_id: str) -> Optional[SessionState]`
Load session state from disk. Returns None if not found or corrupted.

#### `checkpoint(session_id: str, processed_files: List[str], pending_files: List[str], partial_results: Optional[Dict[str, Any]] = None) -> bool`
Create a checkpoint with current progress.

#### `pause_session(session_id: str) -> bool`
Pause a running session.

#### `resume_session(session_id: str) -> Optional[SessionState]`
Resume a paused session.

#### `complete_session(session_id: str) -> bool`
Mark a session as completed.

#### `fail_session(session_id: str) -> bool`
Mark a session as failed.

#### `delete_session(session_id: str) -> bool`
Delete a session and its files.

#### `list_sessions(status_filter: Optional[SessionStatus] = None) -> List[SessionState]`
List all sessions, optionally filtered by status.

#### `cleanup_completed_sessions(keep_recent: int = 10) -> int`
Clean up old completed sessions, keeping only the most recent ones.

#### `cleanup_expired_sessions(max_age_days: int = 30) -> int`
Clean up sessions older than the specified age.

#### `cleanup_failed_sessions() -> int`
Clean up all failed sessions.

#### `get_session_count(status_filter: Optional[SessionStatus] = None) -> int`
Get the count of sessions, optionally filtered by status.

#### `session_exists(session_id: str) -> bool`
Check if a session exists.

#### `backup_session(session_id: str, backup_dir: Optional[str] = None) -> bool`
Create a backup of a session.
