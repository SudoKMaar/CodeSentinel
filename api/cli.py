"""Command-line interface for the code review agent."""

import sys
import json
import yaml
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

from agents.coordinator_agent import CoordinatorAgent
from models.data_models import (
    AnalysisConfig,
    AnalysisDepth,
    SessionStatus,
)
from storage.memory_bank import MemoryBank
from storage.session_manager import SessionManager
from tools.quality_metrics import QualityMetricsCalculator
from config.settings import settings

console = Console()


def load_config_file(config_path: str) -> dict:
    """
    Load configuration from YAML or JSON file.
    
    Args:
        config_path: Path to configuration file
    
    Returns:
        Configuration dictionary
    
    Raises:
        click.ClickException: If file cannot be loaded
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise click.ClickException(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                return yaml.safe_load(f)
            elif config_path.endswith('.json'):
                return json.load(f)
            else:
                raise click.ClickException(
                    f"Unsupported configuration file format. Use .yaml, .yml, or .json"
                )
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise click.ClickException(f"Error parsing configuration file: {e}")
    except Exception as e:
        raise click.ClickException(f"Error loading configuration: {e}")


def create_coordinator() -> CoordinatorAgent:
    """Create and return a CoordinatorAgent instance."""
    memory_bank = MemoryBank()
    session_manager = SessionManager()
    quality_metrics = QualityMetricsCalculator()
    
    return CoordinatorAgent(
        memory_bank=memory_bank,
        session_manager=session_manager,
        quality_metrics=quality_metrics,
        max_workers=settings.max_parallel_files
    )


@click.group()
@click.version_option(version="0.1.0")
def main() -> None:
    """
    Code Review & Documentation Agent CLI.
    
    A multi-agent system for automated code quality analysis, documentation
    generation, and code review with AI-powered suggestions.
    
    \b
    Examples:
        # Analyze a codebase
        code-review analyze --path ./src
        
        # Analyze with custom configuration
        code-review analyze --path ./src --config analysis.yaml
        
        # Check analysis status
        code-review status <session-id>
        
        # Pause a running analysis
        code-review pause <session-id>
        
        # Resume a paused analysis
        code-review resume <session-id>
        
        # View analysis history
        code-review history
    """
    pass


@main.command()
@click.option(
    "--path",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Path to codebase to analyze"
)
@click.option(
    "--config",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Path to configuration file (YAML or JSON)"
)
@click.option(
    "--output",
    type=click.Path(file_okay=False, dir_okay=True),
    help="Output directory for reports (default: ./demo_docs)"
)
@click.option(
    "--depth",
    type=click.Choice(['quick', 'standard', 'deep'], case_sensitive=False),
    default='standard',
    help="Analysis depth (default: standard)"
)
@click.option(
    "--parallel/--no-parallel",
    default=True,
    help="Enable/disable parallel file processing (default: enabled)"
)
@click.option(
    "--file-patterns",
    multiple=True,
    help="File patterns to include (e.g., '*.py', '*.js'). Can be specified multiple times."
)
@click.option(
    "--exclude-patterns",
    multiple=True,
    help="Patterns to exclude (e.g., 'node_modules/**'). Can be specified multiple times."
)
@click.option(
    "--project-id",
    help="Project identifier for Memory Bank patterns"
)
def analyze(
    path: str,
    config: Optional[str],
    output: Optional[str],
    depth: str,
    parallel: bool,
    file_patterns: tuple,
    exclude_patterns: tuple,
    project_id: Optional[str]
) -> None:
    """
    Analyze a codebase for quality issues and generate documentation.
    
    This command performs a comprehensive analysis of your codebase including:
    - Code quality analysis (complexity, duplication, security)
    - Documentation generation
    - Improvement suggestions with prioritization
    - Quality metrics and scoring
    
    The analysis runs asynchronously and you can check its progress using
    the 'status' command with the returned session ID.
    """
    try:
        console.print(Panel.fit(
            "[bold cyan]Code Review & Documentation Agent[/bold cyan]\n"
            "Starting analysis...",
            border_style="cyan"
        ))
        
        # Load configuration from file if provided
        config_dict = {}
        if config:
            console.print(f"[dim]Loading configuration from: {config}[/dim]")
            config_dict = load_config_file(config)
        
        # Build analysis configuration
        analysis_config = AnalysisConfig(
            target_path=path,
            file_patterns=list(file_patterns) if file_patterns else config_dict.get(
                'file_patterns',
                ["*.py", "*.js", "*.ts", "*.tsx", "*.jsx"]
            ),
            exclude_patterns=list(exclude_patterns) if exclude_patterns else config_dict.get(
                'exclude_patterns',
                ["node_modules/**", "venv/**", ".git/**", "__pycache__/**", "*.pyc"]
            ),
            coding_standards=config_dict.get('coding_standards', {}),
            analysis_depth=AnalysisDepth(depth),
            enable_parallel=parallel
        )
        
        # Create coordinator
        coordinator = create_coordinator()
        
        # Start analysis with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]Analyzing codebase at {path}...",
                total=None
            )
            
            try:
                result = coordinator.analyze_codebase(
                    config=analysis_config,
                    project_id=project_id
                )
                
                progress.update(task, completed=True)
                
            except Exception as e:
                progress.stop()
                console.print(f"[bold red]Error during analysis:[/bold red] {e}")
                raise click.Abort()
        
        # Display results summary
        console.print("\n[bold green]✓ Analysis completed successfully![/bold green]\n")
        
        # Create results table
        results_table = Table(title="Analysis Results", show_header=True, header_style="bold magenta")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")
        
        results_table.add_row("Session ID", result.session_id)
        results_table.add_row("Files Analyzed", str(result.files_analyzed))
        results_table.add_row("Total Issues", str(result.total_issues))
        results_table.add_row("Quality Score", f"{result.quality_score:.1f}/100")
        results_table.add_row("Suggestions", str(len(result.suggestions)))
        
        console.print(results_table)
        
        # Display issue breakdown
        if result.metrics_summary.total_issues_by_severity:
            console.print("\n[bold]Issue Breakdown by Severity:[/bold]")
            for severity, count in result.metrics_summary.total_issues_by_severity.items():
                severity_color = {
                    'critical': 'red',
                    'high': 'yellow',
                    'medium': 'blue',
                    'low': 'dim'
                }.get(severity, 'white')
                console.print(f"  [{severity_color}]• {severity.upper()}: {count}[/{severity_color}]")
        
        # Display top suggestions
        if result.suggestions:
            console.print("\n[bold]Top Suggestions:[/bold]")
            for i, suggestion in enumerate(result.suggestions[:5], 1):
                console.print(f"  {i}. [{suggestion.priority}] {suggestion.title}")
        
        # Save detailed report if output directory specified
        if output:
            output_dir = Path(output)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            report_file = output_dir / f"analysis_report_{result.session_id}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(result.model_dump(mode='json'), f, indent=2, ensure_ascii=False)
            
            console.print(f"\n[dim]Detailed report saved to: {report_file}[/dim]")
        
        console.print(f"\n[dim]Session ID: {result.session_id}[/dim]")
        console.print("[dim]Use 'code-review status <session-id>' to check status later[/dim]")
        
    except click.Abort:
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.argument("session_id")
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed status information"
)
def status(session_id: str, verbose: bool) -> None:
    """
    Check the status of an analysis session.
    
    Displays the current status, progress, and file counts for the specified
    analysis session. Use the session ID returned by the 'analyze' command.
    """
    try:
        coordinator = create_coordinator()
        session_state = coordinator.get_analysis_status(session_id)
        
        if session_state is None:
            console.print(f"[bold red]Error:[/bold red] Session not found: {session_id}")
            sys.exit(1)
        
        # Calculate progress
        total_files = len(session_state.processed_files) + len(session_state.pending_files)
        progress_pct = 0.0
        if total_files > 0:
            progress_pct = (len(session_state.processed_files) / total_files) * 100
        
        # Status color mapping
        status_colors = {
            SessionStatus.RUNNING: "yellow",
            SessionStatus.PAUSED: "blue",
            SessionStatus.COMPLETED: "green",
            SessionStatus.FAILED: "red"
        }
        status_color = status_colors.get(session_state.status, "white")
        
        # Display status panel
        status_text = f"""
[bold]Session ID:[/bold] {session_id}
[bold]Status:[/bold] [{status_color}]{session_state.status}[/{status_color}]
[bold]Progress:[/bold] {progress_pct:.1f}% ({len(session_state.processed_files)}/{total_files} files)
[bold]Last Updated:[/bold] {session_state.checkpoint_time.strftime('%Y-%m-%d %H:%M:%S')}
[bold]Target Path:[/bold] {session_state.config.target_path}
        """
        
        console.print(Panel(status_text.strip(), title="Analysis Status", border_style=status_color))
        
        # Show detailed information if verbose
        if verbose:
            console.print("\n[bold]Configuration:[/bold]")
            console.print(f"  Analysis Depth: {session_state.config.analysis_depth}")
            console.print(f"  Parallel Processing: {session_state.config.enable_parallel}")
            console.print(f"  File Patterns: {', '.join(session_state.config.file_patterns)}")
            
            if session_state.pending_files:
                console.print(f"\n[bold]Pending Files:[/bold] ({len(session_state.pending_files)})")
                for file_path in session_state.pending_files[:10]:
                    console.print(f"  • {file_path}")
                if len(session_state.pending_files) > 10:
                    console.print(f"  ... and {len(session_state.pending_files) - 10} more")
            
            if session_state.partial_results:
                console.print(f"\n[bold]Partial Results:[/bold]")
                for key, value in session_state.partial_results.items():
                    if key != 'file_analyses' and key != 'file_mtimes':
                        console.print(f"  {key}: {value}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.argument("session_id")
@click.option(
    "--force",
    is_flag=True,
    help="Force pause even if session is not running"
)
def pause(session_id: str, force: bool) -> None:
    """
    Pause a running analysis session.
    
    Saves the current session state including processed files, pending files,
    and partial results. The session can be resumed later using the 'resume'
    command. File modification times are tracked to detect changes during pause.
    """
    try:
        coordinator = create_coordinator()
        
        # Check session exists and is running
        session_state = coordinator.get_analysis_status(session_id)
        
        if session_state is None:
            console.print(f"[bold red]Error:[/bold red] Session not found: {session_id}")
            sys.exit(1)
        
        if session_state.status != SessionStatus.RUNNING and not force:
            console.print(
                f"[bold yellow]Warning:[/bold yellow] Session is not running "
                f"(current status: {session_state.status})"
            )
            console.print("Use --force to pause anyway")
            sys.exit(1)
        
        # Pause the analysis
        with console.status("[yellow]Pausing analysis...[/yellow]"):
            success = coordinator.pause_analysis(session_id)
        
        if success:
            console.print(f"[bold green]✓ Analysis paused successfully[/bold green]")
            console.print(f"\nSession ID: {session_id}")
            console.print(f"Processed: {len(session_state.processed_files)} files")
            console.print(f"Pending: {len(session_state.pending_files)} files")
            console.print("\n[dim]Use 'code-review resume <session-id>' to continue[/dim]")
        else:
            console.print(f"[bold red]Error:[/bold red] Failed to pause analysis")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.argument("session_id")
@click.option(
    "--project-id",
    help="Project identifier for Memory Bank patterns"
)
def resume(session_id: str, project_id: Optional[str]) -> None:
    """
    Resume a paused analysis session.
    
    Restores the session state and continues analysis from where it left off.
    The system automatically detects files that were modified during the pause
    and re-analyzes them along with any pending files.
    """
    try:
        coordinator = create_coordinator()
        
        # Check session exists and is paused
        session_state = coordinator.get_analysis_status(session_id)
        
        if session_state is None:
            console.print(f"[bold red]Error:[/bold red] Session not found: {session_id}")
            sys.exit(1)
        
        if session_state.status != SessionStatus.PAUSED:
            console.print(
                f"[bold yellow]Warning:[/bold yellow] Session is not paused "
                f"(current status: {session_state.status})"
            )
            sys.exit(1)
        
        console.print(Panel.fit(
            "[bold cyan]Resuming Analysis[/bold cyan]\n"
            f"Session ID: {session_id}",
            border_style="cyan"
        ))
        
        # Resume analysis with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]Resuming analysis and detecting changes...",
                total=None
            )
            
            try:
                result = coordinator.resume_analysis(session_id, project_id)
                progress.update(task, completed=True)
                
            except Exception as e:
                progress.stop()
                console.print(f"[bold red]Error during resume:[/bold red] {e}")
                raise click.Abort()
        
        if result:
            console.print("\n[bold green]✓ Analysis completed successfully![/bold green]\n")
            
            # Display results summary
            results_table = Table(show_header=True, header_style="bold magenta")
            results_table.add_column("Metric", style="cyan")
            results_table.add_column("Value", style="green")
            
            results_table.add_row("Files Analyzed", str(result.files_analyzed))
            results_table.add_row("Total Issues", str(result.total_issues))
            results_table.add_row("Quality Score", f"{result.quality_score:.1f}/100")
            results_table.add_row("Suggestions", str(len(result.suggestions)))
            
            console.print(results_table)
        else:
            console.print("[bold yellow]Analysis resumed but not yet completed[/bold yellow]")
            console.print(f"Use 'code-review status {session_id}' to check progress")
        
    except click.Abort:
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.option(
    "--status-filter",
    type=click.Choice(['running', 'paused', 'completed', 'failed'], case_sensitive=False),
    help="Filter by session status"
)
@click.option(
    "--limit",
    type=int,
    default=20,
    help="Maximum number of sessions to display (default: 20)"
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed information for each session"
)
def history(status_filter: Optional[str], limit: int, verbose: bool) -> None:
    """
    Show history of previous analyses.
    
    Displays a list of all analysis sessions, optionally filtered by status.
    Sessions are sorted by most recent first. Use --verbose to see detailed
    information including file counts and quality scores.
    """
    try:
        session_manager = SessionManager()
        
        # Parse status filter
        status_enum = None
        if status_filter:
            status_enum = SessionStatus(status_filter.lower())
        
        # Get sessions
        sessions = session_manager.list_sessions(status_filter=status_enum)
        
        if not sessions:
            console.print("[yellow]No analysis sessions found[/yellow]")
            if status_filter:
                console.print(f"[dim]Try removing the --status-filter option[/dim]")
            return
        
        # Limit results
        sessions = sessions[:limit]
        
        # Display header
        filter_text = f" ({status_filter.upper()})" if status_filter else ""
        console.print(f"\n[bold cyan]Analysis History{filter_text}[/bold cyan]")
        console.print(f"[dim]Showing {len(sessions)} of {len(sessions)} sessions[/dim]\n")
        
        # Create table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Session ID", style="cyan", no_wrap=True)
        table.add_column("Status", style="white")
        table.add_column("Date", style="dim")
        table.add_column("Path", style="blue")
        
        if verbose:
            table.add_column("Files", justify="right")
            table.add_column("Quality", justify="right")
        
        # Add rows
        for session in sessions:
            # Status with color
            status_colors = {
                SessionStatus.RUNNING: "yellow",
                SessionStatus.PAUSED: "blue",
                SessionStatus.COMPLETED: "green",
                SessionStatus.FAILED: "red"
            }
            status_color = status_colors.get(session.status, "white")
            status_text = f"[{status_color}]{session.status}[/{status_color}]"
            
            # Format date
            date_str = session.checkpoint_time.strftime('%Y-%m-%d %H:%M')
            
            # Truncate path if too long
            path = session.config.target_path
            if len(path) > 40:
                path = "..." + path[-37:]
            
            row = [
                session.session_id[:8] + "...",
                status_text,
                date_str,
                path
            ]
            
            if verbose:
                files_count = len(session.processed_files)
                quality_score = session.partial_results.get('quality_score', 'N/A')
                if isinstance(quality_score, (int, float)):
                    quality_score = f"{quality_score:.1f}"
                
                row.extend([str(files_count), str(quality_score)])
            
            table.add_row(*row)
        
        console.print(table)
        
        # Show usage hint
        console.print("\n[dim]Use 'code-review status <session-id>' for detailed information[/dim]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@main.command()
def examples() -> None:
    """Show usage examples and help."""
    examples_text = """
# Code Review & Documentation Agent - Usage Examples

## Basic Analysis
Analyze a codebase with default settings:
```bash
code-review analyze --path ./src
```

## Custom Configuration
Use a configuration file for advanced settings:
```bash
code-review analyze --path ./src --config analysis.yaml
```

Example configuration file (analysis.yaml):
```yaml
target_path: ./src
file_patterns:
  - "*.py"
  - "*.js"
  - "*.ts"
exclude_patterns:
  - "node_modules/**"
  - "venv/**"
  - "__pycache__/**"
coding_standards:
  max_complexity: 10
  max_line_length: 100
analysis_depth: deep
enable_parallel: true
```

## Analysis Depth Options
- **quick**: Fast analysis with basic checks
- **standard**: Balanced analysis (default)
- **deep**: Comprehensive analysis with all checks

```bash
code-review analyze --path ./src --depth deep
```

## File Filtering
Include specific file patterns:
```bash
code-review analyze --path ./src --file-patterns "*.py" --file-patterns "*.js"
```

Exclude patterns:
```bash
code-review analyze --path ./src --exclude-patterns "tests/**" --exclude-patterns "*.test.js"
```

## Session Management
Check analysis status:
```bash
code-review status <session-id>
```

Pause a running analysis:
```bash
code-review pause <session-id>
```

Resume a paused analysis:
```bash
code-review resume <session-id>
```

## View History
Show all previous analyses:
```bash
code-review history
```

Filter by status:
```bash
code-review history --status-filter completed
```

Show detailed history:
```bash
code-review history --verbose --limit 10
```

## Output Options
Save detailed report to a directory:
```bash
code-review analyze --path ./src --output ./reports
```

## Project Tracking
Use project ID for consistent pattern tracking:
```bash
code-review analyze --path ./src --project-id my-project
```

## Getting Help
Show help for any command:
```bash
code-review --help
code-review analyze --help
code-review status --help
```
    """
    
    console.print(Markdown(examples_text))


if __name__ == "__main__":
    main()
