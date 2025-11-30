"""
Property-based tests for file system tools.

Feature: code-review-documentation-agent
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple
from hypothesis import given, strategies as st, settings, assume
from hypothesis.strategies import SearchStrategy

from tools.file_system import FileSystemTool


# Custom strategies for generating directory structures

@st.composite
def file_name_strategy(draw: st.DrawFn) -> str:
    """Generate valid file names."""
    # Use simple ASCII characters for file names
    base_name = draw(st.text(
        alphabet=st.characters(min_codepoint=97, max_codepoint=122),  # a-z
        min_size=1,
        max_size=10
    ))
    extension = draw(st.sampled_from(['.py', '.js', '.ts', '.tsx', '.jsx', '.txt', '.md']))
    return f"{base_name}{extension}"


@st.composite
def directory_structure_strategy(draw: st.DrawFn) -> Tuple[str, List[str], List[str]]:
    """
    Generate a random directory structure with files.
    
    Returns:
        Tuple of (root_path, list of supported files, list of unsupported files)
    """
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    supported_files: List[str] = []
    unsupported_files: List[str] = []
    
    # Generate number of directories and files
    num_dirs = draw(st.integers(min_value=0, max_value=3))
    num_supported_files = draw(st.integers(min_value=1, max_value=5))
    num_unsupported_files = draw(st.integers(min_value=0, max_value=3))
    
    # Create subdirectories
    subdirs = []
    for i in range(num_dirs):
        subdir_name = f"subdir_{i}"
        subdir_path = os.path.join(temp_dir, subdir_name)
        os.makedirs(subdir_path, exist_ok=True)
        subdirs.append(subdir_path)
    
    # All possible locations (root + subdirs)
    all_locations = [temp_dir] + subdirs
    
    # Create supported files
    for i in range(num_supported_files):
        location = draw(st.sampled_from(all_locations))
        extension = draw(st.sampled_from(['.py', '.js', '.ts', '.tsx', '.jsx']))
        file_name = f"file_{i}{extension}"
        file_path = os.path.join(location, file_name)
        
        # Write some content to the file
        with open(file_path, 'w') as f:
            f.write(f"// Content of {file_name}\n")
        
        supported_files.append(file_path)
    
    # Create unsupported files
    for i in range(num_unsupported_files):
        location = draw(st.sampled_from(all_locations))
        extension = draw(st.sampled_from(['.txt', '.md', '.json', '.xml']))
        file_name = f"unsupported_{i}{extension}"
        file_path = os.path.join(location, file_name)
        
        with open(file_path, 'w') as f:
            f.write(f"Content of {file_name}\n")
        
        unsupported_files.append(file_path)
    
    return temp_dir, supported_files, unsupported_files


# Property-based tests

# Feature: code-review-documentation-agent, Property 1: File Discovery Completeness
# Validates: Requirements 1.1, 1.5

@settings(max_examples=100, deadline=None)
@given(directory_structure_strategy())
def test_file_discovery_completeness(structure_data: Tuple[str, List[str], List[str]]) -> None:
    """
    Property 1: File Discovery Completeness
    For any valid codebase directory structure containing supported file types,
    scanning should discover all supported source files and skip unsupported types
    without failure.
    """
    temp_dir, expected_supported, expected_unsupported = structure_data
    
    try:
        tool = FileSystemTool()
        
        # Discover files
        discovered = tool.discover_files(temp_dir)
        
        # Verify all supported files are discovered
        discovered_set = set(discovered)
        expected_set = set(expected_supported)
        
        assert discovered_set == expected_set, (
            f"Discovered files don't match expected.\n"
            f"Expected: {expected_set}\n"
            f"Discovered: {discovered_set}\n"
            f"Missing: {expected_set - discovered_set}\n"
            f"Extra: {discovered_set - expected_set}"
        )
        
        # Verify unsupported files are not included
        for unsupported_file in expected_unsupported:
            assert unsupported_file not in discovered, (
                f"Unsupported file {unsupported_file} was incorrectly discovered"
            )
        
        # Verify no errors occurred (function completed successfully)
        assert isinstance(discovered, list)
        assert all(isinstance(f, str) for f in discovered)
        
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@settings(max_examples=50, deadline=None)
@given(st.lists(st.sampled_from(['.py', '.js', '.ts', '.tsx', '.jsx']), min_size=1, max_size=5))
def test_file_discovery_with_patterns(extensions: List[str]) -> None:
    """
    Property: File discovery respects include patterns.
    For any set of file extensions, only files matching those patterns should be discovered.
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        tool = FileSystemTool()
        
        # Create files with various extensions
        created_files = []
        for ext in extensions:
            file_path = os.path.join(temp_dir, f"test{ext}")
            with open(file_path, 'w') as f:
                f.write(f"// Test file\n")
            created_files.append(file_path)
        
        # Create a file that shouldn't be discovered
        excluded_file = os.path.join(temp_dir, "test.txt")
        with open(excluded_file, 'w') as f:
            f.write("Excluded\n")
        
        # Discover with specific patterns
        patterns = [f"*{ext}" for ext in extensions]
        discovered = tool.discover_files(temp_dir, include_patterns=patterns)
        
        # Verify only matching files are discovered
        discovered_set = set(discovered)
        expected_set = set(created_files)
        
        assert discovered_set == expected_set
        assert excluded_file not in discovered
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@settings(max_examples=50, deadline=None)
@given(st.lists(st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=10), min_size=1, max_size=3))
def test_file_discovery_excludes_patterns(exclude_dirs: List[str]) -> None:
    """
    Property: File discovery respects exclude patterns.
    For any set of excluded directory names, files in those directories should not be discovered.
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        tool = FileSystemTool()
        
        # Create files in root
        root_file = os.path.join(temp_dir, "root.py")
        with open(root_file, 'w') as f:
            f.write("# Root file\n")
        
        # Create excluded directories with files
        for exclude_dir in exclude_dirs:
            dir_path = os.path.join(temp_dir, exclude_dir)
            os.makedirs(dir_path, exist_ok=True)
            
            file_path = os.path.join(dir_path, "excluded.py")
            with open(file_path, 'w') as f:
                f.write("# Excluded file\n")
        
        # Discover with exclusion patterns
        exclude_patterns = [f"{d}/**" for d in exclude_dirs]
        discovered = tool.discover_files(temp_dir, exclude_patterns=exclude_patterns)
        
        # Verify root file is discovered
        assert root_file in discovered
        
        # Verify excluded files are not discovered
        for exclude_dir in exclude_dirs:
            excluded_file = os.path.join(temp_dir, exclude_dir, "excluded.py")
            assert excluded_file not in discovered, f"File in {exclude_dir} should be excluded"
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def test_file_discovery_invalid_path() -> None:
    """
    Test that file discovery raises ValueError for invalid paths.
    """
    tool = FileSystemTool()
    
    # Test non-existent path
    try:
        tool.discover_files("/nonexistent/path/that/does/not/exist")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "does not exist" in str(e)
    
    # Test file path instead of directory
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file.close()  # Close the file before trying to use it
    try:
        tool.discover_files(temp_file.name)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "not a directory" in str(e)
    finally:
        try:
            os.unlink(temp_file.name)
        except:
            pass  # Ignore cleanup errors on Windows
