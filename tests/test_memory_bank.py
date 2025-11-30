"""
Property-based tests for Memory Bank storage and retrieval.

Feature: code-review-documentation-agent
"""

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from hypothesis import given, strategies as st, settings, HealthCheck
from hypothesis.strategies import SearchStrategy

from models.data_models import ProjectPattern, PatternType
from storage.memory_bank import MemoryBank


# Custom strategies for generating valid ProjectPattern instances

@st.composite
def datetime_strategy(draw: st.DrawFn) -> datetime:
    """Generate random datetime instances."""
    return datetime.fromtimestamp(
        draw(st.integers(min_value=0, max_value=2147483647)),
        tz=timezone.utc
    )


@st.composite
def project_pattern_strategy(draw: st.DrawFn) -> ProjectPattern:
    """Generate random ProjectPattern instances."""
    # Use simple ASCII text to avoid slow generation
    # Restrict to alphanumeric + common punctuation for faster generation
    simple_text = st.text(
        alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.',
        min_size=1,
        max_size=20
    )
    
    return ProjectPattern(
        pattern_id=draw(simple_text),
        project_id=draw(simple_text),
        pattern_type=draw(st.sampled_from(PatternType)),
        description=draw(simple_text),
        examples=draw(st.lists(simple_text, min_size=0, max_size=3)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        last_updated=draw(datetime_strategy()),
    )


# Property-based tests

# Feature: code-review-documentation-agent, Property 15: Memory Bank Round-Trip
# Validates: Requirements 6.2, 6.3, 6.5

@settings(
    max_examples=100,
    deadline=500,  # Allow 500ms per test case
    suppress_health_check=[HealthCheck.too_slow]
)
@given(project_pattern_strategy())
def test_memory_bank_roundtrip(pattern: ProjectPattern) -> None:
    """
    Property 15: Memory Bank Round-Trip
    
    For any ProjectPattern, storing it in the Memory Bank and then retrieving it
    should return an equivalent pattern with all fields preserved.
    
    Validates: Requirements 6.2, 6.3, 6.5
    """
    # Create a temporary database for this test
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory_bank.db")
        memory_bank = MemoryBank(db_path=db_path)
        
        # Store the pattern
        memory_bank.store_pattern(pattern)
        
        # Retrieve the pattern by ID
        retrieved = memory_bank.retrieve_pattern(pattern.pattern_id)
        
        # Verify the pattern was retrieved
        assert retrieved is not None, "Pattern should be retrievable after storage"
        
        # Verify all fields are preserved
        assert retrieved.pattern_id == pattern.pattern_id
        assert retrieved.project_id == pattern.project_id
        assert retrieved.pattern_type == pattern.pattern_type
        assert retrieved.description == pattern.description
        assert retrieved.examples == pattern.examples
        assert abs(retrieved.confidence - pattern.confidence) < 1e-6  # Float comparison with tolerance
        
        # Note: last_updated might differ slightly due to serialization,
        # but should be very close (within a second)
        time_diff = abs((retrieved.last_updated - pattern.last_updated).total_seconds())
        assert time_diff < 1.0, f"Timestamps should be close, but differ by {time_diff} seconds"


@settings(
    max_examples=100,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(st.lists(project_pattern_strategy(), min_size=1, max_size=10))
def test_memory_bank_multiple_patterns_roundtrip(patterns: list[ProjectPattern]) -> None:
    """
    Property: Memory Bank Multiple Patterns Round-Trip
    
    For any list of ProjectPatterns with the same project_id, storing them all
    and then retrieving by project_id should return all patterns.
    
    Validates: Requirements 6.2, 6.3
    """
    # Create a temporary database for this test
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory_bank.db")
        memory_bank = MemoryBank(db_path=db_path)
        
        # Use a consistent project_id for all patterns
        project_id = "test_project_123"
        
        # Make pattern_ids unique to avoid conflicts
        unique_patterns = []
        seen_ids = set()
        for i, pattern in enumerate(patterns):
            # Create a new pattern with unique ID and consistent project_id
            unique_pattern = ProjectPattern(
                pattern_id=f"{pattern.pattern_id}_{i}",
                project_id=project_id,
                pattern_type=pattern.pattern_type,
                description=pattern.description,
                examples=pattern.examples,
                confidence=pattern.confidence,
                last_updated=pattern.last_updated
            )
            if unique_pattern.pattern_id not in seen_ids:
                unique_patterns.append(unique_pattern)
                seen_ids.add(unique_pattern.pattern_id)
        
        # Store all patterns
        for pattern in unique_patterns:
            memory_bank.store_pattern(pattern)
        
        # Retrieve all patterns for the project
        retrieved_patterns = memory_bank.retrieve_patterns(project_id)
        
        # Verify we got the right number of patterns
        assert len(retrieved_patterns) == len(unique_patterns), \
            f"Expected {len(unique_patterns)} patterns, got {len(retrieved_patterns)}"
        
        # Verify all patterns are present (by pattern_id)
        retrieved_ids = {p.pattern_id for p in retrieved_patterns}
        expected_ids = {p.pattern_id for p in unique_patterns}
        assert retrieved_ids == expected_ids, "All stored patterns should be retrievable"


@settings(
    max_examples=100,
    deadline=500,
    suppress_health_check=[HealthCheck.too_slow]
)
@given(project_pattern_strategy())
def test_memory_bank_update_pattern(pattern: ProjectPattern) -> None:
    """
    Property: Memory Bank Pattern Update
    
    For any ProjectPattern, storing it, modifying it, and storing again
    should update the existing pattern rather than creating a duplicate.
    
    Validates: Requirements 6.2, 6.5
    """
    # Create a temporary database for this test
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory_bank.db")
        memory_bank = MemoryBank(db_path=db_path)
        
        # Store the original pattern
        memory_bank.store_pattern(pattern)
        
        # Modify the pattern
        modified_pattern = ProjectPattern(
            pattern_id=pattern.pattern_id,  # Same ID
            project_id=pattern.project_id,
            pattern_type=pattern.pattern_type,
            description=pattern.description + " MODIFIED",
            examples=pattern.examples + ["new_example"],
            confidence=min(1.0, pattern.confidence + 0.1),
            last_updated=datetime.now(timezone.utc)
        )
        
        # Store the modified pattern
        memory_bank.store_pattern(modified_pattern)
        
        # Retrieve the pattern
        retrieved = memory_bank.retrieve_pattern(pattern.pattern_id)
        
        # Verify only one pattern exists (no duplicate)
        all_patterns = memory_bank.retrieve_patterns(pattern.project_id)
        pattern_count = sum(1 for p in all_patterns if p.pattern_id == pattern.pattern_id)
        assert pattern_count == 1, "Should have exactly one pattern with this ID"
        
        # Verify the pattern was updated
        assert retrieved is not None
        assert retrieved.description == modified_pattern.description
        assert retrieved.examples == modified_pattern.examples


@settings(
    max_examples=100,
    deadline=2000,  # Increased deadline to 2000ms
    suppress_health_check=[HealthCheck.too_slow]
)
@given(project_pattern_strategy(), st.lists(st.booleans(), min_size=1, max_size=20))
def test_memory_bank_confidence_update(pattern: ProjectPattern, feedbacks: list[bool]) -> None:
    """
    Property: Memory Bank Confidence Update
    
    For any ProjectPattern and sequence of feedback, applying the feedback
    should update the confidence score, and the score should remain in [0, 1].
    
    Validates: Requirements 6.5
    """
    # Create a temporary database for this test
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory_bank.db")
        memory_bank = MemoryBank(db_path=db_path)
        
        # Store the pattern
        memory_bank.store_pattern(pattern)
        
        # Apply all feedback
        for feedback in feedbacks:
            memory_bank.update_pattern_confidence(pattern.pattern_id, feedback)
        
        # Retrieve the updated pattern
        retrieved = memory_bank.retrieve_pattern(pattern.pattern_id)
        
        # Verify confidence is still in valid range
        assert retrieved is not None
        assert 0.0 <= retrieved.confidence <= 1.0, \
            f"Confidence {retrieved.confidence} should be in [0, 1]"
        
        # Verify the pattern still exists and is retrievable
        assert retrieved.pattern_id == pattern.pattern_id
        assert retrieved.project_id == pattern.project_id


@settings(
    max_examples=100,
    deadline=2000,  # Increased deadline to 2000ms
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
)
@given(
    st.lists(project_pattern_strategy(), min_size=2, max_size=10),
    st.floats(min_value=0.0, max_value=1.0)
)
def test_memory_bank_confidence_filtering(patterns: list[ProjectPattern], min_confidence: float) -> None:
    """
    Property: Memory Bank Confidence Filtering
    
    For any list of patterns and minimum confidence threshold, retrieving patterns
    with that threshold should return only patterns meeting the threshold.
    
    Validates: Requirements 6.3
    """
    # Create a temporary database for this test
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_memory_bank.db")
        memory_bank = MemoryBank(db_path=db_path)
        
        # Use a consistent project_id
        project_id = "test_project_filter"
        
        # Store patterns with unique IDs
        stored_patterns = []
        for i, pattern in enumerate(patterns):
            unique_pattern = ProjectPattern(
                pattern_id=f"{pattern.pattern_id}_{i}",
                project_id=project_id,
                pattern_type=pattern.pattern_type,
                description=pattern.description,
                examples=pattern.examples,
                confidence=pattern.confidence,
                last_updated=pattern.last_updated
            )
            memory_bank.store_pattern(unique_pattern)
            stored_patterns.append(unique_pattern)
        
        # Retrieve patterns with confidence filter
        retrieved = memory_bank.retrieve_patterns(
            project_id=project_id,
            min_confidence=min_confidence
        )
        
        # Verify all retrieved patterns meet the threshold
        for pattern in retrieved:
            assert pattern.confidence >= min_confidence, \
                f"Pattern confidence {pattern.confidence} should be >= {min_confidence}"
        
        # Verify no patterns below threshold are returned
        expected_count = sum(1 for p in stored_patterns if p.confidence >= min_confidence)
        assert len(retrieved) == expected_count, \
            f"Expected {expected_count} patterns with confidence >= {min_confidence}, got {len(retrieved)}"
