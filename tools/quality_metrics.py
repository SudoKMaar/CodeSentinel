"""
Quality Metrics and Evaluation Module.

This module provides functionality for:
- Quality score calculation based on issue severity and count
- Quality trend tracking across multiple analyses
- Comparison metrics generation (delta from previous analysis)
- Evaluation statistics calculation for resolution rates and coverage
- Impact measurement for implemented suggestions
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any

from models.data_models import (
    AnalysisResult,
    FileAnalysis,
    CodeMetrics,
    IssueSeverity,
    QualityTrend,
    QualityComparison,
    EvaluationStatistics,
    SuggestionImpact,
)


class QualityMetricsCalculator:
    """
    Calculator for quality metrics and evaluation statistics.
    
    Provides methods for:
    - Calculating quality scores
    - Tracking quality trends over time
    - Generating comparison metrics
    - Computing evaluation statistics
    - Measuring suggestion impact
    """
    
    def __init__(self, storage_dir: str = ".quality_metrics"):
        """
        Initialize the quality metrics calculator.
        
        Args:
            storage_dir: Directory for storing quality trend data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
    
    def calculate_quality_score(
        self,
        analysis_results: List[FileAnalysis],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate overall quality score for a codebase.
        
        The score is based on:
        - Issue severity and count (weighted by severity)
        - Average maintainability index
        - Average complexity
        
        Args:
            analysis_results: List of file analysis results
            weights: Optional custom weights for score components
                    Default: {'issues': 0.4, 'maintainability': 0.4, 'complexity': 0.2}
        
        Returns:
            Quality score (0-100, higher is better)
        """
        if not analysis_results:
            return 100.0
        
        # Default weights
        if weights is None:
            weights = {
                'issues': 0.4,
                'maintainability': 0.4,
                'complexity': 0.2
            }
        
        total_files = len(analysis_results)
        
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
        
        # Calculate issue penalty (normalized per file)
        issue_penalty = (
            severity_counts[IssueSeverity.CRITICAL] * 10 +
            severity_counts[IssueSeverity.HIGH] * 5 +
            severity_counts[IssueSeverity.MEDIUM] * 2 +
            severity_counts[IssueSeverity.LOW] * 0.5
        ) / max(total_files, 1)
        
        # Normalize issue penalty to 0-100 scale (cap at 100)
        issue_score = max(0.0, 100.0 - min(issue_penalty, 100.0))
        
        # Calculate average maintainability
        avg_maintainability = sum(
            a.metrics.maintainability_index for a in analysis_results
        ) / total_files
        
        # Calculate complexity score (inverse of complexity, normalized)
        # Lower complexity is better, so we invert it
        avg_complexity = sum(
            a.metrics.cyclomatic_complexity for a in analysis_results
        ) / total_files
        
        # Normalize complexity to 0-100 scale
        # Complexity of 1-5 is excellent (100), 6-10 is good (80), 11-20 is fair (60), >20 is poor
        if avg_complexity <= 5:
            complexity_score = 100.0
        elif avg_complexity <= 10:
            complexity_score = 100.0 - ((avg_complexity - 5) * 4)  # 100 to 80
        elif avg_complexity <= 20:
            complexity_score = 80.0 - ((avg_complexity - 10) * 2)  # 80 to 60
        else:
            complexity_score = max(0.0, 60.0 - ((avg_complexity - 20) * 1))  # 60 to 0
        
        # Combine scores using weights
        quality_score = (
            issue_score * weights['issues'] +
            avg_maintainability * weights['maintainability'] +
            complexity_score * weights['complexity']
        )
        
        return max(0.0, min(100.0, quality_score))
    
    def track_quality_trend(
        self,
        project_id: str,
        analysis_result: AnalysisResult
    ) -> QualityTrend:
        """
        Track quality trend for a project by storing a new data point.
        
        Args:
            project_id: Unique project identifier
            analysis_result: Analysis result to track
        
        Returns:
            QualityTrend data point that was stored
        """
        # Count issues by severity
        critical_count = sum(
            1 for fa in analysis_result.file_analyses
            for issue in fa.issues
            if issue.severity == IssueSeverity.CRITICAL
        )
        
        high_count = sum(
            1 for fa in analysis_result.file_analyses
            for issue in fa.issues
            if issue.severity == IssueSeverity.HIGH
        )
        
        # Create trend data point
        trend = QualityTrend(
            timestamp=analysis_result.timestamp,
            quality_score=analysis_result.quality_score,
            total_issues=analysis_result.total_issues,
            critical_issues=critical_count,
            high_issues=high_count,
            files_analyzed=analysis_result.files_analyzed
        )
        
        # Load existing trends
        trends = self._load_trends(project_id)
        trends.append(trend)
        
        # Save updated trends
        self._save_trends(project_id, trends)
        
        return trend
    
    def get_quality_trends(
        self,
        project_id: str,
        limit: Optional[int] = None
    ) -> List[QualityTrend]:
        """
        Get quality trends for a project.
        
        Args:
            project_id: Unique project identifier
            limit: Optional limit on number of trends to return (most recent)
        
        Returns:
            List of QualityTrend data points, ordered by timestamp (oldest first)
        """
        trends = self._load_trends(project_id)
        
        if limit is not None and limit > 0:
            trends = trends[-limit:]
        
        return trends
    
    def generate_comparison(
        self,
        project_id: str,
        current_result: AnalysisResult
    ) -> Optional[QualityComparison]:
        """
        Generate comparison metrics between current and previous analysis.
        
        Args:
            project_id: Unique project identifier
            current_result: Current analysis result
        
        Returns:
            QualityComparison if previous analysis exists, None otherwise
        """
        trends = self._load_trends(project_id)
        
        if len(trends) < 2:
            return None
        
        # Get previous trend (second to last)
        previous = trends[-2]
        
        # Count current critical issues
        current_critical = sum(
            1 for fa in current_result.file_analyses
            for issue in fa.issues
            if issue.severity == IssueSeverity.CRITICAL
        )
        
        # Calculate deltas
        score_delta = current_result.quality_score - previous.quality_score
        issues_delta = current_result.total_issues - previous.total_issues
        critical_delta = current_critical - previous.critical_issues
        
        # Calculate improvement percentage
        if previous.quality_score > 0:
            improvement_percentage = (score_delta / previous.quality_score) * 100
        else:
            improvement_percentage = 0.0
        
        return QualityComparison(
            previous_score=previous.quality_score,
            current_score=current_result.quality_score,
            score_delta=score_delta,
            issues_delta=issues_delta,
            critical_issues_delta=critical_delta,
            improvement_percentage=improvement_percentage
        )
    
    def calculate_evaluation_statistics(
        self,
        project_id: str,
        issues_resolved: int = 0,
        suggestions_implemented: int = 0
    ) -> EvaluationStatistics:
        """
        Calculate evaluation statistics for a project.
        
        Args:
            project_id: Unique project identifier
            issues_resolved: Number of issues that have been resolved
            suggestions_implemented: Number of suggestions that have been implemented
        
        Returns:
            EvaluationStatistics with computed metrics
        """
        trends = self._load_trends(project_id)
        
        if not trends:
            return EvaluationStatistics(
                total_analyses=0,
                total_issues_found=0,
                total_suggestions_made=0,
                issues_resolved=0,
                suggestions_implemented=0,
                resolution_rate=0.0,
                implementation_rate=0.0,
                average_quality_score=100.0,
                documentation_coverage=0.0
            )
        
        # Calculate totals
        total_analyses = len(trends)
        total_issues_found = sum(t.total_issues for t in trends)
        
        # Estimate total suggestions (roughly 1 suggestion per 2 issues)
        total_suggestions_made = total_issues_found // 2
        
        # Calculate rates
        resolution_rate = (
            issues_resolved / total_issues_found
            if total_issues_found > 0
            else 0.0
        )
        
        implementation_rate = (
            suggestions_implemented / total_suggestions_made
            if total_suggestions_made > 0
            else 0.0
        )
        
        # Calculate average quality score
        average_quality_score = sum(t.quality_score for t in trends) / total_analyses
        
        # Estimate documentation coverage (placeholder - would need actual doc analysis)
        # For now, use quality score as a proxy
        documentation_coverage = min(1.0, average_quality_score / 100.0)
        
        return EvaluationStatistics(
            total_analyses=total_analyses,
            total_issues_found=total_issues_found,
            total_suggestions_made=total_suggestions_made,
            issues_resolved=issues_resolved,
            suggestions_implemented=suggestions_implemented,
            resolution_rate=resolution_rate,
            implementation_rate=implementation_rate,
            average_quality_score=average_quality_score,
            documentation_coverage=documentation_coverage
        )
    
    def measure_suggestion_impact(
        self,
        suggestion_id: str,
        suggestion_title: str,
        before_metrics: CodeMetrics,
        after_metrics: CodeMetrics,
        issues_resolved: int = 0
    ) -> SuggestionImpact:
        """
        Measure the impact of an implemented suggestion.
        
        Args:
            suggestion_id: Unique suggestion identifier
            suggestion_title: Title of the suggestion
            before_metrics: Code metrics before implementation
            after_metrics: Code metrics after implementation
            issues_resolved: Number of issues resolved by this change
        
        Returns:
            SuggestionImpact with measured improvements
        """
        complexity_improvement = (
            before_metrics.cyclomatic_complexity - after_metrics.cyclomatic_complexity
        )
        
        maintainability_improvement = (
            after_metrics.maintainability_index - before_metrics.maintainability_index
        )
        
        return SuggestionImpact(
            suggestion_id=suggestion_id,
            suggestion_title=suggestion_title,
            implemented_at=datetime.now(timezone.utc),
            before_metrics=before_metrics,
            after_metrics=after_metrics,
            complexity_improvement=complexity_improvement,
            maintainability_improvement=maintainability_improvement,
            issues_resolved=issues_resolved
        )
    
    def _load_trends(self, project_id: str) -> List[QualityTrend]:
        """Load quality trends from storage."""
        trends_file = self.storage_dir / f"{project_id}_trends.json"
        
        if not trends_file.exists():
            return []
        
        try:
            with open(trends_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return [
                QualityTrend(
                    timestamp=datetime.fromisoformat(t['timestamp']),
                    quality_score=t['quality_score'],
                    total_issues=t['total_issues'],
                    critical_issues=t['critical_issues'],
                    high_issues=t['high_issues'],
                    files_analyzed=t['files_analyzed']
                )
                for t in data
            ]
        except Exception as e:
            print(f"Error loading trends for {project_id}: {e}")
            return []
    
    def _save_trends(self, project_id: str, trends: List[QualityTrend]) -> None:
        """Save quality trends to storage."""
        trends_file = self.storage_dir / f"{project_id}_trends.json"
        
        data = [
            {
                'timestamp': t.timestamp.isoformat(),
                'quality_score': t.quality_score,
                'total_issues': t.total_issues,
                'critical_issues': t.critical_issues,
                'high_issues': t.high_issues,
                'files_analyzed': t.files_analyzed
            }
            for t in trends
        ]
        
        try:
            with open(trends_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving trends for {project_id}: {e}")
    
    def clear_project_trends(self, project_id: str) -> bool:
        """
        Clear all quality trends for a project.
        
        Args:
            project_id: Unique project identifier
        
        Returns:
            True if trends were cleared, False if no trends existed
        """
        trends_file = self.storage_dir / f"{project_id}_trends.json"
        
        if trends_file.exists():
            trends_file.unlink()
            return True
        
        return False
