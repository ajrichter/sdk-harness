"""Configuration loading and validation."""

import json
from pathlib import Path
from typing import Any, Dict, Union

from migration_harness.schema import Config


def load_config(config_source: Union[str, Dict[str, Any]]) -> Config:
    """Load and validate migration configuration.

    Args:
        config_source: Either a file path (str) or a dict with configuration.

    Returns:
        Validated Config object.

    Raises:
        FileNotFoundError: If config file path doesn't exist.
        ValueError: If configuration is invalid.
    """
    if isinstance(config_source, str):
        # Try to load from file
        config_path = Path(config_source)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_source}")

        with open(config_path) as f:
            config_dict = json.load(f)
    else:
        config_dict = config_source

    try:
        return Config(**config_dict)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")
