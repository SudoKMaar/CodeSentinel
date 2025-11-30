"""
CI/CD Integration tools for the Code Review & Documentation Agent.

This module provides:
- Git integration for detecting changed files in PRs
- CI/CD-friendly output formats (JSON, SARIF)
- Exit code handling for failing on critical issues
- Configuration file support for CI/CD environments
"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timezone

from models.data_models import (
    AnalysisResult,
    CodeIssue,
    IssueSeverity,
    IssueCategory,
)


class GitIntegration:
    """Git integration for detecting changed files in pull requests."""
    
    def __init__(self, repo_path: str):
        """
        Initialize Git integration.
        
        Args:
            repo_path: Path to the Git repository
        """
        self.repo_path = Path(repo_path)
        
        # Verify this is a Git repository
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a Git repository: {repo_path}")
    
    def get_changed_files(
        self,
        base_ref: str = "origin/main",
        head_ref: str = "HEAD",
        file_patterns: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get list of files changed between two Git refs.
        
        This is useful for PR analysis where you want to analyze only
        the files that have been modified in the pull request.
        
        Args:
            base_ref: Base reference (e.g., 'origin/main', 'main')
            head_ref: Head reference (e.g., 'HEAD', 'feature-branch')
            file_patterns: Optional list of file patterns to filter (e.g., ['*.py', '*.js'])
        
        Returns:
            List of file paths that have changed
        """
        try:
            # Get list of changed files using git diff
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            changed_files = [
                line.strip()
                for line in result.stdout.split('\n')
                if line.strip()
            ]
            
            # Convert to absolute paths
            changed_files = [
                str(self.repo_path / file_path)
                for file_path in changed_files
            ]
            
            # Filter by file patterns if provided
            if file_patterns:
                filtered_files = []
                for file_path in changed_files:
                    path = Path(file_path)
                    for pattern in file_patterns:
                        # Simple pattern matching (*.py, *.js, etc.)
                        if pattern.startswith('*.'):
                            extension = pattern[1:]  # Remove the *
                            if path.suffix == extension:
                                filtered_files.append(file_path)
                                break
                        elif path.match(pattern):
                            filtered_files.append(file_path)
                            break
                
                changed_files = filtered_files
            
            # Filter out deleted files (only return files that exist)
            changed_files = [
                file_path
                for file_path in changed_files
                if Path(file_path).exists()
            ]
            
            return changed_files
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Git command failed: {e.stderr}")
        except FileNotFoundError:
            raise RuntimeError("Git command not found. Please ensure Git is installed.")
    
    def get_current_branch(self) -> str:
        """
        Get the current Git branch name.
        
        Returns:
            Current branch name
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get current branch: {e.stderr}")
    
    def get_commit_sha(self, ref: str = "HEAD") -> str:
        """
        Get the commit SHA for a given ref.
        
        Args:
            ref: Git reference (default: HEAD)
        
        Returns:
            Commit SHA
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", ref],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get commit SHA: {e.stderr}")


class OutputFormatter:
    """Formatter for CI/CD-friendly output formats."""
    
    @staticmethod
    def to_json(result: AnalysisResult) -> str:
        """
        Convert analysis result to JSON format.
        
        Args:
            result: Analysis result
        
        Returns:
            JSON string
        """
        # Use Pydantic's model_dump with mode='json' for proper serialization
        result_dict = result.model_dump(mode='json')
        return json.dumps(result_dict, indent=2, default=str)
    
    @staticmethod
    def to_sarif(result: AnalysisResult, tool_name: str = "code-review-agent") -> str:
        """
        Convert analysis result to SARIF format.
        
        SARIF (Static Analysis Results Interchange Format) is a standard
        format for static analysis tools, supported by GitHub, GitLab, and
        other CI/CD platforms.
        
        Args:
            result: Analysis result
            tool_name: Name of the tool for SARIF metadata
        
        Returns:
            SARIF JSON string
        """
        # Build SARIF document
        sarif_doc = {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": tool_name,
                            "version": "0.1.0",
                            "informationUri": "https://github.com/your-org/code-review-agent",
                            "rules": OutputFormatter._build_sarif_rules()
                        }
                    },
                    "results": OutputFormatter._build_sarif_results(result),
                    "properties": {
                        "session_id": result.session_id,
                        "timestamp": result.timestamp.isoformat(),
                        "quality_score": result.quality_score,
                        "files_analyzed": result.files_analyzed,
                        "total_issues": result.total_issues
                    }
                }
            ]
        }
        
        return json.dumps(sarif_doc, indent=2)
    
    @staticmethod
    def _build_sarif_rules() -> List[Dict[str, Any]]:
        """Build SARIF rules from issue categories."""
        rules = []
        
        # Define rules for each issue category
        category_rules = {
            IssueCategory.COMPLEXITY: {
                "id": "complexity",
                "name": "Code Complexity",
                "shortDescription": {"text": "Code has high cyclomatic complexity"},
                "fullDescription": {"text": "Functions or methods with high cyclomatic complexity are harder to understand, test, and maintain."},
                "defaultConfiguration": {"level": "warning"}
            },
            IssueCategory.SECURITY: {
                "id": "security",
                "name": "Security Vulnerability",
                "shortDescription": {"text": "Potential security vulnerability detected"},
                "fullDescription": {"text": "Code contains patterns that may lead to security vulnerabilities such as SQL injection or hardcoded credentials."},
                "defaultConfiguration": {"level": "error"}
            },
            IssueCategory.STYLE: {
                "id": "style",
                "name": "Code Style",
                "shortDescription": {"text": "Code style violation"},
                "fullDescription": {"text": "Code does not follow the configured coding standards or style guidelines."},
                "defaultConfiguration": {"level": "note"}
            },
            IssueCategory.DUPLICATION: {
                "id": "duplication",
                "name": "Code Duplication",
                "shortDescription": {"text": "Duplicated code detected"},
                "fullDescription": {"text": "Code contains duplicated blocks that should be refactored into reusable functions or modules."},
                "defaultConfiguration": {"level": "warning"}
            },
            IssueCategory.ERROR_HANDLING: {
                "id": "error_handling",
                "name": "Error Handling",
                "shortDescription": {"text": "Missing or inadequate error handling"},
                "fullDescription": {"text": "Code lacks proper error handling for operations that may fail."},
                "defaultConfiguration": {"level": "warning"}
            },
            IssueCategory.NAMING: {
                "id": "naming",
                "name": "Naming Convention",
                "shortDescription": {"text": "Naming convention violation"},
                "fullDescription": {"text": "Variable, function, or class names do not follow the project's naming conventions."},
                "defaultConfiguration": {"level": "note"}
            }
        }
        
        for category, rule_def in category_rules.items():
            rules.append(rule_def)
        
        return rules
    
    @staticmethod
    def _build_sarif_results(result: AnalysisResult) -> List[Dict[str, Any]]:
        """Build SARIF results from analysis issues."""
        sarif_results = []
        
        for file_analysis in result.file_analyses:
            for issue in file_analysis.issues:
                # Map severity to SARIF level
                level_map = {
                    IssueSeverity.CRITICAL: "error",
                    IssueSeverity.HIGH: "error",
                    IssueSeverity.MEDIUM: "warning",
                    IssueSeverity.LOW: "note"
                }
                
                sarif_result = {
                    "ruleId": issue.category,
                    "level": level_map.get(issue.severity, "warning"),
                    "message": {
                        "text": issue.description
                    },
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {
                                    "uri": issue.file_path,
                                    "uriBaseId": "%SRCROOT%"
                                },
                                "region": {
                                    "startLine": issue.line_number,
                                    "snippet": {
                                        "text": issue.code_snippet
                                    }
                                }
                            }
                        }
                    ]
                }
                
                # Add fix suggestion if available
                if issue.suggestion:
                    sarif_result["fixes"] = [
                        {
                            "description": {
                                "text": issue.suggestion
                            }
                        }
                    ]
                
                sarif_results.append(sarif_result)
        
        return sarif_results


class ExitCodeHandler:
    """Handler for determining exit codes based on analysis results."""
    
    @staticmethod
    def get_exit_code(
        result: AnalysisResult,
        fail_on_critical: bool = True,
        fail_on_high: bool = False,
        max_issues: Optional[int] = None
    ) -> int:
        """
        Determine exit code based on analysis results.
        
        This is useful for CI/CD pipelines where you want to fail the build
        if certain conditions are met (e.g., critical issues found).
        
        Args:
            result: Analysis result
            fail_on_critical: Fail (exit 1) if critical issues are found
            fail_on_high: Fail (exit 1) if high severity issues are found
            max_issues: Fail (exit 1) if total issues exceed this threshold
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        # Count issues by severity
        critical_count = 0
        high_count = 0
        
        for file_analysis in result.file_analyses:
            for issue in file_analysis.issues:
                if issue.severity == IssueSeverity.CRITICAL:
                    critical_count += 1
                elif issue.severity == IssueSeverity.HIGH:
                    high_count += 1
        
        # Check failure conditions
        if fail_on_critical and critical_count > 0:
            return 1
        
        if fail_on_high and high_count > 0:
            return 1
        
        if max_issues is not None and result.total_issues > max_issues:
            return 1
        
        return 0
    
    @staticmethod
    def get_exit_message(
        result: AnalysisResult,
        exit_code: int
    ) -> str:
        """
        Get a human-readable exit message.
        
        Args:
            result: Analysis result
            exit_code: Exit code
        
        Returns:
            Exit message
        """
        if exit_code == 0:
            return f"✓ Analysis passed: {result.files_analyzed} files analyzed, {result.total_issues} issues found, quality score: {result.quality_score:.1f}"
        else:
            # Count critical and high issues
            critical_count = sum(
                1 for fa in result.file_analyses
                for issue in fa.issues
                if issue.severity == IssueSeverity.CRITICAL
            )
            high_count = sum(
                1 for fa in result.file_analyses
                for issue in fa.issues
                if issue.severity == IssueSeverity.HIGH
            )
            
            return f"✗ Analysis failed: {critical_count} critical, {high_count} high severity issues found"


class CICDConfigLoader:
    """Loader for CI/CD configuration files."""
    
    @staticmethod
    def load_config(config_path: str) -> Dict[str, Any]:
        """
        Load configuration from a file.
        
        Supports YAML and JSON formats.
        
        Args:
            config_path: Path to configuration file
        
        Returns:
            Configuration dictionary
        """
        import yaml
        
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif path.suffix == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported configuration format: {path.suffix}")
    
    @staticmethod
    def get_pr_mode_config() -> Dict[str, Any]:
        """
        Get default configuration for PR mode.
        
        Returns:
            Configuration dictionary optimized for PR analysis
        """
        return {
            "analysis_depth": "quick",
            "enable_parallel": True,
            "fail_on_critical": True,
            "fail_on_high": False,
            "output_format": "sarif",
            "exclude_patterns": [
                "node_modules/**",
                "venv/**",
                ".git/**",
                "__pycache__/**",
                "*.min.js",
                "*.min.css",
                "dist/**",
                "build/**"
            ]
        }
