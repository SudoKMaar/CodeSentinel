"""
Demo script showing how to use the SessionManager for pause/resume functionality.

This example demonstrates:
- Creating a new analysis session
- Saving and loading session state
- Creating checkpoints during analysis
- Pausing and resuming sessions
- Cleaning up completed sessions
"""

from datetime import datetime, timezone
from storage.session_manager import SessionManager
from models.data_models import AnalysisConfig, AnalysisDepth, SessionStatus


def main():
    """Demonstrate SessionManager usage."""
    
    # Initialize the session manager
    session_manager = SessionManager(sessions_dir=".demo_sessions")
    
    print("=== Session Manager Demo ===\n")
    
    # 1. Create a new analysis session
    print("1. Creating a new analysis session...")
    config = AnalysisConfig(
        target_path="./src",
        file_patterns=["*.py", "*.js"],
        exclude_patterns=["node_modules/**", "__pycache__/**"],
        analysis_depth=AnalysisDepth.STANDARD,
        enable_parallel=True
    )
    
    session_id = "demo-session-001"
    pending_files = ["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
    
    session_state = session_manager.create_session(
        session_id=session_id,
        config=config,
        pending_files=pending_files
    )
    
    print(f"   Created session: {session_state.session_id}")
    print(f"   Status: {session_state.status}")
    print(f"   Pending files: {len(session_state.pending_files)}")
    print()
    
    # 2. Simulate processing some files and create a checkpoint
    print("2. Processing files and creating checkpoint...")
    processed = ["file1.py", "file2.py"]
    remaining = ["file3.py", "file4.py", "file5.py"]
    partial_results = {
        "file1.py": {"issues": 3, "quality_score": 85.0},
        "file2.py": {"issues": 1, "quality_score": 92.0}
    }
    
    session_manager.checkpoint(
        session_id=session_id,
        processed_files=processed,
        pending_files=remaining,
        partial_results=partial_results
    )
    
    print(f"   Processed: {len(processed)} files")
    print(f"   Remaining: {len(remaining)} files")
    print()
    
    # 3. Pause the session
    print("3. Pausing the session...")
    pause_result = session_manager.pause_session(session_id)
    print(f"   Pause successful: {pause_result}")
    
    # Load and verify paused state
    paused_state = session_manager.load_session(session_id)
    print(f"   Status: {paused_state.status}")
    print(f"   Processed files: {paused_state.processed_files}")
    print(f"   Pending files: {paused_state.pending_files}")
    print()
    
    # 4. Resume the session
    print("4. Resuming the session...")
    resumed_state = session_manager.resume_session(session_id)
    if resumed_state:
        print(f"   Resume successful!")
        print(f"   Status: {resumed_state.status}")
        print(f"   Can continue processing: {len(resumed_state.pending_files)} files remaining")
    print()
    
    # 5. Complete the session
    print("5. Completing the session...")
    session_manager.complete_session(session_id)
    completed_state = session_manager.load_session(session_id)
    print(f"   Status: {completed_state.status}")
    print()
    
    # 6. List all sessions
    print("6. Listing all sessions...")
    all_sessions = session_manager.list_sessions()
    print(f"   Total sessions: {len(all_sessions)}")
    for session in all_sessions:
        print(f"   - {session.session_id}: {session.status}")
    print()
    
    # 7. Create a backup
    print("7. Creating session backup...")
    backup_result = session_manager.backup_session(session_id)
    print(f"   Backup successful: {backup_result}")
    print()
    
    # 8. Cleanup completed sessions
    print("8. Cleaning up completed sessions (keeping 5 most recent)...")
    deleted_count = session_manager.cleanup_completed_sessions(keep_recent=5)
    print(f"   Deleted {deleted_count} old completed sessions")
    print()
    
    # 9. Session statistics
    print("9. Session statistics:")
    print(f"   Total sessions: {session_manager.get_session_count()}")
    print(f"   Running sessions: {session_manager.get_session_count(SessionStatus.RUNNING)}")
    print(f"   Paused sessions: {session_manager.get_session_count(SessionStatus.PAUSED)}")
    print(f"   Completed sessions: {session_manager.get_session_count(SessionStatus.COMPLETED)}")
    print()
    
    print("=== Demo Complete ===")


if __name__ == "__main__":
    main()
