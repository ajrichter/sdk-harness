"""
Unit tests for GradleRunner.

These tests cover the JUnit XML parsing logic only — they do NOT invoke
Gradle or require a JDK.  The subprocess path is tested at integration level.
"""

import textwrap
from pathlib import Path

import pytest

from migration_harness.pipeline.gradle_runner import GradleRunner
from migration_harness.schema import ValidationCheck


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_junit_xml(dir_path: Path, filename: str, xml: str) -> None:
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / filename).write_text(textwrap.dedent(xml))


@pytest.fixture
def gradle_project(tmp_path: Path) -> Path:
    """Fake Gradle project directory with a build.gradle stub."""
    (tmp_path / "build.gradle").write_text("// stub")
    return tmp_path


@pytest.fixture
def report_dir(gradle_project: Path) -> Path:
    return gradle_project / "build" / "test-results" / "test"


# ── constructor ───────────────────────────────────────────────────────────────

def test_raises_if_no_build_gradle(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No build.gradle"):
        GradleRunner(str(tmp_path))


def test_accepts_project_with_build_gradle(gradle_project: Path) -> None:
    runner = GradleRunner(str(gradle_project))
    assert runner.repo_path == gradle_project


# ── XML parsing: passing tests ────────────────────────────────────────────────

def test_parse_all_passing_tests(gradle_project: Path, report_dir: Path) -> None:
    """
    THINKING: A passing testcase has no <failure> or <error> child.
    We expect passed=True and details='PASSED'.
    """
    _write_junit_xml(report_dir, "TEST-ApiClientTest.xml", """\
        <?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="com.example.ApiClientTest" tests="3">
          <testcase classname="com.example.ApiClientTest"
                    name="T1 — application.properties contains api.base-url"
                    time="0.012"/>
          <testcase classname="com.example.ApiClientTest"
                    name="T2 — loadBaseUrl() reads api.base-url from properties, not hardcoded"
                    time="0.008"/>
          <testcase classname="com.example.ApiClientTest"
                    name="T3 — getUser() makes GET /api/v1/users/{id} to the configured base URL"
                    time="0.105"/>
        </testsuite>
    """)

    runner = GradleRunner(str(gradle_project))
    checks = runner._parse_junit_xml()

    assert len(checks) == 3
    assert all(c.passed for c in checks)
    assert all(c.details == "PASSED" for c in checks)
    assert "T1" in checks[0].check_name
    assert "T2" in checks[1].check_name
    assert "T3" in checks[2].check_name


# ── XML parsing: failing test ─────────────────────────────────────────────────

def test_parse_failing_test(gradle_project: Path, report_dir: Path) -> None:
    """
    THINKING: A failing testcase has a <failure> child whose message
    attribute is the concise failure summary.  We map this to passed=False
    and put the message in details so the validation report is readable.
    """
    _write_junit_xml(report_dir, "TEST-ApiClientTest.xml", """\
        <?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="com.example.ApiClientTest" tests="1" failures="1">
          <testcase classname="com.example.ApiClientTest"
                    name="T2 — loadBaseUrl() reads api.base-url from properties, not hardcoded"
                    time="0.001">
            <failure message="expected: &lt;https://api.example.com&gt; but was: &lt;hardcoded&gt;">
              org.opentest4j.AssertionFailedError: expected: ...
            </failure>
          </testcase>
        </testsuite>
    """)

    runner = GradleRunner(str(gradle_project))
    checks = runner._parse_junit_xml()

    assert len(checks) == 1
    assert checks[0].passed is False
    assert "hardcoded" in checks[0].details


# ── XML parsing: skipped test ─────────────────────────────────────────────────

def test_parse_skipped_test(gradle_project: Path, report_dir: Path) -> None:
    """
    THINKING: A skipped test (<skipped/>) is not a failure — the test was
    intentionally disabled.  We report passed=True with details='SKIPPED'
    so the validation phase doesn't block the pipeline.
    """
    _write_junit_xml(report_dir, "TEST-ApiClientTest.xml", """\
        <?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="com.example.ApiClientTest" tests="1" skipped="1">
          <testcase classname="com.example.ApiClientTest"
                    name="T5 — disabled"
                    time="0.000">
            <skipped/>
          </testcase>
        </testsuite>
    """)

    runner = GradleRunner(str(gradle_project))
    checks = runner._parse_junit_xml()

    assert len(checks) == 1
    assert checks[0].passed is True
    assert checks[0].details == "SKIPPED"


# ── XML parsing: multiple report files ───────────────────────────────────────

def test_parse_multiple_xml_files(gradle_project: Path, report_dir: Path) -> None:
    """
    THINKING: Gradle writes one XML file per test class.  We must aggregate
    all files so the Python validation phase sees the full picture.
    """
    _write_junit_xml(report_dir, "TEST-ApiClientTest.xml", """\
        <?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="com.example.ApiClientTest" tests="1">
          <testcase classname="com.example.ApiClientTest" name="T1" time="0.01"/>
        </testsuite>
    """)
    _write_junit_xml(report_dir, "TEST-AnotherTest.xml", """\
        <?xml version="1.0" encoding="UTF-8"?>
        <testsuite name="com.example.AnotherTest" tests="2">
          <testcase classname="com.example.AnotherTest" name="A1" time="0.01"/>
          <testcase classname="com.example.AnotherTest" name="A2" time="0.01"/>
        </testsuite>
    """)

    runner = GradleRunner(str(gradle_project))
    checks = runner._parse_junit_xml()

    assert len(checks) == 3
    assert all(c.passed for c in checks)


# ── no report directory ───────────────────────────────────────────────────────

def test_returns_empty_list_when_no_reports(gradle_project: Path) -> None:
    """
    THINKING: If the build never ran (e.g. compile error before tests), the
    report directory doesn't exist.  We must return an empty list, not raise.
    The caller (run_tests) will synthesise a synthetic failure check.
    """
    runner = GradleRunner(str(gradle_project))
    checks = runner._parse_junit_xml()
    assert checks == []


# ── synthetic check on build failure ─────────────────────────────────────────

def test_run_tests_synthetic_check_on_compile_error(gradle_project: Path) -> None:
    """
    THINKING: When Gradle itself fails (non-zero exit) and produces no XML,
    run_tests() must still return at least one ValidationCheck so the
    validation phase result is non-empty and correctly marked failed.

    We don't invoke real Gradle; we patch _invoke_gradle and _parse_junit_xml.
    """
    runner = GradleRunner(str(gradle_project))

    # Monkey-patch to simulate compile failure with no XML output
    runner._invoke_gradle = lambda _: (False, "error: package does not exist")
    runner._parse_junit_xml = lambda: []

    checks = runner.run_tests()

    assert len(checks) == 1
    assert checks[0].check_name == "gradle-build"
    assert checks[0].passed is False
    assert "package does not exist" in checks[0].details
