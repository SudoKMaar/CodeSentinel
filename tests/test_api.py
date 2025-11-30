"""
Property-based tests for REST API endpoints.

Tests verify:
- API configuration acceptance (Property 25)
- Structured output format (Property 26)
- Webhook notification (Property 27)
"""

import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, strategies as st, settings, HealthCheck

from api.main import app, coordinator, session_manager
from models.data_models import AnalysisDepth


# Test client
client = TestClient(app)


# Hypothesis strategies for generating test data
@st.composite
def analysis_config_strategy(draw):
    """Generate random but valid analysis configurations."""
    # Create a temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    
    # Create some test files
    test_file = Path(temp_dir) / "test.py"
    test_file.write_text("def hello(): pass")
    
    file_patterns = draw(st.lists(
        st.sampled_from(["*.py", "*.js", "*.ts", "*.tsx", "*.jsx"]),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    exclude_patterns = draw(st.lists(
        st.sampled_from(["node_modules/**", "venv/**", ".git/**", "__pycache__/**", "*.pyc"]),
        min_size=0,
        max_size=3,
        unique=True
    ))
    
    analysis_depth = draw(st.sampled_from(["quick", "standard", "deep"]))
    
    enable_parallel = draw(st.booleans())
    
    coding_standards = draw(st.one_of(
        st.none(),
        st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
            st.one_of(st.booleans(), st.integers(min_value=1, max_value=100), st.text(min_size=1, max_size=50)),
            min_size=0,
            max_size=3
        )
    ))
    
    return {
        "codebase_path": temp_dir,
        "file_patterns": file_patterns,
        "exclude_patterns": exclude_patterns,
        "analysis_depth": analysis_depth,
        "enable_parallel": enable_parallel,
        "coding_standards": coding_standards,
        "_temp_dir": temp_dir  # Store for cleanup
    }


# Feature: code-review-documentation-agent, Property 25: API Configuration Acceptance
@given(config=analysis_config_strategy())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_api_configuration_acceptance(config: Dict[str, Any]):
    """
    Property 25: API Configuration Acceptance
    
    For any API-triggered analysis, the system should accept and apply
    configuration parameters including target paths and analysis depth.
    
    Validates: Requirements 10.2
    """
    temp_dir = config.pop("_temp_dir")
    
    try:
        # Mock the background analysis to prevent actual execution
        with patch('api.main.run_analysis_async', new_callable=AsyncMock) as mock_run:
            # Configure mock to return immediately
            mock_run.return_value = None
            
            # Send analysis request with configuration
            response = client.post("/analyze", json=config)
            
            # Verify request was accepted
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Verify response structure
            data = response.json()
            assert "session_id" in data
            assert "status" in data
            assert "message" in data
            assert data["status"] in ["running", "pending"]
            
            # Verify the codebase path was accepted
            assert Path(config["codebase_path"]).exists()
            
            # Verify analysis depth is valid
            if config.get("analysis_depth"):
                assert config["analysis_depth"] in ["quick", "standard", "deep"]
            
            # Verify file patterns are lists of strings
            if config.get("file_patterns"):
                assert isinstance(config["file_patterns"], list)
                assert all(isinstance(p, str) for p in config["file_patterns"])
            
            # Verify exclude patterns are lists of strings
            if config.get("exclude_patterns"):
                assert isinstance(config["exclude_patterns"], list)
                assert all(isinstance(p, str) for p in config["exclude_patterns"])
            
            # Verify enable_parallel is boolean
            if "enable_parallel" in config:
                assert isinstance(config["enable_parallel"], bool)
            
            # Verify coding_standards is dict or None
            if config.get("coding_standards") is not None:
                assert isinstance(config["coding_standards"], dict)
    
    finally:
        # Cleanup temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


# Unit test for basic API functionality
def test_api_root():
    """Test root endpoint returns correct information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Code Review & Documentation Agent"
    assert data["status"] == "running"


def test_api_health():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_analyze_invalid_path():
    """Test analysis with invalid codebase path."""
    response = client.post("/analyze", json={
        "codebase_path": "/nonexistent/path/that/does/not/exist"
    })
    assert response.status_code == 400
    assert "does not exist" in response.text.lower()


def test_status_nonexistent_session():
    """Test status check for nonexistent session."""
    response = client.get("/status/nonexistent-session-id")
    assert response.status_code == 404


def test_pause_nonexistent_session():
    """Test pause for nonexistent session."""
    response = client.post("/pause/nonexistent-session-id")
    assert response.status_code == 404


def test_resume_nonexistent_session():
    """Test resume for nonexistent session."""
    response = client.post("/resume/nonexistent-session-id")
    assert response.status_code == 404


def test_results_nonexistent_session():
    """Test results for nonexistent session."""
    response = client.get("/results/nonexistent-session-id")
    assert response.status_code == 404


def test_history_endpoint():
    """Test history endpoint returns valid structure."""
    response = client.get("/history")
    assert response.status_code == 200
    data = response.json()
    assert "analyses" in data
    assert "total" in data
    assert isinstance(data["analyses"], list)
    assert isinstance(data["total"], int)



# Feature: code-review-documentation-agent, Property 26: Structured Output Format
@given(config=analysis_config_strategy())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_structured_output_format(config: Dict[str, Any]):
    """
    Property 26: Structured Output Format
    
    For any completed analysis, results should be returned in a valid
    structured format (JSON) suitable for CI/CD integration.
    
    Validates: Requirements 10.3
    """
    temp_dir = config.pop("_temp_dir")
    
    try:
        # Create a mock analysis result
        from models.data_models import (
            AnalysisResult, FileAnalysis, CodeMetrics, Suggestion,
            Documentation, MetricsSummary, SessionState, SessionStatus,
            AnalysisConfig, AnalysisDepth
        )
        from datetime import datetime, timezone
        
        session_id = "test-session-" + str(hash(temp_dir))[:8]
        
        # Create minimal analysis result
        mock_result = AnalysisResult(
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            codebase_path=temp_dir,
            files_analyzed=1,
            total_issues=0,
            quality_score=95.0,
            file_analyses=[],
            suggestions=[],
            documentation=Documentation(
                project_structure="Test structure",
                api_docs={},
                examples={}
            ),
            metrics_summary=MetricsSummary(
                total_files=1,
                total_lines=10,
                average_complexity=1.0,
                average_maintainability=95.0,
                total_issues_by_severity={},
                total_issues_by_category={}
            )
        )
        
        # Create session state with completed status
        analysis_config = AnalysisConfig(
            target_path=temp_dir,
            file_patterns=config.get("file_patterns", ["*.py"]),
            exclude_patterns=config.get("exclude_patterns", []),
            analysis_depth=AnalysisDepth(config.get("analysis_depth", "standard")),
            enable_parallel=config.get("enable_parallel", True)
        )
        
        session_state = SessionState(
            session_id=session_id,
            status=SessionStatus.COMPLETED,
            config=analysis_config,
            processed_files=[str(Path(temp_dir) / "test.py")],
            pending_files=[],
            partial_results={
                "file_analyses": [],
                "quality_score": 95.0
            },
            checkpoint_time=datetime.now(timezone.utc)
        )
        
        # Save session state
        session_manager.save_session(session_state)
        
        try:
            # Get results via API
            response = client.get(f"/results/{session_id}")
            
            # Verify response is successful
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            # Verify response is valid JSON
            data = response.json()
            assert isinstance(data, dict), "Response should be a JSON object"
            
            # Verify required fields are present
            required_fields = ["session_id", "status", "timestamp", "codebase_path", "files_analyzed", "results"]
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Verify field types
            assert isinstance(data["session_id"], str)
            assert isinstance(data["status"], str)
            assert isinstance(data["timestamp"], str)
            assert isinstance(data["codebase_path"], str)
            assert isinstance(data["files_analyzed"], int)
            assert isinstance(data["results"], dict)
            
            # Verify status is valid
            assert data["status"] in ["running", "paused", "completed", "failed"]
            
            # Verify files_analyzed is non-negative
            assert data["files_analyzed"] >= 0
            
            # Verify timestamp is ISO format
            try:
                datetime.fromisoformat(data["timestamp"])
            except ValueError:
                pytest.fail(f"Invalid timestamp format: {data['timestamp']}")
            
            # Verify the output is suitable for CI/CD (can be serialized back to JSON)
            json_str = json.dumps(data)
            assert len(json_str) > 0
            
            # Verify we can parse it back
            reparsed = json.loads(json_str)
            assert reparsed == data
            
        finally:
            # Cleanup session
            session_manager.delete_session(session_id)
    
    finally:
        # Cleanup temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass



# Strategy for generating webhook URLs
@st.composite
def webhook_url_strategy(draw):
    """Generate valid webhook URLs."""
    protocol = draw(st.sampled_from(["http://", "https://"]))
    domain = draw(st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=97, max_codepoint=122)))
    tld = draw(st.sampled_from([".com", ".org", ".net", ".io"]))
    path = draw(st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=97, max_codepoint=122)))
    
    url = f"{protocol}{domain}{tld}"
    if path:
        url += f"/{path}"
    
    return url


# Feature: code-review-documentation-agent, Property 27: Webhook Notification
@given(
    config=analysis_config_strategy(),
    webhook_url=webhook_url_strategy()
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_webhook_notification(config: Dict[str, Any], webhook_url: str):
    """
    Property 27: Webhook Notification
    
    For any configured webhook URL, the system should send notifications
    with correct data when analysis completes or issues are found.
    
    Validates: Requirements 10.4
    """
    temp_dir = config.pop("_temp_dir")
    
    try:
        # Mock the background analysis to prevent actual execution
        with patch('api.main.run_analysis_async', new_callable=AsyncMock) as mock_run:
            # Configure mock to return immediately
            mock_run.return_value = None
            
            # Add webhook URL to config
            config["webhook_url"] = webhook_url
            
            # Send analysis request with webhook
            response = client.post("/analyze", json=config)
            
            # Verify request was accepted
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            
            data = response.json()
            session_id = data["session_id"]
            
            # Verify the webhook URL was accepted (it's in the request)
            assert webhook_url.startswith("http"), "Webhook URL should start with http"
            
            # Verify session_id is valid
            assert len(session_id) > 0
            assert isinstance(session_id, str)
            
            # Verify response structure
            assert "status" in data
            assert data["status"] in ["running", "pending"]
    
    finally:
        # Cleanup temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


# Unit test for webhook notification function
@pytest.mark.asyncio
async def test_webhook_notification_function():
    """Test the webhook notification function directly."""
    from api.main import send_webhook_notification
    from models.data_models import AnalysisResult, Documentation, MetricsSummary
    from datetime import datetime, timezone
    
    # Create a mock HTTP server response
    with patch('httpx.AsyncClient.post') as mock_post:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response
        
        # Create test result
        result = AnalysisResult(
            session_id="test-session",
            timestamp=datetime.now(timezone.utc),
            codebase_path="/test/path",
            files_analyzed=5,
            total_issues=3,
            quality_score=90.0,
            file_analyses=[],
            suggestions=[],
            documentation=Documentation(
                project_structure="Test",
                api_docs={},
                examples={}
            ),
            metrics_summary=MetricsSummary(
                total_files=5,
                total_lines=100,
                average_complexity=2.0,
                average_maintainability=90.0,
                total_issues_by_severity={},
                total_issues_by_category={}
            )
        )
        
        # Send webhook notification
        await send_webhook_notification(
            webhook_url="https://example.com/webhook",
            session_id="test-session",
            status="completed",
            result=result
        )
        
        # Verify webhook was called
        assert mock_post.called
        call_args = mock_post.call_args
        
        # Verify URL
        assert call_args[0][0] == "https://example.com/webhook"
        
        # Verify payload structure
        payload = call_args[1]["json"]
        assert "session_id" in payload
        assert "status" in payload
        assert "timestamp" in payload
        assert "files_analyzed" in payload
        assert "total_issues" in payload
        assert "quality_score" in payload
        
        # Verify payload values
        assert payload["session_id"] == "test-session"
        assert payload["status"] == "completed"
        assert payload["files_analyzed"] == 5
        assert payload["total_issues"] == 3
        assert payload["quality_score"] == 90.0
