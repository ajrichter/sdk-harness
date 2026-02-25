"""Validation gates between pipeline phases."""

from typing import Any, Dict


class GateError(Exception):
    """Raised when a validation gate fails."""

    pass


def validate_discovery_gate(result: Dict[str, Any]) -> None:
    """Validate discovery phase result.

    Args:
        result: Discovery result to validate.

    Raises:
        GateError: If validation fails.
    """
    if not isinstance(result, dict):
        raise GateError("Discovery result must be a dictionary")

    if result.get("phase") != "discovery":
        raise GateError("Discovery result must have phase='discovery'")

    usages = result.get("usages", [])
    if not usages:
        raise GateError("Discovery must find at least one usage")


def validate_narrowing_gate(result: Dict[str, Any]) -> None:
    """Validate narrowing phase result.

    Args:
        result: Narrowing result to validate.

    Raises:
        GateError: If validation fails.
    """
    if not isinstance(result, dict):
        raise GateError("Narrowing result must be a dictionary")

    if result.get("phase") != "narrowing":
        raise GateError("Narrowing result must have phase='narrowing'")

    usages = result.get("narrowed_usages", [])
    if not usages:
        raise GateError("Narrowing must produce at least one narrowed usage")


def validate_generation_gate(result: Dict[str, Any]) -> None:
    """Validate generation phase result.

    Args:
        result: Generation result to validate.

    Raises:
        GateError: If validation fails.
    """
    if not isinstance(result, dict):
        raise GateError("Generation result must be a dictionary")

    if result.get("phase") != "generation":
        raise GateError("Generation result must have phase='generation'")

    migrations = result.get("generated_migrations", [])
    if not migrations:
        raise GateError("Generation must produce at least one migration")

    for migration in migrations:
        if not migration.get("graphql_query", "").strip():
            raise GateError("All migrations must have non-empty graphql_query")
        if not migration.get("new_code", "").strip():
            raise GateError("All migrations must have non-empty new_code")
