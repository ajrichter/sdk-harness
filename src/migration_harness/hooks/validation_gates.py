"""Validation hooks for tool outputs."""

import json
from typing import Any, Dict

from migration_harness.pipeline.gates import GateError


def validate_discovery_output(output: str) -> bool:
    """Validate discovery phase tool output.

    Args:
        output: Tool output to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        data = json.loads(output) if isinstance(output, str) else output
        if not isinstance(data, dict):
            return False
        if data.get("phase") != "discovery":
            return False
        if not isinstance(data.get("usages", []), list):
            return False
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def validate_narrowing_output(output: str) -> bool:
    """Validate narrowing phase tool output.

    Args:
        output: Tool output to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        data = json.loads(output) if isinstance(output, str) else output
        if not isinstance(data, dict):
            return False
        if data.get("phase") != "narrowing":
            return False
        if not isinstance(data.get("narrowed_usages", []), list):
            return False
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def validate_generation_output(output: str) -> bool:
    """Validate generation phase tool output.

    Args:
        output: Tool output to validate.

    Returns:
        True if valid, False otherwise.
    """
    try:
        data = json.loads(output) if isinstance(output, str) else output
        if not isinstance(data, dict):
            return False
        if data.get("phase") != "generation":
            return False
        if not isinstance(data.get("generated_migrations", []), list):
            return False
        return True
    except (json.JSONDecodeError, ValueError):
        return False
