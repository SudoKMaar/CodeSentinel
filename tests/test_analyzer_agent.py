"""
Property-based tests for Analyzer Agent.

Feature: code-review-documentation-agent
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from typing import List, Tuple

from agents.analyzer_agent import AnalyzerAgent
from models.data_models import IssueCategory


# Helper functions to generate valid Python code with known complexity

def generate_simple_function(name: str = "test_func") -> str:
    """Generate a simple function with complexity 1."""
    return f"""def {name}():
    return 42
"""


def generate_function_with_if(name: str = "test_func", num_ifs: int = 1) -> str:
    """Generate a function with if statements (complexity = 1 + num_ifs)."""
    code = f"def {name}(x):\n"
    for i in range(num_ifs):
        code += f"    if x > {i}:\n"
        code += f"        return {i}\n"
    code += "    return 0\n"
    return code


def generate_function_with_loops(name: str = "test_func", num_loops: int = 1) -> str:
    """Generate a function with loops (complexity = 1 + num_loops)."""
    code = f"def {name}(items):\n"
    code += "    result = 0\n"
    for i in range(num_loops):
        code += f"    for item in items:\n"
        code += f"        result += item\n"
    code += "    return result\n"
    return code


def generate_function_with_complexity(name: str, complexity: int) -> str:
    """
    Generate a function with specific cyclomatic complexity.
    
    Complexity is achieved by adding if statements.
    Complexity = 1 + number of decision points
    """
    if complexity < 1:
        complexity = 1
    
    num_ifs = complexity - 1
    return generate_function_with_if(name, num_ifs)


# Property-based tests

# Feature: code-review-documentation-agent, Property 4: Complexity Calculation Accuracy
# Validates: Requirements 2.1

@settings(max_examples=100)
@given(
    st.integers(min_value=1, max_value=20),
    st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),
        min_size=5,
        max_size=15
    )
)
def test_complexity_calculation_accuracy(complexity: int, func_name: str) -> None:
    """
    Property 4: Complexity Calculation Accuracy
    
    For any function with a known cyclomatic complexity, the calculated
    complexity should match the actual number of linearly independent paths.
    
    Validates: Requirements 2.1
    """
    # Generate function with known complexity
    source_code = generate_function_with_complexity(func_name, complexity)
    
    # Create analyzer
    analyzer = AnalyzerAgent()
    
    # Analyze the code
    result = analyzer.analyze_file("test.py", source_code)
    
    # Verify analysis succeeded
    assert result is not None, "Analysis should succeed for valid Python code"
    
    # Verify we found the function
    assert len(result.functions) == 1, "Should find exactly one function"
    
    # Verify complexity matches expected value
    calculated_complexity = result.functions[0].complexity
    assert calculated_complexity == complexity, \
        f"Expected complexity {complexity}, got {calculated_complexity}"


@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=5))
def test_complexity_with_multiple_ifs(num_ifs: int) -> None:
    """
    Property: Functions with N if statements have complexity N+1.
    
    Validates: Requirements 2.1
    """
    source_code = generate_function_with_if("test_func", num_ifs)
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    assert len(result.functions) == 1
    
    expected_complexity = 1 + num_ifs
    assert result.functions[0].complexity == expected_complexity


@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=5))
def test_complexity_with_loops(num_loops: int) -> None:
    """
    Property: Functions with N loops have complexity N+1.
    
    Validates: Requirements 2.1
    """
    source_code = generate_function_with_loops("test_func", num_loops)
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    assert len(result.functions) == 1
    
    expected_complexity = 1 + num_loops
    assert result.functions[0].complexity == expected_complexity


@settings(max_examples=100)
@given(st.integers(min_value=15, max_value=30))
def test_high_complexity_flagged(complexity: int) -> None:
    """
    Property: Functions exceeding threshold should be flagged.
    
    For any function with complexity >= 15, an issue should be reported.
    
    Validates: Requirements 2.1
    """
    source_code = generate_function_with_complexity("complex_func", complexity)
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    
    # Should have at least one complexity issue
    complexity_issues = [
        issue for issue in result.issues
        if issue.category == IssueCategory.COMPLEXITY
    ]
    
    assert len(complexity_issues) > 0, \
        f"Function with complexity {complexity} should be flagged"


# Feature: code-review-documentation-agent, Property 6: Error Handling Detection
# Validates: Requirements 2.5

def generate_code_with_file_operation(has_try: bool) -> str:
    """Generate code with file operation, optionally wrapped in try-except."""
    if has_try:
        return """def read_file(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except Exception as e:
        return None
"""
    else:
        return """def read_file(path):
    with open(path, 'r') as f:
        return f.read()
"""


def generate_code_with_json_parse(has_try: bool) -> str:
    """Generate code with JSON parsing, optionally wrapped in try-except."""
    if has_try:
        return """import json

def parse_json(data):
    try:
        return json.loads(data)
    except Exception as e:
        return None
"""
    else:
        return """import json

def parse_json(data):
    return json.loads(data)
"""


def generate_code_with_network_call(has_try: bool) -> str:
    """Generate code with network call, optionally wrapped in try-except."""
    if has_try:
        return """import requests

def fetch_data(url):
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return None
"""
    else:
        return """import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()
"""


@settings(max_examples=100)
@given(st.booleans())
def test_error_handling_detection_file_ops(has_error_handling: bool) -> None:
    """
    Property 6: Error Handling Detection
    
    For any code containing error-prone operations (file I/O), the analysis
    should identify locations missing proper error handling.
    
    Validates: Requirements 2.5
    """
    source_code = generate_code_with_file_operation(has_error_handling)
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    
    # Check for error handling issues
    error_handling_issues = [
        issue for issue in result.issues
        if issue.category == IssueCategory.ERROR_HANDLING
    ]
    
    if has_error_handling:
        # Should have no error handling issues
        assert len(error_handling_issues) == 0, \
            "Code with try-except should not be flagged"
    else:
        # Should have error handling issues
        assert len(error_handling_issues) > 0, \
            "Code without try-except should be flagged"


@settings(max_examples=100)
@given(st.booleans())
def test_error_handling_detection_json_parse(has_error_handling: bool) -> None:
    """
    Property: JSON parsing without error handling should be detected.
    
    Validates: Requirements 2.5
    """
    source_code = generate_code_with_json_parse(has_error_handling)
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    
    error_handling_issues = [
        issue for issue in result.issues
        if issue.category == IssueCategory.ERROR_HANDLING
    ]
    
    if has_error_handling:
        assert len(error_handling_issues) == 0
    else:
        assert len(error_handling_issues) > 0


@settings(max_examples=100)
@given(st.booleans())
def test_error_handling_detection_network_calls(has_error_handling: bool) -> None:
    """
    Property: Network calls without error handling should be detected.
    
    Validates: Requirements 2.5
    """
    source_code = generate_code_with_network_call(has_error_handling)
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    
    error_handling_issues = [
        issue for issue in result.issues
        if issue.category == IssueCategory.ERROR_HANDLING
    ]
    
    if has_error_handling:
        assert len(error_handling_issues) == 0
    else:
        assert len(error_handling_issues) > 0


# Additional unit tests for specific functionality

def test_simple_function_complexity():
    """Unit test: Simple function should have complexity 1."""
    source_code = generate_simple_function()
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    assert len(result.functions) == 1
    assert result.functions[0].complexity == 1


def test_security_sql_injection_detection():
    """Unit test: SQL injection patterns should be detected."""
    source_code = '''def query_user(user_id):
    cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
    return cursor.fetchall()
'''
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    
    security_issues = [
        issue for issue in result.issues
        if issue.category == IssueCategory.SECURITY
    ]
    
    assert len(security_issues) > 0


def test_security_hardcoded_secrets_detection():
    """Unit test: Hardcoded secrets should be detected."""
    source_code = '''def connect():
    password = "super_secret_password_123"
    api_key = "sk_live_1234567890abcdefghij"
    return connect_to_db(password, api_key)
'''
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    assert result is not None
    
    security_issues = [
        issue for issue in result.issues
        if issue.category == IssueCategory.SECURITY
    ]
    
    assert len(security_issues) > 0


def test_parallel_file_processing():
    """Unit test: Parallel processing should analyze multiple files."""
    files = [
        ("file1.py", generate_simple_function("func1")),
        ("file2.py", generate_simple_function("func2")),
        ("file3.py", generate_simple_function("func3")),
    ]
    
    analyzer = AnalyzerAgent(max_workers=2)
    results = analyzer.analyze_files_parallel(files)
    
    assert len(results) == 3
    for result in results:
        assert len(result.functions) == 1


def test_invalid_code_returns_none():
    """Unit test: Invalid code should return partial analysis with syntax error."""
    source_code = "def invalid syntax here"
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.py", source_code)
    
    # Should return partial analysis with syntax error issue (graceful degradation)
    assert result is not None
    assert result.file_path == "test.py"
    assert len(result.issues) > 0
    assert any("syntax" in issue.description.lower() for issue in result.issues)


def test_unsupported_language_returns_none():
    """Unit test: Unsupported file types should return None."""
    source_code = "some random text"
    
    analyzer = AnalyzerAgent()
    result = analyzer.analyze_file("test.txt", source_code)
    
    assert result is None
