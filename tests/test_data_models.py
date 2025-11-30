"""
Property-based tests for data model serialization.

Feature: code-review-documentation-agent
"""

import json
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.strategies import SearchStrategy

from models.data_models import (
    AnalysisConfig,
    AnalysisDepth,
    AnalysisResult,
    ClassInfo,
    CodeIssue,
    CodeMetrics,
    Documentation,
    EffortLevel,
    FileAnalysis,
    FunctionInfo,
    ImpactLevel,
    IssueCategory,
    IssueSeverity,
    MetricsSummary,
    PatternType,
    ProjectPattern,
    SessionState,
    SessionStatus,
    Suggestion,
)


# Custom strategies for generating valid model instances

@st.composite
def analysis_config_strategy(draw: st.DrawFn) -> AnalysisConfig:
    """Generate random AnalysisConfig instances."""
    # Use simple ASCII text to avoid slow generation
    simple_text = st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126, blacklist_categories=('Cc', 'Cs')), min_size=1, max_size=20)
    # File patterns should be valid glob patterns (alphanumeric with * and .)
    file_pattern_text = st.text(alphabet=st.characters(whitelist_characters='abcdefghijklmnopqrstuvwxyz0123456789*.'), min_size=1, max_size=15)
    
    return AnalysisConfig(
        target_path=draw(simple_text),
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
def code_metrics_strategy(draw: st.DrawFn) -> CodeMetrics:
    """Generate random CodeMetrics instances."""
    return CodeMetrics(
        cyclomatic_complexity=draw(st.integers(min_value=1, max_value=100)),
        maintainability_index=draw(st.floats(min_value=0.0, max_value=100.0)),
        lines_of_code=draw(st.integers(min_value=0, max_value=10000)),
        comment_ratio=draw(st.floats(min_value=0.0, max_value=1.0)),
        test_coverage=draw(st.one_of(
            st.none(),
            st.floats(min_value=0.0, max_value=100.0)
        )),
    )


@st.composite
def code_issue_strategy(draw: st.DrawFn) -> CodeIssue:
    """Generate random CodeIssue instances."""
    return CodeIssue(
        severity=draw(st.sampled_from(IssueSeverity)),
        category=draw(st.sampled_from(IssueCategory)),
        file_path=draw(st.text(min_size=1, max_size=100)),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        description=draw(st.text(min_size=1, max_size=200)),
        code_snippet=draw(st.text(min_size=1, max_size=500)),
        suggestion=draw(st.one_of(st.none(), st.text(min_size=1, max_size=200))),
    )


@st.composite
def function_info_strategy(draw: st.DrawFn) -> FunctionInfo:
    """Generate random FunctionInfo instances."""
    return FunctionInfo(
        name=draw(st.text(min_size=1, max_size=50)),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        parameters=draw(st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=10)),
        return_type=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        docstring=draw(st.one_of(st.none(), st.text(min_size=1, max_size=200))),
        complexity=draw(st.integers(min_value=1, max_value=50)),
    )


@st.composite
def class_info_strategy(draw: st.DrawFn) -> ClassInfo:
    """Generate random ClassInfo instances."""
    return ClassInfo(
        name=draw(st.text(min_size=1, max_size=50)),
        line_number=draw(st.integers(min_value=1, max_value=10000)),
        methods=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=20)),
        base_classes=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
        docstring=draw(st.one_of(st.none(), st.text(min_size=1, max_size=200))),
    )


@st.composite
def file_analysis_strategy(draw: st.DrawFn) -> FileAnalysis:
    """Generate random FileAnalysis instances."""
    return FileAnalysis(
        file_path=draw(st.text(min_size=1, max_size=100)),
        language=draw(st.sampled_from(["python", "javascript", "typescript", "java"])),
        metrics=draw(code_metrics_strategy()),
        issues=draw(st.lists(code_issue_strategy(), min_size=0, max_size=5)),
        functions=draw(st.lists(function_info_strategy(), min_size=0, max_size=5)),
        classes=draw(st.lists(class_info_strategy(), min_size=0, max_size=5)),
    )


@st.composite
def suggestion_strategy(draw: st.DrawFn) -> Suggestion:
    """Generate random Suggestion instances."""
    return Suggestion(
        priority=draw(st.integers(min_value=1, max_value=5)),
        category=draw(st.text(min_size=1, max_size=50)),
        title=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.text(min_size=1, max_size=200)),
        code_example=draw(st.one_of(st.none(), st.text(min_size=1, max_size=500))),
        estimated_effort=draw(st.sampled_from(EffortLevel)),
        impact=draw(st.sampled_from(ImpactLevel)),
        related_issues=draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
    )


@st.composite
def documentation_strategy(draw: st.DrawFn) -> Documentation:
    """Generate random Documentation instances."""
    return Documentation(
        project_structure=draw(st.text(min_size=1, max_size=500)),
        api_docs=draw(st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.text(min_size=1, max_size=200),
            min_size=0,
            max_size=5
        )),
        examples=draw(st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.text(min_size=1, max_size=200),
            min_size=0,
            max_size=5
        )),
    )


@st.composite
def metrics_summary_strategy(draw: st.DrawFn) -> MetricsSummary:
    """Generate random MetricsSummary instances."""
    return MetricsSummary(
        total_files=draw(st.integers(min_value=0, max_value=1000)),
        total_lines=draw(st.integers(min_value=0, max_value=100000)),
        average_complexity=draw(st.floats(min_value=0.0, max_value=100.0)),
        average_maintainability=draw(st.floats(min_value=0.0, max_value=100.0)),
        total_issues_by_severity=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.integers(min_value=0, max_value=100),
            min_size=0,
            max_size=5
        )),
        total_issues_by_category=draw(st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.integers(min_value=0, max_value=100),
            min_size=0,
            max_size=5
        )),
    )


@st.composite
def datetime_strategy(draw: st.DrawFn) -> datetime:
    """Generate random datetime instances."""
    return datetime.fromtimestamp(
        draw(st.integers(min_value=0, max_value=2147483647)),
        tz=timezone.utc
    )


@st.composite
def analysis_result_strategy(draw: st.DrawFn) -> AnalysisResult:
    """Generate random AnalysisResult instances."""
    return AnalysisResult(
        session_id=draw(st.text(min_size=1, max_size=50)),
        timestamp=draw(datetime_strategy()),
        codebase_path=draw(st.text(min_size=1, max_size=100)),
        files_analyzed=draw(st.integers(min_value=0, max_value=1000)),
        total_issues=draw(st.integers(min_value=0, max_value=1000)),
        quality_score=draw(st.floats(min_value=0.0, max_value=100.0)),
        file_analyses=draw(st.lists(file_analysis_strategy(), min_size=0, max_size=3)),
        suggestions=draw(st.lists(suggestion_strategy(), min_size=0, max_size=3)),
        documentation=draw(documentation_strategy()),
        metrics_summary=draw(metrics_summary_strategy()),
    )


@st.composite
def session_state_strategy(draw: st.DrawFn) -> SessionState:
    """Generate random SessionState instances."""
    return SessionState(
        session_id=draw(st.text(min_size=1, max_size=50)),
        status=draw(st.sampled_from(SessionStatus)),
        config=draw(analysis_config_strategy()),
        processed_files=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)),
        pending_files=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=10)),
        partial_results=draw(st.dictionaries(
            st.text(min_size=1, max_size=50),
            st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=0,
            max_size=5
        )),
        checkpoint_time=draw(datetime_strategy()),
    )


@st.composite
def project_pattern_strategy(draw: st.DrawFn) -> ProjectPattern:
    """Generate random ProjectPattern instances."""
    return ProjectPattern(
        pattern_id=draw(st.text(min_size=1, max_size=50)),
        project_id=draw(st.text(min_size=1, max_size=50)),
        pattern_type=draw(st.sampled_from(PatternType)),
        description=draw(st.text(min_size=1, max_size=200)),
        examples=draw(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=5)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        last_updated=draw(datetime_strategy()),
    )


# Property-based tests

# Feature: code-review-documentation-agent, Property: Serialization Round-Trip
# Validates: Requirements 1.3, 7.1

@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=100)
@given(analysis_config_strategy())
def test_analysis_config_serialization_roundtrip(config: AnalysisConfig) -> None:
    """
    Property: Serialization Round-Trip for AnalysisConfig
    For any AnalysisConfig instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    # Serialize to JSON
    json_str = config.model_dump_json()
    
    # Deserialize from JSON
    restored = AnalysisConfig.model_validate_json(json_str)
    
    # Verify equivalence
    assert restored == config
    assert restored.model_dump() == config.model_dump()


@given(code_metrics_strategy())
def test_code_metrics_serialization_roundtrip(metrics: CodeMetrics) -> None:
    """
    Property: Serialization Round-Trip for CodeMetrics
    For any CodeMetrics instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = metrics.model_dump_json()
    restored = CodeMetrics.model_validate_json(json_str)
    
    assert restored == metrics
    assert restored.model_dump() == metrics.model_dump()


@given(code_issue_strategy())
def test_code_issue_serialization_roundtrip(issue: CodeIssue) -> None:
    """
    Property: Serialization Round-Trip for CodeIssue
    For any CodeIssue instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = issue.model_dump_json()
    restored = CodeIssue.model_validate_json(json_str)
    
    assert restored == issue
    assert restored.model_dump() == issue.model_dump()


@given(function_info_strategy())
def test_function_info_serialization_roundtrip(func_info: FunctionInfo) -> None:
    """
    Property: Serialization Round-Trip for FunctionInfo
    For any FunctionInfo instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = func_info.model_dump_json()
    restored = FunctionInfo.model_validate_json(json_str)
    
    assert restored == func_info
    assert restored.model_dump() == func_info.model_dump()


@given(class_info_strategy())
def test_class_info_serialization_roundtrip(class_info: ClassInfo) -> None:
    """
    Property: Serialization Round-Trip for ClassInfo
    For any ClassInfo instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = class_info.model_dump_json()
    restored = ClassInfo.model_validate_json(json_str)
    
    assert restored == class_info
    assert restored.model_dump() == class_info.model_dump()


@given(file_analysis_strategy())
def test_file_analysis_serialization_roundtrip(analysis: FileAnalysis) -> None:
    """
    Property: Serialization Round-Trip for FileAnalysis
    For any FileAnalysis instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = analysis.model_dump_json()
    restored = FileAnalysis.model_validate_json(json_str)
    
    assert restored == analysis
    assert restored.model_dump() == analysis.model_dump()


@given(suggestion_strategy())
def test_suggestion_serialization_roundtrip(suggestion: Suggestion) -> None:
    """
    Property: Serialization Round-Trip for Suggestion
    For any Suggestion instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = suggestion.model_dump_json()
    restored = Suggestion.model_validate_json(json_str)
    
    assert restored == suggestion
    assert restored.model_dump() == suggestion.model_dump()


@given(documentation_strategy())
def test_documentation_serialization_roundtrip(doc: Documentation) -> None:
    """
    Property: Serialization Round-Trip for Documentation
    For any Documentation instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = doc.model_dump_json()
    restored = Documentation.model_validate_json(json_str)
    
    assert restored == doc
    assert restored.model_dump() == doc.model_dump()


@given(metrics_summary_strategy())
def test_metrics_summary_serialization_roundtrip(summary: MetricsSummary) -> None:
    """
    Property: Serialization Round-Trip for MetricsSummary
    For any MetricsSummary instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = summary.model_dump_json()
    restored = MetricsSummary.model_validate_json(json_str)
    
    assert restored == summary
    assert restored.model_dump() == summary.model_dump()


@given(analysis_result_strategy())
def test_analysis_result_serialization_roundtrip(result: AnalysisResult) -> None:
    """
    Property: Serialization Round-Trip for AnalysisResult
    For any AnalysisResult instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = result.model_dump_json()
    restored = AnalysisResult.model_validate_json(json_str)
    
    assert restored == result
    assert restored.model_dump() == result.model_dump()


@given(session_state_strategy())
def test_session_state_serialization_roundtrip(state: SessionState) -> None:
    """
    Property: Serialization Round-Trip for SessionState
    For any SessionState instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = state.model_dump_json()
    restored = SessionState.model_validate_json(json_str)
    
    assert restored == state
    assert restored.model_dump() == state.model_dump()


@given(project_pattern_strategy())
def test_project_pattern_serialization_roundtrip(pattern: ProjectPattern) -> None:
    """
    Property: Serialization Round-Trip for ProjectPattern
    For any ProjectPattern instance, serializing to JSON and deserializing
    should produce an equivalent object.
    """
    json_str = pattern.model_dump_json()
    restored = ProjectPattern.model_validate_json(json_str)
    
    assert restored == pattern
    assert restored.model_dump() == pattern.model_dump()
