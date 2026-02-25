"""State management for migration phases."""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class StateManager:
    """Manages inter-phase state persistence."""

    def __init__(self, work_dir: str):
        """Initialize state manager.

        Args:
            work_dir: Working directory for storing state files.
        """
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def _get_state_file(self, phase: str) -> Path:
        """Get the state file path for a phase.

        Args:
            phase: Phase name (e.g., 'discovery', 'narrowing').

        Returns:
            Path to state file.
        """
        return self.work_dir / f"{phase}-result.json"

    def save_discovery_result(self, result: Dict[str, Any]) -> None:
        """Save discovery phase result.

        Args:
            result: Discovery result dictionary.
        """
        self._save_result("discovery", result)

    def get_discovery_result(self) -> Optional[Dict[str, Any]]:
        """Get discovery phase result.

        Returns:
            Discovery result or None if not found.
        """
        return self._get_result("discovery")

    def save_narrowing_result(self, result: Dict[str, Any]) -> None:
        """Save narrowing phase result.

        Args:
            result: Narrowing result dictionary.
        """
        self._save_result("narrowing", result)

    def get_narrowing_result(self) -> Optional[Dict[str, Any]]:
        """Get narrowing phase result.

        Returns:
            Narrowing result or None if not found.
        """
        return self._get_result("narrowing")

    def save_generation_result(self, result: Dict[str, Any]) -> None:
        """Save generation phase result.

        Args:
            result: Generation result dictionary.
        """
        self._save_result("generation", result)

    def get_generation_result(self) -> Optional[Dict[str, Any]]:
        """Get generation phase result.

        Returns:
            Generation result or None if not found.
        """
        return self._get_result("generation")

    def save_migration_result(self, result: Dict[str, Any]) -> None:
        """Save migration phase result.

        Args:
            result: Migration result dictionary.
        """
        self._save_result("migration", result)

    def get_migration_result(self) -> Optional[Dict[str, Any]]:
        """Get migration phase result.

        Returns:
            Migration result or None if not found.
        """
        return self._get_result("migration")

    def save_validation_result(self, result: Dict[str, Any]) -> None:
        """Save validation phase result.

        Args:
            result: Validation result dictionary.
        """
        self._save_result("validation", result)

    def get_validation_result(self) -> Optional[Dict[str, Any]]:
        """Get validation phase result.

        Returns:
            Validation result or None if not found.
        """
        return self._get_result("validation")

    def _save_result(self, phase: str, result: Dict[str, Any]) -> None:
        """Save result to file.

        Args:
            phase: Phase name.
            result: Result dictionary.
        """
        file_path = self._get_state_file(phase)
        with open(file_path, "w") as f:
            json.dump(result, f, indent=2)

    def _get_result(self, phase: str) -> Optional[Dict[str, Any]]:
        """Get result from file.

        Args:
            phase: Phase name.

        Returns:
            Result dictionary or None if file doesn't exist.
        """
        file_path = self._get_state_file(phase)
        if not file_path.exists():
            return None

        with open(file_path) as f:
            return json.load(f)
