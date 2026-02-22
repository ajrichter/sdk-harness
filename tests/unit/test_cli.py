"""Tests for CLI entry point — main.py."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from migration_harness.main import main


@pytest.fixture
def config_file(tmp_path: Path, sample_config) -> Path:
    """Create a config file for CLI testing."""
    config_path = tmp_path / "config.json"
    config_file_data = sample_config.copy()
    config_file_data["work_dir"] = str(tmp_path / "work")
    config_path.write_text(json.dumps(config_file_data))
    return config_path


class TestCLI:
    """CLI entry point tests."""

    # ── Argument parsing ───────────────────────────────────────────────────

    def test_requires_config_argument(self):
        """CLI fails if --config is missing."""
        with patch("sys.argv", ["migration-harness"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # argparse exits with code 2 on missing required argument
            assert exc_info.value.code == 2

    def test_config_file_not_found_returns_error(self):
        """CLI fails if config file doesn't exist."""
        with patch("sys.argv", ["migration-harness", "--config", "/nonexistent/config.json"]):
            code = main()
            assert code == 1

    def test_config_invalid_json_returns_error(self, tmp_path):
        """CLI fails if config file is not valid JSON."""
        config_path = tmp_path / "bad.json"
        config_path.write_text("{invalid json")

        with patch("sys.argv", ["migration-harness", "--config", str(config_path)]):
            code = main()
            assert code == 1

    # ── Status flag ────────────────────────────────────────────────────────

    @patch("migration_harness.orchestrator.Orchestrator.from_config_file")
    def test_status_flag_shows_progress(self, mock_from_config, config_file):
        """--status flag shows pipeline status and exits."""
        mock_orch = MagicMock()
        mock_orch.get_pipeline_status.return_value = {
            "project": "test",
            "phases": {},
        }
        mock_from_config.return_value = mock_orch

        with patch("sys.argv", ["migration-harness", "--config", str(config_file), "--status"]):
            code = main()
            assert code == 0
            mock_orch.get_pipeline_status.assert_called_once()

    @patch("migration_harness.orchestrator.Orchestrator.from_config_file")
    def test_status_flag_prints_no_status_if_not_started(self, mock_from_config, config_file):
        """--status shows 'not yet started' if pipeline hasn't begun."""
        mock_orch = MagicMock()
        mock_orch.get_pipeline_status.return_value = None
        mock_from_config.return_value = mock_orch

        with patch("sys.argv", ["migration-harness", "--config", str(config_file), "--status"]):
            code = main()
            assert code == 0

    # ── Pipeline execution ──────────────────────────────────────────────────

    @patch("asyncio.run")
    @patch("migration_harness.orchestrator.Orchestrator.from_config_file")
    def test_runs_pipeline_without_status_flag(self, mock_from_config, mock_asyncio, config_file):
        """Without --status, CLI runs the full pipeline."""
        mock_orch = MagicMock()
        mock_from_config.return_value = mock_orch
        mock_asyncio.return_value = True  # pipeline succeeds

        with patch("sys.argv", ["migration-harness", "--config", str(config_file)]):
            code = main()
            assert code == 0
            mock_asyncio.assert_called_once()

    @patch("asyncio.run")
    @patch("migration_harness.orchestrator.Orchestrator.from_config_file")
    def test_pipeline_failure_returns_error_code(self, mock_from_config, mock_asyncio, config_file):
        """If pipeline fails, CLI returns error code 1."""
        mock_orch = MagicMock()
        mock_from_config.return_value = mock_orch
        mock_asyncio.return_value = False  # pipeline fails

        with patch("sys.argv", ["migration-harness", "--config", str(config_file)]):
            code = main()
            assert code == 1

    # ── Exception handling ──────────────────────────────────────────────────

    @patch("migration_harness.orchestrator.Orchestrator.from_config_file")
    def test_exception_during_execution_returns_error(self, mock_from_config, config_file):
        """Uncaught exception during pipeline returns error code 1."""
        mock_from_config.side_effect = Exception("Something went wrong")

        with patch("sys.argv", ["migration-harness", "--config", str(config_file)]):
            code = main()
            assert code == 1

    # ── Help text ──────────────────────────────────────────────────────────

    def test_help_flag_works(self):
        """--help flag shows usage and exits cleanly."""
        with patch("sys.argv", ["migration-harness", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # argparse exits with code 0 on --help
            assert exc_info.value.code == 0
