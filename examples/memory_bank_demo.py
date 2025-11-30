"""
Demo script for Memory Bank functionality.

This script demonstrates the key features of the Memory Bank:
- Storing patterns
- Retrieving patterns
- Updating patterns
- Confidence scoring with feedback
- Pattern search and filtering
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.memory_bank import MemoryBank
from models.data_models import ProjectPattern, PatternType
from datetime import datetime, timezone
import tempfile
import os


def main():
    # Create a temporary database for demo
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "demo_memory_bank.db")
    
    print("=" * 60)
    print("Memory Bank Demo")
    print("=" * 60)
    
    # Initialize Memory Bank
    memory_bank = MemoryBank(db_path=db_path)
    print(f"\n✓ Initialized Memory Bank at: {db_path}")
    print(f"  Schema version: {memory_bank.get_schema_version()}")
    
    # 1. Store patterns
    print("\n" + "=" * 60)
    print("1. Storing Patterns")
    print("=" * 60)
    
    patterns = [
        ProjectPattern(
            pattern_id="naming_001",
            project_id="my_project",
            pattern_type=PatternType.NAMING,
            description="Use snake_case for function names",
            examples=["calculate_total", "get_user_data", "process_request"],
            confidence=0.9,
            last_updated=datetime.now(timezone.utc)
        ),
        ProjectPattern(
            pattern_id="structure_001",
            project_id="my_project",
            pattern_type=PatternType.STRUCTURE,
            description="Organize code into models, views, controllers",
            examples=["models/user.py", "views/dashboard.py", "controllers/auth.py"],
            confidence=0.85,
            last_updated=datetime.now(timezone.utc)
        ),
        ProjectPattern(
            pattern_id="convention_001",
            project_id="my_project",
            pattern_type=PatternType.CONVENTION,
            description="Always use type hints for function parameters",
            examples=["def process(data: dict) -> bool:", "def calculate(x: int, y: int) -> int:"],
            confidence=0.75,
            last_updated=datetime.now(timezone.utc)
        ),
    ]
    
    for pattern in patterns:
        memory_bank.store_pattern(pattern)
        print(f"  ✓ Stored pattern: {pattern.pattern_id} ({pattern.pattern_type})")
    
    # 2. Retrieve patterns
    print("\n" + "=" * 60)
    print("2. Retrieving Patterns")
    print("=" * 60)
    
    retrieved = memory_bank.retrieve_pattern("naming_001")
    print(f"\n  Retrieved pattern by ID: {retrieved.pattern_id}")
    print(f"    Description: {retrieved.description}")
    print(f"    Confidence: {retrieved.confidence}")
    print(f"    Examples: {retrieved.examples[:2]}")
    
    # 3. Retrieve all patterns for project
    print("\n" + "=" * 60)
    print("3. Retrieving All Patterns for Project")
    print("=" * 60)
    
    all_patterns = memory_bank.retrieve_patterns("my_project")
    print(f"\n  Found {len(all_patterns)} patterns for 'my_project':")
    for p in all_patterns:
        print(f"    - {p.pattern_id}: {p.description[:50]}... (confidence: {p.confidence})")
    
    # 4. Filter by pattern type
    print("\n" + "=" * 60)
    print("4. Filtering by Pattern Type")
    print("=" * 60)
    
    naming_patterns = memory_bank.retrieve_patterns(
        "my_project",
        pattern_type=PatternType.NAMING
    )
    print(f"\n  Found {len(naming_patterns)} NAMING patterns:")
    for p in naming_patterns:
        print(f"    - {p.pattern_id}: {p.description}")
    
    # 5. Filter by confidence
    print("\n" + "=" * 60)
    print("5. Filtering by Confidence Threshold")
    print("=" * 60)
    
    high_confidence = memory_bank.retrieve_patterns(
        "my_project",
        min_confidence=0.8
    )
    print(f"\n  Found {len(high_confidence)} patterns with confidence >= 0.8:")
    for p in high_confidence:
        print(f"    - {p.pattern_id}: confidence={p.confidence}")
    
    # 6. Update pattern confidence with feedback
    print("\n" + "=" * 60)
    print("6. Updating Pattern Confidence with Feedback")
    print("=" * 60)
    
    pattern_id = "convention_001"
    original = memory_bank.retrieve_pattern(pattern_id)
    print(f"\n  Original confidence for {pattern_id}: {original.confidence}")
    
    # Simulate positive feedback
    print("  Applying positive feedback...")
    memory_bank.update_pattern_confidence(pattern_id, feedback_positive=True)
    memory_bank.update_pattern_confidence(pattern_id, feedback_positive=True)
    memory_bank.update_pattern_confidence(pattern_id, feedback_positive=True)
    
    updated = memory_bank.retrieve_pattern(pattern_id)
    print(f"  Updated confidence: {updated.confidence}")
    print(f"  Change: {updated.confidence - original.confidence:+.4f}")
    
    # 7. Search patterns by description
    print("\n" + "=" * 60)
    print("7. Searching Patterns by Description")
    print("=" * 60)
    
    search_results = memory_bank.search_patterns_by_description(
        "my_project",
        "function"
    )
    print(f"\n  Found {len(search_results)} patterns containing 'function':")
    for p in search_results:
        print(f"    - {p.pattern_id}: {p.description}")
    
    # 8. Statistics
    print("\n" + "=" * 60)
    print("8. Memory Bank Statistics")
    print("=" * 60)
    
    total_patterns = memory_bank.get_pattern_count()
    project_patterns = memory_bank.get_pattern_count("my_project")
    all_projects = memory_bank.get_all_projects()
    
    print(f"\n  Total patterns in database: {total_patterns}")
    print(f"  Patterns for 'my_project': {project_patterns}")
    print(f"  Projects in database: {all_projects}")
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print(f"\nDatabase location: {db_path}")
    print("You can inspect the database using SQLite tools.")


if __name__ == "__main__":
    main()
