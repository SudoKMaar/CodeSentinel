"""
Analyzer Agent for code quality analysis.

This agent performs:
- Cyclomatic complexity calculation
- Code duplication detection
- Security vulnerability pattern matching
- Error handling detection
- Parallel file processing
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from tree_sitter import Node, Tree
import re
import hashlib

from models.data_models import (
    FileAnalysis,
    CodeMetrics,
    CodeIssue,
    FunctionInfo,
    ClassInfo,
    IssueSeverity,
    IssueCategory,
)
from tools.code_parser import CodeParserTool


class AnalyzerAgent:
    """Agent for analyzing code quality and detecting issues."""
    
    # Complexity thresholds
    COMPLEXITY_THRESHOLD_HIGH = 15
    COMPLEXITY_THRESHOLD_MEDIUM = 10
    
    # Security patterns to detect
    SECURITY_PATTERNS = {
        'sql_injection': [
            r'execute\s*\(\s*["\'].*%s.*["\'].*%',
            r'execute\s*\(\s*f["\'].*\{.*\}.*["\']',
            r'execute\s*\(\s*["\'].*\+.*["\']',
            r'["\']SELECT.*WHERE.*["\'].*%',
        ],
        'hardcoded_secrets': [
            r'password\s*=\s*["\'][^"\']{8,}["\']',
            r'api_key\s*=\s*["\'][^"\']{20,}["\']',
            r'secret\s*=\s*["\'][^"\']{8,}["\']',
            r'token\s*=\s*["\'][^"\']{20,}["\']',
        ],
    }
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the Analyzer Agent.
        
        Args:
            max_workers: Maximum number of parallel workers for file processing
        """
        self.code_parser = CodeParserTool()
        self.max_workers = max_workers
    
    def analyze_file(self, file_path: str, source_code: str) -> Optional[FileAnalysis]:
        """
        Analyze a single file for code quality issues.
        
        Args:
            file_path: Path to the file
            source_code: Source code content
        
        Returns:
            FileAnalysis object or None if parsing fails
        """
        from tools.error_handling import handle_parse_error, logger
        
        # Detect language
        language = self.code_parser.detect_language(file_path)
        if language is None:
            logger.warning(f"Unsupported file type: {file_path}")
            return None
        
        # Parse code with error handling
        try:
            tree = self.code_parser.parse_code(source_code, language)
            if tree is None:
                handle_parse_error(file_path, ValueError("Failed to generate AST"))
                return None
        except Exception as e:
            handle_parse_error(file_path, e)
            return None
        
        # Check for syntax errors - if present, create partial analysis
        if self.code_parser.has_syntax_errors(tree):
            logger.warning(f"Syntax errors detected in {file_path}, creating partial analysis")
            # Return partial analysis with syntax error issue
            from models.data_models import CodeIssue, IssueSeverity, IssueCategory, CodeMetrics
            
            return FileAnalysis(
                file_path=file_path,
                language=language,
                metrics=CodeMetrics(
                    cyclomatic_complexity=1,
                    maintainability_index=0.0,
                    lines_of_code=len(source_code.split('\n')),
                    comment_ratio=0.0,
                    test_coverage=None
                ),
                issues=[CodeIssue(
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.STYLE,
                    file_path=file_path,
                    line_number=1,
                    description="File contains syntax errors",
                    code_snippet="",
                    suggestion="Fix syntax errors before further analysis"
                )],
                functions=[],
                classes=[],
            )
        
        try:
            # Extract functions and classes
            functions = self._extract_functions_with_complexity(tree, language, source_code)
            classes = self._extract_classes_info(tree, language)
            
            # Calculate file-level metrics
            metrics = self.calculate_metrics(tree, source_code, functions)
            
            # Detect issues
            issues = self.detect_issues(tree, source_code, file_path, language, functions)
            
            return FileAnalysis(
                file_path=file_path,
                language=language,
                metrics=metrics,
                issues=issues,
                functions=functions,
                classes=classes,
            )
        except Exception as e:
            logger.error(f"Error during analysis of {file_path}: {e}")
            # Return minimal analysis rather than None
            from models.data_models import CodeMetrics
            return FileAnalysis(
                file_path=file_path,
                language=language,
                metrics=CodeMetrics(
                    cyclomatic_complexity=1,
                    maintainability_index=50.0,
                    lines_of_code=len(source_code.split('\n')),
                    comment_ratio=0.0,
                    test_coverage=None
                ),
                issues=[],
                functions=[],
                classes=[],
            )
    
    def analyze_files_parallel(
        self,
        files: List[tuple[str, str]]
    ) -> List[FileAnalysis]:
        """
        Analyze multiple files in parallel with graceful degradation.
        
        Args:
            files: List of (file_path, source_code) tuples
        
        Returns:
            List of FileAnalysis objects (excludes files that failed to analyze)
        """
        from tools.error_handling import logger
        
        results: List[FileAnalysis] = []
        failed_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.analyze_file, file_path, source_code): file_path
                for file_path, source_code in files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result()
                    if result is not None:
                        results.append(result)
                    else:
                        failed_count += 1
                        logger.warning(f"Analysis returned None for {file_path}")
                except Exception as e:
                    # Log error but continue with other files (graceful degradation)
                    failed_count += 1
                    logger.error(f"Exception analyzing {file_path}: {e}")
        
        # Log summary
        total = len(files)
        success_rate = (len(results) / total * 100) if total > 0 else 0
        logger.info(
            f"Parallel analysis completed: {len(results)}/{total} successful ({success_rate:.1f}%), "
            f"{failed_count} failed"
        )
        
        return results
    
    def calculate_metrics(
        self,
        tree: Tree,
        source_code: str,
        functions: List[FunctionInfo]
    ) -> CodeMetrics:
        """
        Calculate code metrics for a file.
        
        Args:
            tree: Parsed AST tree
            source_code: Source code content
            functions: List of functions in the file
        
        Returns:
            CodeMetrics object
        """
        lines = source_code.split('\n')
        total_lines = len(lines)
        
        # Count comment lines
        comment_lines = sum(1 for line in lines if line.strip().startswith('#') or line.strip().startswith('//'))
        comment_ratio = comment_lines / total_lines if total_lines > 0 else 0.0
        
        # Calculate average complexity
        if functions:
            avg_complexity = sum(f.complexity for f in functions) / len(functions)
        else:
            avg_complexity = 1.0
        
        # Calculate maintainability index (simplified formula)
        # MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)
        # Simplified: higher comment ratio and lower complexity = higher maintainability
        maintainability = max(0.0, min(100.0, 100.0 - (avg_complexity * 2) + (comment_ratio * 20)))
        
        return CodeMetrics(
            cyclomatic_complexity=int(avg_complexity),
            maintainability_index=maintainability,
            lines_of_code=total_lines,
            comment_ratio=comment_ratio,
            test_coverage=None,  # Would require external test coverage tool
        )
    
    def detect_issues(
        self,
        tree: Tree,
        source_code: str,
        file_path: str,
        language: str,
        functions: List[FunctionInfo]
    ) -> List[CodeIssue]:
        """
        Detect code quality issues.
        
        Args:
            tree: Parsed AST tree
            source_code: Source code content
            file_path: Path to the file
            language: Programming language
            functions: List of functions in the file
        
        Returns:
            List of CodeIssue objects
        """
        issues: List[CodeIssue] = []
        
        # Check complexity issues
        issues.extend(self._check_complexity_issues(functions, file_path))
        
        # Check for code duplication
        issues.extend(self._check_duplication(tree, source_code, file_path))
        
        # Check security vulnerabilities
        issues.extend(self._check_security(source_code, file_path))
        
        # Check error handling
        issues.extend(self._check_error_handling(tree, source_code, file_path, language))
        
        return issues
    
    def _extract_functions_with_complexity(
        self,
        tree: Tree,
        language: str,
        source_code: str
    ) -> List[FunctionInfo]:
        """
        Extract functions with complexity calculation.
        
        Args:
            tree: Parsed AST tree
            language: Programming language
            source_code: Source code content
        
        Returns:
            List of FunctionInfo objects
        """
        functions_data = self.code_parser.extract_functions(tree, language)
        functions: List[FunctionInfo] = []
        
        for func_data in functions_data:
            if func_data['name'] is None:
                continue
            
            # Find the function node to calculate complexity
            root = tree.root_node
            func_node = self._find_function_node(root, func_data['line_number'])
            
            if func_node:
                complexity = self._calculate_cyclomatic_complexity(func_node, language)
            else:
                complexity = 1
            
            # Extract docstring if available
            docstring = self._extract_docstring(func_node, language) if func_node else None
            
            functions.append(FunctionInfo(
                name=func_data['name'],
                line_number=func_data['line_number'],
                parameters=func_data.get('parameters', []),
                return_type=None,  # Would need type annotation parsing
                docstring=docstring,
                complexity=complexity,
            ))
        
        return functions
    
    def _extract_classes_info(self, tree: Tree, language: str) -> List[ClassInfo]:
        """
        Extract class information.
        
        Args:
            tree: Parsed AST tree
            language: Programming language
        
        Returns:
            List of ClassInfo objects
        """
        classes_data = self.code_parser.extract_classes(tree, language)
        classes: List[ClassInfo] = []
        
        for class_data in classes_data:
            if class_data['name'] is None:
                continue
            
            # Find the class node to extract docstring
            root = tree.root_node
            class_node = self._find_class_node(root, class_data['line_number'])
            docstring = self._extract_docstring(class_node, language) if class_node else None
            
            classes.append(ClassInfo(
                name=class_data['name'],
                line_number=class_data['line_number'],
                methods=class_data.get('methods', []),
                base_classes=class_data.get('base_classes', []),
                docstring=docstring,
            ))
        
        return classes
    
    def _calculate_cyclomatic_complexity(self, node: Node, language: str) -> int:
        """
        Calculate cyclomatic complexity for a function.
        
        Cyclomatic complexity = number of decision points + 1
        Decision points: if, elif, else, for, while, and, or, try, except, case
        
        Args:
            node: Function node
            language: Programming language
        
        Returns:
            Cyclomatic complexity score
        """
        complexity = 1  # Base complexity
        
        # Decision point node types by language
        decision_nodes = {
            'python': ['if_statement', 'elif_clause', 'else_clause', 'for_statement', 
                      'while_statement', 'except_clause', 'boolean_operator'],
            'javascript': ['if_statement', 'else_clause', 'for_statement', 'while_statement',
                          'switch_statement', 'case_clause', 'catch_clause', 'binary_expression'],
            'typescript': ['if_statement', 'else_clause', 'for_statement', 'while_statement',
                          'switch_statement', 'case_clause', 'catch_clause', 'binary_expression'],
            'tsx': ['if_statement', 'else_clause', 'for_statement', 'while_statement',
                   'switch_statement', 'case_clause', 'catch_clause', 'binary_expression'],
        }
        
        if language not in decision_nodes:
            return complexity
        
        # Count decision points
        def count_decisions(n: Node) -> None:
            nonlocal complexity
            if n.type in decision_nodes[language]:
                # For boolean operators, only count 'and' and 'or'
                if n.type == 'boolean_operator' or n.type == 'binary_expression':
                    text = n.text.decode('utf-8')
                    if ' and ' in text or ' or ' in text or ' && ' in text or ' || ' in text:
                        complexity += 1
                else:
                    complexity += 1
        
        self.code_parser.traverse_tree(node, count_decisions)
        
        return complexity
    
    def _find_function_node(self, root: Node, line_number: int) -> Optional[Node]:
        """Find function node at specific line number."""
        result = None
        
        def find_node(n: Node) -> None:
            nonlocal result
            if n.type in ['function_definition', 'function_declaration', 'function_expression', 
                         'arrow_function', 'method_definition']:
                if n.start_point[0] + 1 == line_number:
                    result = n
        
        self.code_parser.traverse_tree(root, find_node)
        return result
    
    def _find_class_node(self, root: Node, line_number: int) -> Optional[Node]:
        """Find class node at specific line number."""
        result = None
        
        def find_node(n: Node) -> None:
            nonlocal result
            if n.type in ['class_definition', 'class_declaration']:
                if n.start_point[0] + 1 == line_number:
                    result = n
        
        self.code_parser.traverse_tree(root, find_node)
        return result
    
    def _extract_docstring(self, node: Optional[Node], language: str) -> Optional[str]:
        """Extract docstring from function or class node."""
        if node is None:
            return None
        
        # For Python, look for string literal as first statement
        if language == 'python':
            for child in node.children:
                if child.type == 'block':
                    for stmt in child.children:
                        if stmt.type == 'expression_statement':
                            for expr in stmt.children:
                                if expr.type == 'string':
                                    return expr.text.decode('utf-8').strip('"\'')
        
        return None
    
    def _check_complexity_issues(
        self,
        functions: List[FunctionInfo],
        file_path: str
    ) -> List[CodeIssue]:
        """Check for high complexity functions."""
        issues: List[CodeIssue] = []
        
        for func in functions:
            if func.complexity >= self.COMPLEXITY_THRESHOLD_HIGH:
                issues.append(CodeIssue(
                    severity=IssueSeverity.HIGH,
                    category=IssueCategory.COMPLEXITY,
                    file_path=file_path,
                    line_number=func.line_number,
                    description=f"Function '{func.name}' has high cyclomatic complexity ({func.complexity})",
                    code_snippet=f"def {func.name}(...)",
                    suggestion="Consider breaking this function into smaller, more focused functions",
                ))
            elif func.complexity >= self.COMPLEXITY_THRESHOLD_MEDIUM:
                issues.append(CodeIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.COMPLEXITY,
                    file_path=file_path,
                    line_number=func.line_number,
                    description=f"Function '{func.name}' has moderate cyclomatic complexity ({func.complexity})",
                    code_snippet=f"def {func.name}(...)",
                    suggestion="Consider simplifying this function to improve maintainability",
                ))
        
        return issues
    
    def _check_duplication(
        self,
        tree: Tree,
        source_code: str,
        file_path: str
    ) -> List[CodeIssue]:
        """
        Check for code duplication using token-based comparison.
        
        This is a simplified implementation that looks for duplicate code blocks.
        """
        issues: List[CodeIssue] = []
        lines = source_code.split('\n')
        
        # Extract code blocks (sequences of 5+ non-empty lines)
        blocks: List[tuple[int, str]] = []
        current_block = []
        start_line = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
                if not current_block:
                    start_line = i + 1
                current_block.append(stripped)
            else:
                if len(current_block) >= 5:
                    blocks.append((start_line, '\n'.join(current_block)))
                current_block = []
        
        if len(current_block) >= 5:
            blocks.append((start_line, '\n'.join(current_block)))
        
        # Find duplicates using hash comparison
        seen: Dict[str, int] = {}
        for line_num, block in blocks:
            block_hash = hashlib.md5(block.encode()).hexdigest()
            if block_hash in seen:
                issues.append(CodeIssue(
                    severity=IssueSeverity.MEDIUM,
                    category=IssueCategory.DUPLICATION,
                    file_path=file_path,
                    line_number=line_num,
                    description=f"Duplicate code block detected (also at line {seen[block_hash]})",
                    code_snippet=block[:100] + "..." if len(block) > 100 else block,
                    suggestion="Consider extracting this code into a reusable function",
                ))
            else:
                seen[block_hash] = line_num
        
        return issues
    
    def _check_security(self, source_code: str, file_path: str) -> List[CodeIssue]:
        """Check for security vulnerabilities using pattern matching."""
        issues: List[CodeIssue] = []
        lines = source_code.split('\n')
        
        # Check SQL injection patterns
        for pattern in self.SECURITY_PATTERNS['sql_injection']:
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(CodeIssue(
                        severity=IssueSeverity.CRITICAL,
                        category=IssueCategory.SECURITY,
                        file_path=file_path,
                        line_number=i + 1,
                        description="Potential SQL injection vulnerability detected",
                        code_snippet=line.strip(),
                        suggestion="Use parameterized queries or prepared statements",
                    ))
        
        # Check hardcoded secrets
        for pattern in self.SECURITY_PATTERNS['hardcoded_secrets']:
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(CodeIssue(
                        severity=IssueSeverity.HIGH,
                        category=IssueCategory.SECURITY,
                        file_path=file_path,
                        line_number=i + 1,
                        description="Potential hardcoded secret detected",
                        code_snippet=line.strip()[:50] + "...",
                        suggestion="Use environment variables or a secrets management system",
                    ))
        
        return issues
    
    def _check_error_handling(
        self,
        tree: Tree,
        source_code: str,
        file_path: str,
        language: str
    ) -> List[CodeIssue]:
        """Check for missing error handling in error-prone operations."""
        issues: List[CodeIssue] = []
        
        # Error-prone operations that should have error handling
        error_prone_patterns = {
            'python': [
                (r'open\s*\(', 'file operations'),
                (r'requests\.(get|post|put|delete)', 'network calls'),
                (r'json\.loads\s*\(', 'JSON parsing'),
            ],
            'javascript': [
                (r'fetch\s*\(', 'network calls'),
                (r'JSON\.parse\s*\(', 'JSON parsing'),
                (r'fs\.(readFile|writeFile)', 'file operations'),
            ],
            'typescript': [
                (r'fetch\s*\(', 'network calls'),
                (r'JSON\.parse\s*\(', 'JSON parsing'),
                (r'fs\.(readFile|writeFile)', 'file operations'),
            ],
        }
        
        if language not in error_prone_patterns:
            return issues
        
        lines = source_code.split('\n')
        root = tree.root_node
        
        # Find all try-except/try-catch blocks
        try_blocks = self._find_try_blocks(root, language)
        protected_lines = set()
        for try_node in try_blocks:
            for line_num in range(try_node.start_point[0], try_node.end_point[0] + 1):
                protected_lines.add(line_num)
        
        # Check for error-prone operations outside try blocks
        for pattern, operation_type in error_prone_patterns[language]:
            for i, line in enumerate(lines):
                if re.search(pattern, line) and i not in protected_lines:
                    issues.append(CodeIssue(
                        severity=IssueSeverity.MEDIUM,
                        category=IssueCategory.ERROR_HANDLING,
                        file_path=file_path,
                        line_number=i + 1,
                        description=f"Missing error handling for {operation_type}",
                        code_snippet=line.strip(),
                        suggestion=f"Wrap {operation_type} in try-except/try-catch block",
                    ))
        
        return issues
    
    def _find_try_blocks(self, root: Node, language: str) -> List[Node]:
        """Find all try-except/try-catch blocks in the AST."""
        try_blocks: List[Node] = []
        
        try_types = {
            'python': ['try_statement'],
            'javascript': ['try_statement'],
            'typescript': ['try_statement'],
            'tsx': ['try_statement'],
        }
        
        if language not in try_types:
            return try_blocks
        
        for try_type in try_types[language]:
            try_blocks.extend(self.code_parser.find_nodes_by_type(root, try_type))
        
        return try_blocks
