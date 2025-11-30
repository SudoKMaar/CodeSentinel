"""
Reviewer Agent for generating improvement suggestions and review reports.

This agent performs:
- Suggestion generation from analysis results using LLM
- Suggestion prioritization based on impact and effort
- Test case suggestion generation for uncovered code
- Design pattern recommendation logic
- Review report generation with formatting
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
    FunctionInfo,
)


class ReviewerAgent:
    """Agent for reviewing code analysis and generating improvement suggestions."""
    
    # Priority weights for different factors
    SEVERITY_WEIGHTS = {
        IssueSeverity.CRITICAL: 5,
        IssueSeverity.HIGH: 4,
        IssueSeverity.MEDIUM: 3,
        IssueSeverity.LOW: 2,
    }
    
    IMPACT_WEIGHTS = {
        ImpactLevel.HIGH: 3,
        ImpactLevel.MEDIUM: 2,
        ImpactLevel.LOW: 1,
    }
    
    EFFORT_WEIGHTS = {
        EffortLevel.LOW: 3,
        EffortLevel.MEDIUM: 2,
        EffortLevel.HIGH: 1,
    }
    
    def __init__(self, use_llm: bool = False):
        """
        Initialize the Reviewer Agent.
        
        Args:
            use_llm: Whether to use LLM for suggestion generation (requires API key)
        """
        self.use_llm = use_llm
    
    def generate_suggestions(
        self,
        analysis_results: List[FileAnalysis],
        project_context: Optional[Dict[str, Any]] = None
    ) -> List[Suggestion]:
        """
        Generate improvement suggestions from analysis results.
        
        Args:
            analysis_results: List of file analysis results
            project_context: Optional project-specific context
        
        Returns:
            List of Suggestion objects
        """
        suggestions: List[Suggestion] = []
        
        # Generate suggestions from issues
        for analysis in analysis_results:
            for issue in analysis.issues:
                suggestion = self._create_suggestion_from_issue(issue, analysis)
                if suggestion:
                    suggestions.append(suggestion)
        
        # Generate test case suggestions for uncovered code
        test_suggestions = self._generate_test_suggestions(analysis_results)
        suggestions.extend(test_suggestions)
        
        # Generate design pattern recommendations
        pattern_suggestions = self._generate_pattern_recommendations(analysis_results)
        suggestions.extend(pattern_suggestions)
        
        return suggestions
    
    def _create_suggestion_from_issue(
        self,
        issue: CodeIssue,
        analysis: FileAnalysis
    ) -> Optional[Suggestion]:
        """
        Create a suggestion from a code issue.
        
        Args:
            issue: Code issue to create suggestion from
            analysis: File analysis containing the issue
        
        Returns:
            Suggestion object or None
        """
        # Determine effort and impact based on issue category and severity
        effort = self._estimate_effort(issue)
        impact = self._estimate_impact(issue)
        
        # Generate detailed description and code example
        description = self._generate_suggestion_description(issue, analysis)
        code_example = self._generate_code_example(issue, analysis)
        
        # Create suggestion title
        title = self._create_suggestion_title(issue)
        
        # Calculate initial priority (will be refined in prioritization)
        priority = self._calculate_initial_priority(issue.severity, impact, effort)
        
        return Suggestion(
            priority=priority,
            category=issue.category,
            title=title,
            description=description,
            code_example=code_example,
            estimated_effort=effort,
            impact=impact,
            related_issues=[f"{issue.file_path}:{issue.line_number}"],
        )
    
    def _estimate_effort(self, issue: CodeIssue) -> EffortLevel:
        """Estimate effort required to fix an issue."""
        if issue.category == IssueCategory.COMPLEXITY:
            return EffortLevel.HIGH  # Refactoring complex code takes time
        elif issue.category == IssueCategory.SECURITY:
            return EffortLevel.MEDIUM  # Security fixes need careful testing
        elif issue.category == IssueCategory.DUPLICATION:
            return EffortLevel.MEDIUM  # Extracting duplicated code
        elif issue.category == IssueCategory.ERROR_HANDLING:
            return EffortLevel.LOW  # Adding try-catch is straightforward
        elif issue.category == IssueCategory.STYLE:
            return EffortLevel.LOW  # Style fixes are usually quick
        else:
            return EffortLevel.MEDIUM
    
    def _estimate_impact(self, issue: CodeIssue) -> ImpactLevel:
        """Estimate impact of fixing an issue."""
        if issue.severity == IssueSeverity.CRITICAL:
            return ImpactLevel.HIGH
        elif issue.severity == IssueSeverity.HIGH:
            return ImpactLevel.HIGH
        elif issue.severity == IssueSeverity.MEDIUM:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW
    
    def _generate_suggestion_description(
        self,
        issue: CodeIssue,
        analysis: FileAnalysis
    ) -> str:
        """Generate detailed description for a suggestion."""
        lines = [
            f"**Issue:** {issue.description}",
            f"**Location:** {issue.file_path}, line {issue.line_number}",
            "",
            "**Recommendation:**",
        ]
        
        if issue.suggestion:
            lines.append(issue.suggestion)
        else:
            lines.append(self._generate_generic_recommendation(issue))
        
        # Add context-specific advice
        if issue.category == IssueCategory.COMPLEXITY:
            lines.append("")
            lines.append("Consider applying the Single Responsibility Principle by breaking this function into smaller, focused functions.")
        elif issue.category == IssueCategory.SECURITY:
            lines.append("")
            lines.append("Security issues should be addressed immediately to prevent potential vulnerabilities.")
        elif issue.category == IssueCategory.ERROR_HANDLING:
            lines.append("")
            lines.append("Proper error handling improves reliability and makes debugging easier.")
        
        return "\n".join(lines)
    
    def _generate_generic_recommendation(self, issue: CodeIssue) -> str:
        """Generate a generic recommendation based on issue category."""
        if issue.category == IssueCategory.COMPLEXITY:
            return "Refactor this code to reduce complexity and improve readability."
        elif issue.category == IssueCategory.SECURITY:
            return "Review and fix this security vulnerability following best practices."
        elif issue.category == IssueCategory.DUPLICATION:
            return "Extract the duplicated code into a reusable function or module."
        elif issue.category == IssueCategory.ERROR_HANDLING:
            return "Add appropriate error handling to make the code more robust."
        elif issue.category == IssueCategory.STYLE:
            return "Update the code to follow project style guidelines."
        else:
            return "Review and improve this code section."
    
    def _generate_code_example(
        self,
        issue: CodeIssue,
        analysis: FileAnalysis
    ) -> Optional[str]:
        """Generate a code example showing how to fix the issue."""
        if issue.category == IssueCategory.ERROR_HANDLING:
            return self._generate_error_handling_example(issue, analysis.language)
        elif issue.category == IssueCategory.COMPLEXITY:
            return self._generate_refactoring_example(issue, analysis.language)
        elif issue.category == IssueCategory.SECURITY:
            return self._generate_security_fix_example(issue, analysis.language)
        
        return None
    
    def _generate_error_handling_example(self, issue: CodeIssue, language: str) -> str:
        """Generate example for adding error handling."""
        if language == 'python':
            return f"""```python
# Before:
{issue.code_snippet}

# After:
try:
    {issue.code_snippet}
except Exception as e:
    # Handle the error appropriately
    logger.error(f"Error occurred: {{e}}")
    raise
```"""
        elif language in ['javascript', 'typescript', 'tsx']:
            return f"""```{language}
// Before:
{issue.code_snippet}

// After:
try {{
    {issue.code_snippet}
}} catch (error) {{
    // Handle the error appropriately
    console.error('Error occurred:', error);
    throw error;
}}
```"""
        
        return f"Add error handling around: {issue.code_snippet}"
    
    def _generate_refactoring_example(self, issue: CodeIssue, language: str) -> str:
        """Generate example for refactoring complex code."""
        if language == 'python':
            return """```python
# Break down complex function into smaller functions:

def complex_function(data):
    # Original complex logic here
    pass

# Refactor to:

def validate_data(data):
    # Validation logic
    pass

def process_data(data):
    # Processing logic
    pass

def complex_function(data):
    validated = validate_data(data)
    return process_data(validated)
```"""
        
        return "Consider breaking this function into smaller, focused functions."
    
    def _generate_security_fix_example(self, issue: CodeIssue, language: str) -> str:
        """Generate example for fixing security issues."""
        if 'SQL' in issue.description or 'sql' in issue.description:
            if language == 'python':
                return """```python
# Unsafe:
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# Safe:
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_id,))
```"""
        
        if 'secret' in issue.description.lower() or 'password' in issue.description.lower():
            if language == 'python':
                return """```python
# Unsafe:
API_KEY = "hardcoded_secret_key_123"

# Safe:
import os
API_KEY = os.environ.get('API_KEY')
```"""
        
        return "Follow security best practices to fix this vulnerability."
    
    def _create_suggestion_title(self, issue: CodeIssue) -> str:
        """Create a concise title for the suggestion."""
        category_titles = {
            IssueCategory.COMPLEXITY: "Reduce complexity",
            IssueCategory.SECURITY: "Fix security vulnerability",
            IssueCategory.DUPLICATION: "Remove code duplication",
            IssueCategory.ERROR_HANDLING: "Add error handling",
            IssueCategory.STYLE: "Fix style issue",
            IssueCategory.NAMING: "Improve naming",
        }
        
        base_title = category_titles.get(issue.category, "Improve code quality")
        
        # Add location context
        file_name = issue.file_path.split('/')[-1]
        return f"{base_title} in {file_name}"
    
    def _calculate_initial_priority(
        self,
        severity: IssueSeverity,
        impact: ImpactLevel,
        effort: EffortLevel
    ) -> int:
        """
        Calculate initial priority score.
        
        Priority is based on: (severity_weight + impact_weight) / effort_weight
        Higher score = higher priority
        
        Returns priority level 1-5 (1 = highest)
        """
        severity_weight = self.SEVERITY_WEIGHTS.get(severity, 2)
        impact_weight = self.IMPACT_WEIGHTS.get(impact, 1)
        effort_weight = self.EFFORT_WEIGHTS.get(effort, 2)
        
        # Calculate score: higher impact and lower effort = higher priority
        score = (severity_weight + impact_weight) * effort_weight
        
        # Map score to priority level (1-5)
        if score >= 18:
            return 1  # Highest priority
        elif score >= 12:
            return 2
        elif score >= 8:
            return 3
        elif score >= 5:
            return 4
        else:
            return 5  # Lowest priority
    
    def _generate_test_suggestions(
        self,
        analysis_results: List[FileAnalysis]
    ) -> List[Suggestion]:
        """
        Generate suggestions for test cases.
        
        Args:
            analysis_results: List of file analysis results
        
        Returns:
            List of test-related suggestions
        """
        suggestions: List[Suggestion] = []
        
        for analysis in analysis_results:
            # Skip test files themselves
            if 'test' in analysis.file_path.lower():
                continue
            
            # Find functions without tests (simplified heuristic)
            for func in analysis.functions:
                # Skip private functions
                if func.name.startswith('_'):
                    continue
                
                # Suggest tests for complex functions
                if func.complexity >= 5:
                    suggestion = Suggestion(
                        priority=2,
                        category="testing",
                        title=f"Add tests for {func.name}",
                        description=self._generate_test_description(func, analysis),
                        code_example=self._generate_test_example(func, analysis),
                        estimated_effort=EffortLevel.MEDIUM,
                        impact=ImpactLevel.HIGH,
                        related_issues=[f"{analysis.file_path}:{func.line_number}"],
                    )
                    suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_test_description(
        self,
        func: FunctionInfo,
        analysis: FileAnalysis
    ) -> str:
        """Generate description for test suggestion."""
        return f"""**Function:** `{func.name}` in {analysis.file_path}
**Complexity:** {func.complexity}

**Recommendation:**
Add comprehensive test cases for this function to ensure correctness and prevent regressions.

**Suggested test cases:**
1. Test with valid inputs
2. Test with edge cases (empty, null, boundary values)
3. Test error conditions
4. Test with typical use cases"""
    
    def _generate_test_example(
        self,
        func: FunctionInfo,
        analysis: FileAnalysis
    ) -> str:
        """Generate example test code."""
        if analysis.language == 'python':
            params_str = ", ".join(func.parameters) if func.parameters else ""
            return f"""```python
import pytest
from {analysis.file_path.replace('/', '.').replace('.py', '')} import {func.name}

def test_{func.name}_valid_input():
    # Test with valid input
    result = {func.name}({params_str})
    assert result is not None

def test_{func.name}_edge_cases():
    # Test edge cases
    result = {func.name}(None)
    # Add assertions

def test_{func.name}_error_handling():
    # Test error conditions
    with pytest.raises(Exception):
        {func.name}(invalid_input)
```"""
        
        return f"Add test cases for {func.name}"
    
    def _generate_pattern_recommendations(
        self,
        analysis_results: List[FileAnalysis]
    ) -> List[Suggestion]:
        """
        Generate design pattern recommendations.
        
        Args:
            analysis_results: List of file analysis results
        
        Returns:
            List of pattern-related suggestions
        """
        suggestions: List[Suggestion] = []
        
        # Analyze code structure for pattern opportunities
        for analysis in analysis_results:
            # Look for opportunities to apply common patterns
            
            # Strategy pattern for complex conditionals
            if self._has_complex_conditionals(analysis):
                suggestions.append(Suggestion(
                    priority=3,
                    category="design_pattern",
                    title=f"Consider Strategy pattern in {analysis.file_path.split('/')[-1]}",
                    description="""**Pattern:** Strategy Pattern

**Recommendation:**
The code contains complex conditional logic that could benefit from the Strategy pattern.
This would make the code more maintainable and easier to extend.

**Benefits:**
- Eliminates complex conditional statements
- Makes it easy to add new strategies
- Improves testability""",
                    code_example=self._generate_strategy_pattern_example(analysis.language),
                    estimated_effort=EffortLevel.MEDIUM,
                    impact=ImpactLevel.MEDIUM,
                    related_issues=[analysis.file_path],
                ))
            
            # Factory pattern for object creation
            if self._has_multiple_constructors(analysis):
                suggestions.append(Suggestion(
                    priority=3,
                    category="design_pattern",
                    title=f"Consider Factory pattern in {analysis.file_path.split('/')[-1]}",
                    description="""**Pattern:** Factory Pattern

**Recommendation:**
The code has multiple ways of creating objects. Consider using a Factory pattern
to centralize object creation logic.

**Benefits:**
- Centralizes object creation
- Makes it easier to manage dependencies
- Improves code organization""",
                    code_example=self._generate_factory_pattern_example(analysis.language),
                    estimated_effort=EffortLevel.MEDIUM,
                    impact=ImpactLevel.MEDIUM,
                    related_issues=[analysis.file_path],
                ))
        
        return suggestions
    
    def _has_complex_conditionals(self, analysis: FileAnalysis) -> bool:
        """Check if file has complex conditional logic."""
        # Look for functions with high complexity
        for func in analysis.functions:
            if func.complexity >= 10:
                return True
        return False
    
    def _has_multiple_constructors(self, analysis: FileAnalysis) -> bool:
        """Check if file has multiple ways of creating objects."""
        # Simplified heuristic: multiple classes or factory-like functions
        return len(analysis.classes) >= 3
    
    def _generate_strategy_pattern_example(self, language: str) -> str:
        """Generate example for Strategy pattern."""
        if language == 'python':
            return """```python
# Before: Complex conditionals
def process_data(data, method):
    if method == 'A':
        # Method A logic
        pass
    elif method == 'B':
        # Method B logic
        pass
    elif method == 'C':
        # Method C logic
        pass

# After: Strategy pattern
class Strategy:
    def execute(self, data):
        raise NotImplementedError

class StrategyA(Strategy):
    def execute(self, data):
        # Method A logic
        pass

class StrategyB(Strategy):
    def execute(self, data):
        # Method B logic
        pass

def process_data(data, strategy: Strategy):
    return strategy.execute(data)
```"""
        
        return "Consider using Strategy pattern for complex conditionals"
    
    def _generate_factory_pattern_example(self, language: str) -> str:
        """Generate example for Factory pattern."""
        if language == 'python':
            return """```python
# Factory pattern example
class ObjectFactory:
    @staticmethod
    def create(object_type, **kwargs):
        if object_type == 'A':
            return ObjectA(**kwargs)
        elif object_type == 'B':
            return ObjectB(**kwargs)
        else:
            raise ValueError(f"Unknown type: {object_type}")

# Usage
obj = ObjectFactory.create('A', param1=value1)
```"""
        
        return "Consider using Factory pattern for object creation"
    
    def prioritize_suggestions(
        self,
        suggestions: List[Suggestion]
    ) -> List[Suggestion]:
        """
        Prioritize suggestions based on impact and effort.
        
        Suggestions are sorted by:
        1. Priority level (1 = highest)
        2. Impact (high > medium > low)
        3. Effort (low > medium > high) - prefer quick wins
        
        Args:
            suggestions: List of suggestions to prioritize
        
        Returns:
            Sorted list of suggestions
        """
        def sort_key(s: Suggestion) -> tuple:
            # Convert to numeric values for sorting
            impact_value = self.IMPACT_WEIGHTS.get(s.impact, 1)
            effort_value = self.EFFORT_WEIGHTS.get(s.estimated_effort, 2)
            
            # Return tuple for sorting: (priority, -impact, -effort)
            # Negative values to sort in descending order
            return (s.priority, -impact_value, -effort_value)
        
        return sorted(suggestions, key=sort_key)
    
    def generate_review_report(
        self,
        analysis_results: List[FileAnalysis],
        suggestions: List[Suggestion],
        quality_score: float
    ) -> str:
        """
        Generate a formatted review report.
        
        Args:
            analysis_results: List of file analysis results
            suggestions: List of prioritized suggestions
            quality_score: Overall quality score
        
        Returns:
            Formatted markdown report
        """
        lines = ["# Code Review Report\n"]
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**Quality Score:** {quality_score:.1f}/100\n")
        
        # Summary statistics
        lines.append("## Summary\n")
        total_files = len(analysis_results)
        total_issues = sum(len(a.issues) for a in analysis_results)
        total_suggestions = len(suggestions)
        
        lines.append(f"- **Files Analyzed:** {total_files}")
        lines.append(f"- **Issues Found:** {total_issues}")
        lines.append(f"- **Suggestions:** {total_suggestions}\n")
        
        # Issues by severity
        severity_counts: Dict[str, int] = {}
        for analysis in analysis_results:
            for issue in analysis.issues:
                severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
        
        if severity_counts:
            lines.append("### Issues by Severity\n")
            for severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH, IssueSeverity.MEDIUM, IssueSeverity.LOW]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    lines.append(f"- **{severity.upper()}:** {count}")
            lines.append("")
        
        # Top priority suggestions
        lines.append("## Top Priority Suggestions\n")
        top_suggestions = [s for s in suggestions if s.priority <= 2][:10]
        
        if top_suggestions:
            for i, suggestion in enumerate(top_suggestions, 1):
                lines.append(f"### {i}. {suggestion.title}")
                lines.append(f"**Priority:** {suggestion.priority} | **Impact:** {suggestion.impact} | **Effort:** {suggestion.estimated_effort}\n")
                lines.append(suggestion.description)
                
                if suggestion.code_example:
                    lines.append("\n**Example:**")
                    lines.append(suggestion.code_example)
                
                lines.append("\n---\n")
        else:
            lines.append("No high-priority suggestions at this time.\n")
        
        # All suggestions by category
        lines.append("## All Suggestions by Category\n")
        
        # Group suggestions by category
        by_category: Dict[str, List[Suggestion]] = {}
        for suggestion in suggestions:
            if suggestion.category not in by_category:
                by_category[suggestion.category] = []
            by_category[suggestion.category].append(suggestion)
        
        for category, cat_suggestions in sorted(by_category.items()):
            lines.append(f"### {category.replace('_', ' ').title()}")
            lines.append(f"Count: {len(cat_suggestions)}\n")
            
            for suggestion in cat_suggestions[:5]:  # Show top 5 per category
                lines.append(f"- **{suggestion.title}** (Priority: {suggestion.priority})")
            
            if len(cat_suggestions) > 5:
                lines.append(f"- ... and {len(cat_suggestions) - 5} more\n")
            else:
                lines.append("")
        
        return "\n".join(lines)
