"""Tests for AgentDefinitions — prompt and config factory."""

import pytest

from migration_harness.agents.definitions import AgentDefinitions
from migration_harness.agents.prompts import (
    DISCOVERY_SYSTEM_PROMPT,
    NARROWING_SYSTEM_PROMPT,
    GENERATION_SYSTEM_PROMPT,
    MIGRATION_SYSTEM_PROMPT,
    VALIDATION_SYSTEM_PROMPT,
)
from migration_harness.schema import Config


@pytest.fixture
def agent_defs(sample_config) -> AgentDefinitions:
    """Create AgentDefinitions with sample config."""
    config = Config(**sample_config)
    return AgentDefinitions(config)


class TestAgentDefinitions:
    """AgentDefinitions provides phase-specific prompts and config."""

    # ── Prompts ────────────────────────────────────────────────────────────

    def test_discovery_prompt_is_nonempty(self, agent_defs):
        """Discovery phase has a system prompt."""
        prompt = agent_defs.get_discovery_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "discovery" in prompt.lower()

    def test_narrowing_prompt_is_nonempty(self, agent_defs):
        """Narrowing phase has a system prompt."""
        prompt = agent_defs.get_narrowing_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "narrow" in prompt.lower()

    def test_generation_prompt_is_nonempty(self, agent_defs):
        """Generation phase has a system prompt."""
        prompt = agent_defs.get_generation_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "graphql" in prompt.lower()

    def test_migration_prompt_is_nonempty(self, agent_defs):
        """Migration phase has a system prompt."""
        prompt = agent_defs.get_migration_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "migrat" in prompt.lower()

    def test_validation_prompt_is_nonempty(self, agent_defs):
        """Validation phase has a system prompt."""
        prompt = agent_defs.get_validation_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        assert "validat" in prompt.lower()

    def test_prompts_match_prompt_module(self, agent_defs):
        """Prompts return the exact strings from prompts.py."""
        assert agent_defs.get_discovery_prompt() == DISCOVERY_SYSTEM_PROMPT
        assert agent_defs.get_narrowing_prompt() == NARROWING_SYSTEM_PROMPT
        assert agent_defs.get_generation_prompt() == GENERATION_SYSTEM_PROMPT
        assert agent_defs.get_migration_prompt() == MIGRATION_SYSTEM_PROMPT
        assert agent_defs.get_validation_prompt() == VALIDATION_SYSTEM_PROMPT

    # ── Configuration ──────────────────────────────────────────────────────

    def test_model_returns_configured_model(self, agent_defs):
        """get_model() returns the model from options."""
        model = agent_defs.get_model()
        assert model == "claude-sonnet-4-5-20250929"
        assert "claude" in model.lower()

    def test_max_turns_returns_configured_value(self, agent_defs):
        """get_max_turns() returns the max_turns_per_phase from options."""
        max_turns = agent_defs.get_max_turns()
        assert max_turns == 50
        assert isinstance(max_turns, int)
        assert max_turns > 0

    def test_config_values_from_sample(self, sample_config):
        """Agent definitions correctly read values from the config passed in."""
        sample_config["options"]["model"] = "custom-model-xyz"
        sample_config["options"]["max_turns_per_phase"] = 100

        config = Config(**sample_config)
        defs = AgentDefinitions(config)

        assert defs.get_model() == "custom-model-xyz"
        assert defs.get_max_turns() == 100
