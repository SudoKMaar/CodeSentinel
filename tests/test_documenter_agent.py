"""
Tests for the Documenter Agent.

This module contains unit tests and property-based tests for the
DocumenterAgent class and its documentation generation capabilities.
"""

import pytest
from hypothesis import given, strategies as st, settings
from pathlib import Path
import tempfile
import shutil
from typing import List

from agents.documenter_agent import DocumenterAgent, CodebaseStructure
from models.data_models import (
    FileAnalysis,
    CodeMetrics,
    FunctionInfo,
    ClassInfo,
    Documentation,
)


# ============================================================================
# Hypothesis Strategies for Generating Test Data
# ============================================================================

@st.composite
def function_info_strategy(draw):
    """Generate random FunctionInfo objects."""
    name = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll'), min_codepoint=97, max_codepoint=122
    )))
    line_number = draw(st.integers(min_value=1, max_value=1000))
    num_params = draw(st.integers(min_value=0, max_value=5))
    parameters = [f"param{i}" for i in range(num_params)]
    docstring = draw(st.one_of(st.none(), st.text(min_size=10, max_size=100)))
    complexity = draw(st.integers(min_value=1, max_value=50))
    
    return FunctionInfo(
        name=name,
        line_number=line_number,
        parameters=parameters,
        return_type=None,
        docstring=docstring,
        complexity=complexity
    )


@st.composite
def class_info_strategy(draw):
    """Generate random ClassInfo objects."""
    name = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll'), min_codepoint=97, max_codepoint=122
    )))
    line_number = draw(st.integers(min_value=1, max_value=1000))
    num_methods = draw(st.integers(min_value=0, max_value=5))
    methods = [f"method{i}" for i in range(num_methods)]
    base_classes = draw(st.lists(st.text(min_size=1, max_size=15), max_size=3))
    docstring = draw(st.one_of(st.none(), st.text(min_size=10, max_size=100)))
    
    return ClassInfo(
        name=name,
        line_number=line_number,
        methods=methods,
        base_classes=base_classes,
        docstring=docstring
    )


@st.composite
def file_analysis_strategy(draw):
    """Generate random FileAnalysis objects."""
    file_path = draw(st.text(min_size=5, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=47, max_codepoint=122
    )))
    # Ensure valid file path
    if not file_path.endswith('.py'):
        file_path = file_path + '.py'
    
    language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
    
    metrics = CodeMetrics(
        cyclomatic_complexity=draw(st.integers(min_value=1, max_value=50)),
        maintainability_index=draw(st.floats(min_value=0.0, max_value=100.0)),
        lines_of_code=draw(st.integers(min_value=1, max_value=1000)),
        comment_ratio=draw(st.floats(min_value=0.0, max_value=1.0)),
        test_coverage=None
    )
    
    functions = draw(st.lists(function_info_strategy(), min_size=0, max_size=5))
    classes = draw(st.lists(class_info_strategy(), min_size=0, max_size=3))
    
    return FileAnalysis(
        file_path=file_path,
        language=language,
        metrics=metrics,
        issues=[],
        functions=functions,
        classes=classes
    )


@st.composite
def codebase_structure_strategy(draw):
    """Generate random CodebaseStructure objects."""
    root_path = draw(st.text(min_size=1, max_size=20))
    structure = CodebaseStructure(root_path)
    
    num_files = draw(st.integers(min_value=1, max_value=10))
    for i in range(num_files):
        file_path = f"module{i % 3}/file{i}.py"
        language = draw(st.sampled_from(['python', 'javascript', 'typescript']))
        structure.add_file(file_path, language)
    
    return structure


# ============================================================================
# Property-Based Tests
# ============================================================================

# Feature: code-review-documentation-agent, Property 7: Documentation Generation Completeness
@given(
    codebase_structure=codebase_structure_strategy(),
    file_analyses=st.lists(file_analysis_strategy(), min_size=1, max_size=3, unique_by=lambda x: x.file_path)
)
@settings(max_examples=100, deadline=2000)
def test_property_documentation_generation_completeness(
    codebase_structure: CodebaseStructure,
    file_analyses: List[FileAnalysis]
):
    """
    Property 7: Documentation Generation Completeness
    
    For any codebase, generated documentation should include:
    - Project structure documentation
    - API documentation with parameters and return types
    - Code examples
    - A hierarchy matching the code structure
    
    Validates: Requirements 3.1, 3.2, 3.4, 3.5
    """
    agent = DocumenterAgent(output_dir="temp_test_docs")
    
    # Generate project structure documentation
    project_docs = agent.generate_project_docs(codebase_structure)
    
    # Verify project structure documentation is not empty
    assert project_docs, "Project structure documentation should not be empty"
    assert "# Project Structure" in project_docs, "Should have project structure header"
    assert f"Root: `{codebase_structure.root_path}`" in project_docs, "Should include root path"
    assert "Total files:" in project_docs, "Should include file count"
    assert "Total directories:" in project_docs, "Should include directory count"
    
    # Generate API documentation
    api_docs = agent.generate_api_docs(file_analyses)
    
    # Verify API documentation is generated for files with functions/classes
    files_with_content = [
        fa for fa in file_analyses 
        if fa.functions or fa.classes
    ]
    
    if files_with_content:
        assert api_docs, "API documentation should be generated for files with content"
        
        # Verify all files with content have some documentation
        assert len(api_docs) >= len(files_with_content), "Should have docs for all files with content"
    
    # Generate code examples
    examples = agent.generate_code_examples(file_analyses, max_examples=2)
    
    # Verify examples are generated if there are public functions/classes
    public_functions = [
        func for fa in file_analyses 
        for func in fa.functions 
        if not func.name.startswith('_')
    ]
    public_classes = [
        cls for fa in file_analyses 
        for cls in fa.classes
    ]
    
    if public_functions or public_classes:
        assert examples, "Code examples should be generated"
        
        # Verify examples contain code blocks
        for title, content in examples.items():
            assert content, f"Example '{title}' should have content"
            assert "```" in content, f"Example '{title}' should contain code block"
    
    # Organize documentation
    documentation = agent.organize_documentation(project_docs, api_docs, examples)
    
    # Verify documentation structure
    assert documentation.project_structure == project_docs, "Should preserve project structure"
    assert documentation.api_docs == api_docs, "Should preserve API docs"
    assert documentation.examples == examples, "Should preserve examples"


# ============================================================================
# Unit Tests
# ============================================================================

def test_documenter_agent_initialization():
    """Test DocumenterAgent initialization."""
    with tempfile.TemporaryDirectory() as temp_dir:
        agent = DocumenterAgent(output_dir=temp_dir)
        assert agent.output_dir == temp_dir
        assert Path(temp_dir).exists()


def test_generate_project_docs_basic():
    """Test basic project documentation generation."""
    structure = CodebaseStructure("/test/project")
    structure.add_file("module1/file1.py", "python")
    structure.add_file("module1/file2.py", "python")
    structure.add_file("module2/file3.js", "javascript")
    
    agent = DocumenterAgent()
    docs = agent.generate_project_docs(structure)
    
    assert "# Project Structure" in docs
    assert "/test/project" in docs
    assert "Total files: 3" in docs
    assert "python: 2 files" in docs
    assert "javascript: 1 files" in docs


def test_generate_api_docs_with_functions():
    """Test API documentation generation for functions."""
    analysis = FileAnalysis(
        file_path="test/module.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=5,
            maintainability_index=80.0,
            lines_of_code=100,
            comment_ratio=0.2
        ),
        issues=[],
        functions=[
            FunctionInfo(
                name="test_function",
                line_number=10,
                parameters=["arg1", "arg2"],
                return_type=None,
                docstring="Test function docstring",
                complexity=3
            )
        ],
        classes=[]
    )
    
    agent = DocumenterAgent()
    api_docs = agent.generate_api_docs([analysis])
    
    assert api_docs
    module_name = "test.module"
    assert module_name in api_docs
    
    doc_content = api_docs[module_name]
    assert "test_function" in doc_content
    assert "arg1" in doc_content
    assert "arg2" in doc_content
    assert "Test function docstring" in doc_content


def test_generate_api_docs_with_classes():
    """Test API documentation generation for classes."""
    analysis = FileAnalysis(
        file_path="test/module.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=5,
            maintainability_index=80.0,
            lines_of_code=100,
            comment_ratio=0.2
        ),
        issues=[],
        functions=[],
        classes=[
            ClassInfo(
                name="TestClass",
                line_number=5,
                methods=["method1", "method2"],
                base_classes=["BaseClass"],
                docstring="Test class docstring"
            )
        ]
    )
    
    agent = DocumenterAgent()
    api_docs = agent.generate_api_docs([analysis])
    
    assert api_docs
    module_name = "test.module"
    assert module_name in api_docs
    
    doc_content = api_docs[module_name]
    assert "TestClass" in doc_content
    assert "method1" in doc_content
    assert "method2" in doc_content
    assert "BaseClass" in doc_content
    assert "Test class docstring" in doc_content


def test_generate_code_examples():
    """Test code example generation."""
    analysis = FileAnalysis(
        file_path="test/module.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=5,
            maintainability_index=80.0,
            lines_of_code=100,
            comment_ratio=0.2
        ),
        issues=[],
        functions=[
            FunctionInfo(
                name="public_function",
                line_number=10,
                parameters=["arg1"],
                return_type=None,
                docstring=None,
                complexity=2
            )
        ],
        classes=[
            ClassInfo(
                name="ExampleClass",
                line_number=20,
                methods=["do_something"],
                base_classes=[],
                docstring=None
            )
        ]
    )
    
    agent = DocumenterAgent()
    examples = agent.generate_code_examples([analysis], max_examples=5)
    
    assert examples
    assert any("ExampleClass" in title for title in examples.keys())
    assert any("public_function" in title for title in examples.keys())
    
    # Verify examples contain code blocks
    for content in examples.values():
        assert "```" in content


def test_organize_documentation():
    """Test documentation organization."""
    agent = DocumenterAgent()
    
    project_docs = "# Project Structure\nTest content"
    api_docs = {"module1": "API docs for module1"}
    examples = {"Example 1": "```python\ncode\n```"}
    
    documentation = agent.organize_documentation(project_docs, api_docs, examples)
    
    assert documentation.project_structure == project_docs
    assert documentation.api_docs == api_docs
    assert documentation.examples == examples


def test_write_and_load_documentation():
    """Test writing and loading documentation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        agent = DocumenterAgent(output_dir=temp_dir)
        
        # Create documentation
        documentation = Documentation(
            project_structure="# Project\nTest structure",
            api_docs={"module1": "API docs"},
            examples={"Example": "```python\ncode\n```"}
        )
        
        # Write documentation
        agent.write_documentation(documentation)
        
        # Verify files exist
        assert (Path(temp_dir) / "PROJECT_STRUCTURE.md").exists()
        assert (Path(temp_dir) / "api" / "module1.md").exists()
        assert (Path(temp_dir) / "EXAMPLES.md").exists()
        
        # Load documentation
        loaded_docs = agent.load_existing_documentation()
        
        assert loaded_docs is not None
        assert loaded_docs.project_structure == documentation.project_structure
        assert "module1" in loaded_docs.api_docs
        assert loaded_docs.examples


# Feature: code-review-documentation-agent, Property 8: Documentation Idempotence
@given(
    codebase_structure=codebase_structure_strategy(),
    file_analyses=st.lists(file_analysis_strategy(), min_size=1, max_size=3, unique_by=lambda x: x.file_path)
)
@settings(max_examples=100, deadline=2000)
def test_property_documentation_idempotence(
    codebase_structure: CodebaseStructure,
    file_analyses: List[FileAnalysis]
):
    """
    Property 8: Documentation Idempotence
    
    For any codebase, running documentation generation multiple times
    should update existing documentation rather than creating duplicates.
    
    Validates: Requirements 3.3
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        agent = DocumenterAgent(output_dir=temp_dir)
        
        # First generation
        project_docs_1 = agent.generate_project_docs(codebase_structure)
        api_docs_1 = agent.generate_api_docs(file_analyses)
        examples_1 = agent.generate_code_examples(file_analyses, max_examples=2)
        
        documentation_1 = agent.organize_documentation(project_docs_1, api_docs_1, examples_1)
        agent.write_documentation(documentation_1)
        
        # Count files after first generation
        output_path = Path(temp_dir)
        files_after_first = list(output_path.rglob("*.md"))
        first_count = len(files_after_first)
        
        # Load existing documentation
        existing_docs = agent.load_existing_documentation()
        assert existing_docs is not None, "Should be able to load existing documentation"
        
        # Second generation with same data
        project_docs_2 = agent.generate_project_docs(codebase_structure)
        api_docs_2 = agent.generate_api_docs(file_analyses)
        examples_2 = agent.generate_code_examples(file_analyses, max_examples=2)
        
        documentation_2 = agent.organize_documentation(project_docs_2, api_docs_2, examples_2)
        
        # Update existing documentation
        updated_docs = agent.update_existing_docs(existing_docs, documentation_2)
        agent.write_documentation(updated_docs)
        
        # Count files after second generation
        files_after_second = list(output_path.rglob("*.md"))
        second_count = len(files_after_second)
        
        # Verify no duplicate files were created
        assert second_count == first_count, "Should not create duplicate files"
        
        # Verify content is updated, not duplicated by checking for duplicate sections
        if api_docs_1:
            for module in api_docs_1.keys():
                api_file = output_path / "api" / f"{module.replace('.', '_')}.md"
                if api_file.exists():
                    content = api_file.read_text(encoding='utf-8')
                    # Check that "## Functions" header doesn't appear multiple times
                    functions_header_count = content.count("## Functions")
                    assert functions_header_count <= 1, f"Functions section appears {functions_header_count} times, suggesting duplication"
                    
                    # Check that "## Classes" header doesn't appear multiple times
                    classes_header_count = content.count("## Classes")
                    assert classes_header_count <= 1, f"Classes section appears {classes_header_count} times, suggesting duplication"
        
        # Verify the updated documentation has the same structure
        assert updated_docs.project_structure, "Should have project structure"
        assert len(updated_docs.api_docs) == len(documentation_2.api_docs), "Should have same number of API docs"
        assert len(updated_docs.examples) == len(documentation_2.examples), "Should have same number of examples"
