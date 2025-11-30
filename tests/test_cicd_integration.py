"""
Property-based tests for CI/CD integration features.

Feature: code-review-documentation-agent
"""

import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import pytest
from hypothesis import given, settings, strategies as st, assume, HealthCheck
from hypothesis.strategies import composite

from tools.cicd_integration import (
    GitIntegration,
    OutputFormatter,
    ExitCodeHandler,
    CICDConfigLoader,
)
from models.data_models import (
    AnalysisResult,
    FileAnalysis,
    CodeMetrics,
    CodeIssue,
    IssueSeverity,
    IssueCategory,
    Suggestion,
    Documentation,
    MetricsSummary,
    FunctionInfo,
    ClassInfo,
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@composite
def file_analysis_strategy(draw):
    """Generate a random FileAnalysis object."""
    file_path = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'N'), whitelist_characters='/_.')))
    if not file_path.endswith('.py'):
        file_path += '.py'
    
    language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
    
    # Generate metrics
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
            code_snippet=draw(st.text(min_size=5, max_size=50)),
            suggestion=draw(st.one_of(st.none(), st.text(min_size=10, max_size=100)))
        )
        issues.append(issue)
    
    # Generate functions
    num_functions = draw(st.integers(min_value=0, max_value=5))
    functions = []
    for i in range(num_functions):
        func = FunctionInfo(
            name=f"function_{i}",
            line_number=draw(st.integers(min_value=1, max_value=1000)),
            parameters=draw(st.lists(st.text(min_size=1, max_size=10), max_size=5)),
            complexity=draw(st.integers(min_value=1, max_value=20))
        )
        functions.append(func)
    
    # Generate classes
    num_classes = draw(st.integers(min_value=0, max_value=3))
    classes = []
    for i in range(num_classes):
        cls = ClassInfo(
            name=f"Class_{i}",
            line_number=draw(st.integers(min_value=1, max_value=1000)),
            methods=draw(st.lists(st.text(min_size=1, max_size=20), max_size=5))
        )
        classes.append(cls)
    
    return FileAnalysis(
        file_path=file_path,
        language=language,
        metrics=metrics,
        issues=issues,
        functions=functions,
        classes=classes
    )


@composite
def analysis_result_strategy(draw):
    """Generate a random AnalysisResult object."""
    session_id = draw(st.uuids()).hex
    
    # Generate file analyses
    num_files = draw(st.integers(min_value=1, max_value=10))
    file_analyses = [draw(file_analysis_strategy()) for _ in range(num_files)]
    
    total_issues = sum(len(fa.issues) for fa in file_analyses)
    
    # Generate suggestions
    num_suggestions = draw(st.integers(min_value=0, max_value=5))
    suggestions = []
    for i in range(num_suggestions):
        suggestion = Suggestion(
            priority=draw(st.integers(min_value=1, max_value=5)),
            category=draw(st.sampled_from(list(IssueCategory))),
            title=f"Suggestion {i}",
            description=draw(st.text(min_size=20, max_size=100)),
            code_example=draw(st.one_of(st.none(), st.text(min_size=10, max_size=50))),
            estimated_effort=draw(st.sampled_from(['low', 'medium', 'high'])),
            impact=draw(st.sampled_from(['low', 'medium', 'high'])),
            related_issues=[]
        )
        suggestions.append(suggestion)
    
    # Generate documentation
    documentation = Documentation(
        project_structure=draw(st.text(min_size=10, max_size=200)),
        api_docs={},
        examples={}
    )
    
    # Generate metrics summary
    metrics_summary = MetricsSummary(
        total_files=num_files,
        total_lines=sum(fa.metrics.lines_of_code for fa in file_analyses),
        average_complexity=sum(fa.metrics.cyclomatic_complexity for fa in file_analyses) / num_files,
        average_maintainability=sum(fa.metrics.maintainability_index for fa in file_analyses) / num_files,
        total_issues_by_severity={},
        total_issues_by_category={}
    )
    
    return AnalysisResult(
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        codebase_path=draw(st.text(min_size=5, max_size=50)),
        files_analyzed=num_files,
        total_issues=total_issues,
        quality_score=draw(st.floats(min_value=0.0, max_value=100.0)),
        file_analyses=file_analyses,
        suggestions=suggestions,
        documentation=documentation,
        metrics_summary=metrics_summary
    )


# ============================================================================
# Property-Based Tests
# ============================================================================

# Feature: code-review-documentation-agent, Property 28: Incremental PR Analysis
# Validates: Requirements 10.5
@given(
    num_total_files=st.integers(min_value=5, max_value=20),
    num_changed_files=st.integers(min_value=1, max_value=5)
)
@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_property_incremental_pr_analysis(num_total_files, num_changed_files):
    """
    Property 28: Incremental PR Analysis
    
    For any pull request with changed files, the system should analyze only
    those files rather than the entire codebase.
    
    Validates: Requirements 10.5
    """
    # Ensure changed files doesn't exceed total files
    num_changed_files = min(num_changed_files, num_total_files)
    
    # Create a temporary Git repository
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir) / "test_repo"
    repo_path.mkdir(exist_ok=True)
    
    try:
        # Initialize Git repository
        subprocess.run(
            ["git", "init"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        
        # Configure Git user for commits
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        
        # Create initial files and commit them (main branch)
        all_files = []
        for i in range(num_total_files):
            file_path = repo_path / f"file_{i}.py"
            file_path.write_text(f"""
def function_{i}():
    \"\"\"Function {i}.\"\"\"
    return {i}
""")
            all_files.append(file_path)
        
        # Add and commit all files
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        
        # Rename default branch to 'main' for consistency
        subprocess.run(
            ["git", "branch", "-M", "main"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        
        # Create a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature-branch"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        
        # Modify some files in the feature branch
        changed_files = all_files[:num_changed_files]
        for i, file_path in enumerate(changed_files):
            file_path.write_text(f"""
def function_{i}():
    \"\"\"Modified function {i}.\"\"\"
    return {i} * 2  # Changed implementation
""")
        
        # Commit the changes
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Feature changes"],
            cwd=repo_path,
            capture_output=True,
            check=True
        )
        
        # Use GitIntegration to get changed files
        git_integration = GitIntegration(str(repo_path))
        detected_changed_files = git_integration.get_changed_files(
            base_ref="main",
            head_ref="feature-branch",
            file_patterns=["*.py"]
        )
        
        # Property: Only changed files should be detected
        assert len(detected_changed_files) == num_changed_files, \
            f"Expected {num_changed_files} changed files, but got {len(detected_changed_files)}"
        
        # Property: All detected files should be in the changed files set
        changed_file_names = {f.name for f in changed_files}
        detected_file_names = {Path(f).name for f in detected_changed_files}
        
        assert detected_file_names == changed_file_names, \
            f"Detected files {detected_file_names} don't match changed files {changed_file_names}"
        
        # Property: Detected files should be a subset of all files
        all_file_names = {f.name for f in all_files}
        assert detected_file_names.issubset(all_file_names), \
            f"Detected files {detected_file_names} are not a subset of all files {all_file_names}"
        
        # Property: Number of detected files should be less than or equal to total files
        assert len(detected_changed_files) <= num_total_files, \
            f"Detected {len(detected_changed_files)} files, but total is only {num_total_files}"
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


# Additional property tests for CI/CD integration

# Test SARIF output format
@given(result=analysis_result_strategy())
@settings(max_examples=50, deadline=None)
def test_property_sarif_output_format(result):
    """
    Property: SARIF output should be valid JSON with required structure.
    
    For any analysis result, the SARIF output should be valid JSON that
    conforms to the SARIF 2.1.0 schema.
    """
    sarif_output = OutputFormatter.to_sarif(result)
    
    # Property: Output should be valid JSON
    sarif_doc = json.loads(sarif_output)
    
    # Property: Should have required SARIF fields
    assert "version" in sarif_doc
    assert sarif_doc["version"] == "2.1.0"
    assert "$schema" in sarif_doc
    assert "runs" in sarif_doc
    assert len(sarif_doc["runs"]) > 0
    
    # Property: Run should have tool and results
    run = sarif_doc["runs"][0]
    assert "tool" in run
    assert "results" in run
    assert "properties" in run
    
    # Property: Tool should have driver with name and rules
    assert "driver" in run["tool"]
    assert "name" in run["tool"]["driver"]
    assert "rules" in run["tool"]["driver"]
    
    # Property: Number of SARIF results should match total issues
    assert len(run["results"]) == result.total_issues


# Test JSON output format
@given(result=analysis_result_strategy())
@settings(max_examples=50, deadline=None)
def test_property_json_output_format(result):
    """
    Property: JSON output should be valid and preserve all data.
    
    For any analysis result, the JSON output should be valid JSON that
    can be parsed back into an equivalent structure.
    """
    json_output = OutputFormatter.to_json(result)
    
    # Property: Output should be valid JSON
    parsed = json.loads(json_output)
    
    # Property: Should have required fields
    assert "session_id" in parsed
    assert "timestamp" in parsed
    assert "codebase_path" in parsed
    assert "files_analyzed" in parsed
    assert "total_issues" in parsed
    assert "quality_score" in parsed
    assert "file_analyses" in parsed
    
    # Property: Numeric fields should match
    assert parsed["files_analyzed"] == result.files_analyzed
    assert parsed["total_issues"] == result.total_issues
    assert abs(parsed["quality_score"] - result.quality_score) < 0.01


# Test exit code handling
@given(
    result=analysis_result_strategy(),
    fail_on_critical=st.booleans(),
    fail_on_high=st.booleans()
)
@settings(max_examples=100, deadline=None)
def test_property_exit_code_handling(result, fail_on_critical, fail_on_high):
    """
    Property: Exit code should correctly reflect failure conditions.
    
    For any analysis result and failure configuration, the exit code
    should be 1 if failure conditions are met, 0 otherwise.
    """
    exit_code = ExitCodeHandler.get_exit_code(
        result,
        fail_on_critical=fail_on_critical,
        fail_on_high=fail_on_high
    )
    
    # Count critical and high issues
    critical_count = sum(
        1 for fa in result.file_analyses
        for issue in fa.issues
        if issue.severity == IssueSeverity.CRITICAL
    )
    high_count = sum(
        1 for fa in result.file_analyses
        for issue in fa.issues
        if issue.severity == IssueSeverity.HIGH
    )
    
    # Property: Exit code should be 0 or 1
    assert exit_code in [0, 1]
    
    # Property: Should fail if critical issues exist and fail_on_critical is True
    if fail_on_critical and critical_count > 0:
        assert exit_code == 1
    
    # Property: Should fail if high issues exist and fail_on_high is True
    if fail_on_high and high_count > 0:
        assert exit_code == 1
    
    # Property: Should pass if no failure conditions are met
    if not (fail_on_critical and critical_count > 0) and not (fail_on_high and high_count > 0):
        assert exit_code == 0


# Test max issues threshold
@given(
    result=analysis_result_strategy(),
    max_issues=st.integers(min_value=0, max_value=100)
)
@settings(max_examples=100, deadline=None)
def test_property_max_issues_threshold(result, max_issues):
    """
    Property: Exit code should fail if total issues exceed threshold.
    
    For any analysis result and max_issues threshold, the exit code
    should be 1 if total issues exceed the threshold.
    """
    exit_code = ExitCodeHandler.get_exit_code(
        result,
        fail_on_critical=False,
        fail_on_high=False,
        max_issues=max_issues
    )
    
    # Property: Exit code should be 0 or 1
    assert exit_code in [0, 1]
    
    # Property: Should fail if total issues exceed threshold
    if result.total_issues > max_issues:
        assert exit_code == 1
    else:
        assert exit_code == 0


# Test configuration file loading
def test_property_config_file_loading():
    """
    Property: Configuration files should be loadable and valid.
    
    For any valid YAML or JSON configuration file, the loader should
    successfully parse it and return a dictionary.
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Test YAML config
        yaml_config_path = Path(temp_dir) / "config.yaml"
        yaml_config_path.write_text("""
analysis_depth: quick
enable_parallel: true
fail_on_critical: true
fail_on_high: false
output_format: sarif
exclude_patterns:
  - node_modules/**
  - venv/**
""")
        
        config = CICDConfigLoader.load_config(str(yaml_config_path))
        
        # Property: Config should be a dictionary
        assert isinstance(config, dict)
        
        # Property: Config should have expected keys
        assert "analysis_depth" in config
        assert "enable_parallel" in config
        assert "fail_on_critical" in config
        
        # Property: Values should match what was written
        assert config["analysis_depth"] == "quick"
        assert config["enable_parallel"] is True
        assert config["fail_on_critical"] is True
        
        # Test JSON config
        json_config_path = Path(temp_dir) / "config.json"
        json_config_path.write_text(json.dumps({
            "analysis_depth": "standard",
            "enable_parallel": False,
            "fail_on_critical": False
        }))
        
        config = CICDConfigLoader.load_config(str(json_config_path))
        
        # Property: Config should be a dictionary
        assert isinstance(config, dict)
        
        # Property: Values should match
        assert config["analysis_depth"] == "standard"
        assert config["enable_parallel"] is False
        
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


# Test PR mode configuration
def test_property_pr_mode_config():
    """
    Property: PR mode configuration should have sensible defaults.
    
    The default PR mode configuration should be optimized for quick
    analysis with appropriate failure conditions.
    """
    config = CICDConfigLoader.get_pr_mode_config()
    
    # Property: Config should be a dictionary
    assert isinstance(config, dict)
    
    # Property: Should have required keys
    assert "analysis_depth" in config
    assert "enable_parallel" in config
    assert "fail_on_critical" in config
    assert "output_format" in config
    assert "exclude_patterns" in config
    
    # Property: Analysis depth should be quick for PR mode
    assert config["analysis_depth"] == "quick"
    
    # Property: Parallel processing should be enabled
    assert config["enable_parallel"] is True
    
    # Property: Should fail on critical issues by default
    assert config["fail_on_critical"] is True
    
    # Property: Output format should be SARIF for CI/CD integration
    assert config["output_format"] == "sarif"
    
    # Property: Should have common exclude patterns
    assert isinstance(config["exclude_patterns"], list)
    assert len(config["exclude_patterns"]) > 0
