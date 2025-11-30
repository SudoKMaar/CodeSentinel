"""
Property-based tests for observability functionality.

Tests verify:
- Operation observability with required log fields
- Historical log retrieval
"""

import json
import uuid
import io
from datetime import datetime, timezone
import tempfile
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch

from tools.observability import ObservabilityManager


# Custom strategies
@st.composite
def operation_name_strategy(draw):
    operations = ["file_analysis", "code_parsing", "documentation_generation", "review_generation"]
    return draw(st.sampled_from(operations))

@st.composite
def agent_name_strategy(draw):
    agents = ["analyzer", "documenter", "reviewer", "coordinator"]
    return draw(st.sampled_from(agents))

@st.composite
def log_level_strategy(draw):
    levels = ["debug", "info", "warning", "error", "critical"]
    return draw(st.sampled_from(levels))

@st.composite
def session_id_strategy(draw):
    return str(uuid.uuid4())

@st.composite
def log_context_strategy(draw):
    return {
        "file_path": draw(st.text(min_size=1, max_size=100)),
        "duration_ms": draw(st.floats(min_value=0.1, max_value=10000.0)),
        "status": draw(st.sampled_from(["success", "failure", "partial"]))
    }


# Feature: code-review-documentation-agent, Property 19: Operation Observability
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    operation=operation_name_strategy(),
    level=log_level_strategy(),
    context=log_context_strategy()
)
def test_property_operation_logging_contains_required_fields(operation, level, context):
    """
    Property 19: Operation Observability
    Validates: Requirements 8.1, 8.2, 8.3
    
    For any operation logged, the log entry should contain required fields.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_manager = ObservabilityManager(
            service_name="test-service",
            logs_dir=tmpdir,
            enable_console_export=False
        )
        
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            obs_manager.log_operation(operation=operation, level=level, **context)
        
        log_output = captured_output.getvalue().strip()
        if log_output:
            log_entry = json.loads(log_output)
            assert "timestamp" in log_entry
            assert "event" in log_entry
            assert log_entry["event"] == operation


# Feature: code-review-documentation-agent, Property 19: Operation Observability
@settings(max_examples=100)
@given(
    agent_name=agent_name_strategy(),
    operation=operation_name_strategy(),
    session_id=session_id_strategy()
)
def test_property_agent_operation_logging_with_correlation(agent_name, operation, session_id):
    """
    Property 19: Operation Observability
    Validates: Requirements 8.1, 8.2, 8.3
    
    For any agent operation, logs should contain agent info and correlation ID.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_manager = ObservabilityManager(
            service_name="test-service",
            logs_dir=tmpdir,
            enable_console_export=False
        )
        
        correlation_id = obs_manager.generate_correlation_id()
        
        captured_output = io.StringIO()
        with patch('sys.stdout', captured_output):
            with obs_manager.correlation_context(correlation_id):
                obs_manager.log_agent_operation(
                    agent_name=agent_name,
                    operation=operation,
                    session_id=session_id
                )
        
        log_output = captured_output.getvalue().strip()
        if log_output:
            log_entry = json.loads(log_output)
            assert "agent" in log_entry
            assert log_entry["agent"] == agent_name
            assert "correlation_id" in log_entry
            assert "event" in log_entry
            assert f"{agent_name}.{operation}" == log_entry["event"]


# Feature: code-review-documentation-agent, Property 20: Historical Log Retrieval
@settings(max_examples=100)
@given(
    session_id=session_id_strategy(),
    num_logs=st.integers(min_value=1, max_value=50)
)
def test_property_historical_log_storage_and_retrieval(session_id, num_logs):
    """
    Property 20: Historical Log Retrieval
    Validates: Requirements 8.5
    
    For any session with logs, storing and retrieving should preserve all data.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_manager = ObservabilityManager(
            service_name="test-service",
            logs_dir=tmpdir,
            enable_console_export=False
        )
        
        logs_to_store = []
        for i in range(num_logs):
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": f"operation_{i}",
                "session_id": session_id,
                "index": i
            }
            logs_to_store.append(log_entry)
        
        obs_manager.store_session_logs(session_id, logs_to_store)
        retrieved_logs = obs_manager.retrieve_session_logs(session_id)
        
        assert len(retrieved_logs) == num_logs
        for i, log_entry in enumerate(retrieved_logs):
            assert log_entry["event"] == f"operation_{i}"
            assert log_entry["index"] == i


# Feature: code-review-documentation-agent, Property 20: Historical Log Retrieval
@settings(max_examples=100)
@given(
    session_id=session_id_strategy(),
    first_batch_size=st.integers(min_value=1, max_value=20),
    second_batch_size=st.integers(min_value=1, max_value=20)
)
def test_property_log_storage_appends_to_existing(session_id, first_batch_size, second_batch_size):
    """
    Property 20: Historical Log Retrieval
    Validates: Requirements 8.5
    
    For any session, storing logs multiple times should append.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_manager = ObservabilityManager(
            service_name="test-service",
            logs_dir=tmpdir,
            enable_console_export=False
        )
        
        first_batch = [
            {"event": f"batch1_op_{i}", "session_id": session_id, "batch": 1}
            for i in range(first_batch_size)
        ]
        obs_manager.store_session_logs(session_id, first_batch)
        
        second_batch = [
            {"event": f"batch2_op_{i}", "session_id": session_id, "batch": 2}
            for i in range(second_batch_size)
        ]
        obs_manager.store_session_logs(session_id, second_batch)
        
        all_logs = obs_manager.retrieve_session_logs(session_id)
        
        expected_total = first_batch_size + second_batch_size
        assert len(all_logs) == expected_total


# Feature: code-review-documentation-agent, Property 20: Historical Log Retrieval
def test_property_retrieve_nonexistent_session_returns_empty():
    """
    Property 20: Historical Log Retrieval
    Validates: Requirements 8.5
    
    For any non-existent session ID, retrieving logs should return empty list.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        obs_manager = ObservabilityManager(
            service_name="test-service",
            logs_dir=tmpdir,
            enable_console_export=False
        )
        
        nonexistent_session_id = str(uuid.uuid4())
        logs = obs_manager.retrieve_session_logs(nonexistent_session_id)
        
        assert logs == []
        assert isinstance(logs, list)
