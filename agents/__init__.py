"""
Multi-agent system for code review and documentation.

This package contains the specialized agents:
- CoordinatorAgent: Orchestrates the workflow
- AnalyzerAgent: Performs code quality analysis
- DocumenterAgent: Generates documentation
- ReviewerAgent: Provides improvement suggestions
"""

from agents.analyzer_agent import AnalyzerAgent
from agents.documenter_agent import DocumenterAgent, CodebaseStructure
from agents.reviewer_agent import ReviewerAgent
from agents.coordinator_agent import CoordinatorAgent

__version__ = "0.1.0"

__all__ = [
    "AnalyzerAgent",
    "DocumenterAgent",
    "CodebaseStructure",
    "ReviewerAgent",
    "CoordinatorAgent",
]
