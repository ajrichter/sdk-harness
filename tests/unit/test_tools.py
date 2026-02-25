"""Tests for ToolRegistry — the MCP tool bridge."""

import json
import pytest

from migration_harness.schema import Config
from migration_harness.state.manager import StateManager
from migration_harness.tools.registry import ToolRegistry


@pytest.fixture
def tool_registry(sample_config, temp_dir) -> ToolRegistry:
    """Create a ToolRegistry with sample config and state manager."""
    sample_config["work_dir"] = str(temp_dir)
    config = Config(**sample_config)
    state_manager = StateManager(str(temp_dir))
    return ToolRegistry(config, state_manager)


# ══════════════════════════════════════════════════════════════════════════════
# T1 — Config retrieval tools
# ══════════════════════════════════════════════════════════════════════════════

def test_get_config_returns_full_dict(tool_registry):
    """get_config() must return the entire config as JSON-serializable dict."""
    config_dict = tool_registry.get_config()

    assert isinstance(config_dict, dict)
    assert config_dict["project_name"] == "test-migration"
    assert "repositories" in config_dict
    assert "rest_endpoints" in config_dict
    assert "options" in config_dict


def test_get_endpoints_returns_list(tool_registry):
    """get_endpoints() returns REST endpoints in a consistent format."""
    endpoints = tool_registry.get_endpoints()

    assert "endpoints" in endpoints
    assert isinstance(endpoints["endpoints"], list)
    assert len(endpoints["endpoints"]) > 0
    assert "id" in endpoints["endpoints"][0]
    assert "method" in endpoints["endpoints"][0]
    assert "path" in endpoints["endpoints"][0]


def test_get_mappings_returns_list(tool_registry):
    """get_mappings() returns attribute mappings in a consistent format."""
    mappings = tool_registry.get_mappings()

    assert "mappings" in mappings
    assert isinstance(mappings["mappings"], list)
    assert len(mappings["mappings"]) > 0
    assert "endpoint_id" in mappings["mappings"][0]
    assert "rest_attribute" in mappings["mappings"][0]
    assert "graphql_field" in mappings["mappings"][0]


def test_get_graphql_schema_reads_file(tool_registry, temp_dir):
    """get_graphql_schema() reads and returns file contents."""
    schema_path = temp_dir / "schema.graphql"
    schema_content = "type Query { user(id: ID!): User }"
    schema_path.write_text(schema_content)

    # Update config to point at our test schema
    tool_registry.config.graphql_schema_path = str(schema_path)

    result = tool_registry.get_graphql_schema()
    assert result == schema_content


def test_get_graphql_schema_raises_if_missing(tool_registry):
    """get_graphql_schema() raises FileNotFoundError if file doesn't exist."""
    tool_registry.config.graphql_schema_path = "/nonexistent/schema.graphql"

    with pytest.raises(FileNotFoundError):
        tool_registry.get_graphql_schema()


# ══════════════════════════════════════════════════════════════════════════════
# T2 — Result persistence tools (save/get round-trip)
# ══════════════════════════════════════════════════════════════════════════════

def test_save_and_get_discovery_result_roundtrip(tool_registry, sample_discovery_result):
    """Discovery save/get is a true round-trip — what you save is what you get."""
    tool_registry.save_discovery_result(sample_discovery_result)
    retrieved = tool_registry.get_discovery_result()

    assert retrieved == sample_discovery_result
    assert retrieved["phase"] == "discovery"


def test_save_and_get_narrowing_result_roundtrip(tool_registry, sample_narrowed_result):
    """Narrowing save/get is a true round-trip."""
    tool_registry.save_narrowing_result(sample_narrowed_result)
    retrieved = tool_registry.get_narrowing_result()

    assert retrieved == sample_narrowed_result
    assert retrieved["phase"] == "narrowing"


def test_save_and_get_generation_result_roundtrip(tool_registry, sample_generated_result):
    """Generation save/get is a true round-trip."""
    tool_registry.save_generation_result(sample_generated_result)
    retrieved = tool_registry.get_generation_result()

    assert retrieved == sample_generated_result
    assert retrieved["phase"] == "generation"


def test_get_result_returns_none_if_never_saved(tool_registry):
    """get_*_result() returns None if save was never called, not error."""
    result = tool_registry.get_discovery_result()
    assert result is None


def test_save_returns_confirmation(tool_registry, sample_discovery_result):
    """save_*_result() returns a confirmation dict with status."""
    response = tool_registry.save_discovery_result(sample_discovery_result)

    assert isinstance(response, dict)
    assert response["status"] == "saved"
    assert response["phase"] == "discovery"


def test_migration_result_save_and_get(tool_registry):
    """Migration results persist correctly."""
    migration_result = {
        "phase": "migration",
        "timestamp": "2025-01-01T00:00:00Z",
        "applied_migrations": [
            {
                "endpoint_id": "test",
                "repo": "test-repo",
                "file": "test.java",
                "applied": True,
                "diff": "--- a/test.java",
                "branch": "migration/test",
                "commit": "abc123",
            }
        ],
    }
    tool_registry.save_migration_result(migration_result)
    retrieved = tool_registry.get_migration_result()

    assert retrieved == migration_result


def test_validation_result_save_and_get(tool_registry):
    """Validation results persist correctly."""
    validation_result = {
        "phase": "validation",
        "timestamp": "2025-01-01T00:00:00Z",
        "checks": [
            {"check_name": "build", "passed": True, "details": "Build successful"}
        ],
    }
    tool_registry.save_validation_result(validation_result)
    retrieved = tool_registry.get_validation_result()

    assert retrieved == validation_result


# ══════════════════════════════════════════════════════════════════════════════
# T3 — Isolation: save/get for different phases don't interfere
# ══════════════════════════════════════════════════════════════════════════════

def test_save_different_phases_are_isolated(tool_registry, sample_discovery_result, sample_narrowed_result):
    """Saving discovery doesn't overwrite narrowing, and vice versa."""
    tool_registry.save_discovery_result(sample_discovery_result)
    tool_registry.save_narrowing_result(sample_narrowed_result)

    # Both should still be present
    discovery = tool_registry.get_discovery_result()
    narrowing = tool_registry.get_narrowing_result()

    assert discovery["phase"] == "discovery"
    assert narrowing["phase"] == "narrowing"
    assert discovery["usages"] != narrowing["narrowed_usages"]


# ══════════════════════════════════════════════════════════════════════════════
# T4 — JSON serialization (tools must return JSON-compatible dicts)
# ══════════════════════════════════════════════════════════════════════════════

def test_all_tool_returns_are_json_serializable(tool_registry):
    """Every tool method must return JSON-serializable dict."""
    results = [
        tool_registry.get_config(),
        tool_registry.get_endpoints(),
        tool_registry.get_mappings(),
    ]

    for result in results:
        # This will raise TypeError if not JSON-serializable
        json_str = json.dumps(result)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
