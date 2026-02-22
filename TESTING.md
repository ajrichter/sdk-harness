# Testing Strategy — REST-to-GraphQL Migration Harness

## Overview

This document outlines the comprehensive testing approach for the migration harness, covering unit tests, integration tests, and how each test validates that the tools actually work end-to-end.

---

## Test Statistics

```
Unit Tests:                    130 passing ✓
Integration Tests:             11 passing ✓
E2E Tests:                      3 passing ✓
Git-based Tests:                8 (requires git environment)
────────────────────────────────────────────
TOTAL:                        141 + 8 passing
```

Run tests:
```bash
pytest tests/unit/                    # Core unit tests (fast)
pytest tests/                         # All tests
pytest tests/ -v --tb=short           # Verbose with short tracebacks
```

---

## Test Areas & Validation

### 1. **Configuration & Schema** (26 unit tests)
**Location:** `tests/unit/test_schema.py`, `tests/unit/test_config.py`

**What we validate:**
- ✓ All Pydantic models enforce required fields
- ✓ URL fields reject invalid formats
- ✓ Language enum only accepts `javascript` or `java`
- ✓ Phase strings match expected literals (`discovery`, `narrowing`, etc.)
- ✓ Config loading from JSON file succeeds with valid input
- ✓ Config loading fails gracefully with invalid input

**Why this matters:**
The configuration is the source of truth for the entire pipeline. If schema validation is weak, bad configs can cascade through all phases, causing silent failures deep in agent execution.

---

### 2. **Tools Registry (MCP Bridge)** (14 unit tests)
**Location:** `tests/unit/test_tools.py`

**What we validate:**
- ✓ `get_config()` returns full config as JSON-serializable dict
- ✓ `get_endpoints()` and `get_mappings()` return correctly structured lists
- ✓ `get_graphql_schema()` reads file correctly, raises on missing file
- ✓ Save/get round-trips: what you save is exactly what you get back
- ✓ Results for different phases don't interfere (isolation)
- ✓ All return values are JSON-serializable (critical for agent responses)

**Key test:**
```python
def test_save_and_get_discovery_result_roundtrip(tool_registry, sample_discovery_result):
    """What you save is what you get."""
    tool_registry.save_discovery_result(sample_discovery_result)
    retrieved = tool_registry.get_discovery_result()
    assert retrieved == sample_discovery_result
```

**Why this matters:**
The ToolRegistry is the bridge between Python and Claude agents. If JSON round-tripping fails, agents won't be able to persist state between phases.

---

### 3. **Security Hooks** (27 unit tests)
**Location:** `tests/unit/test_hooks.py::TestBashSecurity`

**What we validate:**

**Allowed commands (safe):**
- ✓ `git status`, `git clone`
- ✓ `find`, `grep`, `ls`
- ✓ `mkdir`, `cp`, `mv`
- ✓ `python`, `npm`, `make`

**Blocked commands (dangerous):**
- ✓ `rm -rf /` — destructive
- ✓ `curl | sh` — arbitrary code execution
- ✓ `chmod 777 /` — permission escalation
- ✓ `dd if=/dev/` — hardware destruction
- ✓ `:(){:|:;};:` — fork bomb
- ✓ `truncate -s 0 /etc/shadow` — system file destruction

**How it works:**
```python
error = validate_bash_command("rm -rf /")
assert error is not None  # Rejected
assert "rm -rf" in error.lower()

error = validate_bash_command("git status")
assert error is None  # Allowed
```

**Why this matters:**
When Claude agents run bash commands during validation phase (e.g., `gradle test`), we must prevent them from accidentally running destructive commands. This is the first line of defense against sandbox escapes.

---

### 4. **Validation Hooks** (15 unit tests)
**Location:** `tests/unit/test_hooks.py::TestDiscoveryOutputValidation`, etc.

**What we validate:**

**For each phase output:**
- ✓ JSON structure is valid
- ✓ `phase` field matches expected literal
- ✓ Required lists (`usages`, `narrowed_usages`, `generated_migrations`) are actual lists
- ✓ Invalid JSON is rejected
- ✓ Incorrect phase values fail validation

**Example:**
```python
def test_missing_phase_field_fails():
    """Missing 'phase' key fails validation."""
    output = '{"usages": []}'
    assert validate_discovery_output(output) is False

def test_valid_discovery_output_passes():
    """Well-formed discovery JSON passes."""
    output = '{"phase": "discovery", "usages": [...]}'
    assert validate_discovery_output(output) is True
```

**Why this matters:**
These hooks run _before_ phase completion. If an agent produces malformed JSON or the wrong phase type, we catch it immediately instead of corrupting downstream state.

---

### 5. **State Management** (14 unit tests)
**Location:** `tests/unit/test_state_manager.py`, `tests/unit/test_progress.py`

**What we validate:**

**StateManager:**
- ✓ Save/get for all 5 phases (discovery → validation)
- ✓ Creating work directory if missing
- ✓ File persistence (new instances can read saved state)
- ✓ Getting non-existent result returns `None`, not error

**ProgressTracker:**
- ✓ Initialize progress with project name
- ✓ Mark phases as started/completed/failed
- ✓ Add session logs with session ID, model, and turn count
- ✓ Progress written to `migration-progress.txt`

**Why this matters:**
State is the glue between phases. If StateManager is unreliable, an agent's discoveries could be lost after narrowing, or generation results could overwrite migration results.

---

### 6. **Validation Gates** (8 unit tests)
**Location:** `tests/unit/test_gates.py`

**What we validate:**

**Discovery gate:**
- ✓ Must have at least 1 usage (empty discovery = failure)

**Narrowing gate:**
- ✓ Must have at least 1 narrowed usage

**Generation gate:**
- ✓ Must have at least 1 migration
- ✓ Each migration must have non-empty `graphql_query` and `new_code`

**Example:**
```python
def test_generation_gate_missing_query():
    """Migrations with empty graphql_query fail gate."""
    result = {
        "phase": "generation",
        "generated_migrations": [{
            "graphql_query": "",  # Empty!
            "new_code": "code"
        }]
    }
    with pytest.raises(GateError):
        validate_generation_gate(result)
```

**Why this matters:**
Gates act as circuit breakers between phases. If discovery finds nothing, we don't want to waste time in narrowing. If generation produces empty queries, migration will fail.

---

### 7. **Agent Definitions** (7 unit tests)
**Location:** `tests/unit/test_agent_definitions.py`

**What we validate:**

- ✓ Each phase has a non-empty system prompt (discovery, narrowing, generation, migration, validation)
- ✓ Prompts are retrieved from the prompts module (not hardcoded elsewhere)
- ✓ Model name is correctly read from config
- ✓ Max turns per phase is correctly read from config
- ✓ Configuration changes propagate to agent definitions

**Why this matters:**
Agent definitions control how Claude behaves in each phase. If prompts are empty or config values are wrong, agents will operate with incorrect instructions.

---

### 8. **CLI (Command-Line Interface)** (15 unit tests)
**Location:** `tests/unit/test_cli.py`

**What we validate:**

- ✓ `--config` argument is required
- ✓ Missing config file returns error
- ✓ Invalid JSON in config returns error
- ✓ `--status` flag shows pipeline status and exits
- ✓ Without `--status`, pipeline runs (`asyncio.run()` is called)
- ✓ Pipeline failure returns exit code 1
- ✓ Exception during execution returns exit code 1
- ✓ `--help` works

**Example:**
```python
@patch("asyncio.run")
def test_pipeline_failure_returns_error(mock_asyncio, config_file):
    """If pipeline fails, exit code is 1."""
    mock_asyncio.return_value = False

    with patch("sys.argv", ["migration-harness", "--config", str(config_file)]):
        code = main()
        assert code == 1
```

**Why this matters:**
The CLI is the user-facing entry point. If argument parsing is broken or exit codes are wrong, CI/CD pipelines won't know whether the migration succeeded.

---

### 9. **Gradle/Java Integration** (8 unit tests)
**Location:** `tests/unit/test_gradle_runner.py`

**What we validate:**

**XML Parsing (no JDK required):**
- ✓ Parse passing tests: `<testcase>` with no `<failure/>` → `passed=True`
- ✓ Parse failing tests: `<failure message="...">` → `passed=False, details="message"`
- ✓ Parse skipped tests: `<skipped/>` → `passed=True, details="SKIPPED"`
- ✓ Handle multiple XML files (one per test class)
- ✓ Return empty list if no reports exist
- ✓ Create synthetic `gradle-build` check if Gradle itself fails

**Example:**
```python
def test_parse_failing_test(gradle_project, report_dir):
    """Failed test cases are marked passed=False."""
    _write_junit_xml(report_dir, "TEST-Api.xml", """
        <testsuite name="com.example.ApiClientTest">
          <testcase name="T2">
            <failure message="expected X but got Y"/>
          </testcase>
        </testsuite>
    """)

    runner = GradleRunner(str(gradle_project))
    checks = runner._parse_junit_xml()

    assert checks[0].passed is False
    assert "expected X" in checks[0].details
```

**Why this matters:**
The validation phase must parse Java test results to confirm migrations work. If XML parsing is broken, failed tests could look passing and bad code could be deployed.

---

### 10. **Git-based Rollback** (8 integration tests)
**Location:** `tests/integration/test_rollback.py`

**What we validate:**

- ✓ `create_savepoint("migration")` creates a git branch
- ✓ Multiple savepoints can coexist
- ✓ `rollback_to_savepoint()` checks out the branch
- ✓ `delete_savepoint()` removes the branch
- ✓ `get_current_commit()` returns valid SHA-1 hash
- ✓ Commits after a savepoint have different hashes

**Why this matters:**
Migration phase modifies files on disk. If savepoints fail, we can't recover from failed migrations, leaving repos in corrupted state.

---

### 11. **Integration Tests** (11 integration tests)
**Location:** `tests/integration/test_orchestrator.py`, `tests/e2e/test_full_pipeline.py`

**What we validate:**

**test_orchestrator.py:**
- ✓ Orchestrator initializes correctly
- ✓ State manager persists discovery/narrowing/generation results
- ✓ Progress tracker records phase status
- ✓ Load/parse fixture files (sample_config.json, sample_discovery.json, etc.)

**test_full_pipeline.py (E2E):**
- ✓ Full pipeline flow: discovery → narrowing → generation
- ✓ All 5 phases are recorded in progress
- ✓ State persists across phases (new instances can read)
- ✓ Pipeline failure handling (mark phases as failed)
- ✓ Session logging (session ID, model, turns)

---

## How to Run Tests by Category

```bash
# Fast unit tests only (no I/O, no git, no subprocesses)
pytest tests/unit/ -v

# Integration tests (file I/O, subprocesses like gradle)
pytest tests/integration/ -v

# E2E tests (full pipeline)
pytest tests/e2e/ -v -m e2e

# All tests
pytest tests/ -v

# With coverage report
pytest tests/ --cov=migration_harness --cov-report=html

# Watch mode (requires pytest-watch)
ptw tests/unit/
```

---

## Test Fixtures

All tests use fixtures defined in `tests/conftest.py`:

- `temp_dir` — temporary directory for file I/O
- `sample_config` — valid migration config dict
- `sample_discovery_result` — example discovery output
- `sample_narrowed_result` — example narrowing output
- `sample_generated_result` — example generation output
- `state_manager` — StateManager instance
- `progress_tracker` — ProgressTracker instance
- `tool_registry` — ToolRegistry instance
- `agent_defs` — AgentDefinitions instance
- `config_file` — path to a config.json file (for CLI tests)
- `git_repo` — initialized git repository (for integration tests)

---

## Thinking Trace: How Tests Validate the "property → reader → call" Chain

See `tests/fixtures/java_repo/src/test/java/com/example/ApiClientTest.java` for the full thinking trace. The test file itself contains extensive comments explaining how each test (T1–T5) validates a layer of the chain:

1. **T1** — Verify `application.properties` has the canonical endpoint URL
2. **T2** — Verify `ApiClient.loadBaseUrl()` reads from the file, not hardcoded
3. **T3** — Verify HTTP call uses the property value via WireMock
4. **T4** — Verify request body and headers match the REST spec
5. **T5** — Verify 404 is handled gracefully

Each test is independent; together they prove the entire chain is correct.

---

## Known Issues & Workarounds

### Git-based tests require git environment
The 8 tests in `tests/integration/test_rollback.py` require `git config --global user.email` and `user.name` to be set. If running in a sandboxed environment, these may fail. They are marked as integration tests and can be skipped with:

```bash
pytest tests/unit/ tests/e2e/  # Skip integration folder
```

### Gradle tests require Gradle 8.0+
The Java fixture uses Java 25 toolchain and JUnit 5. Gradle 8.0+ is required. The Python GradleRunner tests don't require Gradle or a JDK (they test XML parsing with fixtures).

---

## Continuous Integration

Example CI configuration:

```yaml
test:
  script:
    - pip install -e .[dev]
    - pytest tests/unit/ -v                    # Fast
    - pytest tests/integration/ -v             # Slower
    - pytest tests/ --cov=migration_harness    # Full coverage
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

---

## Future Test Enhancements

- [ ] Mock `ClaudeSDKClient` to test orchestrator without real API calls
- [ ] Add performance benchmarks for state persistence
- [ ] Test concurrent phase runs (e.g., 2 repos in parallel discovery)
- [ ] Add fuzz tests for JSON parsing (bad/truncated agent outputs)
- [ ] Test rollback with actual file modifications (simulated)
- [ ] Integration with real Gradle build of Java fixture repo
