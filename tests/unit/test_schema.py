"""Tests for schema models."""

import pytest
from pydantic import ValidationError

from migration_harness.schema import (
    AttributeMapping,
    Config,
    ConfigOptions,
    DiscoveryResult,
    EndpointUsage,
    GeneratedMigration,
    GenerationResult,
    NarrowedUsage,
    NarrowingResult,
    Repository,
    RestEndpoint,
    ValidationCheck,
    ValidationResult,
)


class TestRestEndpoint:
    """Tests for RestEndpoint model."""

    def test_valid_rest_endpoint(self):
        """Test creating a valid REST endpoint."""
        endpoint = RestEndpoint(
            id="get-user",
            method="GET",
            path="/api/v1/users/{id}",
            patterns=["fetch('/api/v1/users/", "axios.get('/api/v1/users/"],
        )
        assert endpoint.id == "get-user"
        assert endpoint.method == "GET"
        assert endpoint.path == "/api/v1/users/{id}"
        assert len(endpoint.patterns) == 2

    def test_rest_endpoint_missing_id(self):
        """Test that id is required."""
        with pytest.raises(ValidationError):
            RestEndpoint(
                method="GET",
                path="/api/v1/users/{id}",
                patterns=["fetch('/api/v1/users/"],
            )

    def test_rest_endpoint_empty_patterns(self):
        """Test that patterns cannot be empty."""
        with pytest.raises(ValidationError):
            RestEndpoint(
                id="get-user",
                method="GET",
                path="/api/v1/users/{id}",
                patterns=[],
            )


class TestAttributeMapping:
    """Tests for AttributeMapping model."""

    def test_valid_attribute_mapping(self):
        """Test creating a valid attribute mapping."""
        mapping = AttributeMapping(
            endpoint_id="get-user",
            rest_attribute="user_name",
            graphql_field="userName",
            graphql_type="User",
        )
        assert mapping.endpoint_id == "get-user"
        assert mapping.rest_attribute == "user_name"
        assert mapping.graphql_field == "userName"
        assert mapping.graphql_type == "User"

    def test_attribute_mapping_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            AttributeMapping(
                endpoint_id="get-user",
                rest_attribute="user_name",
            )


class TestRepository:
    """Tests for Repository model."""

    def test_valid_repository(self):
        """Test creating a valid repository."""
        repo = Repository(
            name="frontend",
            url="https://github.com/example/frontend.git",
            branch="main",
            language="javascript",
        )
        assert repo.name == "frontend"
        assert repo.language == "javascript"

    def test_repository_invalid_language(self):
        """Test that language must be valid."""
        with pytest.raises(ValidationError):
            Repository(
                name="frontend",
                url="https://github.com/example/frontend.git",
                branch="main",
                language="rust",  # Not in allowed values
            )


class TestConfigOptions:
    """Tests for ConfigOptions model."""

    def test_valid_config_options(self):
        """Test creating valid config options."""
        options = ConfigOptions(
            dry_run=False,
            create_branches=True,
            branch_prefix="migration/rest-to-graphql",
            max_concurrent_repos=2,
        )
        assert options.dry_run is False
        assert options.create_branches is True

    def test_config_options_defaults(self):
        """Test default values for config options."""
        options = ConfigOptions()
        assert options.dry_run is True
        assert options.create_branches is True


class TestConfig:
    """Tests for Config model."""

    def test_valid_config(self, sample_config):
        """Test creating a valid config."""
        config = Config(**sample_config)
        assert config.project_name == "test-migration"
        assert len(config.repositories) == 1
        assert len(config.rest_endpoints) == 1
        assert len(config.attribute_mappings) == 1

    def test_config_missing_project_name(self, sample_config):
        """Test that project_name is required."""
        del sample_config["project_name"]
        with pytest.raises(ValidationError):
            Config(**sample_config)

    def test_config_empty_repositories(self, sample_config):
        """Test that repositories list cannot be empty."""
        sample_config["repositories"] = []
        with pytest.raises(ValidationError):
            Config(**sample_config)


class TestEndpointUsage:
    """Tests for EndpointUsage model."""

    def test_valid_endpoint_usage(self):
        """Test creating a valid endpoint usage."""
        usage = EndpointUsage(
            endpoint_id="get-user",
            repo="frontend",
            file="src/api.js",
            line=42,
            snippet="const user = await fetch('/api/v1/users/{id}');",
            language="javascript",
        )
        assert usage.endpoint_id == "get-user"
        assert usage.line == 42


class TestDiscoveryResult:
    """Tests for DiscoveryResult model."""

    def test_valid_discovery_result(self, sample_discovery_result):
        """Test creating a valid discovery result."""
        result = DiscoveryResult(**sample_discovery_result)
        assert result.phase == "discovery"
        assert len(result.usages) == 1

    def test_discovery_result_as_dict(self, sample_discovery_result):
        """Test serializing discovery result to dict."""
        result = DiscoveryResult(**sample_discovery_result)
        data = result.model_dump()
        assert data["phase"] == "discovery"
        assert len(data["usages"]) == 1


class TestNarrowedUsage:
    """Tests for NarrowedUsage model."""

    def test_valid_narrowed_usage(self):
        """Test creating a valid narrowed usage."""
        usage = NarrowedUsage(
            endpoint_id="get-user",
            repo="frontend",
            file="src/api.js",
            line=42,
            snippet="const user = await fetch('/api/v1/users/{id}');",
            language="javascript",
            matched_mappings=["user_name"],
            complexity="low",
        )
        assert usage.complexity == "low"
        assert len(usage.matched_mappings) == 1

    def test_narrowed_usage_invalid_complexity(self):
        """Test that complexity must be valid."""
        with pytest.raises(ValidationError):
            NarrowedUsage(
                endpoint_id="get-user",
                repo="frontend",
                file="src/api.js",
                line=42,
                snippet="",
                language="javascript",
                matched_mappings=[],
                complexity="impossible",  # Not valid
            )


class TestNarrowingResult:
    """Tests for NarrowingResult model."""

    def test_valid_narrowing_result(self, sample_narrowed_result):
        """Test creating a valid narrowing result."""
        result = NarrowingResult(**sample_narrowed_result)
        assert result.phase == "narrowing"
        assert len(result.narrowed_usages) == 1


class TestGeneratedMigration:
    """Tests for GeneratedMigration model."""

    def test_valid_generated_migration(self):
        """Test creating a valid generated migration."""
        migration = GeneratedMigration(
            endpoint_id="get-user",
            repo="frontend",
            file="src/api.js",
            graphql_query="query GetUser($id: ID!) { user(id: $id) { id userName } }",
            new_code="const { data } = useQuery(GET_USER, { variables: { id } });",
            imports=["import { useQuery } from '@apollo/client';"],
        )
        assert migration.endpoint_id == "get-user"
        assert len(migration.imports) == 1


class TestGenerationResult:
    """Tests for GenerationResult model."""

    def test_valid_generation_result(self, sample_generated_result):
        """Test creating a valid generation result."""
        result = GenerationResult(**sample_generated_result)
        assert result.phase == "generation"
        assert len(result.generated_migrations) == 1


class TestValidationCheck:
    """Tests for ValidationCheck model."""

    def test_valid_validation_check(self):
        """Test creating a valid validation check."""
        check = ValidationCheck(
            check_name="build-test",
            passed=True,
            details="Build and tests passed successfully",
        )
        assert check.check_name == "build-test"
        assert check.passed is True


class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_valid_validation_result(self):
        """Test creating a valid validation result."""
        result = ValidationResult(
            phase="validation",
            timestamp="2025-01-01T00:00:00Z",
            checks=[
                ValidationCheck(
                    check_name="build",
                    passed=True,
                    details="Build successful",
                )
            ],
        )
        assert result.phase == "validation"
        assert len(result.checks) == 1
