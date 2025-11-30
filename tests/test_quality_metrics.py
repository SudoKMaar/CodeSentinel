"""
Tests for Quality Metrics and Evaluation.

This module contains:
- Unit tests for quality metrics calculation
- Property-based tests for quality score calculation and trend tracking
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, settings, assume
from typing import List

from tools.quality_metrics import QualityMetricsCalculator
from models.data_models import (
    AnalysisResult,
    FileAnalysis,
    CodeMetrics,
    CodeIssue,
    IssueSeverity,
    IssueCategory,
    Documentation,
    MetricsSummary,
    QualityTrend,
    QualityComparison,
    EvaluationStatistics,
    SuggestionImpact,
)


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
def quality_calculator(temp_dir):
    """Create a quality metrics calculator with temporary storage."""
    return QualityMetricsCalculator(storage_dir=str(Path(temp_dir) / "quality_metrics"))


# ============================================================================
# Custom Hypothesis Strategies
# ============================================================================

@st.composite
def code_metrics_strategy(draw):
    """Generate random CodeMetrics objects."""
    return CodeMetrics(
        cyclomatic_complexity=draw(st.integers(min_value=1, max_value=50)),
        maintainability_index=draw(st.floats(min_value=0.0, max_value=100.0)),
        lines_of_code=draw(st.integers(min_value=1, max_value=1000)),
        comment_ratio=draw(st.floats(min_value=0.0, max_value=1.0))
    )


@st.composite
def code_issue_strategy(draw, file_path="test.py"):
    """Generate random CodeIssue objects."""
    return CodeIssue(
        severity=draw(st.sampled_from(list(IssueSeverity))),
        category=draw(st.sampled_from(list(IssueCategory))),
        file_path=file_path,
        line_number=draw(st.integers(min_value=1, max_value=1000)),
        description=draw(st.text(min_size=10, max_size=100)),
        code_snippet=draw(st.text(min_size=5, max_size=50))
    )


@st.composite
def file_analysis_strategy(draw):
    """Generate random FileAnalysis objects."""
    file_path = draw(st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='._/')
    ))
    language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
    
    metrics = draw(code_metrics_strategy())
    
    # Generate issues
    num_issues = draw(st.integers(min_value=0, max_value=3))
    issues = [draw(code_issue_strategy(file_path)) for _ in range(num_issues)]
    
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
    num_files = draw(st.integers(min_value=1, max_value=5))
    file_analyses = [draw(file_analysis_strategy()) for _ in range(num_files)]
    
    total_issues = sum(len(fa.issues) for fa in file_analyses)
    
    # Calculate quality score (will be validated by property test)
    quality_score = draw(st.floats(min_value=0.0, max_value=100.0))
    
    return AnalysisResult(
        session_id=draw(st.text(min_size=10, max_size=50)),
        timestamp=datetime.now(timezone.utc),
        codebase_path=draw(st.text(min_size=1, max_size=100)),
        files_analyzed=num_files,
        total_issues=total_issues,
        quality_score=quality_score,
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


# ============================================================================
# Unit Tests
# ============================================================================

def test_quality_calculator_initialization(quality_calculator):
    """Test that quality calculator initializes correctly."""
    assert quality_calculator is not None
    assert quality_calculator.storage_dir.exists()


def test_calculate_quality_score_empty(quality_calculator):
    """Test quality score calculation with no files."""
    score = quality_calculator.calculate_quality_score([])
    assert score == 100.0


def test_calculate_quality_score_perfect(quality_calculator):
    """Test quality score calculation with perfect code."""
    analysis_results = [
        FileAnalysis(
            file_path="perfect.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=2,
                maintainability_index=100.0,
                lines_of_code=50,
                comment_ratio=0.3
            ),
            issues=[],
            functions=[],
            classes=[]
        )
    ]
    
    score = quality_calculator.calculate_quality_score(analysis_results)
    assert 90 <= score <= 100  # Should be very high


def test_calculate_quality_score_with_issues(quality_calculator):
    """Test quality score calculation with issues."""
    analysis_results = [
        FileAnalysis(
            file_path="bad.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=20,
                maintainability_index=40.0,
                lines_of_code=200,
                comment_ratio=0.0
            ),
            issues=[
                CodeIssue(
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    file_path="bad.py",
                    line_number=10,
                    description="Critical security issue",
                    code_snippet="bad code"
                ),
                CodeIssue(
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.COMPLEXITY,
                    file_path="bad.py",
                    line_number=20,
                    description="High complexity",
                    code_snippet="complex code"
                )
            ],
            functions=[],
            classes=[]
        )
    ]
    
    score = quality_calculator.calculate_quality_score(analysis_results)
    assert 0 <= score < 70  # Should be low due to issues and poor metrics


def test_track_quality_trend(quality_calculator):
    """Test tracking quality trends."""
    project_id = "test_project"
    
    result = AnalysisResult(
        session_id="session1",
        timestamp=datetime.now(timezone.utc),
        codebase_path="./test",
        files_analyzed=5,
        total_issues=10,
        quality_score=75.0,
        file_analyses=[],
        suggestions=[],
        documentation=Documentation(
            project_structure="# Project",
            api_docs={},
            examples={}
        ),
        metrics_summary=MetricsSummary(
            total_files=5,
            total_lines=500,
            average_complexity=5.0,
            average_maintainability=75.0,
            total_issues_by_severity={},
            total_issues_by_category={}
        )
    )
    
    trend = quality_calculator.track_quality_trend(project_id, result)
    
    assert trend is not None
    assert trend.quality_score == 75.0
    assert trend.total_issues == 10
    assert trend.files_analyzed == 5


def test_get_quality_trends(quality_calculator):
    """Test retrieving quality trends."""
    project_id = "test_project_2"
    
    # Track multiple trends
    for i in range(3):
        result = AnalysisResult(
            session_id=f"session{i}",
            timestamp=datetime.now(timezone.utc) + timedelta(days=i),
            codebase_path="./test",
            files_analyzed=5,
            total_issues=10 - i,
            quality_score=70.0 + i * 5,
            file_analyses=[],
            suggestions=[],
            documentation=Documentation(
                project_structure="# Project",
                api_docs={},
                examples={}
            ),
            metrics_summary=MetricsSummary(
                total_files=5,
                total_lines=500,
                average_complexity=5.0,
                average_maintainability=75.0,
                total_issues_by_severity={},
                total_issues_by_category={}
            )
        )
        quality_calculator.track_quality_trend(project_id, result)
    
    trends = quality_calculator.get_quality_trends(project_id)
    
    assert len(trends) == 3
    assert trends[0].quality_score == 70.0
    assert trends[2].quality_score == 80.0


def test_generate_comparison(quality_calculator):
    """Test generating comparison metrics."""
    project_id = "test_project_3"
    
    # Track first analysis
    result1 = AnalysisResult(
        session_id="session1",
        timestamp=datetime.now(timezone.utc),
        codebase_path="./test",
        files_analyzed=5,
        total_issues=15,
        quality_score=60.0,
        file_analyses=[
            FileAnalysis(
                file_path="test.py",
                language="python",
                metrics=CodeMetrics(
                    cyclomatic_complexity=10,
                    maintainability_index=60.0,
                    lines_of_code=100,
                    comment_ratio=0.1
                ),
                issues=[
                    CodeIssue(
                        severity=IssueSeverity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        file_path="test.py",
                        line_number=10,
                        description="Critical issue",
                        code_snippet="bad"
                    )
                ],
                functions=[],
                classes=[]
            )
        ],
        suggestions=[],
        documentation=Documentation(
            project_structure="# Project",
            api_docs={},
            examples={}
        ),
        metrics_summary=MetricsSummary(
            total_files=5,
            total_lines=500,
            average_complexity=10.0,
            average_maintainability=60.0,
            total_issues_by_severity={},
            total_issues_by_category={}
        )
    )
    quality_calculator.track_quality_trend(project_id, result1)
    
    # Track second analysis (improved)
    result2 = AnalysisResult(
        session_id="session2",
        timestamp=datetime.now(timezone.utc) + timedelta(days=1),
        codebase_path="./test",
        files_analyzed=5,
        total_issues=8,
        quality_score=75.0,
        file_analyses=[
            FileAnalysis(
                file_path="test.py",
                language="python",
                metrics=CodeMetrics(
                    cyclomatic_complexity=8,
                    maintainability_index=75.0,
                    lines_of_code=100,
                    comment_ratio=0.2
                ),
                issues=[],
                functions=[],
                classes=[]
            )
        ],
        suggestions=[],
        documentation=Documentation(
            project_structure="# Project",
            api_docs={},
            examples={}
        ),
        metrics_summary=MetricsSummary(
            total_files=5,
            total_lines=500,
            average_complexity=8.0,
            average_maintainability=75.0,
            total_issues_by_severity={},
            total_issues_by_category={}
        )
    )
    quality_calculator.track_quality_trend(project_id, result2)
    
    comparison = quality_calculator.generate_comparison(project_id, result2)
    
    assert comparison is not None
    assert comparison.previous_score == 60.0
    assert comparison.current_score == 75.0
    assert comparison.score_delta == 15.0
    assert comparison.issues_delta == -7
    assert comparison.improvement_percentage > 0


def test_calculate_evaluation_statistics(quality_calculator):
    """Test calculating evaluation statistics."""
    project_id = "test_project_4"
    
    # Track some analyses
    for i in range(5):
        result = AnalysisResult(
            session_id=f"session{i}",
            timestamp=datetime.now(timezone.utc) + timedelta(days=i),
            codebase_path="./test",
            files_analyzed=10,
            total_issues=20 - i * 2,
            quality_score=60.0 + i * 5,
            file_analyses=[],
            suggestions=[],
            documentation=Documentation(
                project_structure="# Project",
                api_docs={},
                examples={}
            ),
            metrics_summary=MetricsSummary(
                total_files=10,
                total_lines=1000,
                average_complexity=5.0,
                average_maintainability=70.0,
                total_issues_by_severity={},
                total_issues_by_category={}
            )
        )
        quality_calculator.track_quality_trend(project_id, result)
    
    stats = quality_calculator.calculate_evaluation_statistics(
        project_id,
        issues_resolved=30,
        suggestions_implemented=15
    )
    
    assert stats.total_analyses == 5
    assert stats.total_issues_found == 80  # 20+18+16+14+12 = 80
    assert stats.issues_resolved == 30
    assert stats.suggestions_implemented == 15
    assert 0 <= stats.resolution_rate <= 1
    assert 0 <= stats.implementation_rate <= 1
    assert 0 <= stats.average_quality_score <= 100


def test_measure_suggestion_impact(quality_calculator):
    """Test measuring suggestion impact."""
    before = CodeMetrics(
        cyclomatic_complexity=15,
        maintainability_index=50.0,
        lines_of_code=200,
        comment_ratio=0.1
    )
    
    after = CodeMetrics(
        cyclomatic_complexity=8,
        maintainability_index=75.0,
        lines_of_code=180,
        comment_ratio=0.2
    )
    
    impact = quality_calculator.measure_suggestion_impact(
        suggestion_id="sugg_1",
        suggestion_title="Refactor complex function",
        before_metrics=before,
        after_metrics=after,
        issues_resolved=3
    )
    
    assert impact.complexity_improvement == 7  # 15 - 8
    assert impact.maintainability_improvement == 25.0  # 75 - 50
    assert impact.issues_resolved == 3


# ============================================================================
# Property-Based Tests
# ============================================================================

# Property 21: Quality Score Calculation
# Feature: code-review-documentation-agent, Property 21: Quality Score Calculation
# Validates: Requirements 9.1
@given(file_analyses=st.lists(file_analysis_strategy(), min_size=1, max_size=20))
@settings(max_examples=100, deadline=None)
def test_property_quality_score_calculation(file_analyses):
    """
    Property 21: Quality Score Calculation
    
    For any completed analysis, a quality score should be calculated based on
    identified issues, and the score should be within a valid range (0-100).
    
    Validates: Requirements 9.1
    """
    calculator = QualityMetricsCalculator()
    
    # Calculate quality score
    quality_score = calculator.calculate_quality_score(file_analyses)
    
    # Verify score is in valid range
    assert 0.0 <= quality_score <= 100.0, f"Quality score {quality_score} is out of range [0, 100]"
    
    # Verify score is a valid number (not NaN or infinity)
    assert not (quality_score != quality_score), "Quality score is NaN"  # NaN check
    assert quality_score != float('inf'), "Quality score is infinity"
    assert quality_score != float('-inf'), "Quality score is negative infinity"
    
    # Additional invariants
    # If there are no issues and good metrics, score should be high
    total_issues = sum(len(fa.issues) for fa in file_analyses)
    avg_maintainability = sum(fa.metrics.maintainability_index for fa in file_analyses) / len(file_analyses)
    
    if total_issues == 0 and avg_maintainability > 80:
        assert quality_score >= 70, "Score should be high for good code with no issues"
    
    # If there are many critical issues, score should be lower
    critical_issues = sum(
        1 for fa in file_analyses
        for issue in fa.issues
        if issue.severity == IssueSeverity.CRITICAL
    )
    
    if critical_issues >= len(file_analyses) * 2:  # 2+ critical issues per file
        assert quality_score <= 75, "Score should be relatively low for code with many critical issues"


# Property 22: Quality Trend Tracking
# Feature: code-review-documentation-agent, Property 22: Quality Trend Tracking
# Validates: Requirements 9.2, 9.3
@given(
    analysis_results=st.lists(analysis_result_strategy(), min_size=2, max_size=5)
)
@settings(max_examples=50, deadline=None)
def test_property_quality_trend_tracking(analysis_results):
    """
    Property 22: Quality Trend Tracking
    
    For any sequence of multiple analyses on the same project, quality scores
    should be tracked over time and comparison metrics showing changes since
    the last analysis should be included in reports.
    
    Validates: Requirements 9.2, 9.3
    """
    # Create temporary directory for this test
    temp_path = tempfile.mkdtemp()
    try:
        calculator = QualityMetricsCalculator(storage_dir=str(Path(temp_path) / "trends"))
        project_id = f"test_project_property_{id(analysis_results)}"  # Unique project ID
        
        # Ensure timestamps are unique and ordered
        base_time = datetime.now(timezone.utc)
        for i, result in enumerate(analysis_results):
            result.timestamp = base_time + timedelta(hours=i)
        
        # Track all analyses
        for result in analysis_results:
            trend = calculator.track_quality_trend(project_id, result)
            
            # Verify trend is created
            assert trend is not None
            assert trend.quality_score == result.quality_score
            assert trend.total_issues == result.total_issues
            assert trend.files_analyzed == result.files_analyzed
        
        # Retrieve trends
        trends = calculator.get_quality_trends(project_id)
        
        # Verify all trends are tracked
        assert len(trends) == len(analysis_results), "All analyses should be tracked"
        
        # Verify trends are ordered by timestamp
        for i in range(len(trends) - 1):
            assert trends[i].timestamp <= trends[i + 1].timestamp, "Trends should be ordered by time"
        
        # Verify comparison metrics can be generated
        if len(analysis_results) >= 2:
            comparison = calculator.generate_comparison(project_id, analysis_results[-1])
            
            # Verify comparison exists
            assert comparison is not None, "Comparison should exist for multiple analyses"
            
            # Verify comparison contains required fields
            assert hasattr(comparison, 'previous_score')
            assert hasattr(comparison, 'current_score')
            assert hasattr(comparison, 'score_delta')
            assert hasattr(comparison, 'issues_delta')
            assert hasattr(comparison, 'improvement_percentage')
            
            # Verify comparison values are correct
            assert comparison.current_score == analysis_results[-1].quality_score
            assert comparison.previous_score == trends[-2].quality_score
            
            # Verify delta calculation
            expected_delta = comparison.current_score - comparison.previous_score
            assert abs(comparison.score_delta - expected_delta) < 0.01, "Score delta should be correct"
            
            # Verify improvement percentage calculation
            if comparison.previous_score > 0.01:  # Avoid division by very small numbers
                expected_improvement = (comparison.score_delta / comparison.previous_score) * 100
                # Handle cases where improvement percentage might be very large or infinite
                if abs(expected_improvement) < 1e6:  # Only check if not extremely large
                    assert abs(comparison.improvement_percentage - expected_improvement) < 0.01
        
        # Verify trends can be limited
        limited_trends = calculator.get_quality_trends(project_id, limit=2)
        assert len(limited_trends) <= 2, "Limit should be respected"
        
        # If we have more than 2 trends, verify we get the most recent ones
        if len(trends) > 2:
            assert limited_trends[-1].timestamp == trends[-1].timestamp, "Should get most recent trends"
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_path, ignore_errors=True)


# Additional property tests for edge cases

@given(
    num_files=st.integers(min_value=1, max_value=100),
    avg_complexity=st.floats(min_value=1.0, max_value=50.0),
    avg_maintainability=st.floats(min_value=0.0, max_value=100.0)
)
@settings(max_examples=100, deadline=None)
def test_property_quality_score_monotonicity(num_files, avg_complexity, avg_maintainability):
    """
    Test that quality score decreases monotonically with more issues.
    
    For the same code metrics, adding more issues should not increase the score.
    """
    calculator = QualityMetricsCalculator()
    
    # Create base file analyses with no issues
    base_analyses = [
        FileAnalysis(
            file_path=f"file{i}.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=int(avg_complexity),
                maintainability_index=avg_maintainability,
                lines_of_code=100,
                comment_ratio=0.2
            ),
            issues=[],
            functions=[],
            classes=[]
        )
        for i in range(num_files)
    ]
    
    score_no_issues = calculator.calculate_quality_score(base_analyses)
    
    # Add a critical issue to first file
    analyses_with_issue = [
        FileAnalysis(
            file_path="file0.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=int(avg_complexity),
                maintainability_index=avg_maintainability,
                lines_of_code=100,
                comment_ratio=0.2
            ),
            issues=[
                CodeIssue(
                    severity=IssueSeverity.CRITICAL,
                    category=IssueCategory.SECURITY,
                    file_path="file0.py",
                    line_number=10,
                    description="Critical issue",
                    code_snippet="bad"
                )
            ],
            functions=[],
            classes=[]
        )
    ] + base_analyses[1:]
    
    score_with_issue = calculator.calculate_quality_score(analyses_with_issue)
    
    # Score with issues should be less than or equal to score without issues
    assert score_with_issue <= score_no_issues, "Adding issues should not increase quality score"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
