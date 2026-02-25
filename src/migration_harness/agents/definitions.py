"""Agent definitions and configurations for each phase."""

from migration_harness.agents.prompts import (
    DISCOVERY_SYSTEM_PROMPT,
    GENERATION_SYSTEM_PROMPT,
    MIGRATION_SYSTEM_PROMPT,
    NARROWING_SYSTEM_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
)
from migration_harness.schema import Config


class AgentDefinitions:
    """Factory for creating agent configurations per phase."""

    def __init__(self, config: Config):
        """Initialize agent definitions.

        Args:
            config: Migration configuration.
        """
        self.config = config

    def get_discovery_prompt(self) -> str:
        """Get discovery phase system prompt.

        Returns:
            System prompt for discovery agent.
        """
        return DISCOVERY_SYSTEM_PROMPT

    def get_narrowing_prompt(self) -> str:
        """Get narrowing phase system prompt.

        Returns:
            System prompt for narrowing agent.
        """
        return NARROWING_SYSTEM_PROMPT

    def get_generation_prompt(self) -> str:
        """Get generation phase system prompt.

        Returns:
            System prompt for generation agent.
        """
        return GENERATION_SYSTEM_PROMPT

    def get_migration_prompt(self) -> str:
        """Get migration phase system prompt.

        Returns:
            System prompt for migration agent.
        """
        return MIGRATION_SYSTEM_PROMPT

    def get_validation_prompt(self) -> str:
        """Get validation phase system prompt.

        Returns:
            System prompt for validation agent.
        """
        return VALIDATION_SYSTEM_PROMPT

    def get_model(self) -> str:
        """Get configured Claude model.

        Returns:
            Model name (e.g., 'claude-sonnet-4-5-20250929').
        """
        return self.config.options.model

    def get_max_turns(self) -> int:
        """Get max agent turns per phase.

        Returns:
            Maximum number of agent turns.
        """
        return self.config.options.max_turns_per_phase
