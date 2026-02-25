"""Tests for validation gates."""

import pytest

from migration_harness.pipeline.gates import (
    GateError,
    validate_discovery_gate,
    validate_narrowing_gate,
    validate_generation_gate,
)


def test_discovery_gate_valid(sample_discovery_result):
    """Test discovery gate with valid result."""
    validate_discovery_gate(sample_discovery_result)  # Should not raise


def test_discovery_gate_empty_usages():
    """Test discovery gate with empty usages."""
    result = {"phase": "discovery", "usages": []}
    with pytest.raises(GateError):
        validate_discovery_gate(result)


def test_discovery_gate_missing_phase():
    """Test discovery gate with missing phase."""
    result = {"usages": []}
    with pytest.raises(GateError):
        validate_discovery_gate(result)


def test_narrowing_gate_valid(sample_narrowed_result):
    """Test narrowing gate with valid result."""
    validate_narrowing_gate(sample_narrowed_result)  # Should not raise


def test_narrowing_gate_empty_usages():
    """Test narrowing gate with empty usages."""
    result = {"phase": "narrowing", "narrowed_usages": []}
    with pytest.raises(GateError):
        validate_narrowing_gate(result)


def test_generation_gate_valid(sample_generated_result):
    """Test generation gate with valid result."""
    validate_generation_gate(sample_generated_result)  # Should not raise


def test_generation_gate_empty_migrations():
    """Test generation gate with empty migrations."""
    result = {"phase": "generation", "generated_migrations": []}
    with pytest.raises(GateError):
        validate_generation_gate(result)


def test_generation_gate_missing_query():
    """Test generation gate with missing graphql_query."""
    result = {
        "phase": "generation",
        "generated_migrations": [
            {
                "endpoint_id": "test",
                "repo": "test-repo",
                "file": "test.js",
                "graphql_query": "",  # Empty query
                "new_code": "code",
                "imports": [],
            }
        ],
    }
    with pytest.raises(GateError):
        validate_generation_gate(result)
