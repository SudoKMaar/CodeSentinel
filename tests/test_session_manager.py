"""
Property-based tests for session state management.

Feature: code-review-documentation-agent
"""

import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.strategies import SearchStrategy

from storage.session_manager import SessionManager
from models.data_models import (
    SessionState,
    SessionStatus,
    AnalysisConfig,
    AnalysisDepth,
)


# Custom strategies for generating valid instances

@st.composite
def analysis_config_strategy(draw: st.DrawFn) -> AnalysisConfig:
    """Generate random AnalysisConfig instances."""
    # Generate non-whitespace text for target_path
    target_path_text = st.text(
        alphabet=st.characters(
            min_codepoint=33, max_codepoint=126,  # Exclude space (32)
            blacklist_categories=('Cc', 'Cs')
        ),
        min_size=1,
        max_size=20
    )
    
    simple_text = st.text(
        alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_categories=('Cc', 'Cs')),
        min_size=1,
        max_size=20
    )
    
    # File patterns should be valid glob patterns (alphanumeric with * and .)
    file_pattern_text = st.text(alphabet=st.characters(whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789*.'), min_size=1, max_size=15)
    
    return AnalysisConfig(
        target_path=draw(target_path_text),
        file_patterns=draw(st.lists(file_pattern_text, min_size=1, max_size=3)),  # Use valid file patterns
        exclude_patterns=draw(st.lists(file_pattern_text, min_size=0, max_size=3)),
        coding_standards=draw(st.dictionaries(
            simple_text,
            st.one_of(st.text(max_size=10), st.integers(min_value=-1000, max_value=1000), st.booleans()),
            min_size=0,
            max_size=2
        )),
        analysis_depth=draw(st.sampled_from(AnalysisDepth)),
        enable_parallel=draw(st.booleans()),
    )


@st.composite
def datetime_strategy(draw: st.DrawFn) -> datetime:
    """Generate random datetime instances."""
    return datetime.fromtimestamp(
        draw(st.integers(min_value=0, max_value=2147483647)),
        tz=timezone.utc
    )


@st.composite
def valid_session_id_strategy(draw: st.DrawFn) -> str:
    """Generate valid session IDs (alphanumeric, hyphens, underscores only)."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='-_'),
        min_size=1,
        max_size=50
    ))


@st.composite
def session_state_strategy(draw: st.DrawFn) -> SessionState:
    """Generate random SessionState instances."""
    return SessionState(
        session_id=draw(valid_session_id_strategy()),
        status=draw(st.sampled_from(SessionStatus)),
        config=draw(analysis_config_strategy()),
        processed_files=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)),
        pending_files=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)),
        partial_results=draw(st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=0,
            max_size=5
        )),
        checkpoint_time=draw(datetime_strategy()),
    )


# Property-based tests

# Feature: code-review-documentation-agent, Property 17: Pause-Resume Round-Trip
# Validates: Requirements 7.1, 7.3, 7.4

@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
@given(session_state_strategy())
def test_pause_resume_roundtrip(session_state: SessionState) -> None:
    """
    Property 17: Pause-Resume Round-Trip
    
    For any SessionState, saving it to disk and loading it back should
    produce an equivalent SessionState with all fields preserved.
    
    Validates: Requirements 7.1, 7.3, 7.4
    """
    # Create a temporary directory for this test
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(sessions_dir=temp_dir)
        
        # Save the session state
        session_manager.save_session(session_state)
        
        # Load the session state back
        restored_state = session_manager.load_session(session_state.session_id)
        
        # Verify the session was loaded
        assert restored_state is not None, "Session should be loaded successfully"
        
        # Verify all fields are preserved
        assert restored_state.session_id == session_state.session_id
        assert restored_state.status == session_state.status
        assert restored_state.config == session_state.config
        assert restored_state.processed_files == session_state.processed_files
        assert restored_state.pending_files == session_state.pending_files
        assert restored_state.partial_results == session_state.partial_results
        assert restored_state.checkpoint_time == session_state.checkpoint_time
        
        # Verify complete equivalence
        assert restored_state == session_state
        assert restored_state.model_dump() == session_state.model_dump()


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
@given(
    session_id=valid_session_id_strategy(),
    config=analysis_config_strategy(),
    pending_files=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)
)
def test_create_session_roundtrip(
    session_id: str,
    config: AnalysisConfig,
    pending_files: list
) -> None:
    """
    Property: Create session and verify it can be loaded back.
    
    For any session_id, config, and pending_files, creating a session
    and loading it back should preserve all the provided data.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(sessions_dir=temp_dir)
        
        # Create a new session
        created_state = session_manager.create_session(
            session_id=session_id,
            config=config,
            pending_files=pending_files
        )
        
        # Load the session back
        loaded_state = session_manager.load_session(session_id)
        
        # Verify the session was loaded
        assert loaded_state is not None
        
        # Verify all fields match
        assert loaded_state.session_id == session_id
        assert loaded_state.status == SessionStatus.RUNNING
        assert loaded_state.config == config
        assert loaded_state.processed_files == []
        assert loaded_state.pending_files == pending_files
        assert loaded_state.partial_results == {}
        
        # Verify equivalence with created state
        assert loaded_state == created_state


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
@given(session_state_strategy())
def test_pause_and_resume_preserves_state(session_state: SessionState) -> None:
    """
    Property: Pausing and resuming a session preserves all state except status.
    
    For any running SessionState, pausing it and then resuming should
    preserve all fields except the status should change appropriately.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(sessions_dir=temp_dir)
        
        # Set session to running status for this test
        session_state.status = SessionStatus.RUNNING
        session_manager.save_session(session_state)
        
        # Pause the session
        pause_result = session_manager.pause_session(session_state.session_id)
        assert pause_result is True, "Pause should succeed for running session"
        
        # Load and verify paused state
        paused_state = session_manager.load_session(session_state.session_id)
        assert paused_state is not None
        assert paused_state.status == SessionStatus.PAUSED
        
        # Verify other fields are preserved
        assert paused_state.session_id == session_state.session_id
        assert paused_state.config == session_state.config
        assert paused_state.processed_files == session_state.processed_files
        assert paused_state.pending_files == session_state.pending_files
        assert paused_state.partial_results == session_state.partial_results
        
        # Resume the session
        resumed_state = session_manager.resume_session(session_state.session_id)
        assert resumed_state is not None, "Resume should succeed for paused session"
        assert resumed_state.status == SessionStatus.RUNNING
        
        # Verify all fields are still preserved
        assert resumed_state.session_id == session_state.session_id
        assert resumed_state.config == session_state.config
        assert resumed_state.processed_files == session_state.processed_files
        assert resumed_state.pending_files == session_state.pending_files
        assert resumed_state.partial_results == session_state.partial_results


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
@given(
    session_state=session_state_strategy(),
    processed_files=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10),
    pending_files=st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10),
    partial_results=st.dictionaries(
        st.text(min_size=1, max_size=50),
        st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=5
    )
)
def test_checkpoint_preserves_progress(
    session_state: SessionState,
    processed_files: list,
    pending_files: list,
    partial_results: dict
) -> None:
    """
    Property: Checkpointing updates progress and preserves all data.
    
    For any SessionState and progress data, creating a checkpoint should
    update the progress fields and preserve all data when loaded back.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(sessions_dir=temp_dir)
        
        # Save initial session
        session_manager.save_session(session_state)
        
        # Create a checkpoint with new progress
        checkpoint_result = session_manager.checkpoint(
            session_id=session_state.session_id,
            processed_files=processed_files,
            pending_files=pending_files,
            partial_results=partial_results
        )
        assert checkpoint_result is True, "Checkpoint should succeed"
        
        # Load the checkpointed session
        checkpointed_state = session_manager.load_session(session_state.session_id)
        assert checkpointed_state is not None
        
        # Verify progress was updated
        assert checkpointed_state.processed_files == processed_files
        assert checkpointed_state.pending_files == pending_files
        
        # Verify partial results were merged
        for key, value in partial_results.items():
            assert key in checkpointed_state.partial_results
            assert checkpointed_state.partial_results[key] == value
        
        # Verify other fields are preserved
        assert checkpointed_state.session_id == session_state.session_id
        assert checkpointed_state.status == session_state.status
        assert checkpointed_state.config == session_state.config


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(
    st.lists(session_state_strategy(), min_size=1, max_size=10, unique_by=lambda s: s.session_id)
)
def test_list_sessions_returns_all_saved_sessions(session_states: list) -> None:
    """
    Property: Listing sessions returns all saved sessions.
    
    For any list of SessionStates, saving them all and then listing
    should return all of them.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(sessions_dir=temp_dir)
        
        # Save all sessions
        for session_state in session_states:
            session_manager.save_session(session_state)
        
        # List all sessions
        listed_sessions = session_manager.list_sessions()
        
        # Verify count matches
        assert len(listed_sessions) == len(session_states)
        
        # Verify all session IDs are present
        listed_ids = {s.session_id for s in listed_sessions}
        expected_ids = {s.session_id for s in session_states}
        assert listed_ids == expected_ids


@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(session_state_strategy())
def test_delete_session_removes_session(session_state: SessionState) -> None:
    """
    Property: Deleting a session removes it from storage.
    
    For any SessionState, saving it, deleting it, and then trying to
    load it should return None.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        session_manager = SessionManager(sessions_dir=temp_dir)
        
        # Save the session
        session_manager.save_session(session_state)
        
        # Verify it exists
        assert session_manager.session_exists(session_state.session_id)
        
        # Delete the session
        delete_result = session_manager.delete_session(session_state.session_id)
        assert delete_result is True
        
        # Verify it no longer exists
        assert not session_manager.session_exists(session_state.session_id)
        
        # Verify loading returns None
        loaded_state = session_manager.load_session(session_state.session_id)
        assert loaded_state is None
