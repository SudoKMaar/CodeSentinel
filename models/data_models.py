"""
Core data models for the Code Review & Documentation Agent.

This module defines all Pydantic models used throughout the system for
data validation, serialization, and type safety.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict


class AnalysisDepth(str, Enum):
    """Analysis depth levels."""
    QUICK = "quick"
    STANDARD = "standard"
    DEEP = "deep"


class IssueSeverity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueCategory(str, Enum):
    """Issue category types."""
    COMPLEXITY = "complexity"
    SECURITY = "security"
    STYLE = "style"
    DUPLICATION = "duplication"
    ERROR_HANDLING = "error_handling"
    NAMING = "naming"


class EffortLevel(str, Enum):
    """Effort estimation levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ImpactLevel(str, Enum):
    """Impact estimation levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SessionStatus(str, Enum):
    """Session status values."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class PatternType(str, Enum):
    """Project pattern types."""
    NAMING = "naming"
    STRUCTURE = "structure"
    CONVENTION = "convention"


class AnalysisConfig(BaseModel):
    """Configuration for code analysis."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    target_path: str = Field(..., description="Path to the codebase to analyze")
    file_patterns: List[str] = Field(
        default_factory=lambda: ["*.py", "*.js", "*.ts", "*.tsx", "*.jsx"],
        description="File patterns to include in analysis"
    )
    exclude_patterns: List[str] = Field(
        default_factory=lambda: ["node_modules/**", "venv/**", ".git/**", "__pycache__/**"],
        description="Patterns to exclude from analysis"
    )
    coding_standards: Dict[str, Any] = Field(
        default_factory=dict,
        description="Project-specific coding standards"
    )
    analysis_depth: AnalysisDepth = Field(
        default=AnalysisDepth.STANDARD,
        description="Depth of analysis to perform"
    )
    enable_parallel: bool = Field(
        default=True,
        description="Enable parallel file processing"
    )
    
    @field_validator("target_path")
    @classmethod
    def validate_target_path(cls, v: str) -> str:
        """
        Validate that target path is not empty and contains valid characters.
        
        Raises:
            ValueError: If path is empty or contains only whitespace
        """
        if not v or not v.strip():
            raise ValueError("target_path cannot be empty or whitespace")
        
        # Check for obviously invalid characters
        invalid_chars = ['<', '>', '|', '\0']
        if any(char in v for char in invalid_chars):
            raise ValueError(f"target_path contains invalid characters: {v}")
        
        return v.strip()
    
    @field_validator("file_patterns")
    @classmethod
    def validate_file_patterns(cls, v: List[str]) -> List[str]:
        """
        Validate file patterns are not empty and contain valid patterns.
        
        Raises:
            ValueError: If patterns list is empty or contains invalid patterns
        """
        if not v:
            raise ValueError("file_patterns cannot be empty - at least one pattern is required")
        
        validated = []
        for pattern in v:
            if not pattern or not pattern.strip():
                raise ValueError("file_patterns cannot contain empty patterns")
            
            # Basic validation - patterns should contain at least one alphanumeric or wildcard
            if not any(c.isalnum() or c in '*?.' for c in pattern):
                raise ValueError(f"Invalid file pattern: {pattern}")
            
            validated.append(pattern.strip())
        
        return validated
    
    @field_validator("exclude_patterns")
    @classmethod
    def validate_exclude_patterns(cls, v: List[str]) -> List[str]:
        """
        Validate exclude patterns contain valid patterns.
        
        Raises:
            ValueError: If patterns contain invalid values
        """
        validated = []
        for pattern in v:
            if not pattern or not pattern.strip():
                continue  # Skip empty patterns in exclude list
            validated.append(pattern.strip())
        
        return validated


class CodeMetrics(BaseModel):
    """Code quality metrics for a file or function."""
    
    cyclomatic_complexity: int = Field(
        ge=1,
        description="Cyclomatic complexity score"
    )
    maintainability_index: float = Field(
        ge=0.0,
        le=100.0,
        description="Maintainability index (0-100)"
    )
    lines_of_code: int = Field(
        ge=0,
        description="Total lines of code"
    )
    comment_ratio: float = Field(
        ge=0.0,
        le=1.0,
        description="Ratio of comments to code (0-1)"
    )
    test_coverage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Test coverage percentage (0-100)"
    )


class CodeIssue(BaseModel):
    """Represents a code quality issue."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    severity: IssueSeverity = Field(..., description="Issue severity level")
    category: IssueCategory = Field(..., description="Issue category")
    file_path: str = Field(..., description="Path to the file containing the issue")
    line_number: int = Field(ge=1, description="Line number where issue occurs")
    description: str = Field(..., min_length=1, description="Description of the issue")
    code_snippet: str = Field(..., description="Code snippet showing the issue")
    suggestion: Optional[str] = Field(
        default=None,
        description="Suggested fix for the issue"
    )


class FunctionInfo(BaseModel):
    """Information about a function or method."""
    
    name: str = Field(..., min_length=1, description="Function name")
    line_number: int = Field(ge=1, description="Starting line number")
    parameters: List[str] = Field(
        default_factory=list,
        description="Function parameters"
    )
    return_type: Optional[str] = Field(
        default=None,
        description="Return type annotation"
    )
    docstring: Optional[str] = Field(
        default=None,
        description="Function docstring"
    )
    complexity: int = Field(
        ge=1,
        description="Cyclomatic complexity"
    )


class ClassInfo(BaseModel):
    """Information about a class."""
    
    name: str = Field(..., min_length=1, description="Class name")
    line_number: int = Field(ge=1, description="Starting line number")
    methods: List[str] = Field(
        default_factory=list,
        description="Method names"
    )
    base_classes: List[str] = Field(
        default_factory=list,
        description="Base class names"
    )
    docstring: Optional[str] = Field(
        default=None,
        description="Class docstring"
    )


class FileAnalysis(BaseModel):
    """Analysis results for a single file."""
    
    file_path: str = Field(..., description="Path to the analyzed file")
    language: str = Field(..., description="Programming language")
    metrics: CodeMetrics = Field(..., description="Code metrics for the file")
    issues: List[CodeIssue] = Field(
        default_factory=list,
        description="Issues found in the file"
    )
    functions: List[FunctionInfo] = Field(
        default_factory=list,
        description="Functions defined in the file"
    )
    classes: List[ClassInfo] = Field(
        default_factory=list,
        description="Classes defined in the file"
    )


class Suggestion(BaseModel):
    """Improvement suggestion for code quality."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    priority: int = Field(ge=1, le=5, description="Priority level (1=highest, 5=lowest)")
    category: str = Field(..., min_length=1, description="Suggestion category")
    title: str = Field(..., min_length=1, description="Suggestion title")
    description: str = Field(..., min_length=1, description="Detailed description")
    code_example: Optional[str] = Field(
        default=None,
        description="Example code demonstrating the suggestion"
    )
    estimated_effort: EffortLevel = Field(..., description="Estimated implementation effort")
    impact: ImpactLevel = Field(..., description="Expected impact on code quality")
    related_issues: List[str] = Field(
        default_factory=list,
        description="IDs of related issues"
    )


class Documentation(BaseModel):
    """Generated documentation."""
    
    project_structure: str = Field(..., description="Project structure documentation")
    api_docs: Dict[str, str] = Field(
        default_factory=dict,
        description="API documentation by module"
    )
    examples: Dict[str, str] = Field(
        default_factory=dict,
        description="Code examples by topic"
    )


class MetricsSummary(BaseModel):
    """Summary of code metrics across the codebase."""
    
    total_files: int = Field(ge=0, description="Total files analyzed")
    total_lines: int = Field(ge=0, description="Total lines of code")
    average_complexity: float = Field(ge=0.0, description="Average cyclomatic complexity")
    average_maintainability: float = Field(
        ge=0.0,
        le=100.0,
        description="Average maintainability index"
    )
    total_issues_by_severity: Dict[str, int] = Field(
        default_factory=dict,
        description="Issue counts by severity"
    )
    total_issues_by_category: Dict[str, int] = Field(
        default_factory=dict,
        description="Issue counts by category"
    )


class AnalysisResult(BaseModel):
    """Complete analysis results."""
    
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    timestamp: datetime = Field(..., description="Analysis timestamp")
    codebase_path: str = Field(..., description="Path to analyzed codebase")
    files_analyzed: int = Field(ge=0, description="Number of files analyzed")
    total_issues: int = Field(ge=0, description="Total issues found")
    quality_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Overall quality score (0-100)"
    )
    file_analyses: List[FileAnalysis] = Field(
        default_factory=list,
        description="Per-file analysis results"
    )
    suggestions: List[Suggestion] = Field(
        default_factory=list,
        description="Improvement suggestions"
    )
    documentation: Documentation = Field(..., description="Generated documentation")
    metrics_summary: MetricsSummary = Field(..., description="Metrics summary")


class SessionState(BaseModel):
    """State of an analysis session for pause/resume."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    session_id: str = Field(..., min_length=1, description="Unique session identifier")
    status: SessionStatus = Field(..., description="Current session status")
    config: AnalysisConfig = Field(..., description="Analysis configuration")
    processed_files: List[str] = Field(
        default_factory=list,
        description="Files already processed"
    )
    pending_files: List[str] = Field(
        default_factory=list,
        description="Files pending processing"
    )
    partial_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Partial analysis results"
    )
    checkpoint_time: datetime = Field(..., description="Last checkpoint timestamp")


class ProjectPattern(BaseModel):
    """Learned pattern for a project."""
    
    model_config = ConfigDict(use_enum_values=True)
    
    pattern_id: str = Field(..., min_length=1, description="Unique pattern identifier")
    project_id: str = Field(..., min_length=1, description="Project identifier")
    pattern_type: PatternType = Field(..., description="Type of pattern")
    description: str = Field(..., min_length=1, description="Pattern description")
    examples: List[str] = Field(
        default_factory=list,
        description="Example instances of the pattern"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    last_updated: datetime = Field(..., description="Last update timestamp")
    
    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v


class QualityTrend(BaseModel):
    """Quality trend data point for tracking over time."""
    
    timestamp: datetime = Field(..., description="When this measurement was taken")
    quality_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Quality score at this point in time"
    )
    total_issues: int = Field(ge=0, description="Total issues at this point")
    critical_issues: int = Field(ge=0, description="Critical issues at this point")
    high_issues: int = Field(ge=0, description="High severity issues at this point")
    files_analyzed: int = Field(ge=0, description="Number of files analyzed")


class QualityComparison(BaseModel):
    """Comparison metrics between two analyses."""
    
    previous_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Previous quality score"
    )
    current_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Current quality score"
    )
    score_delta: float = Field(description="Change in quality score")
    issues_delta: int = Field(description="Change in total issues")
    critical_issues_delta: int = Field(description="Change in critical issues")
    improvement_percentage: float = Field(description="Percentage improvement")


class EvaluationStatistics(BaseModel):
    """Statistics for evaluating agent performance."""
    
    total_analyses: int = Field(ge=0, description="Total number of analyses performed")
    total_issues_found: int = Field(ge=0, description="Total issues found across all analyses")
    total_suggestions_made: int = Field(ge=0, description="Total suggestions made")
    issues_resolved: int = Field(ge=0, description="Number of issues resolved")
    suggestions_implemented: int = Field(ge=0, description="Number of suggestions implemented")
    resolution_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Rate of issue resolution (0-1)"
    )
    implementation_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Rate of suggestion implementation (0-1)"
    )
    average_quality_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Average quality score across analyses"
    )
    documentation_coverage: float = Field(
        ge=0.0,
        le=1.0,
        description="Percentage of code with documentation (0-1)"
    )


class SuggestionImpact(BaseModel):
    """Impact measurement for an implemented suggestion."""
    
    suggestion_id: str = Field(..., description="Unique suggestion identifier")
    suggestion_title: str = Field(..., description="Title of the suggestion")
    implemented_at: datetime = Field(..., description="When the suggestion was implemented")
    before_metrics: CodeMetrics = Field(..., description="Metrics before implementation")
    after_metrics: CodeMetrics = Field(..., description="Metrics after implementation")
    complexity_improvement: float = Field(description="Change in complexity")
    maintainability_improvement: float = Field(description="Change in maintainability")
    issues_resolved: int = Field(ge=0, description="Number of issues resolved by this change")
