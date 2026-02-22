"""Progress tracking for migration pipeline."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class ProgressTracker:
    """Tracks progress through migration phases."""

    PROGRESS_FILE = "migration-progress.txt"

    def __init__(self, work_dir: str):
        """Initialize progress tracker.

        Args:
            work_dir: Working directory for storing progress file.
        """
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.work_dir / self.PROGRESS_FILE

    def init_progress(self, project_name: str) -> None:
        """Initialize progress tracking for a project.

        Args:
            project_name: Name of the project being migrated.
        """
        progress = {
            "project": project_name,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "phases": {},
        }
        self._write_progress(progress)

    def mark_phase_started(self, phase: str) -> None:
        """Mark a phase as started.

        Args:
            phase: Phase name.
        """
        progress = self.read_progress() or {"phases": {}}

        if phase not in progress["phases"]:
            progress["phases"][phase] = {}

        progress["phases"][phase].update(
            {
                "status": "in_progress",
                "started_at": datetime.utcnow().isoformat() + "Z",
            }
        )
        self._write_progress(progress)

    def mark_phase_completed(self, phase: str, summary: str = "") -> None:
        """Mark a phase as completed.

        Args:
            phase: Phase name.
            summary: Summary of phase results.
        """
        progress = self.read_progress() or {"phases": {}}

        if phase not in progress["phases"]:
            progress["phases"][phase] = {}

        progress["phases"][phase].update(
            {
                "status": "completed",
                "completed_at": datetime.utcnow().isoformat() + "Z",
                "summary": summary,
            }
        )
        self._write_progress(progress)

    def mark_phase_failed(self, phase: str, error: str = "") -> None:
        """Mark a phase as failed.

        Args:
            phase: Phase name.
            error: Error message.
        """
        progress = self.read_progress() or {"phases": {}}

        if phase not in progress["phases"]:
            progress["phases"][phase] = {}

        progress["phases"][phase].update(
            {
                "status": "failed",
                "failed_at": datetime.utcnow().isoformat() + "Z",
                "error": error,
            }
        )
        self._write_progress(progress)

    def add_session_log(
        self, phase: str, session_id: str, model: str, turns: int = 0
    ) -> None:
        """Add a session log for a phase.

        Args:
            phase: Phase name.
            session_id: Claude SDK session ID.
            model: Claude model used.
            turns: Number of agent turns.
        """
        progress = self.read_progress() or {"phases": {}}

        if phase not in progress["phases"]:
            progress["phases"][phase] = {}

        if "sessions" not in progress["phases"][phase]:
            progress["phases"][phase]["sessions"] = []

        session_log = {
            "session_id": session_id,
            "model": model,
            "turns": turns,
            "logged_at": datetime.utcnow().isoformat() + "Z",
        }
        progress["phases"][phase]["sessions"].append(session_log)
        self._write_progress(progress)

    def read_progress(self) -> Optional[Dict[str, Any]]:
        """Read current progress.

        Returns:
            Progress dictionary or None if file doesn't exist.
        """
        if not self.progress_file.exists():
            return None

        with open(self.progress_file) as f:
            return json.load(f)

    def _write_progress(self, progress: Dict[str, Any]) -> None:
        """Write progress to file.

        Args:
            progress: Progress dictionary.
        """
        with open(self.progress_file, "w") as f:
            json.dump(progress, f, indent=2)
