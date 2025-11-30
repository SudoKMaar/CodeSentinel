"""
Property-based tests for code parsing tools.

Feature: code-review-documentation-agent
"""

from typing import Tuple
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import SearchStrategy

from tools.code_parser import CodeParserTool


# Custom strategies for generating valid source code

@st.composite
def valid_python_code_strategy(draw: st.DrawFn) -> str:
    """Generate valid Python code samples."""
    # Python reserved keywords to avoid
    python_keywords = {
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
        'try', 'while', 'with', 'yield'
    }
    
    # Generate simple but valid Python code structures
    code_type = draw(st.sampled_from([
        'function',
        'class',
        'simple_statement',
        'import',
        'assignment'
    ]))
    
    if code_type == 'function':
        func_name = draw(st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=10
        ))
        # Ensure function name is not a reserved keyword
        assume(func_name not in python_keywords)
        param_count = draw(st.integers(min_value=0, max_value=3))
        params = ', '.join([f'param{i}' for i in range(param_count)])
        
        return f"""def {func_name}({params}):
    \"\"\"A test function.\"\"\"
    return None
"""
    
    elif code_type == 'class':
        class_name = draw(st.text(
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
            min_size=1,
            max_size=10
        ))
        
        return f"""class {class_name}:
    \"\"\"A test class.\"\"\"
    
    def __init__(self):
        self.value = 0
    
    def method(self):
        return self.value
"""
    
    elif code_type == 'simple_statement':
        return "x = 42\n"
    
    elif code_type == 'import':
        module = draw(st.sampled_from(['os', 'sys', 'json', 'math']))
        return f"import {module}\n"
    
    else:  # assignment
        var_name = draw(st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=10
        ))
        value = draw(st.integers(min_value=0, max_value=1000))
        return f"{var_name} = {value}\n"


@st.composite
def valid_javascript_code_strategy(draw: st.DrawFn) -> str:
    """Generate valid JavaScript code samples."""
    # JavaScript reserved keywords to avoid
    js_keywords = {
        'abstract', 'arguments', 'await', 'boolean', 'break', 'byte', 'case',
        'catch', 'char', 'class', 'const', 'continue', 'debugger', 'default',
        'delete', 'do', 'double', 'else', 'enum', 'eval', 'export', 'extends',
        'false', 'final', 'finally', 'float', 'for', 'function', 'goto', 'if',
        'implements', 'import', 'in', 'instanceof', 'int', 'interface', 'let',
        'long', 'native', 'new', 'null', 'package', 'private', 'protected',
        'public', 'return', 'short', 'static', 'super', 'switch', 'synchronized',
        'this', 'throw', 'throws', 'transient', 'true', 'try', 'typeof', 'var',
        'void', 'volatile', 'while', 'with', 'yield'
    }
    
    code_type = draw(st.sampled_from([
        'function',
        'arrow_function',
        'class',
        'variable',
        'const'
    ]))
    
    if code_type == 'function':
        func_name = draw(st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=10
        ))
        # Ensure function name is not a reserved keyword
        assume(func_name not in js_keywords)
        param_count = draw(st.integers(min_value=0, max_value=3))
        params = ', '.join([f'param{i}' for i in range(param_count)])
        
        return f"""function {func_name}({params}) {{
    return null;
}}
"""
    
    elif code_type == 'arrow_function':
        func_name = draw(st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=10
        ))
        # Ensure function name is not a reserved keyword
        assume(func_name not in js_keywords)
        
        return f"""const {func_name} = () => {{
    return 42;
}};
"""
    
    elif code_type == 'class':
        class_name = draw(st.text(
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
            min_size=1,
            max_size=10
        ))
        
        return f"""class {class_name} {{
    constructor() {{
        this.value = 0;
    }}
    
    method() {{
        return this.value;
    }}
}}
"""
    
    elif code_type == 'variable':
        var_name = draw(st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=10
        ))
        value = draw(st.integers(min_value=0, max_value=1000))
        return f"let {var_name} = {value};\n"
    
    else:  # const
        var_name = draw(st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=10
        ))
        value = draw(st.integers(min_value=0, max_value=1000))
        return f"const {var_name} = {value};\n"


@st.composite
def valid_typescript_code_strategy(draw: st.DrawFn) -> str:
    """Generate valid TypeScript code samples."""
    code_type = draw(st.sampled_from([
        'function',
        'interface',
        'type_alias',
        'class'
    ]))
    
    if code_type == 'function':
        func_name = draw(st.text(
            alphabet=st.characters(min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=10
        ))
        
        return f"""function {func_name}(x: number): number {{
    return x * 2;
}}
"""
    
    elif code_type == 'interface':
        interface_name = draw(st.text(
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
            min_size=1,
            max_size=10
        ))
        
        return f"""interface {interface_name} {{
    id: number;
    name: string;
}}
"""
    
    elif code_type == 'type_alias':
        type_name = draw(st.text(
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
            min_size=1,
            max_size=10
        ))
        
        return f"type {type_name} = string | number;\n"
    
    else:  # class
        class_name = draw(st.text(
            alphabet=st.characters(min_codepoint=65, max_codepoint=90),
            min_size=1,
            max_size=10
        ))
        
        return f"""class {class_name} {{
    private value: number;
    
    constructor() {{
        this.value = 0;
    }}
    
    getValue(): number {{
        return this.value;
    }}
}}
"""


@st.composite
def valid_code_with_language_strategy(draw: st.DrawFn) -> Tuple[str, str]:
    """
    Generate valid source code with its language.
    
    Returns:
        Tuple of (source_code, language)
    """
    language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
    
    if language == 'python':
        code = draw(valid_python_code_strategy())
    elif language == 'javascript':
        code = draw(valid_javascript_code_strategy())
    else:  # typescript
        code = draw(valid_typescript_code_strategy())
    
    return code, language


# Property-based tests

# Feature: code-review-documentation-agent, Property 2: Valid Code Parsing
# Validates: Requirements 1.2

@settings(max_examples=100, deadline=None)
@given(valid_code_with_language_strategy())
def test_valid_code_parsing(code_data: Tuple[str, str]) -> None:
    """
    Property 2: Valid Code Parsing
    For any valid source file in a supported language, parsing should
    successfully produce a valid AST representation.
    """
    source_code, language = code_data
    
    tool = CodeParserTool()
    
    # Parse the code
    tree = tool.parse_code(source_code, language)
    
    # Verify parsing succeeded
    assert tree is not None, f"Failed to parse valid {language} code:\n{source_code}"
    
    # Verify we can get the root node
    root = tool.get_root_node(tree)
    assert root is not None
    
    # Verify the tree has no syntax errors
    has_errors = tool.has_syntax_errors(tree)
    assert not has_errors, f"Valid {language} code should not have syntax errors:\n{source_code}"
    
    # Verify we can get text from the root node
    node_text = tool.get_node_text(root)
    assert isinstance(node_text, str)
    assert len(node_text) > 0


@settings(max_examples=50, deadline=None)
@given(valid_python_code_strategy())
def test_python_function_extraction(python_code: str) -> None:
    """
    Property: Python function extraction works for valid code.
    For any valid Python code containing functions, extraction should succeed.
    """
    tool = CodeParserTool()
    
    tree = tool.parse_code(python_code, 'python')
    assert tree is not None
    
    # Extract functions
    functions = tool.extract_functions(tree, 'python')
    
    # Verify extraction returns a list
    assert isinstance(functions, list)
    
    # If code contains 'def ', it should extract at least one function
    if 'def ' in python_code:
        assert len(functions) > 0, f"Should extract functions from:\n{python_code}"
        
        # Verify function info structure
        for func in functions:
            assert 'name' in func
            assert 'line_number' in func
            assert 'parameters' in func
            assert isinstance(func['parameters'], list)


@settings(max_examples=50, deadline=None)
@given(valid_javascript_code_strategy())
def test_javascript_function_extraction(js_code: str) -> None:
    """
    Property: JavaScript function extraction works for valid code.
    For any valid JavaScript code containing functions, extraction should succeed.
    """
    tool = CodeParserTool()
    
    tree = tool.parse_code(js_code, 'javascript')
    assert tree is not None
    
    # Extract functions
    functions = tool.extract_functions(tree, 'javascript')
    
    # Verify extraction returns a list
    assert isinstance(functions, list)
    
    # If code contains 'function ' or '=>', it should extract at least one function
    if 'function ' in js_code or '=>' in js_code:
        assert len(functions) > 0, f"Should extract functions from:\n{js_code}"
        
        # Verify function info structure
        for func in functions:
            assert 'name' in func
            assert 'line_number' in func
            assert 'parameters' in func


@settings(max_examples=50, deadline=None)
@given(valid_python_code_strategy())
def test_python_class_extraction(python_code: str) -> None:
    """
    Property: Python class extraction works for valid code.
    For any valid Python code containing classes, extraction should succeed.
    """
    tool = CodeParserTool()
    
    tree = tool.parse_code(python_code, 'python')
    assert tree is not None
    
    # Extract classes
    classes = tool.extract_classes(tree, 'python')
    
    # Verify extraction returns a list
    assert isinstance(classes, list)
    
    # If code contains 'class ', it should extract at least one class
    if 'class ' in python_code:
        assert len(classes) > 0, f"Should extract classes from:\n{python_code}"
        
        # Verify class info structure
        for cls in classes:
            assert 'name' in cls
            assert 'line_number' in cls
            assert 'methods' in cls
            assert isinstance(cls['methods'], list)


def test_language_detection() -> None:
    """
    Test that language detection works correctly for supported file extensions.
    """
    tool = CodeParserTool()
    
    # Test Python
    assert tool.detect_language('test.py') == 'python'
    assert tool.detect_language('/path/to/file.py') == 'python'
    
    # Test JavaScript
    assert tool.detect_language('test.js') == 'javascript'
    assert tool.detect_language('test.jsx') == 'javascript'
    
    # Test TypeScript
    assert tool.detect_language('test.ts') == 'typescript'
    assert tool.detect_language('test.tsx') == 'tsx'
    
    # Test unsupported
    assert tool.detect_language('test.txt') is None
    assert tool.detect_language('test.md') is None


def test_unsupported_language() -> None:
    """
    Test that parsing with unsupported language raises ValueError.
    """
    tool = CodeParserTool()
    
    try:
        tool.parse_code("some code", "unsupported_language")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported language" in str(e)


def test_parse_file_integration() -> None:
    """
    Test that parse_file correctly detects language and parses code.
    """
    tool = CodeParserTool()
    
    # Test Python file
    python_code = "def test():\n    return 42\n"
    tree = tool.parse_file('test.py', python_code)
    assert tree is not None
    assert not tool.has_syntax_errors(tree)
    
    # Test JavaScript file
    js_code = "function test() { return 42; }"
    tree = tool.parse_file('test.js', js_code)
    assert tree is not None
    assert not tool.has_syntax_errors(tree)
    
    # Test unsupported file
    tree = tool.parse_file('test.txt', "some text")
    assert tree is None
