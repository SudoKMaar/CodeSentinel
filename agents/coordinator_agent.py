"""
Coordinator Agent for orchestrating the multi-agent workflow.

This agent performs:
- Workflow orchestration using LangGraph
- Configuration loading from YAML files
- Parallel execution of Analyzer and Documenter agents
- Sequential execution of Reviewer agent after analysis
- Result aggregation and report generation
- Memory Bank integration for pattern retrieval and storage
"""

import uuid
import yaml
import structlog
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logger
logger = structlog.get_logger()

from models.data_models import (
    AnalysisConfig,
    AnalysisResult,
    FileAnalysis,
    Suggestion,
    Documentation,
    MetricsSummary,
    IssueSeverity,
    IssueCategory,
    SessionState,
    SessionStatus,
    ProjectPattern,
    PatternType,
)
from agents.analyzer_agent import AnalyzerAgent
from agents.documenter_agent import DocumenterAgent, CodebaseStructure
from agents.reviewer_agent import ReviewerAgent
from agents.llm_reviewer_agent import LLMReviewerAgent
from storage.memory_bank import MemoryBank
from storage.session_manager import SessionManager
from tools.file_system import FileSystemTool
from tools.code_parser import CodeParserTool
from tools.quality_metrics import QualityMetricsCalculator
from tools.cicd_integration import GitIntegration
from tools.error_handling import (
    retry_with_backoff,
    validate_path,
    validate_session_id,
    GracefulDegradation,
    create_partial_report_on_failure,
    ValidationError,
    PartialFailureError,
    logger as error_logger,
)


class CoordinatorAgent:
    """
    Main orchestrator for the multi-agent code review system.
    
    Coordinates:
    - File discovery and filtering
    - Parallel analysis and documentation generation
    - Sequential review and suggestion generation
    - Memory Bank pattern retrieval and storage
    - Session state management for pause/resume
    """
    
    def __init__(
        self,
        memory_bank: Optional[MemoryBank] = None,
        session_manager: Optional[SessionManager] = None,
        quality_metrics: Optional[QualityMetricsCalculator] = None,
        max_workers: int = 4
    ):
        """
        Initialize the Coordinator Agent.
        
        Args:
            memory_bank: Memory Bank instance for pattern storage
            session_manager: Session Manager instance for state persistence
            quality_metrics: Quality metrics calculator for evaluation
            max_workers: Maximum number of parallel workers
        """
        self.memory_bank = memory_bank or MemoryBank()
        self.session_manager = session_manager or SessionManager()
        self.quality_metrics = quality_metrics or QualityMetricsCalculator()
        self.max_workers = max_workers
        
        # Initialize tools
        self.file_system = FileSystemTool()
        self.code_parser = CodeParserTool()
        
        # Initialize agents
        self.analyzer = AnalyzerAgent(max_workers=max_workers)
        self.documenter = DocumenterAgent()
        self.reviewer = ReviewerAgent()
        
        # Initialize LLM-powered reviewer (with fallback to rule-based)
        try:
            self.llm_reviewer = LLMReviewerAgent(enable_llm=True)
        except Exception as e:
            logger.warning(f"LLM Reviewer initialization failed: {e}. Using rule-based reviewer only.")
            self.llm_reviewer = None
    
    def analyze_codebase(
        self,
        config: AnalysisConfig,
        session_id: Optional[str] = None,
        project_id: Optional[str] = None,
        pr_mode: bool = False,
        base_ref: str = "origin/main",
        head_ref: str = "HEAD"
    ) -> AnalysisResult:
        """
        Analyze a codebase with the full multi-agent workflow.
        
        Args:
            config: Analysis configuration
            session_id: Optional session ID for resume (creates new if None)
            project_id: Optional project ID for Memory Bank patterns
            pr_mode: If True, analyze only changed files in PR
            base_ref: Base Git reference for PR mode (default: origin/main)
            head_ref: Head Git reference for PR mode (default: HEAD)
        
        Returns:
            Complete analysis results
        
        Raises:
            ValidationError: If input validation fails
            PartialFailureError: If some files fail but others succeed
        """
        # Validate inputs
        try:
            validate_path(config.target_path, must_exist=True, must_be_dir=True)
        except ValidationError as e:
            error_logger.error(f"Invalid target path: {e}")
            raise
        
        # Generate session ID if not provided
        if session_id is None:
            session_id = str(uuid.uuid4())
        else:
            session_id = validate_session_id(session_id)
        
        # Use target path as project ID if not provided
        if project_id is None:
            project_id = Path(config.target_path).name
        
        # Discover files to analyze
        if pr_mode:
            # Use Git integration to get only changed files
            try:
                git_integration = GitIntegration(config.target_path)
                files = git_integration.get_changed_files(
                    base_ref=base_ref,
                    head_ref=head_ref,
                    file_patterns=config.file_patterns
                )
            except (ValueError, RuntimeError) as e:
                # Fall back to full analysis if Git integration fails
                print(f"Warning: Git integration failed ({e}), falling back to full analysis")
                files = self.file_system.discover_files(
                    config.target_path,
                    include_patterns=config.file_patterns,
                    exclude_patterns=config.exclude_patterns
                )
        else:
            files = self.file_system.discover_files(
                config.target_path,
                include_patterns=config.file_patterns,
                exclude_patterns=config.exclude_patterns
            )
        
        # Create session state
        session_state = self.session_manager.create_session(
            session_id=session_id,
            config=config,
            pending_files=files
        )
        
        try:
            # Retrieve project patterns from Memory Bank with retry logic
            project_patterns = self._retrieve_patterns_with_retry(project_id)
            
            # Read file contents with graceful degradation
            file_contents, failed_reads = self._read_files_with_graceful_degradation(files)
            
            # Handle empty codebase (no files to analyze)
            if len(files) == 0:
                logger.info(f"No files to analyze for session {session_id}")
                # Return empty result with perfect quality score
                return AnalysisResult(
                    session_id=session_id,
                    timestamp=datetime.now(timezone.utc),
                    codebase_path=config.target_path,
                    files_analyzed=0,
                    total_issues=0,
                    quality_score=100.0,
                    file_analyses=[],
                    suggestions=[],
                    documentation=Documentation(
                        project_structure="",
                        api_docs={},
                        code_examples={}
                    ),
                    metrics_summary=MetricsSummary(
                        total_files=0,
                        total_lines=0,
                        average_complexity=0.0,
                        average_maintainability=100.0
                    )
                )
            
            # If all files failed to read, create partial report
            if not file_contents:
                error_logger.error(f"Failed to read any files for session {session_id}")
                partial_report = create_partial_report_on_failure(
                    session_id=session_id,
                    successful_analyses=[],
                    failed_files=failed_reads,
                    error=PartialFailureError(
                        "All files failed to read",
                        [],
                        failed_reads
                    )
                )
                self.session_manager.fail_session(session_id)
                raise PartialFailureError(
                    f"Failed to read all {len(files)} files",
                    [],
                    failed_reads
                )
            
            # Log warning if some files failed
            if failed_reads:
                error_logger.warning(
                    f"Failed to read {len(failed_reads)} out of {len(files)} files. "
                    f"Continuing with {len(file_contents)} files."
                )
            
            # Phase 1: Parallel execution of Analyzer and Documenter with error handling
            analysis_results, documentation, analysis_failures = self._execute_parallel_phase_with_recovery(
                file_contents,
                config,
                session_id
            )
            
            # If all analyses failed, create partial report
            if not analysis_results:
                error_logger.error(f"All file analyses failed for session {session_id}")
                all_failures = failed_reads + analysis_failures
                partial_report = create_partial_report_on_failure(
                    session_id=session_id,
                    successful_analyses=[],
                    failed_files=all_failures,
                    error=PartialFailureError(
                        "All file analyses failed",
                        [],
                        all_failures
                    )
                )
                self.session_manager.fail_session(session_id)
                raise PartialFailureError(
                    f"Failed to analyze all files",
                    [],
                    all_failures
                )
            
            # Log warning if some analyses failed
            if analysis_failures:
                error_logger.warning(
                    f"Failed to analyze {len(analysis_failures)} files. "
                    f"Continuing with {len(analysis_results)} successful analyses."
                )
            
            # Phase 2: Sequential execution of Reviewer with fallback
            try:
                suggestions = self._execute_review_phase(
                    analysis_results,
                    project_patterns
                )
            except Exception as e:
                error_logger.error(f"Reviewer phase failed: {e}. Generating partial report without suggestions.")
                suggestions = []  # Continue without suggestions
            
            # Calculate quality score using quality metrics calculator
            try:
                quality_score = self.quality_metrics.calculate_quality_score(analysis_results)
            except Exception as e:
                error_logger.error(f"Quality score calculation failed: {e}. Using default score.")
                quality_score = 50.0  # Default middle score
            
            # Generate metrics summary
            metrics_summary = self._generate_metrics_summary(analysis_results)
            
            # Store new patterns in Memory Bank (non-critical, don't fail if this errors)
            try:
                self._store_discovered_patterns(
                    project_id,
                    analysis_results,
                    project_patterns
                )
            except Exception as e:
                error_logger.warning(f"Failed to store patterns in Memory Bank: {e}")
            
            # Create final result
            result = AnalysisResult(
                session_id=session_id,
                timestamp=datetime.now(timezone.utc),
                codebase_path=config.target_path,
                files_analyzed=len(analysis_results),
                total_issues=sum(len(a.issues) for a in analysis_results),
                quality_score=quality_score,
                file_analyses=analysis_results,
                suggestions=suggestions,
                documentation=documentation,
                metrics_summary=metrics_summary
            )
            
            # Track quality trend for this project (non-critical)
            try:
                self.quality_metrics.track_quality_trend(project_id, result)
            except Exception as e:
                error_logger.warning(f"Failed to track quality trend: {e}")
            
            # Mark session as completed
            self.session_manager.complete_session(session_id)
            
            # If there were any failures, log them in the result
            if failed_reads or analysis_failures:
                error_logger.info(
                    f"Analysis completed with partial failures: "
                    f"{len(failed_reads)} read failures, {len(analysis_failures)} analysis failures"
                )
            
            return result
            
        except PartialFailureError:
            # Re-raise partial failures as-is
            raise
        except Exception as e:
            # Mark session as failed and create partial report if possible
            error_logger.error(f"Critical error in analysis: {e}")
            self.session_manager.fail_session(session_id)
            
            # Try to create a partial report with any successful work
            try:
                checkpoint_data = self.session_manager.load_session(session_id)
                if checkpoint_data and checkpoint_data.partial_results:
                    error_logger.info("Creating partial report from checkpoint data")
                    # Return partial results if available
                    pass
            except Exception as checkpoint_error:
                error_logger.error(f"Failed to recover from checkpoint: {checkpoint_error}")
            
            raise
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def _retrieve_patterns_with_retry(self, project_id: str) -> List[ProjectPattern]:
        """
        Retrieve project patterns from Memory Bank with retry logic.
        
        Args:
            project_id: Project identifier
        
        Returns:
            List of project patterns
        """
        try:
            return self.memory_bank.retrieve_patterns(
                project_id=project_id,
                min_confidence=0.5
            )
        except Exception as e:
            error_logger.warning(f"Failed to retrieve patterns for {project_id}: {e}")
            # Return empty list as fallback
            return []
    
    def _read_files_with_graceful_degradation(
        self,
        file_paths: List[str]
    ) -> tuple[List[tuple[str, str]], List[tuple[str, Exception]]]:
        """
        Read files with graceful degradation for failures.
        
        Args:
            file_paths: List of file paths to read
        
        Returns:
            Tuple of (successful_reads, failed_reads)
            - successful_reads: List of (file_path, content) tuples
            - failed_reads: List of (file_path, exception) tuples
        """
        degradation = GracefulDegradation("file reading", continue_on_error=True)
        
        for file_path in file_paths:
            def read_file():
                return (file_path, self.file_system.read_file(file_path))
            
            degradation.process_item(file_path, read_file)
        
        successful, failed = degradation.get_results()
        degradation.log_summary()
        
        return successful, failed
    
    def _execute_parallel_phase_with_recovery(
        self,
        file_contents: List[tuple[str, str]],
        config: AnalysisConfig,
        session_id: str
    ) -> tuple[List[FileAnalysis], Documentation, List[tuple[str, Exception]]]:
        """
        Execute Analyzer and Documenter agents in parallel with error recovery.
        
        Args:
            file_contents: List of (file_path, content) tuples
            config: Analysis configuration
            session_id: Session identifier
        
        Returns:
            Tuple of (analysis_results, documentation, analysis_failures)
        """
        analysis_results: List[FileAnalysis] = []
        documentation: Optional[Documentation] = None
        analysis_failures: List[tuple[str, Exception]] = []
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit analyzer task with error handling
            analyzer_future = executor.submit(
                self._analyze_files_with_graceful_degradation,
                file_contents
            )
            
            # Submit documenter task with error handling
            documenter_future = executor.submit(
                self._generate_documentation_with_fallback,
                file_contents,
                config.target_path
            )
            
            # Wait for both to complete
            try:
                analysis_results, analysis_failures = analyzer_future.result()
            except Exception as e:
                error_logger.error(f"Analyzer phase failed completely: {e}")
                analysis_failures = [(f[0], e) for f in file_contents]
            
            try:
                documentation = documenter_future.result()
            except Exception as e:
                error_logger.error(f"Documenter phase failed: {e}. Using empty documentation.")
                # Create minimal documentation as fallback
                documentation = Documentation(
                    project_structure="Documentation generation failed",
                    api_docs={},
                    examples={}
                )
        
        # Checkpoint progress with full analysis results
        if analysis_results:
            processed_files = [a.file_path for a in analysis_results]
            
            # Store analysis results in serializable format
            analysis_dicts = [a.model_dump(mode='json') for a in analysis_results]
            
            try:
                self.session_manager.checkpoint(
                    session_id=session_id,
                    processed_files=processed_files,
                    pending_files=[],
                    partial_results={
                        'analysis_count': len(analysis_results),
                        'file_analyses': analysis_dicts,
                        'failed_files': [(f, str(e)) for f, e in analysis_failures]
                    }
                )
            except Exception as e:
                error_logger.error(f"Failed to checkpoint progress: {e}")
        
        return analysis_results, documentation, analysis_failures
    
    def _analyze_files_with_graceful_degradation(
        self,
        file_contents: List[tuple[str, str]]
    ) -> tuple[List[FileAnalysis], List[tuple[str, Exception]]]:
        """
        Analyze files with graceful degradation for parse failures.
        
        Args:
            file_contents: List of (file_path, content) tuples
        
        Returns:
            Tuple of (successful_analyses, failed_analyses)
        """
        degradation = GracefulDegradation("file analysis", continue_on_error=True)
        
        for file_path, content in file_contents:
            def analyze_file():
                result = self.analyzer.analyze_file(file_path, content)
                if result is None:
                    raise ValueError(f"Failed to parse {file_path}")
                return result
            
            degradation.process_item(file_path, analyze_file)
        
        successful, failed = degradation.get_results()
        degradation.log_summary()
        
        return successful, failed
    
    def _generate_documentation_with_fallback(
        self,
        file_contents: List[tuple[str, str]],
        root_path: str
    ) -> Documentation:
        """
        Generate documentation with fallback for failures.
        
        Args:
            file_contents: List of (file_path, content) tuples
            root_path: Root path of the codebase
        
        Returns:
            Generated documentation (may be partial if errors occur)
        """
        try:
            return self._generate_documentation(file_contents, root_path)
        except Exception as e:
            error_logger.error(f"Documentation generation failed: {e}")
            # Return minimal documentation
            return Documentation(
                project_structure=f"# Project at {root_path}\n\nDocumentation generation encountered errors.",
                api_docs={},
                examples={}
            )
    
    def _execute_parallel_phase(
        self,
        file_contents: List[tuple[str, str]],
        config: AnalysisConfig,
        session_id: str
    ) -> tuple[List[FileAnalysis], Documentation]:
        """
        Execute Analyzer and Documenter agents in parallel.
        
        DEPRECATED: Use _execute_parallel_phase_with_recovery instead.
        This method is kept for backward compatibility.
        
        Args:
            file_contents: List of (file_path, content) tuples
            config: Analysis configuration
            session_id: Session identifier
        
        Returns:
            Tuple of (analysis_results, documentation)
        """
        analysis_results, documentation, _ = self._execute_parallel_phase_with_recovery(
            file_contents,
            config,
            session_id
        )
        return analysis_results, documentation
    
    def _generate_documentation(
        self,
        file_contents: List[tuple[str, str]],
        root_path: str
    ) -> Documentation:
        """
        Generate documentation using the Documenter agent.
        
        Args:
            file_contents: List of (file_path, content) tuples
            root_path: Root path of the codebase
        
        Returns:
            Generated documentation
        """
        # Build codebase structure
        codebase_structure = CodebaseStructure(root_path)
        
        # Analyze files to extract structure
        file_analyses: List[FileAnalysis] = []
        for file_path, content in file_contents:
            language = self.code_parser.detect_language(file_path)
            if language:
                codebase_structure.add_file(file_path, language)
                
                # Parse for documentation generation
                tree = self.code_parser.parse_code(content, language)
                if tree and not self.code_parser.has_syntax_errors(tree):
                    # Extract basic info for documentation
                    functions = self.code_parser.extract_functions(tree, language)
                    classes = self.code_parser.extract_classes(tree, language)
                    
                    # Create minimal FileAnalysis for documentation
                    from models.data_models import CodeMetrics, FunctionInfo, ClassInfo
                    
                    func_infos = [
                        FunctionInfo(
                            name=f['name'] or 'anonymous',
                            line_number=f['line_number'],
                            parameters=f['parameters'],
                            complexity=1
                        )
                        for f in functions if f['name']
                    ]
                    
                    class_infos = [
                        ClassInfo(
                            name=c['name'] or 'Anonymous',
                            line_number=c['line_number'],
                            methods=c['methods']
                        )
                        for c in classes if c['name']
                    ]
                    
                    file_analysis = FileAnalysis(
                        file_path=file_path,
                        language=language,
                        metrics=CodeMetrics(
                            cyclomatic_complexity=1,
                            maintainability_index=100.0,
                            lines_of_code=len(content.split('\n')),
                            comment_ratio=0.0
                        ),
                        issues=[],
                        functions=func_infos,
                        classes=class_infos
                    )
                    file_analyses.append(file_analysis)
        
        # Generate documentation components
        project_docs = self.documenter.generate_project_docs(codebase_structure)
        api_docs = self.documenter.generate_api_docs(file_analyses)
        examples = self.documenter.generate_code_examples(file_analyses, max_examples=5)
        
        # Organize into Documentation object
        documentation = self.documenter.organize_documentation(
            project_docs,
            api_docs,
            examples
        )
        
        # Check for existing documentation and update if needed
        existing_docs = self.documenter.load_existing_documentation()
        if existing_docs:
            documentation = self.documenter.update_existing_docs(existing_docs, documentation)
        
        # Write documentation to files
        self.documenter.write_documentation(documentation)
        
        return documentation
    
    def _execute_review_phase(
        self,
        analysis_results: List[FileAnalysis],
        project_patterns: List[ProjectPattern]
    ) -> List[Suggestion]:
        """
        Execute Reviewer agent sequentially after analysis.
        
        Args:
            analysis_results: Results from Analyzer agent
            project_patterns: Project patterns from Memory Bank
        
        Returns:
            List of prioritized suggestions
        """
        # Build project context from patterns
        project_context = {
            'patterns': [
                {
                    'type': p.pattern_type,
                    'description': p.description,
                    'confidence': p.confidence
                }
                for p in project_patterns
            ]
        }
        
        # Generate suggestions
        suggestions = self.reviewer.generate_suggestions(
            analysis_results,
            project_context
        )
        
        # Prioritize suggestions
        prioritized_suggestions = self.reviewer.prioritize_suggestions(suggestions)
        
        return prioritized_suggestions
    
    def _calculate_quality_score(self, analysis_results: List[FileAnalysis]) -> float:
        """
        Calculate overall quality score for the codebase.
        
        Score is based on:
        - Issue severity and count
        - Code complexity
        - Maintainability index
        
        Args:
            analysis_results: List of file analysis results
        
        Returns:
            Quality score (0-100, higher is better)
        """
        if not analysis_results:
            return 100.0
        
        # Count issues by severity
        severity_counts = {
            IssueSeverity.CRITICAL: 0,
            IssueSeverity.HIGH: 0,
            IssueSeverity.MEDIUM: 0,
            IssueSeverity.LOW: 0,
        }
        
        for analysis in analysis_results:
            for issue in analysis.issues:
                severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        
        # Calculate penalty based on issues
        total_files = len(analysis_results)
        issue_penalty = (
            severity_counts[IssueSeverity.CRITICAL] * 10 +
            severity_counts[IssueSeverity.HIGH] * 5 +
            severity_counts[IssueSeverity.MEDIUM] * 2 +
            severity_counts[IssueSeverity.LOW] * 0.5
        ) / max(total_files, 1)
        
        # Calculate average maintainability
        avg_maintainability = sum(a.metrics.maintainability_index for a in analysis_results) / total_files
        
        # Combine metrics (weighted average)
        quality_score = (avg_maintainability * 0.6) + ((100 - min(issue_penalty, 100)) * 0.4)
        
        return max(0.0, min(100.0, quality_score))
    
    def _generate_metrics_summary(self, analysis_results: List[FileAnalysis]) -> MetricsSummary:
        """
        Generate summary metrics for the codebase.
        
        Args:
            analysis_results: List of file analysis results
        
        Returns:
            Metrics summary
        """
        total_files = len(analysis_results)
        total_lines = sum(a.metrics.lines_of_code for a in analysis_results)
        
        # Calculate averages
        if total_files > 0:
            avg_complexity = sum(a.metrics.cyclomatic_complexity for a in analysis_results) / total_files
            avg_maintainability = sum(a.metrics.maintainability_index for a in analysis_results) / total_files
        else:
            avg_complexity = 0.0
            avg_maintainability = 100.0
        
        # Count issues by severity
        issues_by_severity: Dict[str, int] = {}
        issues_by_category: Dict[str, int] = {}
        
        for analysis in analysis_results:
            for issue in analysis.issues:
                severity_key = issue.severity
                issues_by_severity[severity_key] = issues_by_severity.get(severity_key, 0) + 1
                
                category_key = issue.category
                issues_by_category[category_key] = issues_by_category.get(category_key, 0) + 1
        
        return MetricsSummary(
            total_files=total_files,
            total_lines=total_lines,
            average_complexity=avg_complexity,
            average_maintainability=avg_maintainability,
            total_issues_by_severity=issues_by_severity,
            total_issues_by_category=issues_by_category
        )
    
    def _store_discovered_patterns(
        self,
        project_id: str,
        analysis_results: List[FileAnalysis],
        existing_patterns: List[ProjectPattern]
    ) -> None:
        """
        Store newly discovered patterns in Memory Bank.
        
        Args:
            project_id: Project identifier
            analysis_results: Analysis results to extract patterns from
            existing_patterns: Existing patterns to avoid duplicates
        """
        # Extract naming patterns from functions and classes
        naming_patterns: Dict[str, List[str]] = {
            'function_naming': [],
            'class_naming': [],
        }
        
        for analysis in analysis_results:
            for func in analysis.functions:
                if func.name and not func.name.startswith('_'):
                    naming_patterns['function_naming'].append(func.name)
            
            for cls in analysis.classes:
                if cls.name:
                    naming_patterns['class_naming'].append(cls.name)
        
        # Detect naming conventions
        if naming_patterns['function_naming']:
            # Check if snake_case is predominant
            snake_case_count = sum(1 for name in naming_patterns['function_naming'] if '_' in name)
            if snake_case_count / len(naming_patterns['function_naming']) > 0.7:
                # Store snake_case pattern
                pattern_id = f"{project_id}_function_snake_case"
                
                # Check if pattern already exists
                if not any(p.pattern_id == pattern_id for p in existing_patterns):
                    pattern = ProjectPattern(
                        pattern_id=pattern_id,
                        project_id=project_id,
                        pattern_type=PatternType.NAMING,
                        description="Functions use snake_case naming convention",
                        examples=naming_patterns['function_naming'][:5],
                        confidence=0.8,
                        last_updated=datetime.now(timezone.utc)
                    )
                    self.memory_bank.store_pattern(pattern)
        
        if naming_patterns['class_naming']:
            # Check if PascalCase is predominant
            pascal_case_count = sum(1 for name in naming_patterns['class_naming'] if name[0].isupper())
            if pascal_case_count / len(naming_patterns['class_naming']) > 0.7:
                # Store PascalCase pattern
                pattern_id = f"{project_id}_class_pascal_case"
                
                if not any(p.pattern_id == pattern_id for p in existing_patterns):
                    pattern = ProjectPattern(
                        pattern_id=pattern_id,
                        project_id=project_id,
                        pattern_type=PatternType.NAMING,
                        description="Classes use PascalCase naming convention",
                        examples=naming_patterns['class_naming'][:5],
                        confidence=0.8,
                        last_updated=datetime.now(timezone.utc)
                    )
                    self.memory_bank.store_pattern(pattern)
    
    def load_config_from_yaml(self, config_path: str) -> AnalysisConfig:
        """
        Load analysis configuration from a YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
        
        Returns:
            AnalysisConfig object
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
            
            # Validate and create AnalysisConfig
            return AnalysisConfig.model_validate(config_dict)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def pause_analysis(self, session_id: str) -> bool:
        """
        Pause an active analysis session.
        
        Saves the current session state including:
        - Processed files
        - Pending files
        - Partial results
        - File modification times for change detection
        
        Args:
            session_id: Session identifier
        
        Returns:
            True if paused successfully, False otherwise
        """
        session_state = self.session_manager.load_session(session_id)
        if session_state is None:
            return False
        
        # Store file modification times in partial results for change detection
        file_mtimes = {}
        all_files = session_state.processed_files + session_state.pending_files
        for file_path in all_files:
            try:
                mtime = self.file_system.get_modification_time(file_path)
                file_mtimes[file_path] = mtime.timestamp()
            except FileNotFoundError:
                # File may have been deleted
                file_mtimes[file_path] = None
        
        # Update partial results with modification times
        session_state.partial_results['file_mtimes'] = file_mtimes
        self.session_manager.save_session(session_state)
        
        # Pause the session
        return self.session_manager.pause_session(session_id)
    
    def resume_analysis(self, session_id: str, project_id: Optional[str] = None) -> Optional[AnalysisResult]:
        """
        Resume a paused analysis session.
        
        Performs change detection to identify modified files during pause
        and re-analyzes only those files along with any pending files.
        
        Args:
            session_id: Session identifier
            project_id: Optional project ID for Memory Bank patterns
        
        Returns:
            Analysis result if completed, None if session not found
        """
        session_state = self.session_manager.resume_session(session_id)
        
        if session_state is None:
            return None
        
        # Detect changed files during pause
        changed_files = self._detect_changed_files(session_state)
        
        # Combine changed files with pending files
        files_to_process = list(set(changed_files + session_state.pending_files))
        
        # If there are changed files, move them from processed to pending
        if changed_files:
            # Remove changed files from processed list
            session_state.processed_files = [
                f for f in session_state.processed_files if f not in changed_files
            ]
            # Add to pending
            session_state.pending_files = files_to_process
            self.session_manager.save_session(session_state)
        
        # Use target path as project ID if not provided
        if project_id is None:
            project_id = Path(session_state.config.target_path).name
        
        # Continue analysis with detected changes
        return self._continue_analysis(session_state, project_id, files_to_process)
    
    def _detect_changed_files(self, session_state: SessionState) -> List[str]:
        """
        Detect files that have been modified during pause.
        
        Args:
            session_state: Current session state
        
        Returns:
            List of file paths that have been modified
        """
        changed_files = []
        
        # Get stored modification times from partial results
        stored_mtimes = session_state.partial_results.get('file_mtimes', {})
        
        # Check all processed files for changes
        for file_path in session_state.processed_files:
            stored_mtime = stored_mtimes.get(file_path)
            
            if stored_mtime is None:
                # File was deleted or not tracked, skip
                continue
            
            try:
                current_mtime = self.file_system.get_modification_time(file_path)
                
                # Compare timestamps (allow 1 second tolerance for filesystem precision)
                if abs(current_mtime.timestamp() - stored_mtime) > 1.0:
                    changed_files.append(file_path)
            except FileNotFoundError:
                # File was deleted, don't re-analyze
                pass
        
        return changed_files
    
    def _continue_analysis(
        self,
        session_state: SessionState,
        project_id: str,
        files_to_process: List[str]
    ) -> AnalysisResult:
        """
        Continue analysis from a resumed session.
        
        Args:
            session_state: Restored session state
            project_id: Project identifier
            files_to_process: Files that need to be analyzed
        
        Returns:
            Complete analysis results
        """
        try:
            # Retrieve project patterns from Memory Bank with retry
            project_patterns = self._retrieve_patterns_with_retry(project_id)
            
            # Handle case where no files need to be processed (all already done, none changed)
            if not files_to_process:
                logger.info(f"No files to process on resume for session {session_state.session_id}")
                # Use existing partial results to generate final report
                existing_analyses = session_state.partial_results.get('file_analyses', [])
                if existing_analyses and isinstance(existing_analyses[0], dict):
                    existing_analyses = [FileAnalysis.model_validate(a) for a in existing_analyses]
                
                # Generate final report from existing analyses
                return self._generate_final_report(
                    session_state.session_id,
                    session_state.config,
                    existing_analyses,
                    Documentation(project_structure="", api_docs={}, code_examples={}),
                    project_patterns
                )
            
            # Read file contents with graceful degradation
            file_contents, failed_reads = self._read_files_with_graceful_degradation(files_to_process)
            
            if not file_contents:
                error_logger.error(f"Failed to read any files for resumed session {session_state.session_id}")
                raise PartialFailureError(
                    "Failed to read all files on resume",
                    [],
                    failed_reads
                )
            
            # Phase 1: Parallel execution of Analyzer and Documenter with recovery
            new_analysis_results, documentation, analysis_failures = self._execute_parallel_phase_with_recovery(
                file_contents,
                session_state.config,
                session_state.session_id
            )
            
            # Merge with existing partial results if any
            existing_analyses = session_state.partial_results.get('file_analyses', [])
            
            # Convert existing analyses from dict to FileAnalysis objects if needed
            if existing_analyses and isinstance(existing_analyses[0], dict):
                existing_analyses = [FileAnalysis.model_validate(a) for a in existing_analyses]
            
            # Remove old analyses for re-analyzed files (changed files)
            reanalyzed_paths = {a.file_path for a in new_analysis_results}
            
            # Keep analyses for files that weren't re-analyzed
            # These are the unchanged processed files
            unchanged_analyses = [a for a in existing_analyses if a.file_path not in reanalyzed_paths]
            
            # Combine: unchanged files + newly analyzed files
            all_analysis_results = unchanged_analyses + new_analysis_results
            
            # Phase 2: Sequential execution of Reviewer
            suggestions = self._execute_review_phase(
                all_analysis_results,
                project_patterns
            )
            
            # Calculate quality score
            quality_score = self.quality_metrics.calculate_quality_score(all_analysis_results)
            
            # Generate metrics summary
            metrics_summary = self._generate_metrics_summary(all_analysis_results)
            
            # Store new patterns in Memory Bank
            self._store_discovered_patterns(
                project_id,
                all_analysis_results,
                project_patterns
            )
            
            # Create final result
            result = AnalysisResult(
                session_id=session_state.session_id,
                timestamp=datetime.now(timezone.utc),
                codebase_path=session_state.config.target_path,
                files_analyzed=len(all_analysis_results),
                total_issues=sum(len(a.issues) for a in all_analysis_results),
                quality_score=quality_score,
                file_analyses=all_analysis_results,
                suggestions=suggestions,
                documentation=documentation,
                metrics_summary=metrics_summary
            )
            
            # Track quality trend for this project
            self.quality_metrics.track_quality_trend(project_id, result)
            
            # Mark session as completed
            self.session_manager.complete_session(session_state.session_id)
            
            return result
            
        except Exception as e:
            # Mark session as failed
            self.session_manager.fail_session(session_state.session_id)
            raise
    
    def get_analysis_status(self, session_id: str) -> Optional[SessionState]:
        """
        Get the status of an analysis session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            SessionState if found, None otherwise
        """
        return self.session_manager.load_session(session_id)
    
    def generate_review_report(
        self,
        result: AnalysisResult
    ) -> str:
        """
        Generate a formatted review report from analysis results.
        
        Args:
            result: Analysis result
        
        Returns:
            Formatted markdown report
        """
        return self.reviewer.generate_review_report(
            result.file_analyses,
            result.suggestions,
            result.quality_score
        )
    
    def get_quality_trends(
        self,
        project_id: str,
        limit: Optional[int] = None
    ):
        """
        Get quality trends for a project.
        
        Args:
            project_id: Unique project identifier
            limit: Optional limit on number of trends to return
        
        Returns:
            List of QualityTrend data points
        """
        return self.quality_metrics.get_quality_trends(project_id, limit)
    
    def get_quality_comparison(
        self,
        project_id: str,
        current_result: AnalysisResult
    ):
        """
        Get comparison metrics between current and previous analysis.
        
        Args:
            project_id: Unique project identifier
            current_result: Current analysis result
        
        Returns:
            QualityComparison if previous analysis exists, None otherwise
        """
        return self.quality_metrics.generate_comparison(project_id, current_result)
    
    def get_evaluation_statistics(
        self,
        project_id: str,
        issues_resolved: int = 0,
        suggestions_implemented: int = 0
    ):
        """
        Get evaluation statistics for a project.
        
        Args:
            project_id: Unique project identifier
            issues_resolved: Number of issues that have been resolved
            suggestions_implemented: Number of suggestions implemented
        
        Returns:
            EvaluationStatistics with computed metrics
        """
        return self.quality_metrics.calculate_evaluation_statistics(
            project_id,
            issues_resolved,
            suggestions_implemented
        )
    
    def measure_suggestion_impact(
        self,
        suggestion_id: str,
        suggestion_title: str,
        before_metrics,
        after_metrics,
        issues_resolved: int = 0
    ):
        """
        Measure the impact of an implemented suggestion.
        
        Args:
            suggestion_id: Unique suggestion identifier
            suggestion_title: Title of the suggestion
            before_metrics: Code metrics before implementation
            after_metrics: Code metrics after implementation
            issues_resolved: Number of issues resolved
        
        Returns:
            SuggestionImpact with measured improvements
        """
        return self.quality_metrics.measure_suggestion_impact(
            suggestion_id,
            suggestion_title,
            before_metrics,
            after_metrics,
            issues_resolved
        )
