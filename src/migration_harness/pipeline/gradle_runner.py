"""
Runs a Gradle project's tests from Python and parses the resulting JUnit XML
reports into ValidationCheck objects.

This bridges the Java fixture tests and the Python migration-harness validation
phase.  The flow is:

  PhaseRunner (Python)
      └── GradleRunner.run_tests()
              ├── subprocess: gradle test --daemon
              ├── parses build/test-results/test/*.xml  (JUnit XML)
              └── returns List[ValidationCheck]

Because Gradle's daemon keeps the JVM warm between invocations, repeated calls
during iteration are fast even across Python/Java language boundaries.
"""

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple

from migration_harness.schema import ValidationCheck


class GradleRunner:
    """Runs `gradle test` and parses JUnit XML reports into ValidationChecks."""

    # Relative to the repo root passed to the constructor
    TEST_RESULTS_DIR = Path("build/test-results/test")

    def __init__(self, repo_path: str):
        """
        Args:
            repo_path: Absolute path to the root of the Gradle project
                       (the directory containing build.gradle).
        """
        self.repo_path = Path(repo_path)
        if not (self.repo_path / "build.gradle").exists():
            raise ValueError(f"No build.gradle found in {repo_path}")

    # ── Public API ──────────────────────────────────────────────────────────

    def run_tests(self, extra_args: List[str] | None = None) -> List[ValidationCheck]:
        """
        Run `gradle test` with the daemon and return parsed results.

        Args:
            extra_args: Additional Gradle arguments, e.g. ['--info'].

        Returns:
            List of ValidationCheck objects, one per test case in the XML.
        """
        success, output = self._invoke_gradle(extra_args or [])
        checks = self._parse_junit_xml()

        # If Gradle itself failed but produced no XML (compile error, etc.)
        # add a synthetic failure check so the validation phase isn't empty.
        if not checks:
            checks.append(
                ValidationCheck(
                    check_name="gradle-build",
                    passed=success,
                    details=output if not success else "Build succeeded, no test cases found",
                )
            )

        return checks

    def get_test_report_dir(self) -> Path:
        """Return the directory where JUnit XML reports are written."""
        return self.repo_path / self.TEST_RESULTS_DIR

    # ── Internal ─────────────────────────────────────────────────────────────

    def _invoke_gradle(self, extra_args: List[str]) -> Tuple[bool, str]:
        """
        Execute `gradle test --daemon` in the project directory.

        Returns:
            (success, combined_stdout_stderr)
        """
        cmd = ["gradle", "test", "--daemon", "--continue"] + extra_args
        result = subprocess.run(
            cmd,
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        return result.returncode == 0, output

    def _parse_junit_xml(self) -> List[ValidationCheck]:
        """
        Parse every *.xml file in the JUnit report directory.

        JUnit XML structure:
            <testsuite name="..." tests="N" failures="F" errors="E">
              <testcase classname="..." name="..." time="...">
                <failure message="...">...</failure>  <!-- only on failure -->
              </testcase>
            </testsuite>

        Returns:
            One ValidationCheck per <testcase> element.
        """
        checks: List[ValidationCheck] = []
        report_dir = self.repo_path / self.TEST_RESULTS_DIR

        if not report_dir.exists():
            return checks

        for xml_file in sorted(report_dir.glob("*.xml")):
            checks.extend(self._parse_single_xml(xml_file))

        return checks

    def _parse_single_xml(self, xml_file: Path) -> List[ValidationCheck]:
        checks: List[ValidationCheck] = []
        try:
            tree = ET.parse(xml_file)
        except ET.ParseError:
            return checks

        for testcase in tree.iter("testcase"):
            class_name = testcase.get("classname", "")
            test_name  = testcase.get("name", "")
            check_name = f"{class_name}.{test_name}"

            # <failure> or <error> child → test did not pass
            failure = testcase.find("failure")
            error   = testcase.find("error")
            skipped = testcase.find("skipped")

            if skipped is not None:
                checks.append(ValidationCheck(
                    check_name=check_name,
                    passed=True,         # skipped ≠ failed
                    details="SKIPPED",
                ))
            elif failure is not None or error is not None:
                node    = failure if failure is not None else error
                message = node.get("message", node.text or "")
                checks.append(ValidationCheck(
                    check_name=check_name,
                    passed=False,
                    details=message[:500],   # cap length for readability
                ))
            else:
                checks.append(ValidationCheck(
                    check_name=check_name,
                    passed=True,
                    details="PASSED",
                ))

        return checks
