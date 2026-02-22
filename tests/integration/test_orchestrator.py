"""Integration tests for orchestrator."""

import json
from pathlib import Path

import pytest

from migration_harness.config import load_config
from migration_harness.orchestrator import Orchestrator
from migration_harness.state.manager import StateManager


def test_orchestrator_initialization(sample_config, temp_dir):
    """Test orchestrator initialization."""
    sample_config["work_dir"] = str(temp_dir)
    orchestrator = Orchestrator(load_config(sample_config))

    assert orchestrator.config.project_name == "test-migration"
    assert isinstance(orchestrator.state_manager, StateManager)


def test_state_manager_integration(sample_config, temp_dir):
    """Test state manager with orchestrator."""
    sample_config["work_dir"] = str(temp_dir)
    orchestrator = Orchestrator(load_config(sample_config))

    discovery_result = {"phase": "discovery", "usages": []}
    orchestrator.state_manager.save_discovery_result(discovery_result)

    retrieved = orchestrator.state_manager.get_discovery_result()
    assert retrieved == discovery_result


def test_progress_tracking(sample_config, temp_dir):
    """Test progress tracking with orchestrator."""
    sample_config["work_dir"] = str(temp_dir)
    orchestrator = Orchestrator(load_config(sample_config))

    orchestrator.progress_tracker.init_progress(sample_config["project_name"])
    orchestrator.progress_tracker.mark_phase_started("discovery")

    progress = orchestrator.get_pipeline_status()
    assert progress is not None
    assert progress["project"] == sample_config["project_name"]
    assert "discovery" in progress["phases"]


def test_config_from_fixture(temp_dir):
    """Test loading config from fixture file."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_config.json"
    config = load_config(str(fixture_path))

    assert config.project_name == "test-rest-to-graphql"
    assert len(config.repositories) == 2
    assert len(config.rest_endpoints) == 2


def test_discovery_fixture_loading(temp_dir):
    """Test loading discovery fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_discovery.json"
    with open(fixture_path) as f:
        discovery = json.load(f)

    assert discovery["phase"] == "discovery"
    assert len(discovery["usages"]) == 5


def test_narrowed_fixture_loading(temp_dir):
    """Test loading narrowed fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_narrowed.json"
    with open(fixture_path) as f:
        narrowed = json.load(f)

    assert narrowed["phase"] == "narrowing"
    assert len(narrowed["narrowed_usages"]) == 3


def test_generated_fixture_loading(temp_dir):
    """Test loading generated fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "sample_generated.json"
    with open(fixture_path) as f:
        generated = json.load(f)

    assert generated["phase"] == "generation"
    assert len(generated["generated_migrations"]) == 3
