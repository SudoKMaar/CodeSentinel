"""
LLM-Powered Reviewer Agent for intelligent code review.

This agent uses Large Language Models to:
- Understand code context and purpose
- Provide intelligent fix recommendations
- Prioritize issues based on business impact
- Generate detailed explanations
- Learn from project patterns
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from models.data_models import (
    FileAnalysis,
    CodeIssue,
    Suggestion,
    IssueSeverity,
    IssueCategory,
    EffortLevel,
    ImpactLevel,
)
from tools.llm_client import LLMClient


class LLMReviewerAgent:
    """LLM-powered agent for intelligent code review."""
    
    def __init__(
        self,
        llm_provider: Optional[str] = None,
        llm_model: Optional[str] = None,
        enable_llm: bool = True
    ):
        """
        Initialize the LLM Reviewer Agent.
        
        Args:
            llm_provider: LLM provider (bedrock, openai, anthropic, ollama)
            llm_model: Model name/ID
            enable_llm: Whether to use LLM (fallback to rule-based if False)
        """
        self.enable_llm = enable_llm
        
        if self.enable_llm:
            try:
                self.llm_client = LLMClient(
                    provider=llm_provider,
                    model=llm_model
                )
                print(f"✓ LLM Reviewer initialized with {self.llm_client.provider}/{self.llm_client.model}")
            except Exception as e:
                print(f"⚠ LLM initialization failed: {e}. Falling back to rule-based review.")
                self.enable_llm = False
                self.llm_client = None
        else:
            self.llm_client = None
    
    def review_code_with_llm(
        self,
        file_analysis: FileAnalysis,
        source_code: str,
        project_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Use LLM to review code and provide intelligent insights.
        
        Args:
            file_analysis: Static analysis results
            source_code: Original source code
            project_context: Optional project description
        
        Returns:
            Dictionary with LLM review results
        """
        if not self.enable_llm or not self.llm_client:
            return {"status": "llm_disabled", "message": "Using rule-based review only"}
        
        try:
            # Convert issues to dict format for LLM
            issues_dict = [
                {
                    "line_number": issue.line_number,
                    "severity": issue.severity,
                    "category": issue.category,
                    "description": issue.description,
                    "code_snippet": issue.code_snippet
                }
                for issue in file_analysis.issues
            ]
            
            # Get LLM analysis
            llm_analysis = self.llm_client.analyze_code(
                code=source_code,
                file_path=file_analysis.file_path,
                issues=issues_dict,
                language=file_analysis.language
            )
            
            return {
                "status": "success",
                "llm_analysis": llm_analysis,
                "provider": self.llm_client.provider,
                "model": self.llm_client.model
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "message": "LLM review failed, using static analysis only"
            }
    
    def generate_intelligent_suggestions(
        self,
        analysis_results: List[FileAnalysis],
        source_codes: Dict[str, str],
        project_context: Optional[str] = None
    ) -> List[Suggestion]:
        """
        Generate intelligent suggestions using LLM.
        
        Args:
            analysis_results: List of file analysis results
            source_codes: Dictionary mapping file paths to source code
            project_context: Optional project description
        
        Returns:
            List of LLM-enhanced suggestions
        """
        suggestions: List[Suggestion] = []
        
        for analysis in analysis_results:
            if not analysis.issues:
                continue
            
            # Get source code for this file
            source_code = source_codes.get(analysis.file_path, "")
            
            # Get LLM review
            llm_review = self.review_code_with_llm(
                file_analysis=analysis,
                source_code=source_code,
                project_context=project_context
            )
            
            # Generate suggestions from LLM analysis
            if llm_review.get("status") == "success":
                llm_suggestions = self._create_suggestions_from_llm(
                    analysis=analysis,
                    llm_review=llm_review,
                    source_code=source_code
                )
                suggestions.extend(llm_suggestions)
            else:
                # Fallback to rule-based suggestions
                fallback_suggestions = self._create_fallback_suggestions(analysis)
                suggestions.extend(fallback_suggestions)
        
        return suggestions
    
    def _create_suggestions_from_llm(
        self,
        analysis: FileAnalysis,
        llm_review: Dict[str, Any],
        source_code: str
    ) -> List[Suggestion]:
        """Create suggestions from LLM analysis."""
        suggestions: List[Suggestion] = []
        
        llm_analysis = llm_review.get("llm_analysis", {})
        
        # Extract recommendations from LLM
        recommendations = llm_analysis.get("recommendations", [])
        if isinstance(recommendations, str):
            # If recommendations is a string, create a single suggestion
            recommendations = [recommendations]
        
        for i, rec in enumerate(recommendations[:5]):  # Limit to top 5
            # Determine priority based on LLM analysis
            critical_issues = llm_analysis.get("critical_issues", [])
            is_critical = i < len(critical_issues)
            
            suggestion = Suggestion(
                priority=1 if is_critical else 2,
                category="llm_recommendation",
                title=f"LLM Recommendation: {analysis.file_path.split('/')[-1]}",
                description=self._format_llm_recommendation(rec, llm_analysis),
                code_example=self._generate_code_example_with_llm(
                    source_code=source_code,
                    recommendation=rec,
                    language=analysis.language
                ),
                estimated_effort=EffortLevel.MEDIUM,
                impact=ImpactLevel.HIGH if is_critical else ImpactLevel.MEDIUM,
                related_issues=[f"{analysis.file_path}:LLM-{i+1}"],
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _format_llm_recommendation(
        self,
        recommendation: Any,
        llm_analysis: Dict[str, Any]
    ) -> str:
        """Format LLM recommendation as markdown."""
        lines = ["**AI-Powered Code Review**\n"]
        
        # Add code purpose if available
        purpose = llm_analysis.get("purpose", "")
        if purpose:
            lines.append(f"**Code Purpose:** {purpose}\n")
        
        # Add recommendation
        if isinstance(recommendation, dict):
            rec_text = recommendation.get("description", str(recommendation))
        else:
            rec_text = str(recommendation)
        
        lines.append(f"**Recommendation:**\n{rec_text}\n")
        
        # Add additional concerns if available
        additional = llm_analysis.get("additional_concerns", "")
        if additional:
            lines.append(f"**Additional Concerns:**\n{additional}")
        
        return "\n".join(lines)
    
    def _generate_code_example_with_llm(
        self,
        source_code: str,
        recommendation: Any,
        language: str
    ) -> Optional[str]:
        """Generate code example using LLM."""
        if not self.enable_llm or not self.llm_client:
            return None
        
        try:
            # Create a mock issue for fix generation
            issue = {
                "description": str(recommendation),
                "line_number": 1,
                "severity": "medium"
            }
            
            fix = self.llm_client.generate_fix(
                code=source_code[:1000],  # Limit code length
                issue=issue,
                language=language
            )
            
            return fix
        
        except Exception as e:
            return f"Error generating code example: {e}"
    
    def _create_fallback_suggestions(
        self,
        analysis: FileAnalysis
    ) -> List[Suggestion]:
        """Create rule-based suggestions when LLM is unavailable."""
        suggestions: List[Suggestion] = []
        
        for issue in analysis.issues[:3]:  # Top 3 issues
            suggestion = Suggestion(
                priority=self._severity_to_priority(issue.severity),
                category=issue.category,
                title=f"Fix {issue.category} in {analysis.file_path.split('/')[-1]}",
                description=f"**Issue:** {issue.description}\n\n**Suggestion:** {issue.suggestion}",
                code_example=None,
                estimated_effort=self._estimate_effort(issue),
                impact=self._estimate_impact(issue),
                related_issues=[f"{issue.file_path}:{issue.line_number}"],
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    def _severity_to_priority(self, severity: IssueSeverity) -> int:
        """Convert severity to priority."""
        mapping = {
            IssueSeverity.CRITICAL: 1,
            IssueSeverity.HIGH: 2,
            IssueSeverity.MEDIUM: 3,
            IssueSeverity.LOW: 4,
        }
        return mapping.get(severity, 3)
    
    def _estimate_effort(self, issue: CodeIssue) -> EffortLevel:
        """Estimate effort to fix issue."""
        if issue.category == IssueCategory.COMPLEXITY:
            return EffortLevel.HIGH
        elif issue.category == IssueCategory.SECURITY:
            return EffortLevel.MEDIUM
        else:
            return EffortLevel.LOW
    
    def _estimate_impact(self, issue: CodeIssue) -> ImpactLevel:
        """Estimate impact of fixing issue."""
        if issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]:
            return ImpactLevel.HIGH
        elif issue.severity == IssueSeverity.MEDIUM:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW
    
    def prioritize_with_llm(
        self,
        suggestions: List[Suggestion],
        project_context: Optional[str] = None
    ) -> List[Suggestion]:
        """
        Use LLM to intelligently prioritize suggestions.
        
        Args:
            suggestions: List of suggestions
            project_context: Optional project description
        
        Returns:
            Prioritized list of suggestions
        """
        if not self.enable_llm or not self.llm_client or not suggestions:
            return sorted(suggestions, key=lambda s: s.priority)
        
        try:
            # Convert suggestions to dict format
            issues_dict = [
                {
                    "description": s.title,
                    "severity": "high" if s.priority <= 2 else "medium",
                    "file_path": s.related_issues[0] if s.related_issues else "unknown"
                }
                for s in suggestions
            ]
            
            # Get LLM prioritization
            priorities = self.llm_client.prioritize_issues(
                issues=issues_dict,
                project_context=project_context or "General software project"
            )
            
            # Apply LLM priorities
            if priorities:
                priority_map = {
                    p["issue_number"] - 1: p["priority_score"]
                    for p in priorities
                    if isinstance(p, dict) and "issue_number" in p
                }
                
                for i, suggestion in enumerate(suggestions):
                    if i in priority_map:
                        # Convert 1-10 score to 1-5 priority
                        llm_priority = max(1, min(5, 6 - (priority_map[i] // 2)))
                        suggestion.priority = llm_priority
            
            return sorted(suggestions, key=lambda s: s.priority)
        
        except Exception as e:
            print(f"⚠ LLM prioritization failed: {e}. Using default prioritization.")
            return sorted(suggestions, key=lambda s: s.priority)
    
    def generate_review_report_with_llm(
        self,
        analysis_results: List[FileAnalysis],
        suggestions: List[Suggestion],
        quality_score: float,
        project_context: Optional[str] = None
    ) -> str:
        """
        Generate an AI-enhanced review report.
        
        Args:
            analysis_results: List of file analysis results
            suggestions: List of suggestions
            quality_score: Overall quality score
            project_context: Optional project description
        
        Returns:
            Formatted markdown report with LLM insights
        """
        lines = ["# AI-Powered Code Review Report\n"]
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Quality Score:** {quality_score:.1f}/100")
        
        if self.enable_llm and self.llm_client:
            lines.append(f"**AI Model:** {self.llm_client.provider}/{self.llm_client.model}\n")
        
        lines.append("\n## Executive Summary\n")
        
        # Generate executive summary with LLM
        if self.enable_llm and self.llm_client:
            summary = self._generate_executive_summary(
                analysis_results=analysis_results,
                quality_score=quality_score,
                project_context=project_context
            )
            lines.append(summary)
        else:
            lines.append(f"Analyzed {len(analysis_results)} files with {len(suggestions)} suggestions.")
        
        lines.append("\n## Top Priority Actions\n")
        
        for i, suggestion in enumerate(suggestions[:5], 1):
            lines.append(f"### {i}. {suggestion.title}")
            lines.append(f"**Priority:** {suggestion.priority} | **Impact:** {suggestion.impact} | **Effort:** {suggestion.estimated_effort}\n")
            lines.append(suggestion.description)
            
            if suggestion.code_example:
                lines.append("\n**Code Example:**")
                lines.append(suggestion.code_example)
            
            lines.append("\n---\n")
        
        return "\n".join(lines)
    
    def _generate_executive_summary(
        self,
        analysis_results: List[FileAnalysis],
        quality_score: float,
        project_context: Optional[str]
    ) -> str:
        """Generate executive summary using LLM."""
        if not self.llm_client:
            return "LLM unavailable for summary generation."
        
        try:
            # Prepare analysis summary
            total_issues = sum(len(a.issues) for a in analysis_results)
            critical_issues = sum(
                1 for a in analysis_results
                for i in a.issues
                if i.severity == IssueSeverity.CRITICAL
            )
            
            prompt = f"""Generate an executive summary for this code review:

Project: {project_context or "Software project"}
Files Analyzed: {len(analysis_results)}
Total Issues: {total_issues}
Critical Issues: {critical_issues}
Quality Score: {quality_score:.1f}/100

Provide a 2-3 sentence executive summary highlighting:
1. Overall code quality assessment
2. Most critical concerns
3. Recommended next steps

Be concise and actionable."""
            
            summary = self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a senior engineering manager providing executive summaries.",
                temperature=0.5,
                max_tokens=300
            )
            
            return summary
        
        except Exception as e:
            return f"Error generating summary: {e}"
