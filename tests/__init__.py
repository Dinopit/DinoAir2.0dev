"""
DinoAir 2.0 Test Suite
======================

Organized test structure:
- unit/: Unit tests for individual components
- integration/: Integration tests for component interactions
- debug/: Debug scripts and diagnostic tools

Run tests with:
    pytest tests/unit/
    pytest tests/integration/
    pytest tests/
"""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Test configuration
pytest_plugins = []

# Common test fixtures can be defined here
@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for testing."""
    return tmp_path / "test.db"

@pytest.fixture
def sample_note():
    """Provide a sample note for testing."""
    from src.models.note import Note
    return Note(
        title="Test Note",
        content="This is a test note content",
        tags=["test", "sample"]
    )