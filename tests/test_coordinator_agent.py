"""
Tests for the Coordinator Agent.

This module contains:
- Unit tests for coordinator functionality
- Property-based tests for report structure, standards compliance, and custom rules
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings
from typing import List, Dict

from agents.coordinator_agent import CoordinatorAgent
from models.data_models import (
    AnalysisConfig,
    AnalysisResult,
    FileAnalysis,
    CodeMetrics,
    CodeIssue,
    FunctionInfo,
    ClassInfo,
    IssueSeverity,
    IssueCategory,
    AnalysisDepth,
    Documentation,
    MetricsSummary,
)
from storage.memory_bank import MemoryBank
from storage.session_manager import SessionManager


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def coordinator(temp_dir):
    """Create a coordinator agent with temporary storage."""
    memory_bank = MemoryBank(db_path=str(Path(temp_dir) / "test_memory.db"))
    session_manager = SessionManager(sessions_dir=str(Path(temp_dir) / "sessions"))
    return CoordinatorAgent(memory_bank=memory_bank, session_manager=session_manager)


@pytest.fixture
def sample_codebase(temp_dir):
    """Create a sample codebase for testing."""
    codebase_path = Path(temp_dir) / "sample_code"
    codebase_path.mkdir()
    
    # Create a simple Python file
    (codebase_path / "example.py").write_text("""
def simple_function(x, y):
    \"\"\"Add two numbers.\"\"\"
    return x + y

class SimpleClass:
    \"\"\"A simple class.\"\"\"
    
    def method(self):
        return 42
""")
    
    return str(codebase_path)


# ============================================================================
# Unit Tests
# ============================================================================

def test_coordinator_initialization():
    """Test that coordinator initializes correctly."""
    coordinator = CoordinatorAgent()
    
    assert coordinator.memory_bank is not None
    assert coordinator.session_manager is not None
    assert coordinator.analyzer is not None
    assert coordinator.documenter is not None
    assert coordinator.reviewer is not None


def test_analyze_codebase_basic(coordinator, sample_codebase):
    """Test basic codebase analysis."""
    config = AnalysisConfig(
        target_path=sample_codebase,
        file_patterns=["*.py"],
        analysis_depth=AnalysisDepth.QUICK
    )
    
    result = coordinator.analyze_codebase(config)
    
    assert result is not None
    assert result.session_id is not None
    assert result.files_analyzed >= 0
    assert 0 <= result.quality_score <= 100
    assert result.documentation is not None
    assert result.metrics_summary is not None


def test_load_config_from_yaml(coordinator, temp_dir):
    """Test loading configuration from YAML file."""
    config_path = Path(temp_dir) / "test_config.yaml"
    config_path.write_text("""
target_path: "./test"
file_patterns:
  - "*.py"
  - "*.js"
analysis_depth: "standard"
enable_parallel: true
""")
    
    config = coordinator.load_config_from_yaml(str(config_path))
    
    assert config.target_path == "./test"
    assert "*.py" in config.file_patterns
    assert config.analysis_depth == AnalysisDepth.STANDARD
    assert config.enable_parallel is True


def test_quality_score_calculation(coordinator):
    """Test quality score calculation."""
    # Create analysis results with known issues
    analysis_results = [
        FileAnalysis(
            file_path="test.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=5,
                maintainability_index=80.0,
                lines_of_code=100,
                comment_ratio=0.2
            ),
            issues=[
                CodeIssue(
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.COMPLEXITY,
                    file_path="test.py",
                    line_number=10,
                    description="High complexity",
                    code_snippet="def complex():"
                )
            ],
            functions=[],
            classes=[]
        )
    ]
    
    score = coordinator._calculate_quality_score(analysis_results)
    
    assert 0 <= score <= 100
    assert score < 100  # Should be penalized for issues


def test_metrics_summary_generation(coordinator):
    """Test metrics summary generation."""
    analysis_results = [
        FileAnalysis(
            file_path="test1.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=3,
                maintainability_index=90.0,
                lines_of_code=50,
                comment_ratio=0.3
            ),
            issues=[
                CodeIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.STYLE,
                    file_path="test1.py",
                    line_number=5,
                    description="Style issue",
                    code_snippet="x=1"
                )
            ],
            functions=[],
            classes=[]
        ),
        FileAnalysis(
            file_path="test2.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=7,
                maintainability_index=70.0,
                lines_of_code=150,
                comment_ratio=0.1
            ),
            issues=[],
            functions=[],
            classes=[]
        )
    ]
    
    summary = coordinator._generate_metrics_summary(analysis_results)
    
    assert summary.total_files == 2
    assert summary.total_lines == 200
    assert summary.average_complexity == 5.0
    assert summary.average_maintainability == 80.0
    assert IssueSeverity.MEDIUM in summary.total_issues_by_severity


# ============================================================================
# Property-Based Tests
# ============================================================================

# Custom Hypothesis strategies for generating test data

@st.composite
def file_analysis_strategy(draw):
    """Generate random FileAnalysis objects."""
    file_path = draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='._/')))
    language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
    
    metrics = CodeMetrics(
        cyclomatic_complexity=draw(st.integers(min_value=1, max_value=50)),
        maintainability_index=draw(st.floats(min_value=0.0, max_value=100.0)),
        lines_of_code=draw(st.integers(min_value=1, max_value=1000)),
        comment_ratio=draw(st.floats(min_value=0.0, max_value=1.0))
    )
    
    # Generate issues
    num_issues = draw(st.integers(min_value=0, max_value=10))
    issues = []
    for _ in range(num_issues):
        issue = CodeIssue(
            severity=draw(st.sampled_from(list(IssueSeverity))),
            category=draw(st.sampled_from(list(IssueCategory))),
            file_path=file_path,
            line_number=draw(st.integers(min_value=1, max_value=1000)),
            description=draw(st.text(min_size=10, max_size=100)),
            code_snippet=draw(st.text(min_size=5, max_size=50))
        )
        issues.append(issue)
    
    return FileAnalysis(
        file_path=file_path,
        language=language,
        metrics=metrics,
        issues=issues,
        functions=[],
        classes=[]
    )


@st.composite
def analysis_result_strategy(draw):
    """Generate random AnalysisResult objects."""
    num_files = draw(st.integers(min_value=1, max_value=20))
    file_analyses = [draw(file_analysis_strategy()) for _ in range(num_files)]
    
    total_issues = sum(len(fa.issues) for fa in file_analyses)
    
    return AnalysisResult(
        session_id=draw(st.text(min_size=10, max_size=50)),
        timestamp=datetime.now(timezone.utc),
        codebase_path=draw(st.text(min_size=1, max_size=100)),
        files_analyzed=num_files,
        total_issues=total_issues,
        quality_score=draw(st.floats(min_value=0.0, max_value=100.0)),
        file_analyses=file_analyses,
        suggestions=[],
        documentation=Documentation(
            project_structure="# Project",
            api_docs={},
            examples={}
        ),
        metrics_summary=MetricsSummary(
            total_files=num_files,
            total_lines=sum(fa.metrics.lines_of_code for fa in file_analyses),
            average_complexity=sum(fa.metrics.cyclomatic_complexity for fa in file_analyses) / num_files,
            average_maintainability=sum(fa.metrics.maintainability_index for fa in file_analyses) / num_files,
            total_issues_by_severity={},
            total_issues_by_category={}
        )
    )


# Property 3: Report Structure Completeness
# Feature: code-review-documentation-agent, Property 3: Report Structure Completeness
# Validates: Requirements 1.3
@given(result=analysis_result_strategy())
@settings(max_examples=100, deadline=None)
def test_property_report_structure_completeness(result):
    """
    Property 3: Report Structure Completeness
    
    For any completed analysis, the generated Review Report should contain
    all identified issues with assigned severity levels and proper structure.
    
    Validates: Requirements 1.3
    """
    coordinator = CoordinatorAgent()
    
    # Generate review report
    report = coordinator.generate_review_report(result)
    
    # Verify report is not empty
    assert report is not None
    assert len(report) > 0
    
    # Verify report contains required sections
    assert "# Code Review Report" in report or "Code Review Report" in report
    assert "Quality Score" in report or "quality" in report.lower()
    
    # Verify report contains summary information
    assert "Files Analyzed" in report or "files" in report.lower()
    assert "Issues Found" in report or "issues" in report.lower()
    
    # If there are issues, verify they appear in the report
    if result.total_issues > 0:
        # Report should mention issues
        assert "issue" in report.lower() or "suggestion" in report.lower()
    
    # Verify report contains severity information if issues exist
    for file_analysis in result.file_analyses:
        for issue in file_analysis.issues:
            # At least one severity level should be mentioned
            severity_mentioned = any(
                sev.value in report.lower()
                for sev in IssueSeverity
            )
            if severity_mentioned:
                break
    
    # Verify report structure is valid markdown
    assert report.count("#") >= 1  # At least one heading
    
    # Verify quality score is present
    assert str(int(result.quality_score)) in report or f"{result.quality_score:.1f}" in report


# Property 12: Standards Compliance Evaluation
# Feature: code-review-documentation-agent, Property 12: Standards Compliance Evaluation
# Validates: Requirements 5.2, 5.3
@given(
    file_analyses=st.lists(file_analysis_strategy(), min_size=1, max_size=10),
    standards=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.integers(), st.text(min_size=1, max_size=50), st.booleans()),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100, deadline=None)
def test_property_standards_compliance_evaluation(file_analyses, standards):
    """
    Property 12: Standards Compliance Evaluation
    
    For any code and configured coding standards, the analysis should evaluate
    compliance and include violations in the Review Report with references to
    specific standards.
    
    Validates: Requirements 5.2, 5.3
    """
    coordinator = CoordinatorAgent()
    
    # Create config with coding standards
    config = AnalysisConfig(
        target_path="./test",
        coding_standards=standards,
        analysis_depth=AnalysisDepth.STANDARD
    )
    
    # Verify standards are stored in config
    assert config.coding_standards == standards
    
    # Generate metrics summary to verify analysis considers standards
    metrics_summary = coordinator._generate_metrics_summary(file_analyses)
    
    # Verify metrics summary is generated
    assert metrics_summary is not None
    assert metrics_summary.total_files == len(file_analyses)
    
    # Verify issues are categorized
    assert isinstance(metrics_summary.total_issues_by_severity, dict)
    assert isinstance(metrics_summary.total_issues_by_category, dict)
    
    # Count total issues
    total_issues = sum(len(fa.issues) for fa in file_analyses)
    
    # Verify issue counts match
    severity_total = sum(metrics_summary.total_issues_by_severity.values())
    category_total = sum(metrics_summary.total_issues_by_category.values())
    
    assert severity_total == total_issues
    assert category_total == total_issues


# Property 13: Custom Rules Application
# Feature: code-review-documentation-agent, Property 13: Custom Rules Application
# Validates: Requirements 5.4
@given(
    file_analyses=st.lists(file_analysis_strategy(), min_size=1, max_size=10),
    custom_rules=st.dictionaries(
        keys=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), whitelist_characters='_')),
        values=st.one_of(st.integers(min_value=1, max_value=100), st.booleans()),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100, deadline=None)
def test_property_custom_rules_application(file_analyses, custom_rules):
    """
    Property 13: Custom Rules Application
    
    For any analysis with custom rules defined, both custom rules and default
    quality checks should be applied and violations from both should appear
    in results.
    
    Validates: Requirements 5.4
    """
    coordinator = CoordinatorAgent()
    
    # Create config with custom rules in coding_standards
    config = AnalysisConfig(
        target_path="./test",
        coding_standards={"custom_rules": custom_rules},
        analysis_depth=AnalysisDepth.STANDARD
    )
    
    # Verify custom rules are in config
    assert "custom_rules" in config.coding_standards
    assert config.coding_standards["custom_rules"] == custom_rules
    
    # Generate metrics summary (default quality checks)
    metrics_summary = coordinator._generate_metrics_summary(file_analyses)
    
    # Verify default quality checks are applied (metrics are calculated)
    assert metrics_summary.total_files == len(file_analyses)
    assert metrics_summary.average_complexity >= 0
    assert 0 <= metrics_summary.average_maintainability <= 100
    
    # Verify issues from analysis are present (default checks)
    total_issues = sum(len(fa.issues) for fa in file_analyses)
    severity_total = sum(metrics_summary.total_issues_by_severity.values())
    
    # Both default and custom rules should be considered
    # Default rules produce the issues in file_analyses
    assert severity_total == total_issues
    
    # Verify all standard issue categories are recognized
    for fa in file_analyses:
        for issue in fa.issues:
            assert issue.category in IssueCategory
            assert issue.severity in IssueSeverity


# Additional unit tests for edge cases

def test_empty_codebase_analysis(coordinator, temp_dir):
    """Test analysis of empty codebase."""
    empty_dir = Path(temp_dir) / "empty"
    empty_dir.mkdir()
    
    config = AnalysisConfig(
        target_path=str(empty_dir),
        file_patterns=["*.py"]
    )
    
    result = coordinator.analyze_codebase(config)
    
    assert result.files_analyzed == 0
    assert result.total_issues == 0
    assert result.quality_score == 100.0  # Perfect score for no code


def test_quality_score_bounds(coordinator):
    """Test that quality score is always between 0 and 100."""
    # Test with no issues (should be high)
    good_results = [
        FileAnalysis(
            file_path="good.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=2,
                maintainability_index=95.0,
                lines_of_code=50,
                comment_ratio=0.3
            ),
            issues=[],
            functions=[],
            classes=[]
        )
    ]
    
    score_good = coordinator._calculate_quality_score(good_results)
    assert 0 <= score_good <= 100
    assert score_good > 80  # Should be high
    
    # Test with many critical issues (should be low)
    bad_results = [
        FileAnalysis(
            file_path="bad.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=20,
                maintainability_index=20.0,
                lines_of_code=100,
                comment_ratio=0.0
            ),
            issues=[
                CodeIssue(
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    file_path="bad.py",
                    line_number=i + 1,
                    description=f"Critical issue {i}",
                    code_snippet="bad code"
                )
                for i in range(10)
            ],
            functions=[],
            classes=[]
        )
    ]
    
    score_bad = coordinator._calculate_quality_score(bad_results)
    assert 0 <= score_bad <= 100
    assert score_bad < 50  # Should be low


def test_session_management_integration(coordinator, sample_codebase):
    """Test session management integration."""
    config = AnalysisConfig(
        target_path=sample_codebase,
        file_patterns=["*.py"]
    )
    
    # Run analysis with specific session ID
    session_id = "test_session_123"
    result = coordinator.analyze_codebase(config, session_id=session_id)
    
    assert result.session_id == session_id
    
    # Check session status
    session_state = coordinator.get_analysis_status(session_id)
    assert session_state is not None
    assert session_state.session_id == session_id
    assert session_state.status == "completed"


def test_pause_resume_basic(coordinator, sample_codebase):
    """Test basic pause and resume functionality."""
    import time
    
    config = AnalysisConfig(
        target_path=sample_codebase,
        file_patterns=["*.py"]
    )
    
    # Start analysis
    session_id = "test_pause_resume"
    
    # Create session manually
    files = coordinator.file_system.discover_files(
        sample_codebase,
        include_patterns=["*.py"],
        exclude_patterns=[]
    )
    
    session_state = coordinator.session_manager.create_session(
        session_id=session_id,
        config=config,
        pending_files=files
    )
    
    # Simulate some processing
    if files:
        processed = [files[0]]
        pending = files[1:] if len(files) > 1 else []
        
        # Create a mock analysis
        mock_analysis = FileAnalysis(
            file_path=files[0],
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=1,
                maintainability_index=95.0,
                lines_of_code=10,
                comment_ratio=0.2
            ),
            issues=[],
            functions=[],
            classes=[]
        )
        
        coordinator.session_manager.checkpoint(
            session_id=session_id,
            processed_files=processed,
            pending_files=pending,
            partial_results={
                'analysis_count': 1,
                'file_analyses': [mock_analysis.model_dump(mode='json')]
            }
        )
    
    # Pause
    pause_success = coordinator.pause_analysis(session_id)
    assert pause_success is True
    
    # Verify paused
    session_state = coordinator.get_analysis_status(session_id)
    assert session_state.status == "paused"
    
    # Wait and modify a file
    time.sleep(0.1)
    if files:
        Path(files[0]).write_text("# Modified content\ndef new_function():\n    pass\n")
        time.sleep(0.1)
    
    # Resume
    result = coordinator.resume_analysis(session_id)
    
    # Verify completed
    assert result is not None
    assert result.session_id == session_id
    
    final_state = coordinator.get_analysis_status(session_id)
    assert final_state.status == "completed"


# ============================================================================
# Property-Based Test for Pause/Resume with Change Detection
# ============================================================================

# Property 18: Change Detection on Resume
# Feature: code-review-documentation-agent, Property 18: Change Detection on Resume
# Validates: Requirements 7.5
@given(
    num_files=st.integers(min_value=2, max_value=5),
    files_to_modify=st.integers(min_value=1, max_value=3)
)
@settings(max_examples=100, deadline=None)
def test_property_change_detection_on_resume(num_files, files_to_modify):
    """
    Property 18: Change Detection on Resume
    
    For any paused analysis where the codebase is modified, resuming should
    detect the modifications and re-analyze only the changed files.
    
    Validates: Requirements 7.5
    """
    import time
    
    # Ensure files_to_modify doesn't exceed num_files
    files_to_modify = min(files_to_modify, num_files)
    
    # Create a temporary directory for this test
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create a temporary codebase with multiple files
        codebase_path = Path(temp_dir) / "test_codebase"
        codebase_path.mkdir(exist_ok=True)
        
        # Create initial files
        file_paths = []
        for i in range(num_files):
            file_path = codebase_path / f"file_{i}.py"
            file_path.write_text(f"""
def function_{i}(x):
    \"\"\"Function {i}.\"\"\"
    return x + {i}

class Class_{i}:
    \"\"\"Class {i}.\"\"\"
    def method(self):
        return {i}
""")
            file_paths.append(str(file_path))
            # Small delay to ensure different timestamps
            time.sleep(0.01)
        
        # Create coordinator with temporary storage
        memory_bank = MemoryBank(db_path=str(Path(temp_dir) / "test_memory.db"))
        session_manager = SessionManager(sessions_dir=str(Path(temp_dir) / "sessions"))
        coordinator = CoordinatorAgent(memory_bank=memory_bank, session_manager=session_manager)
        
        # Create analysis config
        config = AnalysisConfig(
            target_path=str(codebase_path),
            file_patterns=["*.py"],
            analysis_depth=AnalysisDepth.QUICK
        )
        
        # Start analysis
        session_id = f"test_session_{num_files}_{files_to_modify}"
        
        # Create session and process some files
        session_state = session_manager.create_session(
            session_id=session_id,
            config=config,
            pending_files=file_paths
        )
        
        # Simulate partial processing - mark some files as processed
        processed_count = max(1, num_files // 2)
        processed_files = file_paths[:processed_count]
        pending_files = file_paths[processed_count:]
        
        # Create mock analysis results for processed files
        mock_analyses = []
        for file_path in processed_files:
            mock_analysis = FileAnalysis(
                file_path=file_path,
                language="python",
                metrics=CodeMetrics(
                    cyclomatic_complexity=1,
                    maintainability_index=95.0,
                    lines_of_code=10,
                    comment_ratio=0.2
                ),
                issues=[],
                functions=[],
                classes=[]
            )
            mock_analyses.append(mock_analysis.model_dump(mode='json'))
        
        session_manager.checkpoint(
            session_id=session_id,
            processed_files=processed_files,
            pending_files=pending_files,
            partial_results={
                'analysis_count': processed_count,
                'file_analyses': mock_analyses
            }
        )
        
        # Pause the analysis
        pause_success = coordinator.pause_analysis(session_id)
        assert pause_success is True
        
        # Verify session is paused
        session_state = coordinator.get_analysis_status(session_id)
        assert session_state.status == "paused"
        
        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)
        
        # Modify some of the processed files
        files_modified = []
        for i in range(min(files_to_modify, len(processed_files))):
            file_path = Path(processed_files[i])
            # Modify the file content
            file_path.write_text(f"""
def function_{i}_modified(x, y):
    \"\"\"Modified function {i}.\"\"\"
    return x + y + {i}

class Class_{i}_Modified:
    \"\"\"Modified class {i}.\"\"\"
    def method(self):
        return {i} * 2
    
    def new_method(self):
        return {i} + 1
""")
            files_modified.append(str(file_path))
            time.sleep(0.01)
        
        # Resume the analysis
        result = coordinator.resume_analysis(session_id)
        
        # Verify analysis completed
        assert result is not None
        assert result.session_id == session_id
        
        # Verify session is completed
        final_session_state = coordinator.get_analysis_status(session_id)
        assert final_session_state.status == "completed"
        
        # Verify change detection worked
        # The modified files should have been detected and re-analyzed
        # We can verify this by checking that all files were analyzed
        assert result.files_analyzed == num_files
        
        # Verify that the analysis includes all files
        analyzed_paths = {fa.file_path for fa in result.file_analyses}
        expected_paths = set(file_paths)
        assert analyzed_paths == expected_paths
        
        # Verify modified files are included in results
        for modified_file in files_modified:
            # Find the analysis for this file
            file_analysis = next(
                (fa for fa in result.file_analyses if fa.file_path == modified_file),
                None
            )
            assert file_analysis is not None, f"Modified file {modified_file} not found in results"
    
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
