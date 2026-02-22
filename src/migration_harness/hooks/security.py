"""Security hooks for bash command validation."""

from typing import Optional

# Blocklist of dangerous bash commands
DANGEROUS_COMMANDS = {
    "rm -rf",
    "rm -f /",
    "curl | sh",
    "wget | sh",
    "chmod 777",
    "sudo",
    "dd if=/dev/",
    "mkfs",
    "fdisk",
    "shutdown",
    "reboot",
    ":(){:|:;};:",  # fork bomb
    "truncate -s 0",
}

# Allowlist of safe commands
SAFE_COMMANDS = {
    "git",
    "ls",
    "cd",
    "cat",
    "grep",
    "find",
    "mkdir",
    "cp",
    "mv",
    "head",
    "tail",
    "echo",
    "sed",
    "awk",
    "python",
    "npm",
    "pip",
    "make",
}


def validate_bash_command(command: str) -> Optional[str]:
    """Validate a bash command for security.

    Args:
        command: Command to validate.

    Returns:
        Error message if command is unsafe, None if safe.
    """
    # Check for dangerous commands
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in command:
            return f"Command blocked: contains dangerous operation '{dangerous}'"

    # Check that command starts with an allowed operation
    cmd_parts = command.split()
    if not cmd_parts:
        return "Empty command"

    base_cmd = cmd_parts[0].split("/")[-1]  # Handle paths like /usr/bin/git

    if base_cmd not in SAFE_COMMANDS:
        return f"Command '{base_cmd}' is not in allowlist"

    return None
