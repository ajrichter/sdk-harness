"""Tests for progress tracking."""

from pathlib import Path

import pytest

from migration_harness.state.progress import ProgressTracker


@pytest.fixture
def progress_tracker(temp_dir):
    """Create a ProgressTracker instance with temp directory."""
    return ProgressTracker(work_dir=str(temp_dir))


def test_init_progress(progress_tracker):
    """Test initializing progress tracking."""
    progress_tracker.init_progress("test-migration")
    progress = progress_tracker.read_progress()

    assert progress["project"] == "test-migration"
    assert progress["phases"] == {}
    assert "started_at" in progress


def test_mark_phase_started(progress_tracker):
    """Test marking a phase as started."""
    progress_tracker.init_progress("test-migration")
    progress_tracker.mark_phase_started("discovery")
    progress = progress_tracker.read_progress()

    assert "discovery" in progress["phases"]
    assert progress["phases"]["discovery"]["status"] == "in_progress"
    assert "started_at" in progress["phases"]["discovery"]


def test_mark_phase_completed(progress_tracker):
    """Test marking a phase as completed."""
    progress_tracker.init_progress("test-migration")
    progress_tracker.mark_phase_started("discovery")
    progress_tracker.mark_phase_completed("discovery", "10 endpoints found")
    progress = progress_tracker.read_progress()

    phase = progress["phases"]["discovery"]
    assert phase["status"] == "completed"
    assert phase["summary"] == "10 endpoints found"
    assert "completed_at" in phase


def test_mark_phase_failed(progress_tracker):
    """Test marking a phase as failed."""
    progress_tracker.init_progress("test-migration")
    progress_tracker.mark_phase_started("discovery")
    progress_tracker.mark_phase_failed("discovery", "Repository not found")
    progress = progress_tracker.read_progress()

    phase = progress["phases"]["discovery"]
    assert phase["status"] == "failed"
    assert phase["error"] == "Repository not found"


def test_add_session_log(progress_tracker):
    """Test adding session log."""
    progress_tracker.init_progress("test-migration")
    progress_tracker.mark_phase_started("discovery")
    progress_tracker.add_session_log("discovery", "session_123", "claude-sonnet-4-5")
    progress = progress_tracker.read_progress()

    phase = progress["phases"]["discovery"]
    assert "sessions" in phase
    assert len(phase["sessions"]) == 1
    assert phase["sessions"][0]["session_id"] == "session_123"
    assert phase["sessions"][0]["model"] == "claude-sonnet-4-5"


def test_progress_persistence(temp_dir):
    """Test that progress is persisted to disk."""
    tracker1 = ProgressTracker(work_dir=str(temp_dir))
    tracker1.init_progress("test-project")
    tracker1.mark_phase_started("discovery")

    # Create new instance and read
    tracker2 = ProgressTracker(work_dir=str(temp_dir))
    progress = tracker2.read_progress()

    assert progress["project"] == "test-project"
    assert "discovery" in progress["phases"]


def test_read_nonexistent_progress(progress_tracker):
    """Test reading progress when file doesn't exist."""
    progress = progress_tracker.read_progress()
    assert progress is None


def test_progress_file_format(progress_tracker):
    """Test that progress file has correct format."""
    progress_tracker.init_progress("test-migration")
    progress_tracker.mark_phase_started("discovery")

    progress_file = Path(progress_tracker.progress_file)
    assert progress_file.exists()

    # Verify it's valid JSON
    content = progress_file.read_text()
    data = __import__("json").loads(content)
    assert "project" in data
    assert "phases" in data
