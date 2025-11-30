"""
Demo script for the Coordinator Agent.

This script demonstrates:
- Loading configuration from YAML
- Running a complete analysis workflow
- Generating review reports
- Using Memory Bank for pattern storage
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.coordinator_agent import CoordinatorAgent
from models.data_models import AnalysisConfig, AnalysisDepth
from storage.memory_bank import MemoryBank
from storage.session_manager import SessionManager


def demo_basic_analysis():
    """Demonstrate basic codebase analysis."""
    print("=" * 80)
    print("Demo: Basic Codebase Analysis")
    print("=" * 80)
    
    # Create coordinator
    coordinator = CoordinatorAgent()
    
    # Create analysis configuration
    config = AnalysisConfig(
        target_path="./agents",  # Analyze the agents directory
        file_patterns=["*.py"],
        exclude_patterns=["__pycache__/**", "*.pyc"],
        analysis_depth=AnalysisDepth.STANDARD,
        enable_parallel=True
    )
    
    print(f"\nAnalyzing codebase: {config.target_path}")
    print(f"Analysis depth: {config.analysis_depth}")
    
    # Run analysis
    result = coordinator.analyze_codebase(config, project_id="demo_project")
    
    # Display results
    print(f"\n{'Results':=^80}")
    print(f"Session ID: {result.session_id}")
    print(f"Files analyzed: {result.files_analyzed}")
    print(f"Total issues: {result.total_issues}")
    print(f"Quality score: {result.quality_score:.1f}/100")
    
    print(f"\n{'Metrics Summary':=^80}")
    print(f"Total lines of code: {result.metrics_summary.total_lines}")
    print(f"Average complexity: {result.metrics_summary.average_complexity:.1f}")
    print(f"Average maintainability: {result.metrics_summary.average_maintainability:.1f}")
    
    print(f"\n{'Issues by Severity':=^80}")
    for severity, count in result.metrics_summary.total_issues_by_severity.items():
        print(f"  {severity}: {count}")
    
    print(f"\n{'Top Suggestions':=^80}")
    for i, suggestion in enumerate(result.suggestions[:5], 1):
        print(f"{i}. [{suggestion.priority}] {suggestion.title}")
        print(f"   Impact: {suggestion.impact}, Effort: {suggestion.estimated_effort}")
    
    return result


def demo_yaml_config():
    """Demonstrate loading configuration from YAML."""
    print("\n" + "=" * 80)
    print("Demo: Loading Configuration from YAML")
    print("=" * 80)
    
    coordinator = CoordinatorAgent()
    
    # Check if example config exists
    config_path = "./examples/analysis_config_example.yaml"
    if not Path(config_path).exists():
        print(f"\nConfig file not found: {config_path}")
        print("Skipping YAML config demo")
        return
    
    try:
        # Load configuration from YAML
        config = coordinator.load_config_from_yaml(config_path)
        
        print(f"\nLoaded configuration from: {config_path}")
        print(f"Target path: {config.target_path}")
        print(f"File patterns: {config.file_patterns}")
        print(f"Analysis depth: {config.analysis_depth}")
        print(f"Parallel processing: {config.enable_parallel}")
        
        if config.coding_standards:
            print(f"\nCoding standards:")
            for key, value in config.coding_standards.items():
                print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"\nError loading configuration: {e}")


def demo_memory_bank_integration():
    """Demonstrate Memory Bank pattern storage and retrieval."""
    print("\n" + "=" * 80)
    print("Demo: Memory Bank Integration")
    print("=" * 80)
    
    # Create coordinator with Memory Bank
    memory_bank = MemoryBank(db_path="demo_memory_bank.db")
    coordinator = CoordinatorAgent(memory_bank=memory_bank)
    
    # Run analysis (patterns will be stored automatically)
    config = AnalysisConfig(
        target_path="./models",
        file_patterns=["*.py"],
        analysis_depth=AnalysisDepth.QUICK
    )
    
    print(f"\nAnalyzing: {config.target_path}")
    result = coordinator.analyze_codebase(config, project_id="demo_project")
    
    # Retrieve stored patterns
    patterns = memory_bank.retrieve_patterns("demo_project")
    
    print(f"\n{'Stored Patterns':=^80}")
    print(f"Total patterns: {len(patterns)}")
    
    for pattern in patterns:
        print(f"\nPattern: {pattern.description}")
        print(f"  Type: {pattern.pattern_type}")
        print(f"  Confidence: {pattern.confidence:.2f}")
        if pattern.examples:
            print(f"  Examples: {', '.join(pattern.examples[:3])}")
    
    # Clean up demo database
    import os
    if os.path.exists("demo_memory_bank.db"):
        os.remove("demo_memory_bank.db")


def demo_review_report():
    """Demonstrate review report generation."""
    print("\n" + "=" * 80)
    print("Demo: Review Report Generation")
    print("=" * 80)
    
    coordinator = CoordinatorAgent()
    
    # Run analysis
    config = AnalysisConfig(
        target_path="./storage",
        file_patterns=["*.py"],
        analysis_depth=AnalysisDepth.STANDARD
    )
    
    print(f"\nAnalyzing: {config.target_path}")
    result = coordinator.analyze_codebase(config)
    
    # Generate review report
    report = coordinator.generate_review_report(result)
    
    print(f"\n{'Review Report':=^80}")
    print(report[:1000])  # Print first 1000 characters
    print("\n... (truncated)")
    
    # Optionally save to file
    report_path = "demo_review_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nFull report saved to: {report_path}")


def demo_session_management():
    """Demonstrate pause/resume functionality."""
    print("\n" + "=" * 80)
    print("Demo: Session Management (Pause/Resume)")
    print("=" * 80)
    
    session_manager = SessionManager(sessions_dir=".demo_sessions")
    coordinator = CoordinatorAgent(session_manager=session_manager)
    
    # Create a session
    config = AnalysisConfig(
        target_path="./tools",
        file_patterns=["*.py"],
        analysis_depth=AnalysisDepth.STANDARD
    )
    
    print("\nStarting analysis...")
    result = coordinator.analyze_codebase(config, session_id="demo_session_001")
    
    print(f"Session ID: {result.session_id}")
    print(f"Status: Completed")
    
    # Check session status
    session_state = coordinator.get_analysis_status(result.session_id)
    if session_state:
        print(f"\nSession details:")
        print(f"  Status: {session_state.status}")
        print(f"  Files processed: {len(session_state.processed_files)}")
        print(f"  Checkpoint time: {session_state.checkpoint_time}")


def main():
    """Run all demos."""
    print("\n" + "=" * 80)
    print("COORDINATOR AGENT DEMONSTRATION")
    print("=" * 80)
    
    try:
        # Run demos
        demo_basic_analysis()
        demo_yaml_config()
        demo_memory_bank_integration()
        demo_review_report()
        demo_session_management()
        
        print("\n" + "=" * 80)
        print("All demos completed successfully!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
