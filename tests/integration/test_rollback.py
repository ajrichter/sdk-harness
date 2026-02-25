"""Tests for RollbackManager — git-based savepoints and rollback."""

import subprocess
from pathlib import Path

import pytest

from migration_harness.pipeline.rollback import RollbackManager


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Set up git config globally for tests to avoid permission issues
    subprocess.run(
        ["git", "config", "--global", "user.email", "test@example.com"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--global", "user.name", "Test User"],
        capture_output=True,
    )

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=True)

    # Create initial commit
    (repo / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        capture_output=True,
        check=True,
    )

    return repo


@pytest.fixture
def rollback_manager(git_repo: Path) -> RollbackManager:
    """Create a RollbackManager for a test git repo."""
    return RollbackManager(str(git_repo))


@pytest.mark.integration
class TestRollbackManager:
    """RollbackManager creates git savepoints and can rollback to them.

    NOTE: These tests require git to be properly configured with user.email and user.name.
    They are marked as integration tests since they interact with the filesystem.
    """

    # ── Savepoint creation ──────────────────────────────────────────────────

    def test_create_savepoint_returns_branch_name(self, rollback_manager):
        """create_savepoint() returns the branch name it created."""
        branch = rollback_manager.create_savepoint("migration")
        assert branch == "savepoint/migration"

    def test_create_savepoint_creates_git_branch(self, rollback_manager, git_repo):
        """create_savepoint() actually creates a git branch."""
        branch = rollback_manager.create_savepoint("migration")

        # List branches
        result = subprocess.run(
            ["git", "branch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        branches = result.stdout
        assert branch in branches or branch.strip() in branches

    def test_can_create_multiple_savepoints(self, rollback_manager):
        """Can create multiple savepoints for different phases."""
        branch1 = rollback_manager.create_savepoint("generation")
        branch2 = rollback_manager.create_savepoint("migration")

        assert branch1 == "savepoint/generation"
        assert branch2 == "savepoint/migration"
        assert branch1 != branch2

    # ── Rollback ────────────────────────────────────────────────────────────

    def test_rollback_to_savepoint(self, rollback_manager, git_repo):
        """rollback_to_savepoint() checks out the savepoint branch."""
        # Create a savepoint
        branch = rollback_manager.create_savepoint("test")

        # Make a change on main branch
        (git_repo / "file.txt").write_text("modified")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Modification"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        # Rollback to savepoint
        rollback_manager.rollback_to_savepoint(branch)

        # Verify we're on the savepoint branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()
        assert current_branch == branch

    # ── Delete savepoint ────────────────────────────────────────────────────

    def test_delete_savepoint(self, rollback_manager, git_repo):
        """delete_savepoint() removes the branch."""
        branch = rollback_manager.create_savepoint("cleanup")

        # Verify branch exists
        result = subprocess.run(
            ["git", "branch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert branch in result.stdout

        # Delete it
        rollback_manager.delete_savepoint(branch)

        # Verify it's gone
        result = subprocess.run(
            ["git", "branch"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert branch not in result.stdout

    def test_delete_nonexistent_savepoint_doesnt_error(self, rollback_manager):
        """delete_savepoint() on a non-existent branch doesn't raise."""
        # Should not raise
        rollback_manager.delete_savepoint("nonexistent/branch")

    # ── Commit tracking ────────────────────────────────────────────────────

    def test_get_current_commit(self, rollback_manager, git_repo):
        """get_current_commit() returns the HEAD commit hash."""
        commit = rollback_manager.get_current_commit()

        assert commit is not None
        assert len(commit) == 40  # SHA-1 is 40 hex chars
        assert commit.isalnum()

    def test_get_current_commit_not_in_git_repo_returns_none(self, tmp_path):
        """get_current_commit() returns None if not in a git repo."""
        manager = RollbackManager(str(tmp_path))
        commit = manager.get_current_commit()
        assert commit is None

    def test_commit_changes_after_savepoint(self, rollback_manager, git_repo):
        """Commits created after a savepoint have different hashes."""
        commit1 = rollback_manager.get_current_commit()

        # Make a change
        (git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "."], cwd=git_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Change"],
            cwd=git_repo,
            capture_output=True,
            check=True,
        )

        commit2 = rollback_manager.get_current_commit()

        assert commit1 != commit2
        assert commit1 is not None
        assert commit2 is not None
