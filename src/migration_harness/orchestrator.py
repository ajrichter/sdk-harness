"""Pipeline orchestrator for coordinating migration phases."""

import asyncio
from pathlib import Path
from typing import Optional

from migration_harness.agents.definitions import AgentDefinitions
from migration_harness.config import load_config
from migration_harness.pipeline.gates import (
    GateError,
    validate_discovery_gate,
    validate_generation_gate,
    validate_narrowing_gate,
)
from migration_harness.pipeline.runner import PhaseRunner
from migration_harness.schema import Config
from migration_harness.state.manager import StateManager
from migration_harness.state.progress import ProgressTracker


class Orchestrator:
    """Orchestrates the REST-to-GraphQL migration pipeline."""

    PHASES = ["discovery", "narrowing", "generation", "migration", "validation"]

    def __init__(self, config: Config):
        """Initialize orchestrator.

        Args:
            config: Migration configuration.
        """
        self.config = config
        self.state_manager = StateManager(config.work_dir)
        self.progress_tracker = ProgressTracker(config.work_dir)
        self.agent_definitions = AgentDefinitions(config)

    @classmethod
    def from_config_file(cls, config_path: str) -> "Orchestrator":
        """Create orchestrator from configuration file.

        Args:
            config_path: Path to configuration file.

        Returns:
            Orchestrator instance.
        """
        config = load_config(config_path)
        return cls(config)

    async def run_pipeline(self) -> bool:
        """Run the complete migration pipeline.

        Returns:
            True if pipeline succeeded, False otherwise.
        """
        self.progress_tracker.init_progress(self.config.project_name)

        try:
            for phase in self.PHASES:
                print(f"Starting phase: {phase}")
                runner = PhaseRunner(
                    self.config,
                    self.state_manager,
                    self.progress_tracker,
                    phase,
                )

                result = await runner.run()

                if not result:
                    print(f"Phase {phase} failed")
                    return False

                # Validate phase output
                if not self._validate_phase_result(phase, result):
                    print(f"Phase {phase} validation failed")
                    return False

                print(f"Phase {phase} completed successfully")

            return True
        except Exception as e:
            print(f"Pipeline failed: {e}")
            return False

    def _validate_phase_result(self, phase: str, result: dict) -> bool:
        """Validate phase result with gates.

        Args:
            phase: Phase name.
            result: Phase result to validate.

        Returns:
            True if validation passed, False otherwise.
        """
        try:
            if phase == "discovery":
                validate_discovery_gate(result)
            elif phase == "narrowing":
                validate_narrowing_gate(result)
            elif phase == "generation":
                validate_generation_gate(result)
            # Migration and validation gates are non-blocking
            return True
        except GateError as e:
            print(f"Gate validation failed for {phase}: {e}")
            return False

    def get_pipeline_status(self) -> Optional[dict]:
        """Get current pipeline status.

        Returns:
            Progress dictionary or None if not started.
        """
        return self.progress_tracker.read_progress()
