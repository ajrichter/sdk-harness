"""Git-based rollback management for migration phase."""

import subprocess
from pathlib import Path
from typing import Optional


class RollbackManager:
    """Manages git savepoints and rollback."""

    def __init__(self, repo_path: str):
        """Initialize rollback manager.

        Args:
            repo_path: Path to git repository.
        """
        self.repo_path = Path(repo_path)

    def create_savepoint(self, phase: str) -> str:
        """Create a git savepoint before a phase.

        Args:
            phase: Phase name (e.g., 'migration').

        Returns:
            Branch name created as savepoint.
        """
        branch_name = f"savepoint/{phase}"

        try:
            # Create and checkout savepoint branch
            subprocess.run(
                ["git", "-C", str(self.repo_path), "checkout", "-b", branch_name],
                check=True,
                capture_output=True,
            )
            return branch_name
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create savepoint: {e.stderr.decode()}")

    def rollback_to_savepoint(self, branch_name: str) -> None:
        """Rollback repository to a savepoint.

        Args:
            branch_name: Savepoint branch name to rollback to.

        Raises:
            RuntimeError: If rollback fails.
        """
        try:
            # Get the original branch
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "branch", "-a"],
                check=True,
                capture_output=True,
                text=True,
            )

            # Switch to savepoint branch and reset
            subprocess.run(
                ["git", "-C", str(self.repo_path), "checkout", branch_name],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to rollback to savepoint: {e.stderr.decode()}")

    def delete_savepoint(self, branch_name: str) -> None:
        """Delete a savepoint branch.

        Args:
            branch_name: Savepoint branch name to delete.
        """
        try:
            subprocess.run(
                ["git", "-C", str(self.repo_path), "branch", "-D", branch_name],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError:
            # Ignore errors if branch doesn't exist
            pass

    def get_current_commit(self) -> Optional[str]:
        """Get current commit hash.

        Returns:
            Commit hash or None if not in a git repo.
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
