"""
Demo script for ReviewerAgent.

This script demonstrates:
- Generating suggestions from analysis results
- Prioritizing suggestions
- Generating review reports
"""

from datetime import datetime
from agents.reviewer_agent import ReviewerAgent
from models.data_models import (
    FileAnalysis,
    CodeMetrics,
    CodeIssue,
    FunctionInfo,
    IssueSeverity,
    IssueCategory,
)


def create_sample_analysis() -> list[FileAnalysis]:
    """Create sample analysis results for demonstration."""
    
    # Sample file 1: Complex function with security issue
    analysis1 = FileAnalysis(
        file_path="src/database.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=18,
            maintainability_index=45.0,
            lines_of_code=250,
            comment_ratio=0.1,
        ),
        issues=[
            CodeIssue(
                severity=IssueSeverity.CRITICAL,
                category=IssueCategory.SECURITY,
                file_path="src/database.py",
                line_number=42,
                description="Potential SQL injection vulnerability detected",
                code_snippet='query = f"SELECT * FROM users WHERE id = {user_id}"',
                suggestion="Use parameterized queries or prepared statements",
            ),
            CodeIssue(
                severity=IssueSeverity.HIGH,
                category=IssueCategory.COMPLEXITY,
                file_path="src/database.py",
                line_number=100,
                description="Function 'process_query' has high cyclomatic complexity (18)",
                code_snippet="def process_query(...):",
                suggestion="Consider breaking this function into smaller, more focused functions",
            ),
        ],
        functions=[
            FunctionInfo(
                name="process_query",
                line_number=100,
                parameters=["query", "params", "options"],
                complexity=18,
            ),
            FunctionInfo(
                name="execute_query",
                line_number=150,
                parameters=["sql", "params"],
                complexity=8,
            ),
        ],
        classes=[],
    )
    
    # Sample file 2: Missing error handling
    analysis2 = FileAnalysis(
        file_path="src/api_client.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=5,
            maintainability_index=75.0,
            lines_of_code=120,
            comment_ratio=0.2,
        ),
        issues=[
            CodeIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.ERROR_HANDLING,
                file_path="src/api_client.py",
                line_number=25,
                description="Missing error handling for network calls",
                code_snippet="response = requests.get(url)",
                suggestion="Wrap network calls in try-except/try-catch block",
            ),
        ],
        functions=[
            FunctionInfo(
                name="fetch_data",
                line_number=20,
                parameters=["url", "headers"],
                complexity=5,
            ),
        ],
        classes=[],
    )
    
    # Sample file 3: Code duplication
    analysis3 = FileAnalysis(
        file_path="src/utils.py",
        language="python",
        metrics=CodeMetrics(
            cyclomatic_complexity=3,
            maintainability_index=80.0,
            lines_of_code=80,
            comment_ratio=0.15,
        ),
        issues=[
            CodeIssue(
                severity=IssueSeverity.MEDIUM,
                category=IssueCategory.DUPLICATION,
                file_path="src/utils.py",
                line_number=30,
                description="Duplicate code block detected (also at line 50)",
                code_snippet="for item in items:\n    validate(item)\n    process(item)",
                suggestion="Consider extracting this code into a reusable function",
            ),
        ],
        functions=[
            FunctionInfo(
                name="process_items_a",
                line_number=25,
                parameters=["items"],
                complexity=3,
            ),
            FunctionInfo(
                name="process_items_b",
                line_number=45,
                parameters=["items"],
                complexity=3,
            ),
        ],
        classes=[],
    )
    
    return [analysis1, analysis2, analysis3]


def main():
    """Run the ReviewerAgent demo."""
    print("=" * 80)
    print("ReviewerAgent Demo")
    print("=" * 80)
    print()
    
    # Create reviewer agent
    reviewer = ReviewerAgent(use_llm=False)
    print("✓ Created ReviewerAgent")
    print()
    
    # Create sample analysis results
    analysis_results = create_sample_analysis()
    print(f"✓ Created {len(analysis_results)} sample file analyses")
    print()
    
    # Generate suggestions
    print("Generating suggestions from analysis results...")
    suggestions = reviewer.generate_suggestions(analysis_results)
    print(f"✓ Generated {len(suggestions)} suggestions")
    print()
    
    # Display some suggestions
    print("Sample suggestions (before prioritization):")
    for i, suggestion in enumerate(suggestions[:3], 1):
        print(f"\n{i}. {suggestion.title}")
        print(f"   Category: {suggestion.category}")
        print(f"   Priority: {suggestion.priority}")
        print(f"   Impact: {suggestion.impact}, Effort: {suggestion.estimated_effort}")
    print()
    
    # Prioritize suggestions
    print("Prioritizing suggestions...")
    prioritized = reviewer.prioritize_suggestions(suggestions)
    print(f"✓ Prioritized {len(prioritized)} suggestions")
    print()
    
    # Display prioritized suggestions
    print("Top 5 prioritized suggestions:")
    for i, suggestion in enumerate(prioritized[:5], 1):
        print(f"\n{i}. {suggestion.title}")
        print(f"   Priority: {suggestion.priority}")
        print(f"   Impact: {suggestion.impact}, Effort: {suggestion.estimated_effort}")
        print(f"   Category: {suggestion.category}")
    print()
    
    # Generate review report
    print("Generating review report...")
    quality_score = 65.0  # Sample quality score
    report = reviewer.generate_review_report(
        analysis_results,
        prioritized,
        quality_score
    )
    print("✓ Generated review report")
    print()
    
    # Display report preview
    print("Review Report Preview:")
    print("-" * 80)
    report_lines = report.split('\n')
    for line in report_lines[:30]:  # Show first 30 lines
        print(line)
    print("...")
    print(f"(Report continues for {len(report_lines)} total lines)")
    print("-" * 80)
    print()
    
    # Summary
    print("=" * 80)
    print("Demo Summary:")
    print(f"- Analyzed {len(analysis_results)} files")
    print(f"- Found {sum(len(a.issues) for a in analysis_results)} issues")
    print(f"- Generated {len(suggestions)} suggestions")
    print(f"- Quality Score: {quality_score}/100")
    print("=" * 80)


if __name__ == "__main__":
    main()
