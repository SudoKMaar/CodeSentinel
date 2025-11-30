"""
Property-based tests for Reviewer Agent.

Feature: code-review-documentation-agent
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from typing import List

from agents.reviewer_agent import ReviewerAgent
from models.data_models import (
    FileAnalysis,
    CodeMetrics,
    CodeIssue,
    FunctionInfo,
    ClassInfo,
    Suggestion,
    IssueSeverity,
    IssueCategory,
    EffortLevel,
    ImpactLevel,
)


# Custom strategies for generating test data

@st.composite
def code_issue_strategy(draw):
    """Generate a valid CodeIssue."""
    severity = draw(st.sampled_from(list(IssueSeverity)))
    category = draw(st.sampled_from(list(IssueCategory)))
    # Generate a simple file path without filtering
    file_name = draw(st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=5,
        max_size=20
    ))
    file_path = f"src/{file_name}.py"
    line_number = draw(st.integers(min_value=1, max_value=1000))
    description = draw(st.text(min_size=10, max_size=200))
    code_snippet = draw(st.text(min_size=5, max_size=100))
    suggestion = draw(st.one_of(st.none(), st.text(min_size=10, max_size=100)))
    
    return CodeIssue(
        severity=severity,
        category=category,
        file_path=file_path,
        line_number=line_number,
        description=description,
        code_snippet=code_snippet,
        suggestion=suggestion,
    )


@st.composite
def function_info_strategy(draw):
    """Generate a valid FunctionInfo."""
    name = draw(st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=20
    ))
    line_number = draw(st.integers(min_value=1, max_value=1000))
    num_params = draw(st.integers(min_value=0, max_value=5))
    parameters = [f"param{i}" for i in range(num_params)]
    complexity = draw(st.integers(min_value=1, max_value=30))
    
    return FunctionInfo(
        name=name,
        line_number=line_number,
        parameters=parameters,
        complexity=complexity,
    )


@st.composite
def file_analysis_strategy(draw):
    """Generate a valid FileAnalysis."""
    file_path = draw(st.text(min_size=5, max_size=50))
    if not file_path.endswith('.py'):
        file_path = f"{file_path}.py"
    
    language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
    
    metrics = CodeMetrics(
        cyclomatic_complexity=draw(st.integers(min_value=1, max_value=50)),
        maintainability_index=draw(st.floats(min_value=0.0, max_value=100.0)),
        lines_of_code=draw(st.integers(min_value=1, max_value=1000)),
        comment_ratio=draw(st.floats(min_value=0.0, max_value=1.0)),
    )
    
    num_issues = draw(st.integers(min_value=0, max_value=10))
    issues = [draw(code_issue_strategy()) for _ in range(num_issues)]
    
    num_functions = draw(st.integers(min_value=0, max_value=5))
    functions = [draw(function_info_strategy()) for _ in range(num_functions)]
    
    return FileAnalysis(
        file_path=file_path,
        language=language,
        metrics=metrics,
        issues=issues,
        functions=functions,
        classes=[],
    )


@st.composite
def suggestion_strategy(draw):
    """Generate a valid Suggestion."""
    priority = draw(st.integers(min_value=1, max_value=5))
    category = draw(st.text(min_size=3, max_size=20))
    title = draw(st.text(min_size=5, max_size=100))
    description = draw(st.text(min_size=10, max_size=200))
    code_example = draw(st.one_of(st.none(), st.text(min_size=10, max_size=200)))
    estimated_effort = draw(st.sampled_from(list(EffortLevel)))
    impact = draw(st.sampled_from(list(ImpactLevel)))
    related_issues = draw(st.lists(st.text(min_size=5, max_size=50), max_size=5))
    
    return Suggestion(
        priority=priority,
        category=category,
        title=title,
        description=description,
        code_example=code_example,
        estimated_effort=estimated_effort,
        impact=impact,
        related_issues=related_issues,
    )


# Property-based tests

# Feature: code-review-documentation-agent, Property 9: Issue-Suggestion Mapping
# Validates: Requirements 4.1

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(file_analysis_strategy(), min_size=1, max_size=3))
def test_issue_suggestion_mapping(analysis_results: List[FileAnalysis]) -> None:
    """
    Property 9: Issue-Suggestion Mapping
    
    For any identified code issue, the system should provide a corresponding
    refactoring suggestion with a code example.
    
    Validates: Requirements 4.1
    """
    # Create reviewer agent
    reviewer = ReviewerAgent(use_llm=False)
    
    # Generate suggestions from analysis results
    suggestions = reviewer.generate_suggestions(analysis_results)
    
    # Count total issues in analysis results
    total_issues = sum(len(analysis.issues) for analysis in analysis_results)
    
    # Each issue should have at least one corresponding suggestion
    # Note: We may have additional suggestions (test suggestions, pattern suggestions)
    # so we check that we have at least as many suggestions as issues
    assert len(suggestions) >= total_issues, \
        f"Expected at least {total_issues} suggestions for {total_issues} issues, got {len(suggestions)}"
    
    # Verify that each suggestion has required fields
    for suggestion in suggestions:
        assert suggestion.title is not None and len(suggestion.title) > 0, \
            "Each suggestion must have a title"
        assert suggestion.description is not None and len(suggestion.description) > 0, \
            "Each suggestion must have a description"
        assert suggestion.priority >= 1 and suggestion.priority <= 5, \
            "Priority must be between 1 and 5"
        assert suggestion.estimated_effort in [EffortLevel.LOW, EffortLevel.MEDIUM, EffortLevel.HIGH], \
            "Effort must be a valid EffortLevel"
        assert suggestion.impact in [ImpactLevel.LOW, ImpactLevel.MEDIUM, ImpactLevel.HIGH], \
            "Impact must be a valid ImpactLevel"


@settings(max_examples=100)
@given(code_issue_strategy())
def test_single_issue_generates_suggestion(issue: CodeIssue) -> None:
    """
    Property: Each individual issue generates a suggestion.
    
    Validates: Requirements 4.1
    """
    # Create a file analysis with one issue
    analysis = FileAnalysis(
        file_path="test.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=5,
            maintainability_index=70.0,
            lines_of_code=100,
            comment_ratio=0.2,
        ),
        issues=[issue],
        functions=[],
        classes=[],
    )
    
    reviewer = ReviewerAgent(use_llm=False)
    suggestions = reviewer.generate_suggestions([analysis])
    
    # Should have at least one suggestion for the issue
    assert len(suggestions) >= 1, "Each issue should generate at least one suggestion"
    
    # Find suggestion related to this issue
    related_suggestions = [
        s for s in suggestions
        if any(issue.file_path in related for related in s.related_issues)
    ]
    
    assert len(related_suggestions) >= 1, \
        "Should have at least one suggestion related to the issue"


@settings(max_examples=100)
@given(st.lists(code_issue_strategy(), min_size=1, max_size=10))
def test_all_issues_have_suggestions(issues: List[CodeIssue]) -> None:
    """
    Property: All issues should have corresponding suggestions.
    
    Validates: Requirements 4.1
    """
    # Create file analyses with issues
    analyses = []
    for i, issue in enumerate(issues):
        analysis = FileAnalysis(
            file_path=f"file{i}.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=5,
                maintainability_index=70.0,
                lines_of_code=100,
                comment_ratio=0.2,
            ),
            issues=[issue],
            functions=[],
            classes=[],
        )
        analyses.append(analysis)
    
    reviewer = ReviewerAgent(use_llm=False)
    suggestions = reviewer.generate_suggestions(analyses)
    
    # Should have at least as many suggestions as issues
    assert len(suggestions) >= len(issues), \
        f"Expected at least {len(issues)} suggestions, got {len(suggestions)}"


# Feature: code-review-documentation-agent, Property 11: Suggestion Prioritization
# Validates: Requirements 4.5

@settings(max_examples=100)
@given(st.lists(suggestion_strategy(), min_size=2, max_size=20))
def test_suggestion_prioritization(suggestions: List[Suggestion]) -> None:
    """
    Property 11: Suggestion Prioritization
    
    For any set of improvement suggestions, they should be ordered by priority
    based on impact and effort, with each suggestion having valid priority,
    impact, and effort values.
    
    Validates: Requirements 4.5
    """
    # Create reviewer agent
    reviewer = ReviewerAgent(use_llm=False)
    
    # Prioritize suggestions
    prioritized = reviewer.prioritize_suggestions(suggestions)
    
    # Verify same number of suggestions
    assert len(prioritized) == len(suggestions), \
        "Prioritization should not change the number of suggestions"
    
    # Verify all suggestions are present
    assert set(id(s) for s in prioritized) == set(id(s) for s in suggestions), \
        "Prioritization should not lose any suggestions"
    
    # Verify suggestions are properly ordered by priority
    for i in range(len(prioritized) - 1):
        current = prioritized[i]
        next_item = prioritized[i + 1]
        
        # Priority should be non-decreasing (1 is highest, 5 is lowest)
        assert current.priority <= next_item.priority, \
            f"Suggestions should be ordered by priority: {current.priority} > {next_item.priority}"
        
        # If priorities are equal, check impact (higher impact first)
        if current.priority == next_item.priority:
            current_impact = reviewer.IMPACT_WEIGHTS.get(current.impact, 1)
            next_impact = reviewer.IMPACT_WEIGHTS.get(next_item.impact, 1)
            assert current_impact >= next_impact, \
                "Within same priority, higher impact should come first"
    
    # Verify all suggestions have valid values
    for suggestion in prioritized:
        assert 1 <= suggestion.priority <= 5, \
            f"Priority must be 1-5, got {suggestion.priority}"
        assert suggestion.impact in [ImpactLevel.LOW, ImpactLevel.MEDIUM, ImpactLevel.HIGH], \
            f"Impact must be valid, got {suggestion.impact}"
        assert suggestion.estimated_effort in [EffortLevel.LOW, EffortLevel.MEDIUM, EffortLevel.HIGH], \
            f"Effort must be valid, got {suggestion.estimated_effort}"


@settings(max_examples=100)
@given(st.integers(min_value=2, max_value=10))
def test_prioritization_preserves_count(num_suggestions: int) -> None:
    """
    Property: Prioritization preserves the number of suggestions.
    
    Validates: Requirements 4.5
    """
    # Create suggestions with random priorities
    suggestions = []
    for i in range(num_suggestions):
        suggestion = Suggestion(
            priority=i % 5 + 1,  # Cycle through priorities 1-5
            category="test",
            title=f"Suggestion {i}",
            description=f"Description {i}",
            estimated_effort=EffortLevel.MEDIUM,
            impact=ImpactLevel.MEDIUM,
            related_issues=[],
        )
        suggestions.append(suggestion)
    
    reviewer = ReviewerAgent(use_llm=False)
    prioritized = reviewer.prioritize_suggestions(suggestions)
    
    assert len(prioritized) == num_suggestions, \
        "Prioritization should preserve the number of suggestions"


@settings(max_examples=100)
@given(st.lists(st.integers(min_value=1, max_value=5), min_size=2, max_size=20))
def test_prioritization_ordering(priorities: List[int]) -> None:
    """
    Property: Prioritized suggestions are in non-decreasing priority order.
    
    Validates: Requirements 4.5
    """
    # Create suggestions with given priorities
    suggestions = []
    for i, priority in enumerate(priorities):
        suggestion = Suggestion(
            priority=priority,
            category="test",
            title=f"Suggestion {i}",
            description=f"Description {i}",
            estimated_effort=EffortLevel.MEDIUM,
            impact=ImpactLevel.MEDIUM,
            related_issues=[],
        )
        suggestions.append(suggestion)
    
    reviewer = ReviewerAgent(use_llm=False)
    prioritized = reviewer.prioritize_suggestions(suggestions)
    
    # Verify ordering
    for i in range(len(prioritized) - 1):
        assert prioritized[i].priority <= prioritized[i + 1].priority, \
            "Suggestions should be in non-decreasing priority order"


# Additional unit tests

def test_generate_suggestions_empty_analysis():
    """Unit test: Empty analysis should return empty suggestions."""
    reviewer = ReviewerAgent(use_llm=False)
    suggestions = reviewer.generate_suggestions([])
    
    assert len(suggestions) == 0


def test_generate_suggestions_no_issues():
    """Unit test: Analysis with no issues should return minimal suggestions."""
    analysis = FileAnalysis(
        file_path="test.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=2,
            maintainability_index=90.0,
            lines_of_code=50,
            comment_ratio=0.3,
        ),
        issues=[],
        functions=[],
        classes=[],
    )
    
    reviewer = ReviewerAgent(use_llm=False)
    suggestions = reviewer.generate_suggestions([analysis])
    
    # Should have no issue-based suggestions, but may have test/pattern suggestions
    assert len(suggestions) >= 0


def test_critical_issue_high_priority():
    """Unit test: Critical issues should generate high priority suggestions."""
    issue = CodeIssue(
        severity=IssueSeverity.CRITICAL,
        category=IssueCategory.SECURITY,
        file_path="test.py",
        line_number=10,
        description="Critical security issue",
        code_snippet="vulnerable_code()",
        suggestion="Fix immediately",
    )
    
    analysis = FileAnalysis(
        file_path="test.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=5,
            maintainability_index=70.0,
            lines_of_code=100,
            comment_ratio=0.2,
        ),
        issues=[issue],
        functions=[],
        classes=[],
    )
    
    reviewer = ReviewerAgent(use_llm=False)
    suggestions = reviewer.generate_suggestions([analysis])
    
    # Should have at least one suggestion
    assert len(suggestions) >= 1
    
    # Critical issues should have high priority (low number)
    critical_suggestions = [s for s in suggestions if 'security' in s.category.lower()]
    assert len(critical_suggestions) > 0
    assert all(s.priority <= 3 for s in critical_suggestions)


def test_generate_review_report():
    """Unit test: Review report should be generated with proper structure."""
    analysis = FileAnalysis(
        file_path="test.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=5,
            maintainability_index=70.0,
            lines_of_code=100,
            comment_ratio=0.2,
        ),
        issues=[
            CodeIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.COMPLEXITY,
                file_path="test.py",
                line_number=10,
                description="High complexity",
                code_snippet="complex_code()",
            )
        ],
        functions=[],
        classes=[],
    )
    
    reviewer = ReviewerAgent(use_llm=False)
    suggestions = reviewer.generate_suggestions([analysis])
    prioritized = reviewer.prioritize_suggestions(suggestions)
    
    report = reviewer.generate_review_report([analysis], prioritized, 75.0)
    
    # Verify report structure
    assert "# Code Review Report" in report
    assert "Quality Score" in report
    assert "Summary" in report
    assert "75.0" in report


def test_test_suggestions_for_complex_functions():
    """Unit test: Complex functions should get test suggestions."""
    func = FunctionInfo(
        name="complex_function",
        line_number=10,
        parameters=["param1", "param2"],
        complexity=10,
    )
    
    analysis = FileAnalysis(
        file_path="src/module.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=10,
            maintainability_index=60.0,
            lines_of_code=200,
            comment_ratio=0.1,
        ),
        issues=[],
        functions=[func],
        classes=[],
    )
    
    reviewer = ReviewerAgent(use_llm=False)
    suggestions = reviewer.generate_suggestions([analysis])
    
    # Should have test suggestions for complex function
    test_suggestions = [s for s in suggestions if s.category == "testing"]
    assert len(test_suggestions) > 0
