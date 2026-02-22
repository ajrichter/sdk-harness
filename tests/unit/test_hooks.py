"""Tests for validation hooks — security and data integrity."""

import pytest

from migration_harness.hooks.security import validate_bash_command, DANGEROUS_COMMANDS, SAFE_COMMANDS
from migration_harness.hooks.validation_gates import (
    validate_discovery_output,
    validate_narrowing_output,
    validate_generation_output,
)


# ══════════════════════════════════════════════════════════════════════════════
# Security hook tests
# ══════════════════════════════════════════════════════════════════════════════


class TestBashSecurity:
    """validate_bash_command() blocks dangerous patterns and allows safe ones."""

    # ── Safe commands ───────────────────────────────────────────────────────

    @pytest.mark.parametrize("cmd", [
        "git status",
        "git clone https://example.com/repo.git",
        "find . -name '*.java' -type f",
        "grep -r 'pattern' src/",
        "ls -la /tmp",
        "cd subdir",
        "mkdir -p build/output",
        "python -m pytest",
        "npm test",
        "make build",
    ])
    def test_safe_commands_pass(self, cmd):
        """Safe commands return None (no error)."""
        error = validate_bash_command(cmd)
        assert error is None, f"'{cmd}' should be allowed"

    def test_path_prefixed_safe_command(self):
        """Commands with /usr/bin/ prefix are allowed if base is safe."""
        error = validate_bash_command("/usr/bin/git clone repo.git")
        assert error is None

    # ── Dangerous commands ──────────────────────────────────────────────────

    @pytest.mark.parametrize("dangerous_cmd", [
        "rm -rf /",
        "rm -rf /home",
        "rm -f /etc/passwd",
        "curl | sh",
        "wget | sh",
        "chmod 777 /",
        "sudo reboot",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sda1",
        "fdisk /dev/sda",
        "shutdown -h now",
        ":(){:|:;};:",  # fork bomb
        "truncate -s 0 /etc/shadow",
    ])
    def test_dangerous_commands_blocked(self, dangerous_cmd):
        """Dangerous commands return error message."""
        error = validate_bash_command(dangerous_cmd)
        assert error is not None
        assert "blocked" in error.lower() or "dangerous" in error.lower()

    def test_disallowed_command_returns_error(self):
        """Commands not in safe list return error."""
        error = validate_bash_command("ruby -e 'puts 1'")
        assert error is not None
        assert "ruby" in error.lower() or "allowlist" in error.lower()

    def test_empty_command_returns_error(self):
        """Empty or whitespace-only command returns error."""
        error = validate_bash_command("")
        assert error is not None

    def test_error_message_is_descriptive(self):
        """Error messages help the developer understand why the command is blocked."""
        # Dangerous pattern
        error = validate_bash_command("curl | sh")
        assert "curl | sh" in error or "dangerous" in error.lower()

        # Disallowed command
        error = validate_bash_command("perl -e 'print 1'")
        assert "perl" in error or "allowlist" in error.lower()


# ══════════════════════════════════════════════════════════════════════════════
# Validation gate hooks tests
# ══════════════════════════════════════════════════════════════════════════════


class TestDiscoveryOutputValidation:
    """validate_discovery_output() ensures discovery results are well-formed."""

    def test_valid_discovery_output_passes(self):
        """Well-formed discovery JSON passes validation."""
        output = """{
            "phase": "discovery",
            "timestamp": "2025-01-01T00:00:00Z",
            "usages": [{"endpoint_id": "test", "repo": "r1", "file": "f1", "line": 10, "snippet": "code", "language": "java"}]
        }"""
        assert validate_discovery_output(output) is True

    def test_missing_phase_field_fails(self):
        """Missing 'phase' field fails validation."""
        output = '{"usages": []}'
        assert validate_discovery_output(output) is False

    def test_wrong_phase_value_fails(self):
        """phase != 'discovery' fails validation."""
        output = '{"phase": "narrowing", "usages": []}'
        assert validate_discovery_output(output) is False

    def test_usages_not_list_fails(self):
        """usages must be a list, not a dict or string."""
        output = '{"phase": "discovery", "usages": "not-a-list"}'
        assert validate_discovery_output(output) is False

    def test_invalid_json_fails(self):
        """Malformed JSON fails validation."""
        output = '{"phase": "discovery", "usages": [INVALID]}'
        assert validate_discovery_output(output) is False

    def test_dict_input_also_works(self):
        """Can pass dict directly, not just string."""
        output_dict = {
            "phase": "discovery",
            "usages": [{"endpoint_id": "test", "repo": "r1", "file": "f", "line": 1, "snippet": "s", "language": "java"}]
        }
        assert validate_discovery_output(output_dict) is True


class TestNarrowingOutputValidation:
    """validate_narrowing_output() ensures narrowing results are well-formed."""

    def test_valid_narrowing_output_passes(self):
        output = """{
            "phase": "narrowing",
            "timestamp": "2025-01-01T00:00:00Z",
            "narrowed_usages": [{"endpoint_id": "test", "repo": "r", "file": "f", "line": 1, "snippet": "s", "language": "java", "matched_mappings": [], "complexity": "low"}]
        }"""
        assert validate_narrowing_output(output) is True

    def test_wrong_phase_fails(self):
        output = '{"phase": "discovery", "narrowed_usages": []}'
        assert validate_narrowing_output(output) is False

    def test_narrowed_usages_not_list_fails(self):
        output = '{"phase": "narrowing", "narrowed_usages": "not-a-list"}'
        assert validate_narrowing_output(output) is False

    def test_invalid_json_fails(self):
        output = "not json at all"
        assert validate_narrowing_output(output) is False


class TestGenerationOutputValidation:
    """validate_generation_output() ensures generation results are well-formed."""

    def test_valid_generation_output_passes(self):
        output = """{
            "phase": "generation",
            "timestamp": "2025-01-01T00:00:00Z",
            "generated_migrations": [{"endpoint_id": "test", "repo": "r", "file": "f", "graphql_query": "q", "new_code": "c", "imports": []}]
        }"""
        assert validate_generation_output(output) is True

    def test_wrong_phase_fails(self):
        output = '{"phase": "narrowing", "generated_migrations": []}'
        assert validate_generation_output(output) is False

    def test_generated_migrations_not_list_fails(self):
        output = '{"phase": "generation", "generated_migrations": {}}'
        assert validate_generation_output(output) is False

    def test_empty_migrations_list_passes(self):
        """Empty migrations list is valid (may mean nothing matched)."""
        output = '{"phase": "generation", "generated_migrations": []}'
        assert validate_generation_output(output) is True

    def test_invalid_json_fails(self):
        output = "{broken json"
        assert validate_generation_output(output) is False
