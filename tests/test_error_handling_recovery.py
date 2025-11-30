"""
Tests for error handling and recovery functionality.

This module tests:
- Graceful degradation for unparseable files
- Retry logic with exponential backoff
- Input validation with clear error messages
- Partial report generation when agents fail
- Crash recovery using checkpoints
"""

import pytest
import tempfile
import time
from pathlib import Path
from typing import List, Tuple
from unittest.mock import Mock, patch, MagicMock

from tools.error_handling import (
    retry_with_backoff,
    validate_path,
    validate_file_patterns,
    validate_session_id,
    safe_file_operation,
    handle_parse_error,
    classify_error,
    create_error_summary,
    GracefulDegradation,
    create_partial_report_on_failure,
    ValidationError,
    TransientError,
    PermanentError,
    PartialFailureError,
)
from models.data_models import AnalysisConfig, AnalysisDepth
from agents.coordinator_agent import CoordinatorAgent
from agents.analyzer_agent import AnalyzerAgent


class TestRetryLogic:
    """Test retry logic with exponential backoff."""
    
    def test_retry_succeeds_on_first_attempt(self):
        """Test that successful operations don't retry."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def successful_operation():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_operation()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_succeeds_after_transient_failures(self):
        """Test that transient failures trigger retry and eventually succeed."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TransientError("Temporary failure")
            return "success"
        
        result = flaky_operation()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_fails_after_max_retries(self):
        """Test that operation fails after exhausting retries."""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise TransientError("Always fails")
        
        with pytest.raises(TransientError):
            always_fails()
        
        assert call_count == 3  # Initial attempt + 2 retries
    
    def test_retry_respects_exponential_backoff(self):
        """Test that retry delays increase exponentially."""
        call_times = []
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1, backoff_factor=2.0)
        def timed_operation():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise TransientError("Retry me")
            return "success"
        
        timed_operation()
        
        # Check that delays increase (with some tolerance for timing)
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]
        assert delay2 > delay1  # Second delay should be longer
    
    def test_retry_does_not_retry_permanent_errors(self):
        """Test that permanent errors fail immediately without retry."""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def permanent_failure():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError):
            permanent_failure()
        
        assert call_count == 1  # Should not retry


class TestInputValidation:
    """Test input validation with clear error messages."""
    
    def test_validate_path_success(self):
        """Test successful path validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = validate_path(tmpdir, must_exist=True, must_be_dir=True)
            assert path.exists()
            assert path.is_dir()
    
    def test_validate_path_empty_fails(self):
        """Test that empty path raises ValidationError."""
        with pytest.raises(ValidationError, match="Path cannot be empty"):
            validate_path("")
        
        with pytest.raises(ValidationError, match="Path cannot be empty"):
            validate_path("   ")
    
    def test_validate_path_nonexistent_fails(self):
        """Test that nonexistent path fails when must_exist=True."""
        with pytest.raises(ValidationError, match="Path does not exist"):
            validate_path("/nonexistent/path/12345", must_exist=True)
    
    def test_validate_path_file_not_dir_fails(self):
        """Test that file fails when must_be_dir=True."""
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfile_path = tmpfile.name
        
        try:
            with pytest.raises(ValidationError, match="not a directory"):
                validate_path(tmpfile_path, must_exist=True, must_be_dir=True)
        finally:
            try:
                Path(tmpfile_path).unlink()
            except PermissionError:
                pass  # Windows may still have file locked
    
    def test_validate_file_patterns_success(self):
        """Test successful file pattern validation."""
        patterns = validate_file_patterns(["*.py", "*.js", "test_*.py"])
        assert len(patterns) == 3
        assert "*.py" in patterns
    
    def test_validate_file_patterns_empty_fails(self):
        """Test that empty patterns list fails."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            validate_file_patterns([])
    
    def test_validate_file_patterns_empty_string_fails(self):
        """Test that empty pattern string fails."""
        with pytest.raises(ValidationError, match="Pattern cannot be empty"):
            validate_file_patterns(["*.py", "", "*.js"])
    
    def test_validate_session_id_success(self):
        """Test successful session ID validation."""
        session_id = validate_session_id("session-123_abc")
        assert session_id == "session-123_abc"
    
    def test_validate_session_id_empty_fails(self):
        """Test that empty session ID fails."""
        with pytest.raises(ValidationError, match="Session ID cannot be empty"):
            validate_session_id("")
    
    def test_validate_session_id_invalid_chars_fails(self):
        """Test that session ID with invalid characters fails."""
        with pytest.raises(ValidationError, match="invalid characters"):
            validate_session_id("session@123")
    
    def test_analysis_config_validation(self):
        """Test AnalysisConfig validation."""
        # Valid config
        config = AnalysisConfig(
            target_path="/valid/path",
            file_patterns=["*.py"],
            analysis_depth=AnalysisDepth.STANDARD
        )
        assert config.target_path == "/valid/path"
        
        # Empty target path
        with pytest.raises(ValueError, match="target_path cannot be empty"):
            AnalysisConfig(target_path="", file_patterns=["*.py"])
        
        # Empty file patterns
        with pytest.raises(ValueError, match="file_patterns cannot be empty"):
            AnalysisConfig(target_path="/path", file_patterns=[])
        
        # Invalid file pattern
        with pytest.raises(ValueError, match="Invalid file pattern"):
            AnalysisConfig(target_path="/path", file_patterns=["!!!"])


class TestGracefulDegradation:
    """Test graceful degradation for partial failures."""
    
    def test_graceful_degradation_all_succeed(self):
        """Test that all successful operations are collected."""
        degradation = GracefulDegradation("test operation")
        
        for i in range(5):
            result = degradation.process_item(f"item_{i}", lambda i=i: i * 2)
            assert result == i * 2
        
        successful, failed = degradation.get_results()
        assert len(successful) == 5
        assert len(failed) == 0
        assert not degradation.has_failures()
    
    def test_graceful_degradation_partial_failures(self):
        """Test that partial failures are handled gracefully."""
        degradation = GracefulDegradation("test operation", continue_on_error=True)
        
        for i in range(5):
            def operation(i=i):
                if i % 2 == 0:
                    raise ValueError(f"Error on item {i}")
                return i * 2
            
            degradation.process_item(f"item_{i}", operation)
        
        successful, failed = degradation.get_results()
        assert len(successful) == 2  # Items 1 and 3
        assert len(failed) == 3  # Items 0, 2, and 4
        assert degradation.has_failures()
    
    def test_graceful_degradation_stops_on_error_when_configured(self):
        """Test that degradation stops on first error when continue_on_error=False."""
        degradation = GracefulDegradation("test operation", continue_on_error=False)
        
        with pytest.raises(ValueError):
            for i in range(5):
                def operation(i=i):
                    if i == 2:
                        raise ValueError(f"Error on item {i}")
                    return i * 2
                
                degradation.process_item(f"item_{i}", operation)
        
        successful, failed = degradation.get_results()
        assert len(successful) == 2  # Items 0 and 1
        assert len(failed) == 1  # Item 2
    
    def test_graceful_degradation_raise_if_all_failed(self):
        """Test that exception is raised if all items fail."""
        degradation = GracefulDegradation("test operation", continue_on_error=True)
        
        for i in range(3):
            degradation.process_item(f"item_{i}", lambda: (_ for _ in ()).throw(ValueError("Fail")))
        
        with pytest.raises(PartialFailureError, match="All items failed"):
            degradation.raise_if_all_failed()


class TestErrorClassification:
    """Test error classification and handling."""
    
    def test_classify_transient_errors(self):
        """Test that transient errors are classified correctly."""
        assert classify_error(TransientError()) == 'transient'
        assert classify_error(IOError()) == 'transient'
        assert classify_error(ConnectionError()) == 'transient'
        assert classify_error(TimeoutError()) == 'transient'
    
    def test_classify_permanent_errors(self):
        """Test that permanent errors are classified correctly."""
        assert classify_error(ValidationError("test")) == 'permanent'
        assert classify_error(ValueError()) == 'permanent'
        assert classify_error(TypeError()) == 'permanent'
        assert classify_error(SyntaxError()) == 'permanent'
    
    def test_classify_unknown_errors(self):
        """Test that unknown errors are classified as unknown."""
        assert classify_error(RuntimeError()) == 'unknown'
    
    def test_create_error_summary(self):
        """Test error summary generation."""
        errors = [
            ("file1.py", ValueError("Invalid value")),
            ("file2.py", ValueError("Another error")),
            ("file3.py", OSError("File not found")),  # IOError is OSError in Python 3
        ]
        
        summary = create_error_summary(errors)
        assert "3 error(s)" in summary
        assert "ValueError" in summary
        assert "OSError" in summary
        assert "file1.py" in summary


class TestPartialReportGeneration:
    """Test partial report generation when agents fail."""
    
    def test_create_partial_report_on_failure(self):
        """Test that partial reports are created correctly."""
        successful_analyses = [
            {"file_path": "file1.py", "issues": []},
            {"file_path": "file2.py", "issues": []},
        ]
        
        failed_files = [
            ("file3.py", ValueError("Parse error")),
            ("file4.py", SyntaxError("Syntax error")),
        ]
        
        error = PartialFailureError("Some files failed", successful_analyses, failed_files)
        
        report = create_partial_report_on_failure(
            session_id="test-session",
            successful_analyses=successful_analyses,
            failed_files=failed_files,
            error=error
        )
        
        assert report['session_id'] == "test-session"
        assert report['status'] == "partial_failure"
        assert report['successful_analyses'] == 2
        assert report['failed_files'] == 2
        assert len(report['analyses']) == 2
        assert len(report['errors']) == 2
        assert report['errors'][0]['file'] == "file3.py"
        assert report['errors'][1]['file'] == "file4.py"


class TestAnalyzerGracefulDegradation:
    """Test analyzer agent's graceful degradation for unparseable files."""
    
    def test_analyzer_handles_unparseable_file(self):
        """Test that analyzer handles unparseable files gracefully."""
        analyzer = AnalyzerAgent()
        
        # Invalid Python code
        invalid_code = "def broken_function(\n    # Missing closing parenthesis"
        
        result = analyzer.analyze_file("test.py", invalid_code)
        
        # Should return partial analysis with syntax error issue
        assert result is not None
        assert result.file_path == "test.py"
        assert len(result.issues) > 0
        assert any("syntax" in issue.description.lower() for issue in result.issues)
    
    def test_analyzer_handles_unsupported_language(self):
        """Test that analyzer handles unsupported file types gracefully."""
        analyzer = AnalyzerAgent()
        
        result = analyzer.analyze_file("test.unknown", "some code")
        
        # Should return None for unsupported languages
        assert result is None
    
    def test_analyzer_parallel_continues_on_failures(self):
        """Test that parallel analysis continues when some files fail."""
        analyzer = AnalyzerAgent()
        
        files = [
            ("valid1.py", "def valid_function():\n    pass"),
            ("invalid.py", "def broken(\n"),  # Syntax error
            ("valid2.py", "def another_valid():\n    return True"),
        ]
        
        results = analyzer.analyze_files_parallel(files)
        
        # Should have results for valid files
        assert len(results) >= 2  # At least the 2 valid files
        file_paths = [r.file_path for r in results]
        assert "valid1.py" in file_paths
        assert "valid2.py" in file_paths


class TestCoordinatorErrorRecovery:
    """Test coordinator agent's error recovery and checkpoint functionality."""
    
    @patch('agents.coordinator_agent.FileSystemTool')
    @patch('agents.coordinator_agent.MemoryBank')
    @patch('agents.coordinator_agent.SessionManager')
    def test_coordinator_handles_file_read_failures(
        self,
        mock_session_manager,
        mock_memory_bank,
        mock_file_system
    ):
        """Test that coordinator handles file read failures gracefully."""
        # Setup mocks
        mock_session_manager_instance = Mock()
        mock_session_manager.return_value = mock_session_manager_instance
        
        mock_memory_bank_instance = Mock()
        mock_memory_bank_instance.retrieve_patterns.return_value = []
        mock_memory_bank.return_value = mock_memory_bank_instance
        
        # Create coordinator
        coordinator = CoordinatorAgent(
            memory_bank=mock_memory_bank_instance,
            session_manager=mock_session_manager_instance
        )
        
        # Test file reading with failures
        files = ["file1.py", "file2.py", "file3.py"]
        
        # Mock file system to fail on file2.py
        def mock_read_file(path):
            if path == "file2.py":
                raise IOError("File not found")
            return f"# Content of {path}"
        
        coordinator.file_system.read_file = mock_read_file
        
        successful, failed = coordinator._read_files_with_graceful_degradation(files)
        
        assert len(successful) == 2
        assert len(failed) == 1
        assert failed[0][0] == "file2.py"
    
    def test_safe_file_operation_returns_default_on_error(self):
        """Test that safe_file_operation returns default value on error."""
        def failing_operation():
            raise FileNotFoundError("File not found")
        
        result = safe_file_operation(
            operation=failing_operation,
            file_path="test.txt",
            operation_name="read",
            default_value="default"
        )
        
        assert result == "default"
    
    def test_safe_file_operation_returns_result_on_success(self):
        """Test that safe_file_operation returns result on success."""
        def successful_operation():
            return "success"
        
        result = safe_file_operation(
            operation=successful_operation,
            file_path="test.txt",
            operation_name="read",
            default_value="default"
        )
        
        assert result == "success"


class TestHandleParseError:
    """Test parse error handling."""
    
    def test_handle_parse_error_logs_warning(self, caplog):
        """Test that parse errors are logged appropriately."""
        import logging
        caplog.set_level(logging.WARNING)
        
        handle_parse_error("test.py", SyntaxError("Invalid syntax"))
        
        assert "Failed to parse test.py" in caplog.text
        assert "Invalid syntax" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
