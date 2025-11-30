"""
Observability module for structured logging and tracing.

This module provides:
- Structured JSON logging with structlog
- OpenTelemetry instrumentation for distributed tracing
- Correlation ID generation and propagation
- Metrics collection for analysis operations
- Log storage and retrieval for historical sessions
"""

import uuid
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

import structlog
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode


class ObservabilityManager:
    """
    Manages observability for the code review agent system.
    
    Provides:
    - Structured logging with correlation IDs
    - Distributed tracing with OpenTelemetry
    - Metrics collection for operations
    - Historical log storage and retrieval
    """
    
    def __init__(
        self,
        service_name: str = "code-review-agent",
        logs_dir: str = ".logs",
        enable_console_export: bool = True
    ):
        """
        Initialize the Observability Manager.
        
        Args:
            service_name: Name of the service for tracing
            logs_dir: Directory for storing log files
            enable_console_export: Whether to export traces to console
        """
        self.service_name = service_name
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize structured logging
        self._setup_logging()
        
        # Initialize OpenTelemetry tracing
        self._setup_tracing(enable_console_export)
        
        # Get logger and tracer
        self.logger = structlog.get_logger()
        self.tracer = trace.get_tracer(__name__)
        
        # Metrics storage
        self.metrics: Dict[str, List[Dict[str, Any]]] = {}
    
    def _setup_logging(self) -> None:
        """Configure structlog for structured JSON logging."""
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def _setup_tracing(self, enable_console_export: bool) -> None:
        """Configure OpenTelemetry tracing."""
        # Create resource with service information
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "1.0.0",
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Add span processor with console exporter if enabled
        if enable_console_export:
            processor = BatchSpanProcessor(ConsoleSpanExporter())
            provider.add_span_processor(processor)
        
        # Set as global tracer provider
        trace.set_tracer_provider(provider)
    
    def generate_correlation_id(self) -> str:
        """
        Generate a unique correlation ID for request tracking.
        
        Returns:
            UUID-based correlation ID
        """
        return str(uuid.uuid4())
    
    def bind_correlation_id(self, correlation_id: str) -> None:
        """
        Bind a correlation ID to the current logging context.
        
        Args:
            correlation_id: The correlation ID to bind
        """
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    
    def unbind_correlation_id(self) -> None:
        """Remove correlation ID from logging context."""
        structlog.contextvars.unbind_contextvars("correlation_id")
    
    @contextmanager
    def correlation_context(self, correlation_id: Optional[str] = None):
        """
        Context manager for correlation ID binding.
        
        Args:
            correlation_id: Optional correlation ID (generates new if None)
            
        Yields:
            The correlation ID being used
        """
        if correlation_id is None:
            correlation_id = self.generate_correlation_id()
        
        self.bind_correlation_id(correlation_id)
        try:
            yield correlation_id
        finally:
            self.unbind_correlation_id()
    
    @contextmanager
    def trace_operation(
        self,
        operation_name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for tracing an operation.
        
        Args:
            operation_name: Name of the operation being traced
            attributes: Optional attributes to attach to the span
            
        Yields:
            The span object
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            # Add attributes if provided
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, str(value))
            
            try:
                yield span
            except Exception as e:
                # Record exception in span
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
    
    def log_operation(
        self,
        operation: str,
        level: str = "info",
        **kwargs
    ) -> None:
        """
        Log an operation with structured data.
        
        Args:
            operation: Name of the operation
            level: Log level (debug, info, warning, error, critical)
            **kwargs: Additional context to log
        """
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(
            operation,
            timestamp=datetime.now(timezone.utc).isoformat(),
            **kwargs
        )
    
    def log_agent_operation(
        self,
        agent_name: str,
        operation: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log an agent operation with standard fields.
        
        Args:
            agent_name: Name of the agent performing the operation
            operation: Operation being performed
            session_id: Optional session identifier
            **kwargs: Additional context
        """
        self.log_operation(
            f"{agent_name}.{operation}",
            agent=agent_name,
            session_id=session_id,
            **kwargs
        )
    
    def log_file_analysis(
        self,
        file_path: str,
        language: str,
        duration_ms: float,
        issues_found: int,
        session_id: Optional[str] = None
    ) -> None:
        """
        Log file analysis completion.
        
        Args:
            file_path: Path to the analyzed file
            language: Programming language
            duration_ms: Analysis duration in milliseconds
            issues_found: Number of issues found
            session_id: Optional session identifier
        """
        self.log_operation(
            "file_analysis_complete",
            file_path=file_path,
            language=language,
            duration_ms=duration_ms,
            issues_found=issues_found,
            session_id=session_id
        )
    
    def log_analysis_complete(
        self,
        session_id: str,
        files_analyzed: int,
        total_issues: int,
        duration_seconds: float,
        quality_score: float
    ) -> None:
        """
        Log analysis completion with summary metrics.
        
        Args:
            session_id: Session identifier
            files_analyzed: Number of files analyzed
            total_issues: Total issues found
            duration_seconds: Total analysis duration
            quality_score: Calculated quality score
        """
        self.log_operation(
            "analysis_complete",
            session_id=session_id,
            files_analyzed=files_analyzed,
            total_issues=total_issues,
            duration_seconds=duration_seconds,
            quality_score=quality_score
        )
    
    def log_error(
        self,
        operation: str,
        error: Exception,
        session_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log an error with exception details.
        
        Args:
            operation: Operation that failed
            error: The exception that occurred
            session_id: Optional session identifier
            **kwargs: Additional context
        """
        self.log_operation(
            operation,
            level="error",
            error_type=type(error).__name__,
            error_message=str(error),
            session_id=session_id,
            **kwargs
        )
    
    def record_metric(
        self,
        metric_name: str,
        value: float,
        unit: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            tags: Optional tags for the metric
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        metric_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": value,
            "unit": unit,
            "tags": tags or {}
        }
        
        self.metrics[metric_name].append(metric_entry)
        
        # Log the metric
        self.log_operation(
            "metric_recorded",
            level="debug",
            metric_name=metric_name,
            value=value,
            unit=unit,
            tags=tags
        )
    
    def get_metrics(
        self,
        metric_name: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get recorded metrics.
        
        Args:
            metric_name: Optional specific metric to retrieve
            
        Returns:
            Dictionary of metrics
        """
        if metric_name:
            return {metric_name: self.metrics.get(metric_name, [])}
        return self.metrics.copy()
    
    def store_session_logs(
        self,
        session_id: str,
        logs: List[Dict[str, Any]]
    ) -> None:
        """
        Store logs for a session to disk.
        
        Args:
            session_id: Session identifier
            logs: List of log entries
        """
        log_file = self.logs_dir / f"{session_id}.json"
        
        # Append to existing logs if file exists
        existing_logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            except (json.JSONDecodeError, IOError):
                existing_logs = []
        
        # Combine and write
        all_logs = existing_logs + logs
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(all_logs, f, indent=2, ensure_ascii=False)
    
    def retrieve_session_logs(
        self,
        session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of log entries for the session
        """
        log_file = self.logs_dir / f"{session_id}.json"
        
        if not log_file.exists():
            return []
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    
    def list_session_logs(self) -> List[str]:
        """
        List all session IDs that have logs.
        
        Returns:
            List of session IDs
        """
        return [f.stem for f in self.logs_dir.glob("*.json")]
    
    def delete_session_logs(self, session_id: str) -> bool:
        """
        Delete logs for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully, False otherwise
        """
        log_file = self.logs_dir / f"{session_id}.json"
        
        if not log_file.exists():
            return False
        
        try:
            log_file.unlink()
            return True
        except OSError:
            return False
    
    def cleanup_old_logs(self, max_age_days: int = 30) -> int:
        """
        Clean up logs older than the specified age.
        
        Args:
            max_age_days: Maximum age in days for logs to keep
            
        Returns:
            Number of log files deleted
        """
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        deleted_count = 0
        for log_file in self.logs_dir.glob("*.json"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except OSError:
                    pass
        
        return deleted_count


# Global observability manager instance
_observability_manager: Optional[ObservabilityManager] = None


def get_observability_manager() -> ObservabilityManager:
    """
    Get the global observability manager instance.
    
    Returns:
        ObservabilityManager instance
    """
    global _observability_manager
    if _observability_manager is None:
        _observability_manager = ObservabilityManager()
    return _observability_manager


def setup_observability(
    service_name: str = "code-review-agent",
    logs_dir: str = ".logs",
    enable_console_export: bool = True
) -> ObservabilityManager:
    """
    Setup and configure the global observability manager.
    
    Args:
        service_name: Name of the service for tracing
        logs_dir: Directory for storing log files
        enable_console_export: Whether to export traces to console
        
    Returns:
        Configured ObservabilityManager instance
    """
    global _observability_manager
    _observability_manager = ObservabilityManager(
        service_name=service_name,
        logs_dir=logs_dir,
        enable_console_export=enable_console_export
    )
    return _observability_manager
