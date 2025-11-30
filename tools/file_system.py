"""
File system MCP tools for directory scanning and file operations.

This module provides tools for:
- Directory scanning and file discovery
- File reading with multiple encoding support
- File modification time checking for change detection
"""

import os
from pathlib import Path
from typing import List, Optional, Set
from datetime import datetime
import fnmatch
import chardet


class FileSystemTool:
    """MCP tool for file system operations."""
    
    SUPPORTED_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx'}
    
    def __init__(self):
        """Initialize the file system tool."""
        self._file_mtimes: dict[str, float] = {}
    
    def discover_files(
        self,
        root_path: str,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        Scan directory structure and discover all supported source files.
        
        Args:
            root_path: Root directory to scan
            include_patterns: File patterns to include (e.g., ['*.py', '*.js'])
            exclude_patterns: Patterns to exclude (e.g., ['node_modules/**', 'venv/**'])
        
        Returns:
            List of absolute file paths for all discovered files
        
        Raises:
            ValueError: If root_path doesn't exist or is not a directory
        """
        root = Path(root_path).resolve()
        
        if not root.exists():
            raise ValueError(f"Path does not exist: {root_path}")
        
        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root_path}")
        
        # Default patterns if not provided
        if include_patterns is None:
            include_patterns = ['*.py', '*.js', '*.ts', '*.tsx', '*.jsx']
        
        if exclude_patterns is None:
            exclude_patterns = [
                'node_modules/**',
                'venv/**',
                '.git/**',
                '__pycache__/**',
                '*.pyc',
                '.pytest_cache/**',
                '.hypothesis/**',
                'dist/**',
                'build/**',
            ]
        
        discovered_files: List[str] = []
        
        # Walk the directory tree
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = Path(dirpath).relative_to(root)
            
            # Check if directory should be excluded
            dir_excluded = False
            for pattern in exclude_patterns:
                # Handle directory exclusion patterns
                if '**' in pattern:
                    pattern_dir = pattern.replace('/**', '').replace('**/', '')
                    if pattern_dir in str(rel_dir).split(os.sep):
                        dir_excluded = True
                        break
            
            if dir_excluded:
                # Clear dirnames to prevent walking into excluded directories
                dirnames.clear()
                continue
            
            # Process files in current directory
            for filename in filenames:
                file_path = Path(dirpath) / filename
                rel_path = file_path.relative_to(root)
                
                # Check if file should be excluded
                file_excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(str(rel_path), pattern) or fnmatch.fnmatch(filename, pattern):
                        file_excluded = True
                        break
                
                if file_excluded:
                    continue
                
                # Check if file matches include patterns
                file_included = False
                for pattern in include_patterns:
                    if fnmatch.fnmatch(filename, pattern):
                        file_included = True
                        break
                
                # Also check if extension is supported
                if file_included and file_path.suffix in self.SUPPORTED_EXTENSIONS:
                    discovered_files.append(str(file_path))
        
        return sorted(discovered_files)
    
    def read_file(self, file_path: str, encoding: Optional[str] = None) -> str:
        """
        Read file contents with automatic encoding detection.
        
        Args:
            file_path: Path to the file to read
            encoding: Specific encoding to use (if None, auto-detect)
        
        Returns:
            File contents as string
        
        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not path.is_file():
            raise IOError(f"Path is not a file: {file_path}")
        
        # If encoding not specified, try to detect it
        if encoding is None:
            try:
                with open(path, 'rb') as f:
                    raw_data = f.read()
                    result = chardet.detect(raw_data)
                    encoding = result['encoding'] or 'utf-8'
            except Exception:
                encoding = 'utf-8'
        
        # Try to read with detected/specified encoding
        try:
            with open(path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to utf-8 with error handling
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
    
    def get_modification_time(self, file_path: str) -> datetime:
        """
        Get the last modification time of a file.
        
        Args:
            file_path: Path to the file
        
        Returns:
            Datetime of last modification
        
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        mtime = path.stat().st_mtime
        return datetime.fromtimestamp(mtime)
    
    def has_file_changed(self, file_path: str) -> bool:
        """
        Check if a file has been modified since last check.
        
        Args:
            file_path: Path to the file
        
        Returns:
            True if file has changed or is being checked for first time
        """
        path = Path(file_path)
        
        if not path.exists():
            return False
        
        current_mtime = path.stat().st_mtime
        previous_mtime = self._file_mtimes.get(file_path)
        
        if previous_mtime is None:
            # First time checking this file
            self._file_mtimes[file_path] = current_mtime
            return True
        
        if current_mtime > previous_mtime:
            # File has been modified
            self._file_mtimes[file_path] = current_mtime
            return True
        
        return False
    
    def update_file_timestamp(self, file_path: str) -> None:
        """
        Update the stored modification time for a file.
        
        Args:
            file_path: Path to the file
        """
        path = Path(file_path)
        
        if path.exists():
            self._file_mtimes[file_path] = path.stat().st_mtime
    
    def get_changed_files(self, file_paths: List[str]) -> List[str]:
        """
        Get list of files that have changed since last check.
        
        Args:
            file_paths: List of file paths to check
        
        Returns:
            List of file paths that have changed
        """
        changed = []
        for file_path in file_paths:
            if self.has_file_changed(file_path):
                changed.append(file_path)
        return changed
