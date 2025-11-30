"""
Demo script for the Documenter Agent.

This script demonstrates how to use the DocumenterAgent to generate
documentation for a codebase.
"""

from agents.documenter_agent import DocumenterAgent, CodebaseStructure
from models.data_models import (
    FileAnalysis,
    CodeMetrics,
    FunctionInfo,
    ClassInfo,
)


def main():
    """Run the Documenter Agent demo."""
    print("=" * 60)
    print("Documenter Agent Demo")
    print("=" * 60)
    
    # Create a documenter agent
    agent = DocumenterAgent(output_dir="demo_docs")
    print("\n✓ Created DocumenterAgent with output directory: demo_docs")
    
    # Create a sample codebase structure
    structure = CodebaseStructure("/demo/project")
    structure.add_file("src/main.py", "python")
    structure.add_file("src/utils.py", "python")
    structure.add_file("src/models/user.py", "python")
    structure.add_file("src/models/post.py", "python")
    structure.add_file("tests/test_main.py", "python")
    print("\n✓ Created sample codebase structure with 5 files")
    
    # Generate project structure documentation
    print("\n" + "-" * 60)
    print("Generating Project Structure Documentation")
    print("-" * 60)
    project_docs = agent.generate_project_docs(structure)
    print(project_docs[:500] + "...")
    
    # Create sample file analyses
    file_analyses = [
        FileAnalysis(
            file_path="src/main.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=5,
                maintainability_index=75.0,
                lines_of_code=150,
                comment_ratio=0.15
            ),
            issues=[],
            functions=[
                FunctionInfo(
                    name="main",
                    line_number=10,
                    parameters=[],
                    return_type="None",
                    docstring="Main entry point for the application.",
                    complexity=3
                ),
                FunctionInfo(
                    name="process_data",
                    line_number=25,
                    parameters=["data", "options"],
                    return_type="dict",
                    docstring="Process input data with given options.",
                    complexity=5
                )
            ],
            classes=[]
        ),
        FileAnalysis(
            file_path="src/models/user.py",
            language="python",
            metrics=CodeMetrics(
                cyclomatic_complexity=8,
                maintainability_index=80.0,
                lines_of_code=200,
                comment_ratio=0.20
            ),
            issues=[],
            functions=[],
            classes=[
                ClassInfo(
                    name="User",
                    line_number=5,
                    methods=["__init__", "save", "delete", "update"],
                    base_classes=["BaseModel"],
                    docstring="User model representing a system user."
                )
            ]
        )
    ]
    print("\n✓ Created sample file analyses")
    
    # Generate API documentation
    print("\n" + "-" * 60)
    print("Generating API Documentation")
    print("-" * 60)
    api_docs = agent.generate_api_docs(file_analyses)
    print(f"Generated API docs for {len(api_docs)} modules:")
    for module in api_docs.keys():
        print(f"  - {module}")
    
    # Generate code examples
    print("\n" + "-" * 60)
    print("Generating Code Examples")
    print("-" * 60)
    examples = agent.generate_code_examples(file_analyses, max_examples=3)
    print(f"Generated {len(examples)} code examples:")
    for title in examples.keys():
        print(f"  - {title}")
    
    # Organize documentation
    documentation = agent.organize_documentation(project_docs, api_docs, examples)
    print("\n✓ Organized documentation into structured format")
    
    # Write documentation to files
    print("\n" + "-" * 60)
    print("Writing Documentation to Files")
    print("-" * 60)
    agent.write_documentation(documentation)
    print("✓ Documentation written to demo_docs/")
    print("  - PROJECT_STRUCTURE.md")
    print("  - api/*.md")
    print("  - EXAMPLES.md")
    
    # Demonstrate idempotence - update existing documentation
    print("\n" + "-" * 60)
    print("Demonstrating Documentation Idempotence")
    print("-" * 60)
    
    # Load existing documentation
    existing_docs = agent.load_existing_documentation()
    print("✓ Loaded existing documentation")
    
    # Update with new documentation
    updated_docs = agent.update_existing_docs(existing_docs, documentation)
    agent.write_documentation(updated_docs)
    print("✓ Updated documentation without creating duplicates")
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\nCheck the 'demo_docs' directory to see the generated documentation.")


if __name__ == "__main__":
    main()
