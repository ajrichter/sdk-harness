"""Tests for configuration loading."""

import json
from pathlib import Path

import pytest

from migration_harness.config import load_config
from migration_harness.schema import Config


def test_load_config_from_dict(sample_config):
    """Test loading config from dictionary."""
    config = load_config(sample_config)
    assert isinstance(config, Config)
    assert config.project_name == "test-migration"


def test_load_config_from_file(sample_config, tmp_path):
    """Test loading config from JSON file."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(sample_config))

    config = load_config(str(config_file))
    assert isinstance(config, Config)
    assert config.project_name == "test-migration"


def test_load_config_validates_schema(tmp_path):
    """Test that config loading validates schema."""
    invalid_config = {"project_name": "test"}  # Missing required fields
    config_file = tmp_path / "invalid.json"
    config_file.write_text(json.dumps(invalid_config))

    with pytest.raises(ValueError):
        load_config(str(config_file))


def test_load_config_file_not_found():
    """Test that loading from non-existent file raises error."""
    with pytest.raises((FileNotFoundError, ValueError)):
        load_config("/nonexistent/path/config.json")
