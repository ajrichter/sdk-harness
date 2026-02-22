"""Shared pytest fixtures for all tests."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Load sample migration configuration."""
    return {
        "project_name": "test-migration",
        "work_dir": "/tmp/test-workspace",
        "repositories": [
            {
                "name": "test-frontend",
                "url": "https://github.com/test/frontend.git",
                "branch": "main",
                "language": "javascript",
            }
        ],
        "rest_endpoints": [
            {
                "id": "get-user",
                "method": "GET",
                "path": "/api/v1/users/{id}",
                "patterns": ["fetch('/api/v1/users/'", "axios.get('/api/v1/users/'"],
            }
        ],
        "attribute_mappings": [
            {
                "endpoint_id": "get-user",
                "rest_attribute": "user_name",
                "graphql_field": "userName",
                "graphql_type": "User",
            }
        ],
        "graphql_endpoint": "https://api.example.com/graphql",
        "graphql_schema_path": "./schema.graphql",
        "options": {
            "dry_run": False,
            "create_branches": True,
            "branch_prefix": "migration/rest-to-graphql",
            "max_concurrent_repos": 2,
            "model": "claude-sonnet-4-5-20250929",
            "max_turns_per_phase": 50,
        },
    }


@pytest.fixture
def sample_discovery_result() -> Dict[str, Any]:
    """Sample discovery phase output."""
    return {
        "phase": "discovery",
        "timestamp": "2025-01-01T00:00:00Z",
        "usages": [
            {
                "endpoint_id": "get-user",
                "repo": "test-frontend",
                "file": "src/api.js",
                "line": 42,
                "snippet": "const user = await fetch('/api/v1/users/{id}');",
                "language": "javascript",
            }
        ],
    }


@pytest.fixture
def sample_narrowed_result() -> Dict[str, Any]:
    """Sample narrowing phase output."""
    return {
        "phase": "narrowing",
        "timestamp": "2025-01-01T00:00:00Z",
        "narrowed_usages": [
            {
                "endpoint_id": "get-user",
                "repo": "test-frontend",
                "file": "src/api.js",
                "line": 42,
                "snippet": "const user = await fetch('/api/v1/users/{id}');",
                "language": "javascript",
                "matched_mappings": ["user_name"],
                "complexity": "low",
            }
        ],
    }


@pytest.fixture
def sample_generated_result() -> Dict[str, Any]:
    """Sample generation phase output."""
    return {
        "phase": "generation",
        "timestamp": "2025-01-01T00:00:00Z",
        "generated_migrations": [
            {
                "endpoint_id": "get-user",
                "repo": "test-frontend",
                "file": "src/api.js",
                "graphql_query": """
                    query GetUser($id: ID!) {
                        user(id: $id) {
                            id
                            userName
                        }
                    }
                """,
                "new_code": """
                    import { useQuery } from '@apollo/client';
                    const { data } = useQuery(GET_USER, { variables: { id } });
                    const user = data?.user;
                """,
                "imports": ["import { useQuery } from '@apollo/client';"],
            }
        ],
    }
