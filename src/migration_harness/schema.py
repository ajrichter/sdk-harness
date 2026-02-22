"""Pydantic models for migration harness data structures."""

from typing import List, Literal

from pydantic import BaseModel, Field, field_validator


class RestEndpoint(BaseModel):
    """REST endpoint configuration."""

    id: str = Field(..., description="Unique endpoint identifier")
    method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    path: str = Field(..., description="API path (e.g., /api/v1/users/{id})")
    patterns: List[str] = Field(..., description="Code patterns to search for")

    @field_validator("patterns")
    @classmethod
    def patterns_not_empty(cls, v: List[str]) -> List[str]:
        """Ensure patterns list is not empty."""
        if not v:
            raise ValueError("patterns cannot be empty")
        return v


class AttributeMapping(BaseModel):
    """Mapping from REST attribute to GraphQL field."""

    endpoint_id: str = Field(..., description="Associated endpoint ID")
    rest_attribute: str = Field(..., description="REST API attribute name")
    graphql_field: str = Field(..., description="GraphQL field name")
    graphql_type: str = Field(..., description="GraphQL type containing this field")


class Repository(BaseModel):
    """Git repository configuration."""

    name: str = Field(..., description="Repository name")
    url: str = Field(..., description="Git repository URL")
    branch: str = Field(..., description="Branch to work on")
    language: Literal["javascript", "java"] = Field(
        ..., description="Programming language"
    )


class ConfigOptions(BaseModel):
    """Configuration options for the migration."""

    dry_run: bool = Field(default=True, description="Run without applying changes")
    create_branches: bool = Field(
        default=True, description="Create feature branches for migrations"
    )
    branch_prefix: str = Field(
        default="migration/rest-to-graphql", description="Prefix for feature branches"
    )
    max_concurrent_repos: int = Field(
        default=2, description="Maximum concurrent repository processing"
    )
    model: str = Field(
        default="claude-sonnet-4-5-20250929", description="Claude model to use"
    )
    max_turns_per_phase: int = Field(
        default=50, description="Maximum agent turns per phase"
    )


class Config(BaseModel):
    """Main migration configuration."""

    project_name: str = Field(..., description="Project name")
    work_dir: str = Field(..., description="Working directory for migrations")
    repositories: List[Repository] = Field(
        ..., description="List of repositories to migrate"
    )
    rest_endpoints: List[RestEndpoint] = Field(..., description="REST endpoints")
    attribute_mappings: List[AttributeMapping] = Field(
        ..., description="Attribute mappings"
    )
    graphql_endpoint: str = Field(..., description="GraphQL endpoint URL")
    graphql_schema_path: str = Field(..., description="Path to GraphQL schema file")
    options: ConfigOptions = Field(default_factory=ConfigOptions)

    @field_validator("repositories")
    @classmethod
    def repositories_not_empty(cls, v: List[Repository]) -> List[Repository]:
        """Ensure repositories list is not empty."""
        if not v:
            raise ValueError("repositories cannot be empty")
        return v


class EndpointUsage(BaseModel):
    """Discovery of a REST endpoint usage in code."""

    endpoint_id: str = Field(..., description="Endpoint ID")
    repo: str = Field(..., description="Repository name")
    file: str = Field(..., description="File path")
    line: int = Field(..., description="Line number")
    snippet: str = Field(..., description="Code snippet")
    language: str = Field(..., description="Programming language")


class DiscoveryResult(BaseModel):
    """Output of discovery phase."""

    phase: Literal["discovery"] = "discovery"
    timestamp: str = Field(..., description="ISO timestamp")
    usages: List[EndpointUsage] = Field(..., description="All discovered usages")


class NarrowedUsage(BaseModel):
    """Endpoint usage that passes narrowing filters."""

    endpoint_id: str = Field(..., description="Endpoint ID")
    repo: str = Field(..., description="Repository name")
    file: str = Field(..., description="File path")
    line: int = Field(..., description="Line number")
    snippet: str = Field(..., description="Code snippet")
    language: str = Field(..., description="Programming language")
    matched_mappings: List[str] = Field(
        ..., description="Matched attribute mapping IDs"
    )
    complexity: Literal["low", "medium", "high"] = Field(
        ..., description="Estimated complexity"
    )


class NarrowingResult(BaseModel):
    """Output of narrowing phase."""

    phase: Literal["narrowing"] = "narrowing"
    timestamp: str = Field(..., description="ISO timestamp")
    narrowed_usages: List[NarrowedUsage] = Field(
        ..., description="Filtered usages with mappings"
    )


class GeneratedMigration(BaseModel):
    """Generated migration code for one usage."""

    endpoint_id: str = Field(..., description="Endpoint ID")
    repo: str = Field(..., description="Repository name")
    file: str = Field(..., description="File path")
    graphql_query: str = Field(..., description="GraphQL query/mutation")
    new_code: str = Field(..., description="Replacement code")
    imports: List[str] = Field(..., description="Required imports")


class GenerationResult(BaseModel):
    """Output of generation phase."""

    phase: Literal["generation"] = "generation"
    timestamp: str = Field(..., description="ISO timestamp")
    generated_migrations: List[GeneratedMigration] = Field(
        ..., description="Generated migrations"
    )


class AppliedMigration(BaseModel):
    """Metadata about an applied migration."""

    endpoint_id: str = Field(..., description="Endpoint ID")
    repo: str = Field(..., description="Repository name")
    file: str = Field(..., description="File path")
    applied: bool = Field(..., description="Whether migration was successfully applied")
    diff: str = Field(..., description="Git diff of changes")
    branch: str = Field(..., description="Feature branch name")
    commit: str = Field(..., description="Commit hash")


class MigrationResult(BaseModel):
    """Output of migration phase."""

    phase: Literal["migration"] = "migration"
    timestamp: str = Field(..., description="ISO timestamp")
    applied_migrations: List[AppliedMigration] = Field(
        ..., description="Applied migrations"
    )


class ValidationCheck(BaseModel):
    """Single validation check result."""

    check_name: str = Field(..., description="Check name")
    passed: bool = Field(..., description="Whether check passed")
    details: str = Field(..., description="Check details/error message")


class ValidationResult(BaseModel):
    """Output of validation phase."""

    phase: Literal["validation"] = "validation"
    timestamp: str = Field(..., description="ISO timestamp")
    checks: List[ValidationCheck] = Field(..., description="Validation checks")
