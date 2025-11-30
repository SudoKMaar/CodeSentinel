"""
Documenter Agent for automatic documentation generation.

This agent performs:
- Project structure documentation generation
- API documentation extraction from function/class signatures
- Code example generation using LLM
- Documentation hierarchy organization
- Documentation update logic to avoid duplicates
"""

from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
import json
import os

from models.data_models import (
    FileAnalysis,
    FunctionInfo,
    ClassInfo,
    Documentation,
)


class CodebaseStructure:
    """Represents the structure of a codebase."""
    
    def __init__(self, root_path: str):
        """
        Initialize codebase structure.
        
        Args:
            root_path: Root path of the codebase
        """
        self.root_path = root_path
        self.directories: List[str] = []
        self.files: Dict[str, str] = {}  # file_path -> language
        self.modules: Dict[str, List[str]] = {}  # module -> files
    
    def add_file(self, file_path: str, language: str) -> None:
        """Add a file to the structure."""
        self.files[file_path] = language
        
        # Track directory
        directory = str(Path(file_path).parent)
        if directory not in self.directories:
            self.directories.append(directory)
        
        # Track module (directory-based)
        module = directory.replace(os.sep, '.')
        if module not in self.modules:
            self.modules[module] = []
        self.modules[module].append(file_path)


class DocumenterAgent:
    """Agent for generating and maintaining code documentation."""
    
    def __init__(self, output_dir: str = "docs"):
        """
        Initialize the Documenter Agent.
        
        Args:
            output_dir: Directory where documentation will be written
        """
        self.output_dir = output_dir
        self._ensure_output_dir()
    
    def _ensure_output_dir(self) -> None:
        """Ensure the output directory exists."""
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def generate_project_docs(
        self,
        codebase_structure: CodebaseStructure
    ) -> str:
        """
        Generate project structure documentation.
        
        Args:
            codebase_structure: Structure of the codebase
        
        Returns:
            Markdown documentation of project structure
        """
        lines = ["# Project Structure\n"]
        lines.append(f"Root: `{codebase_structure.root_path}`\n")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Overview
        lines.append("## Overview\n")
        lines.append(f"- Total files: {len(codebase_structure.files)}")
        lines.append(f"- Total directories: {len(codebase_structure.directories)}")
        
        # Language breakdown
        lang_counts: Dict[str, int] = {}
        for language in codebase_structure.files.values():
            lang_counts[language] = lang_counts.get(language, 0) + 1
        
        lines.append("\n### Languages")
        for lang, count in sorted(lang_counts.items()):
            lines.append(f"- {lang}: {count} files")
        
        # Directory structure
        lines.append("\n## Directory Structure\n")
        sorted_dirs = sorted(codebase_structure.directories)
        for directory in sorted_dirs:
            # Calculate depth for indentation
            depth = directory.count(os.sep)
            indent = "  " * depth
            dir_name = Path(directory).name or directory
            lines.append(f"{indent}- `{dir_name}/`")
        
        # Module organization
        lines.append("\n## Modules\n")
        for module, files in sorted(codebase_structure.modules.items()):
            if module and module != '.':
                lines.append(f"\n### {module}")
                lines.append(f"Files: {len(files)}")
                for file_path in sorted(files):
                    file_name = Path(file_path).name
                    lines.append(f"- `{file_name}`")
        
        return "\n".join(lines)
    
    def generate_api_docs(
        self,
        file_analyses: List[FileAnalysis]
    ) -> Dict[str, str]:
        """
        Generate API documentation from code analysis.
        
        Args:
            file_analyses: List of file analysis results
        
        Returns:
            Dictionary mapping module names to API documentation
        """
        api_docs: Dict[str, str] = {}
        
        for analysis in file_analyses:
            module_name = self._get_module_name(analysis.file_path)
            doc_content = self._generate_file_api_doc(analysis)
            
            if doc_content:
                api_docs[module_name] = doc_content
        
        return api_docs
    
    def _get_module_name(self, file_path: str) -> str:
        """Extract module name from file path."""
        path = Path(file_path)
        # Remove extension and convert to module notation
        module = str(path.with_suffix('')).replace(os.sep, '.')
        return module
    
    def _generate_file_api_doc(self, analysis: FileAnalysis) -> str:
        """
        Generate API documentation for a single file.
        
        Args:
            analysis: File analysis result
        
        Returns:
            Markdown documentation string
        """
        lines = [f"# {Path(analysis.file_path).name}\n"]
        lines.append(f"Language: {analysis.language}\n")
        
        # Classes
        if analysis.classes:
            lines.append("## Classes\n")
            for cls in analysis.classes:
                lines.append(f"### `{cls.name}`")
                lines.append(f"Line: {cls.line_number}\n")
                
                if cls.docstring:
                    lines.append(f"{cls.docstring}\n")
                
                if cls.base_classes:
                    lines.append(f"**Inherits from:** {', '.join(f'`{bc}`' for bc in cls.base_classes)}\n")
                
                if cls.methods:
                    lines.append("**Methods:**")
                    for method in cls.methods:
                        lines.append(f"- `{method}()`")
                    lines.append("")
        
        # Functions
        if analysis.functions:
            lines.append("## Functions\n")
            for func in analysis.functions:
                # Build function signature
                params_str = ", ".join(func.parameters)
                signature = f"{func.name}({params_str})"
                
                lines.append(f"### `{signature}`")
                lines.append(f"Line: {func.line_number}")
                lines.append(f"Complexity: {func.complexity}\n")
                
                if func.docstring:
                    lines.append(f"{func.docstring}\n")
                
                if func.parameters:
                    lines.append("**Parameters:**")
                    for param in func.parameters:
                        lines.append(f"- `{param}`")
                    lines.append("")
                
                if func.return_type:
                    lines.append(f"**Returns:** `{func.return_type}`\n")
        
        return "\n".join(lines)
    
    def generate_code_examples(
        self,
        file_analyses: List[FileAnalysis],
        max_examples: int = 5
    ) -> Dict[str, str]:
        """
        Generate code examples from analyzed code.
        
        This is a simplified version that extracts actual code snippets.
        In a full implementation, this would use an LLM to generate
        contextual examples.
        
        Args:
            file_analyses: List of file analysis results
            max_examples: Maximum number of examples to generate
        
        Returns:
            Dictionary mapping example titles to code snippets
        """
        examples: Dict[str, str] = {}
        example_count = 0
        
        for analysis in file_analyses:
            if example_count >= max_examples:
                break
            
            # Generate examples from classes
            for cls in analysis.classes:
                if example_count >= max_examples:
                    break
                
                title = f"Using {cls.name} class"
                example = self._generate_class_example(cls, analysis.language)
                examples[title] = example
                example_count += 1
            
            # Generate examples from functions
            for func in analysis.functions:
                if example_count >= max_examples:
                    break
                
                # Skip private/internal functions
                if func.name.startswith('_'):
                    continue
                
                title = f"Using {func.name} function"
                example = self._generate_function_example(func, analysis.language)
                examples[title] = example
                example_count += 1
        
        return examples
    
    def _generate_class_example(self, cls: ClassInfo, language: str) -> str:
        """Generate a usage example for a class."""
        if language == 'python':
            lines = [
                f"```python",
                f"# Create an instance of {cls.name}",
                f"obj = {cls.name}()",
                ""
            ]
            
            # Add method calls for first few methods
            for method in cls.methods[:3]:
                if not method.startswith('_'):
                    lines.append(f"# Call {method}")
                    lines.append(f"result = obj.{method}()")
            
            lines.append("```")
            return "\n".join(lines)
        
        elif language in ['javascript', 'typescript', 'tsx']:
            lines = [
                f"```{language}",
                f"// Create an instance of {cls.name}",
                f"const obj = new {cls.name}();",
                ""
            ]
            
            for method in cls.methods[:3]:
                if not method.startswith('_'):
                    lines.append(f"// Call {method}")
                    lines.append(f"const result = obj.{method}();")
            
            lines.append("```")
            return "\n".join(lines)
        
        return f"Example for {cls.name}"
    
    def _generate_function_example(self, func: FunctionInfo, language: str) -> str:
        """Generate a usage example for a function."""
        if language == 'python':
            # Build example arguments
            args = ", ".join(f"arg{i}" for i in range(len(func.parameters)))
            
            lines = [
                f"```python",
                f"# Call {func.name}",
                f"result = {func.name}({args})",
                "```"
            ]
            return "\n".join(lines)
        
        elif language in ['javascript', 'typescript', 'tsx']:
            args = ", ".join(f"arg{i}" for i in range(len(func.parameters)))
            
            lines = [
                f"```{language}",
                f"// Call {func.name}",
                f"const result = {func.name}({args});",
                "```"
            ]
            return "\n".join(lines)
        
        return f"Example for {func.name}"
    
    def organize_documentation(
        self,
        project_docs: str,
        api_docs: Dict[str, str],
        examples: Dict[str, str]
    ) -> Documentation:
        """
        Organize documentation into a structured format.
        
        Args:
            project_docs: Project structure documentation
            api_docs: API documentation by module
            examples: Code examples by topic
        
        Returns:
            Documentation object with organized content
        """
        return Documentation(
            project_structure=project_docs,
            api_docs=api_docs,
            examples=examples
        )
    
    def update_existing_docs(
        self,
        existing_docs: Documentation,
        new_docs: Documentation
    ) -> Documentation:
        """
        Update existing documentation without creating duplicates.
        
        This merges new documentation with existing documentation,
        updating changed sections and preserving unchanged ones.
        
        Args:
            existing_docs: Existing documentation
            new_docs: Newly generated documentation
        
        Returns:
            Updated documentation
        """
        # Update project structure (always replace with latest)
        updated_structure = new_docs.project_structure
        
        # Merge API docs (update existing modules, add new ones)
        updated_api_docs = dict(existing_docs.api_docs)
        for module, content in new_docs.api_docs.items():
            updated_api_docs[module] = content
        
        # Merge examples (update existing, add new)
        updated_examples = dict(existing_docs.examples)
        for title, content in new_docs.examples.items():
            updated_examples[title] = content
        
        return Documentation(
            project_structure=updated_structure,
            api_docs=updated_api_docs,
            examples=updated_examples
        )
    
    def write_documentation(
        self,
        documentation: Documentation,
        output_dir: Optional[str] = None
    ) -> None:
        """
        Write documentation to files.
        
        Args:
            documentation: Documentation to write
            output_dir: Output directory (uses self.output_dir if None)
        """
        out_dir = output_dir or self.output_dir
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        # Write project structure
        structure_file = out_path / "PROJECT_STRUCTURE.md"
        structure_file.write_text(documentation.project_structure, encoding='utf-8')
        
        # Write API docs
        api_dir = out_path / "api"
        api_dir.mkdir(exist_ok=True)
        
        for module, content in documentation.api_docs.items():
            # Sanitize module name for filename
            filename = module.replace('.', '_') + ".md"
            api_file = api_dir / filename
            api_file.write_text(content, encoding='utf-8')
        
        # Write examples
        if documentation.examples:
            examples_file = out_path / "EXAMPLES.md"
            lines = ["# Code Examples\n"]
            
            for title, content in documentation.examples.items():
                lines.append(f"## {title}\n")
                lines.append(content)
                lines.append("")
            
            examples_file.write_text("\n".join(lines), encoding='utf-8')
    
    def load_existing_documentation(
        self,
        input_dir: Optional[str] = None
    ) -> Optional[Documentation]:
        """
        Load existing documentation from files.
        
        Args:
            input_dir: Input directory (uses self.output_dir if None)
        
        Returns:
            Documentation object or None if no documentation exists
        """
        in_dir = input_dir or self.output_dir
        in_path = Path(in_dir)
        
        if not in_path.exists():
            return None
        
        # Load project structure
        structure_file = in_path / "PROJECT_STRUCTURE.md"
        if not structure_file.exists():
            return None
        
        project_structure = structure_file.read_text(encoding='utf-8')
        
        # Load API docs
        api_docs: Dict[str, str] = {}
        api_dir = in_path / "api"
        if api_dir.exists():
            for api_file in api_dir.glob("*.md"):
                module = api_file.stem.replace('_', '.')
                content = api_file.read_text(encoding='utf-8')
                api_docs[module] = content
        
        # Load examples
        examples: Dict[str, str] = {}
        examples_file = in_path / "EXAMPLES.md"
        if examples_file.exists():
            content = examples_file.read_text(encoding='utf-8')
            # Parse examples from markdown
            examples = self._parse_examples_from_markdown(content)
        
        return Documentation(
            project_structure=project_structure,
            api_docs=api_docs,
            examples=examples
        )
    
    def _parse_examples_from_markdown(self, content: str) -> Dict[str, str]:
        """Parse examples from markdown content."""
        examples: Dict[str, str] = {}
        lines = content.split('\n')
        
        current_title = None
        current_content: List[str] = []
        
        for line in lines:
            if line.startswith('## '):
                # Save previous example
                if current_title and current_content:
                    examples[current_title] = '\n'.join(current_content).strip()
                
                # Start new example
                current_title = line[3:].strip()
                current_content = []
            elif current_title:
                current_content.append(line)
        
        # Save last example
        if current_title and current_content:
            examples[current_title] = '\n'.join(current_content).strip()
        
        return examples
