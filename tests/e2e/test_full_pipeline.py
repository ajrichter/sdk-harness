"""End-to-end tests for the full pipeline."""

import json
from pathlib import Path

import pytest

from migration_harness.config import load_config
from migration_harness.orchestrator import Orchestrator
from migration_harness.pipeline.gates import (
    validate_discovery_gate,
    validate_generation_gate,
    validate_narrowing_gate,
)


@pytest.mark.e2e
def test_full_pipeline_with_fixtures(temp_dir):
    """Test full pipeline flow with fixture data."""
    # Load fixture config
    config_fixture = Path(__file__).parent.parent / "fixtures" / "sample_config.json"
    config = load_config(str(config_fixture))
    config.work_dir = str(temp_dir)

    # Create orchestrator
    orchestrator = Orchestrator(config)

    # Initialize progress
    orchestrator.progress_tracker.init_progress(config.project_name)

    # Simulate discovery phase
    discovery_fixture = Path(__file__).parent.parent / "fixtures" / "sample_discovery.json"
    with open(discovery_fixture) as f:
        discovery_result = json.load(f)

    validate_discovery_gate(discovery_result)
    orchestrator.state_manager.save_discovery_result(discovery_result)
    orchestrator.progress_tracker.mark_phase_completed("discovery", "Found 5 usages")

    # Simulate narrowing phase
    narrowed_fixture = Path(__file__).parent.parent / "fixtures" / "sample_narrowed.json"
    with open(narrowed_fixture) as f:
        narrowed_result = json.load(f)

    validate_narrowing_gate(narrowed_result)
    orchestrator.state_manager.save_narrowing_result(narrowed_result)
    orchestrator.progress_tracker.mark_phase_completed("narrowing", "Filtered to 3 usages")

    # Simulate generation phase
    generated_fixture = Path(__file__).parent.parent / "fixtures" / "sample_generated.json"
    with open(generated_fixture) as f:
        generated_result = json.load(f)

    validate_generation_gate(generated_result)
    orchestrator.state_manager.save_generation_result(generated_result)
    orchestrator.progress_tracker.mark_phase_completed(
        "generation", "Generated 3 migrations"
    )

    # Verify pipeline state
    progress = orchestrator.get_pipeline_status()
    assert progress is not None
    assert progress["project"] == config.project_name
    assert len(progress["phases"]) == 3
    assert progress["phases"]["discovery"]["status"] == "completed"
    assert progress["phases"]["narrowing"]["status"] == "completed"
    assert progress["phases"]["generation"]["status"] == "completed"

    # Verify state persistence
    retrieved_discovery = orchestrator.state_manager.get_discovery_result()
    assert retrieved_discovery is not None
    assert retrieved_discovery["phase"] == "discovery"
    assert len(retrieved_discovery["usages"]) == 5

    retrieved_narrowed = orchestrator.state_manager.get_narrowing_result()
    assert retrieved_narrowed is not None
    assert retrieved_narrowed["phase"] == "narrowing"
    assert len(retrieved_narrowed["narrowed_usages"]) == 3

    retrieved_generated = orchestrator.state_manager.get_generation_result()
    assert retrieved_generated is not None
    assert retrieved_generated["phase"] == "generation"
    assert len(retrieved_generated["generated_migrations"]) == 3


@pytest.mark.e2e
def test_pipeline_failure_handling(temp_dir):
    """Test pipeline error handling."""
    config_fixture = Path(__file__).parent.parent / "fixtures" / "sample_config.json"
    config = load_config(str(config_fixture))
    config.work_dir = str(temp_dir)

    orchestrator = Orchestrator(config)
    orchestrator.progress_tracker.init_progress(config.project_name)

    # Simulate phase failure
    orchestrator.progress_tracker.mark_phase_started("discovery")
    orchestrator.progress_tracker.mark_phase_failed("discovery", "Repository not found")

    progress = orchestrator.get_pipeline_status()
    assert progress["phases"]["discovery"]["status"] == "failed"
    assert progress["phases"]["discovery"]["error"] == "Repository not found"


@pytest.mark.e2e
def test_pipeline_with_sessions(temp_dir):
    """Test pipeline with session logging."""
    config_fixture = Path(__file__).parent.parent / "fixtures" / "sample_config.json"
    config = load_config(str(config_fixture))
    config.work_dir = str(temp_dir)

    orchestrator = Orchestrator(config)
    orchestrator.progress_tracker.init_progress(config.project_name)

    # Simulate phase with session logs
    orchestrator.progress_tracker.mark_phase_started("discovery")
    orchestrator.progress_tracker.add_session_log(
        "discovery", "session_abc123", "claude-sonnet-4-5-20250929", 10
    )

    progress = orchestrator.get_pipeline_status()
    assert "sessions" in progress["phases"]["discovery"]
    assert len(progress["phases"]["discovery"]["sessions"]) == 1
    assert progress["phases"]["discovery"]["sessions"][0]["session_id"] == "session_abc123"
