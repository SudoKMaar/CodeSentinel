"""
Code parsing MCP tools using tree-sitter for AST generation.

This module provides tools for:
- Parsing Python, JavaScript, and TypeScript code into AST
- AST traversal and extraction utilities
- Code structure analysis
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from tree_sitter import Language, Parser, Node, Tree
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_typescript


class CodeParserTool:
    """MCP tool for code parsing using tree-sitter."""
    
    # Language to file extension mapping
    LANGUAGE_EXTENSIONS = {
        'python': ['.py'],
        'javascript': ['.js', '.jsx'],
        'typescript': ['.ts', '.tsx'],
    }
    
    def __init__(self):
        """Initialize the code parser with tree-sitter languages."""
        # Initialize parsers for each language
        self._parsers: Dict[str, Parser] = {}
        self._languages: Dict[str, Language] = {}
        
        # Set up Python parser
        self._languages['python'] = Language(tree_sitter_python.language())
        python_parser = Parser(self._languages['python'])
        self._parsers['python'] = python_parser
        
        # Set up JavaScript parser
        self._languages['javascript'] = Language(tree_sitter_javascript.language())
        js_parser = Parser(self._languages['javascript'])
        self._parsers['javascript'] = js_parser
        
        # Set up TypeScript parser
        self._languages['typescript'] = Language(tree_sitter_typescript.language_typescript())
        ts_parser = Parser(self._languages['typescript'])
        self._parsers['typescript'] = ts_parser
        
        # Set up TSX parser (TypeScript with JSX)
        self._languages['tsx'] = Language(tree_sitter_typescript.language_tsx())
        tsx_parser = Parser(self._languages['tsx'])
        self._parsers['tsx'] = tsx_parser
    
    def detect_language(self, file_path: str) -> Optional[str]:
        """
        Detect programming language from file extension.
        
        Args:
            file_path: Path to the source file
        
        Returns:
            Language name ('python', 'javascript', 'typescript', 'tsx') or None
        """
        ext = Path(file_path).suffix.lower()
        
        if ext == '.py':
            return 'python'
        elif ext in ['.js', '.jsx']:
            return 'javascript'
        elif ext == '.ts':
            return 'typescript'
        elif ext == '.tsx':
            return 'tsx'
        
        return None
    
    def parse_code(self, source_code: str, language: str) -> Optional[Tree]:
        """
        Parse source code into an AST.
        
        Args:
            source_code: Source code as string
            language: Programming language ('python', 'javascript', 'typescript', 'tsx')
        
        Returns:
            Tree-sitter Tree object or None if parsing fails
        
        Raises:
            ValueError: If language is not supported
        """
        if language not in self._parsers:
            raise ValueError(f"Unsupported language: {language}")
        
        parser = self._parsers[language]
        
        try:
            # Convert string to bytes for tree-sitter
            source_bytes = source_code.encode('utf-8')
            tree = parser.parse(source_bytes)
            return tree
        except Exception as e:
            # Return None if parsing fails
            return None
    
    def parse_file(self, file_path: str, source_code: str) -> Optional[Tree]:
        """
        Parse a source file into an AST.
        
        Args:
            file_path: Path to the source file (used for language detection)
            source_code: Source code content
        
        Returns:
            Tree-sitter Tree object or None if parsing fails
        """
        language = self.detect_language(file_path)
        
        if language is None:
            return None
        
        return self.parse_code(source_code, language)
    
    def get_root_node(self, tree: Tree) -> Node:
        """
        Get the root node of an AST.
        
        Args:
            tree: Tree-sitter Tree object
        
        Returns:
            Root node of the tree
        """
        return tree.root_node
    
    def traverse_tree(self, node: Node, callback: callable) -> None:
        """
        Traverse AST in depth-first order, calling callback for each node.
        
        Args:
            node: Starting node for traversal
            callback: Function to call for each node, receives node as argument
        """
        callback(node)
        
        for child in node.children:
            self.traverse_tree(child, callback)
    
    def find_nodes_by_type(self, node: Node, node_type: str) -> List[Node]:
        """
        Find all nodes of a specific type in the AST.
        
        Args:
            node: Root node to start search from
            node_type: Type of nodes to find (e.g., 'function_definition', 'class_definition')
        
        Returns:
            List of nodes matching the type
        """
        matching_nodes: List[Node] = []
        
        def collect_matching(n: Node) -> None:
            if n.type == node_type:
                matching_nodes.append(n)
        
        self.traverse_tree(node, collect_matching)
        return matching_nodes
    
    def extract_functions(self, tree: Tree, language: str) -> List[Dict[str, Any]]:
        """
        Extract function definitions from AST.
        
        Args:
            tree: Parsed AST tree
            language: Programming language
        
        Returns:
            List of dictionaries containing function information
        """
        root = tree.root_node
        functions: List[Dict[str, Any]] = []
        
        # Language-specific function node types
        function_types = {
            'python': ['function_definition'],
            'javascript': ['function_declaration', 'function_expression', 'arrow_function'],
            'typescript': ['function_declaration', 'function_expression', 'arrow_function', 'method_definition'],
            'tsx': ['function_declaration', 'function_expression', 'arrow_function', 'method_definition'],
        }
        
        if language not in function_types:
            return functions
        
        for func_type in function_types[language]:
            func_nodes = self.find_nodes_by_type(root, func_type)
            
            for func_node in func_nodes:
                func_info = self._extract_function_info(func_node, language)
                if func_info:
                    functions.append(func_info)
        
        return functions
    
    def _extract_function_info(self, node: Node, language: str) -> Optional[Dict[str, Any]]:
        """
        Extract information from a function node.
        
        Args:
            node: Function node
            language: Programming language
        
        Returns:
            Dictionary with function information or None
        """
        info: Dict[str, Any] = {
            'name': None,
            'line_number': node.start_point[0] + 1,
            'end_line': node.end_point[0] + 1,
            'parameters': [],
            'type': node.type,
        }
        
        # Extract function name (language-specific)
        if language == 'python':
            for child in node.children:
                if child.type == 'identifier':
                    info['name'] = child.text.decode('utf-8')
                    break
                elif child.type == 'parameters':
                    info['parameters'] = self._extract_parameters(child, language)
        
        elif language in ['javascript', 'typescript', 'tsx']:
            for child in node.children:
                if child.type == 'identifier':
                    info['name'] = child.text.decode('utf-8')
                elif child.type == 'formal_parameters':
                    info['parameters'] = self._extract_parameters(child, language)
        
        return info
    
    def _extract_parameters(self, params_node: Node, language: str) -> List[str]:
        """
        Extract parameter names from a parameters node.
        
        Args:
            params_node: Parameters node
            language: Programming language
        
        Returns:
            List of parameter names
        """
        parameters: List[str] = []
        
        for child in params_node.children:
            if language == 'python':
                if child.type == 'identifier':
                    parameters.append(child.text.decode('utf-8'))
                elif child.type == 'typed_parameter':
                    # Get the identifier from typed parameter
                    for subchild in child.children:
                        if subchild.type == 'identifier':
                            parameters.append(subchild.text.decode('utf-8'))
                            break
            
            elif language in ['javascript', 'typescript', 'tsx']:
                if child.type == 'identifier':
                    parameters.append(child.text.decode('utf-8'))
                elif child.type == 'required_parameter':
                    for subchild in child.children:
                        if subchild.type == 'identifier':
                            parameters.append(subchild.text.decode('utf-8'))
                            break
        
        return parameters
    
    def extract_classes(self, tree: Tree, language: str) -> List[Dict[str, Any]]:
        """
        Extract class definitions from AST.
        
        Args:
            tree: Parsed AST tree
            language: Programming language
        
        Returns:
            List of dictionaries containing class information
        """
        root = tree.root_node
        classes: List[Dict[str, Any]] = []
        
        # Language-specific class node types
        class_types = {
            'python': ['class_definition'],
            'javascript': ['class_declaration'],
            'typescript': ['class_declaration'],
            'tsx': ['class_declaration'],
        }
        
        if language not in class_types:
            return classes
        
        for class_type in class_types[language]:
            class_nodes = self.find_nodes_by_type(root, class_type)
            
            for class_node in class_nodes:
                class_info = self._extract_class_info(class_node, language)
                if class_info:
                    classes.append(class_info)
        
        return classes
    
    def _extract_class_info(self, node: Node, language: str) -> Optional[Dict[str, Any]]:
        """
        Extract information from a class node.
        
        Args:
            node: Class node
            language: Programming language
        
        Returns:
            Dictionary with class information or None
        """
        info: Dict[str, Any] = {
            'name': None,
            'line_number': node.start_point[0] + 1,
            'end_line': node.end_point[0] + 1,
            'methods': [],
            'base_classes': [],
        }
        
        # Extract class name
        for child in node.children:
            if child.type == 'identifier':
                info['name'] = child.text.decode('utf-8')
                break
        
        # Extract methods (functions within the class)
        if language == 'python':
            method_nodes = self.find_nodes_by_type(node, 'function_definition')
        else:
            method_nodes = self.find_nodes_by_type(node, 'method_definition')
        
        for method_node in method_nodes:
            method_info = self._extract_function_info(method_node, language)
            if method_info and method_info['name']:
                info['methods'].append(method_info['name'])
        
        return info
    
    def has_syntax_errors(self, tree: Tree) -> bool:
        """
        Check if the parsed tree contains syntax errors.
        
        Args:
            tree: Parsed AST tree
        
        Returns:
            True if tree contains ERROR nodes, False otherwise
        """
        root = tree.root_node
        error_nodes = self.find_nodes_by_type(root, 'ERROR')
        return len(error_nodes) > 0
    
    def get_node_text(self, node: Node) -> str:
        """
        Get the source code text for a node.
        
        Args:
            node: AST node
        
        Returns:
            Source code text as string
        """
        return node.text.decode('utf-8')
