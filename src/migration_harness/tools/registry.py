"""MCP tool registry for agent sessions."""

from typing import Any, Dict, Optional

from migration_harness.config import load_config
from migration_harness.schema import Config
from migration_harness.state.manager import StateManager


class ToolRegistry:
    """Registry of MCP tools for agent sessions."""

    def __init__(self, config: Config, state_manager: StateManager):
        """Initialize tool registry.

        Args:
            config: Migration configuration.
            state_manager: State manager instance.
        """
        self.config = config
        self.state_manager = state_manager

    def get_config(self) -> Dict[str, Any]:
        """Get configuration as JSON.

        Returns:
            Configuration dictionary.
        """
        return self.config.model_dump()

    def get_endpoints(self) -> Dict[str, Any]:
        """Get REST endpoints configuration.

        Returns:
            REST endpoints dictionary.
        """
        return {
            "endpoints": [ep.model_dump() for ep in self.config.rest_endpoints]
        }

    def get_mappings(self) -> Dict[str, Any]:
        """Get attribute mappings configuration.

        Returns:
            Attribute mappings dictionary.
        """
        return {
            "mappings": [m.model_dump() for m in self.config.attribute_mappings]
        }

    def get_graphql_schema(self) -> str:
        """Get GraphQL schema content.

        Returns:
            GraphQL schema content.

        Raises:
            FileNotFoundError: If schema file not found.
        """
        schema_path = self.config.graphql_schema_path
        try:
            with open(schema_path) as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"GraphQL schema not found: {schema_path}")

    def save_discovery_result(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Save discovery phase result.

        Args:
            result: Discovery result to save.

        Returns:
            Confirmation message.
        """
        self.state_manager.save_discovery_result(result)
        return {"status": "saved", "phase": "discovery"}

    def get_discovery_result(self) -> Optional[Dict[str, Any]]:
        """Get saved discovery result.

        Returns:
            Discovery result or None if not found.
        """
        return self.state_manager.get_discovery_result()

    def save_narrowing_result(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Save narrowing phase result.

        Args:
            result: Narrowing result to save.

        Returns:
            Confirmation message.
        """
        self.state_manager.save_narrowing_result(result)
        return {"status": "saved", "phase": "narrowing"}

    def get_narrowing_result(self) -> Optional[Dict[str, Any]]:
        """Get saved narrowing result.

        Returns:
            Narrowing result or None if not found.
        """
        return self.state_manager.get_narrowing_result()

    def save_generation_result(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Save generation phase result.

        Args:
            result: Generation result to save.

        Returns:
            Confirmation message.
        """
        self.state_manager.save_generation_result(result)
        return {"status": "saved", "phase": "generation"}

    def get_generation_result(self) -> Optional[Dict[str, Any]]:
        """Get saved generation result.

        Returns:
            Generation result or None if not found.
        """
        return self.state_manager.get_generation_result()

    def save_migration_result(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Save migration phase result.

        Args:
            result: Migration result to save.

        Returns:
            Confirmation message.
        """
        self.state_manager.save_migration_result(result)
        return {"status": "saved", "phase": "migration"}

    def get_migration_result(self) -> Optional[Dict[str, Any]]:
        """Get saved migration result.

        Returns:
            Migration result or None if not found.
        """
        return self.state_manager.get_migration_result()

    def save_validation_result(self, result: Dict[str, Any]) -> Dict[str, str]:
        """Save validation phase result.

        Args:
            result: Validation result to save.

        Returns:
            Confirmation message.
        """
        self.state_manager.save_validation_result(result)
        return {"status": "saved", "phase": "validation"}

    def get_validation_result(self) -> Optional[Dict[str, Any]]:
        """Get saved validation result.

        Returns:
            Validation result or None if not found.
        """
        return self.state_manager.get_validation_result()
