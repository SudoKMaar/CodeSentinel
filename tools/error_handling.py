"""
Error handling and recovery utilities for the Code Review & Documentation Agent.

This module provides:
- Retry logic with exponential backoff for transient failures
- Input validation with clear error messages
- Error classification and handling strategies
- Graceful degradation utilities
"""

import time
import functools
from typing import Any, Callable, Optional, TypeVar, List, Type
from pathlib import Path
import logging

# Set up logging
logger = logging.getLogger(__name__)

T = TypeVar('T')


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class TransientError(Exception):
    """Raised for errors that may succeed on retry."""
    pass


class PermanentError(Exception):
    """Raised for errors that will not succeed on retry."""
    pass


class PartialFailureError(Exception):
    """Raised when some operations succeed but others fail."""
    
    def __init__(self, message: str, successful_results: List[Any], failed_items: List[tuple[str, Exception]]):
        """
        Initialize partial failure error.
        
        Args:
            message: Error message
            successful_results: List of successful results
            failed_items: List of (item_id, exception) tuples for failed items
        """
        super().__init__(message)
        self.successful_results = successful_results
        self.failed_items = failed_items


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retryable_exceptions: tuple = (TransientError, IOError, ConnectionError, TimeoutError)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds before first retry
        backoff_factor: Multiplier for delay after each retry
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types that should trigger retry
    
    Returns:
        Decorated function with retry logic
    
    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def fetch_data():
            # Code that might fail transiently
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
                except Exception as e:
                    # Non-retryable exception, fail immediately
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator


def validate_path(path: str, must_exist: bool = True, must_be_dir: bool = False, must_be_file: bool = False) -> Path:
    """
    Validate a file system path with clear error messages.
    
    Args:
        path: Path to validate
        must_exist: If True, path must exist
        must_be_dir: If True, path must be a directory
        must_be_file: If True, path must be a file
    
    Returns:
        Validated Path object
    
    Raises:
        ValidationError: If validation fails with descriptive message
    """
    if not path or not path.strip():
        raise ValidationError("Path cannot be empty")
    
    try:
        path_obj = Path(path).resolve()
    except Exception as e:
        raise ValidationError(f"Invalid path '{path}': {e}")
    
    if must_exist and not path_obj.exists():
        raise ValidationError(f"Path does not exist: {path}")
    
    if must_be_dir and path_obj.exists() and not path_obj.is_dir():
        raise ValidationError(f"Path is not a directory: {path}")
    
    if must_be_file and path_obj.exists() and not path_obj.is_file():
        raise ValidationError(f"Path is not a file: {path}")
    
    return path_obj


def validate_file_patterns(patterns: List[str]) -> List[str]:
    """
    Validate file patterns.
    
    Args:
        patterns: List of file patterns (e.g., ['*.py', '*.js'])
    
    Returns:
        Validated patterns
    
    Raises:
        ValidationError: If patterns are invalid
    """
    if not patterns:
        raise ValidationError("File patterns cannot be empty")
    
    if not isinstance(patterns, list):
        raise ValidationError("File patterns must be a list")
    
    validated = []
    for pattern in patterns:
        if not isinstance(pattern, str):
            raise ValidationError(f"Pattern must be a string: {pattern}")
        
        if not pattern.strip():
            raise ValidationError("Pattern cannot be empty")
        
        validated.append(pattern.strip())
    
    return validated


def validate_session_id(session_id: str) -> str:
    """
    Validate a session ID.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Validated session ID
    
    Raises:
        ValidationError: If session ID is invalid
    """
    if not session_id or not session_id.strip():
        raise ValidationError("Session ID cannot be empty")
    
    # Check for valid characters (alphanumeric, hyphens, underscores)
    if not all(c.isalnum() or c in '-_' for c in session_id):
        raise ValidationError(f"Session ID contains invalid characters: {session_id}")
    
    return session_id.strip()


def safe_file_operation(
    operation: Callable[[], T],
    file_path: str,
    operation_name: str = "file operation",
    default_value: Optional[T] = None
) -> Optional[T]:
    """
    Safely execute a file operation with error handling.
    
    Args:
        operation: Function to execute
        file_path: Path to the file being operated on
        operation_name: Name of the operation for error messages
        default_value: Value to return if operation fails
    
    Returns:
        Result of operation or default_value if it fails
    """
    try:
        return operation()
    except FileNotFoundError:
        logger.warning(f"File not found during {operation_name}: {file_path}")
        return default_value
    except PermissionError:
        logger.error(f"Permission denied during {operation_name}: {file_path}")
        return default_value
    except IOError as e:
        logger.error(f"IO error during {operation_name} on {file_path}: {e}")
        return default_value
    except Exception as e:
        logger.error(f"Unexpected error during {operation_name} on {file_path}: {e}")
        return default_value


def handle_parse_error(file_path: str, error: Exception) -> None:
    """
    Handle parsing errors with appropriate logging.
    
    Args:
        file_path: Path to the file that failed to parse
        error: Exception that occurred
    """
    logger.warning(
        f"Failed to parse {file_path}: {error}. "
        f"File will be skipped. Consider checking for syntax errors."
    )


def classify_error(error: Exception) -> str:
    """
    Classify an error as transient, permanent, or unknown.
    
    Args:
        error: Exception to classify
    
    Returns:
        Error classification: 'transient', 'permanent', or 'unknown'
    """
    # Transient errors that may succeed on retry
    transient_types = (
        TransientError,
        IOError,
        ConnectionError,
        TimeoutError,
        OSError,
    )
    
    # Permanent errors that won't succeed on retry
    permanent_types = (
        ValidationError,
        PermanentError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
        SyntaxError,
    )
    
    if isinstance(error, transient_types):
        return 'transient'
    elif isinstance(error, permanent_types):
        return 'permanent'
    else:
        return 'unknown'


def create_error_summary(errors: List[tuple[str, Exception]]) -> str:
    """
    Create a human-readable summary of errors.
    
    Args:
        errors: List of (item_id, exception) tuples
    
    Returns:
        Formatted error summary
    """
    if not errors:
        return "No errors occurred"
    
    lines = [f"Encountered {len(errors)} error(s):"]
    
    # Group errors by type
    by_type: dict[str, List[str]] = {}
    for item_id, error in errors:
        error_type = type(error).__name__
        if error_type not in by_type:
            by_type[error_type] = []
        by_type[error_type].append(f"  - {item_id}: {str(error)}")
    
    # Format by type
    for error_type, items in sorted(by_type.items()):
        lines.append(f"\n{error_type}:")
        lines.extend(items[:5])  # Show first 5 of each type
        if len(items) > 5:
            lines.append(f"  ... and {len(items) - 5} more")
    
    return "\n".join(lines)


class GracefulDegradation:
    """
    Context manager for graceful degradation of operations.
    
    Allows operations to partially succeed even if some items fail.
    """
    
    def __init__(self, operation_name: str, continue_on_error: bool = True):
        """
        Initialize graceful degradation context.
        
        Args:
            operation_name: Name of the operation for logging
            continue_on_error: If True, continue processing after errors
        """
        self.operation_name = operation_name
        self.continue_on_error = continue_on_error
        self.successful_results: List[Any] = []
        self.failed_items: List[tuple[str, Exception]] = []
    
    def process_item(self, item_id: str, operation: Callable[[], T]) -> Optional[T]:
        """
        Process a single item with error handling.
        
        Args:
            item_id: Identifier for the item being processed
            operation: Function to execute for this item
        
        Returns:
            Result of operation or None if it failed
        """
        try:
            result = operation()
            self.successful_results.append(result)
            return result
        except Exception as e:
            logger.warning(f"Failed to process {item_id} in {self.operation_name}: {e}")
            self.failed_items.append((item_id, e))
            
            if not self.continue_on_error:
                raise
            
            return None
    
    def get_results(self) -> tuple[List[Any], List[tuple[str, Exception]]]:
        """
        Get results and errors.
        
        Returns:
            Tuple of (successful_results, failed_items)
        """
        return self.successful_results, self.failed_items
    
    def has_failures(self) -> bool:
        """Check if any items failed."""
        return len(self.failed_items) > 0
    
    def raise_if_all_failed(self) -> None:
        """Raise exception if all items failed."""
        if self.failed_items and not self.successful_results:
            error_summary = create_error_summary(self.failed_items)
            raise PartialFailureError(
                f"All items failed in {self.operation_name}:\n{error_summary}",
                self.successful_results,
                self.failed_items
            )
    
    def log_summary(self) -> None:
        """Log a summary of the operation."""
        total = len(self.successful_results) + len(self.failed_items)
        success_rate = len(self.successful_results) / total * 100 if total > 0 else 0
        
        logger.info(
            f"{self.operation_name} completed: "
            f"{len(self.successful_results)}/{total} successful ({success_rate:.1f}%)"
        )
        
        if self.failed_items:
            error_summary = create_error_summary(self.failed_items)
            logger.warning(f"Errors in {self.operation_name}:\n{error_summary}")


def create_partial_report_on_failure(
    session_id: str,
    successful_analyses: List[Any],
    failed_files: List[tuple[str, Exception]],
    error: Exception
) -> dict:
    """
    Create a partial report when analysis fails.
    
    Args:
        session_id: Session identifier
        successful_analyses: List of successful file analyses
        failed_files: List of (file_path, exception) tuples for failed files
        error: The exception that caused the failure
    
    Returns:
        Dictionary containing partial report data
    """
    from datetime import datetime, timezone
    
    report = {
        'session_id': session_id,
        'status': 'partial_failure',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'error': str(error),
        'error_type': type(error).__name__,
        'successful_analyses': len(successful_analyses),
        'failed_files': len(failed_files),
        'analyses': successful_analyses,
        'errors': [
            {
                'file': file_path,
                'error': str(exc),
                'error_type': type(exc).__name__
            }
            for file_path, exc in failed_files
        ]
    }
    
    return report
