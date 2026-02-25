"""Tests for state management."""

import json
from pathlib import Path

import pytest

from migration_harness.state.manager import StateManager


@pytest.fixture
def state_manager(temp_dir):
    """Create a StateManager instance with temp directory."""
    return StateManager(work_dir=str(temp_dir))


def test_save_and_get_discovery_result(state_manager, sample_discovery_result):
    """Test saving and retrieving discovery result."""
    state_manager.save_discovery_result(sample_discovery_result)
    result = state_manager.get_discovery_result()

    assert result == sample_discovery_result
    assert result["phase"] == "discovery"


def test_save_and_get_narrowing_result(state_manager, sample_narrowed_result):
    """Test saving and retrieving narrowing result."""
    state_manager.save_narrowing_result(sample_narrowed_result)
    result = state_manager.get_narrowing_result()

    assert result == sample_narrowed_result
    assert result["phase"] == "narrowing"


def test_save_and_get_generation_result(state_manager, sample_generated_result):
    """Test saving and retrieving generation result."""
    state_manager.save_generation_result(sample_generated_result)
    result = state_manager.get_generation_result()

    assert result == sample_generated_result
    assert result["phase"] == "generation"


def test_get_nonexistent_result(state_manager):
    """Test getting a result that doesn't exist."""
    result = state_manager.get_discovery_result()
    assert result is None


def test_save_creates_work_dir(tmp_path):
    """Test that save creates work directory if needed."""
    work_dir = tmp_path / "new_dir"
    assert not work_dir.exists()

    state_manager = StateManager(work_dir=str(work_dir))
    state_manager.save_discovery_result({"phase": "discovery", "usages": []})

    assert work_dir.exists()


def test_file_persistence(temp_dir, sample_discovery_result):
    """Test that results are persisted to disk."""
    state_manager = StateManager(work_dir=str(temp_dir))
    state_manager.save_discovery_result(sample_discovery_result)

    # Create a new instance to read from disk
    state_manager2 = StateManager(work_dir=str(temp_dir))
    result = state_manager2.get_discovery_result()

    assert result == sample_discovery_result
