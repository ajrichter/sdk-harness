# REST-to-GraphQL Migration Harness — Implementation Plan

## Context

We need to build a Python-based multi-agent workflow system that automates migrating REST API calls to GraphQL across JS and Java repositories. The system uses the **Claude Agent SDK** (`claude-agent-sdk` PyPI package) following Anthropic's [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) patterns: an orchestrator in Python code (not a Claude agent itself), per-phase Claude sessions with isolated context, subagents for parallel work within phases, inter-phase state on disk, validation hooks, and progress tracking.

The repo (`/home/user/sdk-harness`) is currently empty (only `README.md`). We are building from scratch on branch `claude/python-sdk-agent-flow-DP72N`.

---

## Input

A JSON configuration file containing:
- **REST endpoints** with search patterns (method, path, code patterns to grep for)
- **Attribute mappings** — old REST attributes to new GraphQL fields
- **Git repositories** (JS and Java) with URLs/branches

## Pipeline (5 Phases)

```
Discovery → Narrowing → Generation → Migration → Validation
     ↓          ↓            ↓            ↓           ↓
  [Gate]     [Gate]       [Gate]       [Gate]     [Final Report]
```

Each phase runs as a **separate `ClaudeSDKClient` session** (fresh context window) with phase-specific tools, permissions, and subagents. A Python orchestrator drives the pipeline, running validation gates between phases.

---

## Project Structure

```
sdk-harness/
├── pyproject.toml
├── .gitignore
├── src/migration_harness/
│   ├── __init__.py
│   ├── main.py                     # CLI entry point (asyncio runner)
│   ├── config.py                   # Load + validate JSON config
│   ├── schema.py                   # All Pydantic models
│   ├── orchestrator.py             # Pipeline controller (Python, not an agent)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── definitions.py          # ClaudeAgentOptions factories per phase
│   │   ├── prompts.py              # System prompts for each phase agent
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py             # In-process MCP server with custom tools
│   ├── hooks/
│   │   ├── __init__.py
│   │   ├── security.py             # Bash command allowlist hook
│   │   ├── validation_gates.py     # PreToolUse hooks validating save_* calls
│   ├── state/
│   │   ├── __init__.py
│   │   ├── manager.py              # JSON-file-based state persistence
│   │   ├── progress.py             # migration-progress.txt read/write
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── runner.py               # PhaseRunner — creates ClaudeSDKClient per phase
│   │   ├── gates.py                # Python validation between phases
│   │   ├── rollback.py             # Git-based savepoints and rollback
├── tests/
│   ├── conftest.py                 # Shared pytest fixtures
│   ├── fixtures/
│   │   ├── sample_config.json
│   │   ├── sample_discovery.json
│   │   ├── sample_narrowed.json
│   │   ├── sample_generated.json
│   │   ├── js_repo/                # Fake JS repo with REST calls
│   │   │   ├── package.json
│   │   │   └── src/api.js
│   │   └── java_repo/              # Fake Java repo with REST calls
│   │       ├── pom.xml
│   │       └── src/main/java/com/example/ApiClient.java
│   ├── unit/
│   │   ├── test_schema.py
│   │   ├── test_config.py
│   │   ├── test_state_manager.py
│   │   ├── test_progress.py
│   │   ├── test_gates.py
│   │   ├── test_rollback.py
│   │   └── test_tools.py
│   ├── integration/
│   │   ├── test_discovery_phase.py
│   │   ├── test_narrowing_phase.py
│   │   ├── test_generation_phase.py
│   │   ├── test_migration_phase.py
│   │   └── test_validation_phase.py
│   └── e2e/
│       └── test_full_pipeline.py
```

---

## Key Architectural Decisions

1. **Orchestrator is Python code, not a Claude agent.** It creates fresh `ClaudeSDKClient` sessions for each phase, maximizing context window per phase.

2. **Inter-phase state passes through disk (JSON files).** Custom MCP tools (`save_*_result` / `get_*_result`) bridge state between phases. No state passes through Claude context.

3. **Subagents within phases for parallelism.** Discovery: `repo-scanner` per repo. Generation: `graphql-generator` per migration. Validation: `build-checker` + `code-reviewer`. Defined via `AgentDefinition` in `ClaudeAgentOptions.agents`.

4. **Double-layered validation.** Hook-based validation (validates JSON structure during agent session) + gate-based validation (Python checks after phase, before next phase).

5. **Model selection per role.** Main phase agents: configurable (default Sonnet). Simple subagents: Haiku. Complex subagents: Sonnet.

6. **Git-based rollback.** Savepoints before migration phase, automatic rollback on failure.

---

## Agent Definitions Per Phase

### Phase 1: Discovery
- **Goal**: Scan all repos, find every REST endpoint usage
- **Tools**: `Read, Grep, Glob, Bash, Task` + `get_config, get_endpoints, save_discovery_result`
- **Subagent**: `repo-scanner` (per repo, tools: `Read, Grep, Glob`, model: Sonnet)
- **Permissions**: `acceptEdits` (needs Bash for git clone)
- **Output**: `DiscoveryResult` — list of `EndpointUsage` (endpoint_id, repo, file, line, snippet, language)

### Phase 2: Narrowing
- **Goal**: Filter usages to only those with complete attribute mappings
- **Tools**: `Read, Grep, Glob` + `get_config, get_mappings, get_discovery_result, save_narrowing_result`
- **Subagent**: none (analysis only)
- **Permissions**: read-only (`plan` mode)
- **Output**: `NarrowingResult` — list of `NarrowedUsage` (usage + matched_mappings + complexity)

### Phase 3: Generation
- **Goal**: Generate GraphQL queries/mutations for each narrowed usage
- **Tools**: `Read, Grep, Glob, Task` + `get_config, get_narrowing_result, get_graphql_schema, save_generation_result`
- **Subagent**: `graphql-generator` (per migration, model: Sonnet)
- **Permissions**: read-only (`plan` mode)
- **Output**: `GenerationResult` — list of `GeneratedMigration` (graphql_query, new_code, imports)

### Phase 4: Migration
- **Goal**: Apply generated code changes to actual repo files
- **Tools**: `Read, Write, Edit, Grep, Glob, Bash, Task` + `get_config, get_generation_result, save_migration_result`
- **Subagent**: `file-migrator` (per file, tools: `Read, Write, Edit, Grep, Glob`, model: Sonnet)
- **Permissions**: `acceptEdits`
- **Output**: `MigrationResult` — list of `AppliedMigration` (applied, diff, branch, commit)

### Phase 5: Validation
- **Goal**: Verify all migrations are correct (builds, tests, code review)
- **Tools**: `Read, Grep, Glob, Bash, Task` + `get_config, get_migration_result, get_generation_result, save_validation_result`
- **Subagents**: `build-checker` (Haiku, runs build/test), `code-reviewer` (Sonnet, reviews diffs)
- **Permissions**: `acceptEdits`
- **Output**: `ValidationResult` — list of `ValidationCheck` (check_name, passed, details)

---

## Custom MCP Tools (In-Process Server)

Using `@tool` decorator and `create_sdk_mcp_server()`:

| Tool | Purpose |
|------|---------|
| `get_config` | Returns full migration config as JSON |
| `get_endpoints` | Returns REST endpoints with search patterns |
| `get_mappings` | Returns attribute mappings |
| `get_graphql_schema` | Returns GraphQL schema file contents |
| `save_discovery_result` | Persists discovery output JSON |
| `get_discovery_result` | Loads discovery output JSON |
| `save_narrowing_result` | Persists narrowing output JSON |
| `get_narrowing_result` | Loads narrowing output JSON |
| `save_generation_result` | Persists generation output JSON |
| `get_generation_result` | Loads generation output JSON |
| `save_migration_result` | Persists migration output JSON |
| `get_migration_result` | Loads migration output JSON |
| `save_validation_result` | Persists validation output JSON |

---

## Validation Hooks

### PreToolUse Hooks
- **`bash_security_hook`**: Allowlists Bash commands (blocks `rm -rf`, `curl | sh`, etc.)
- **`validate_*_output`**: Attached to `save_*_result` tools — validates JSON parses as correct Pydantic model, blocks save if invalid

### Python Validation Gates (between phases)
- **After Discovery**: All repos scanned? At least 1 usage found?
- **After Narrowing**: At least 1 usage passes filter?
- **After Generation**: All migrations have non-empty graphql_query and new_code?
- **After Migration**: Log any failed applications (non-blocking, validation phase will verify)

---

## Configuration Schema (JSON Input)

```json
{
  "project_name": "my-migration",
  "work_dir": "/tmp/migration-workspace",
  "repositories": [
    { "name": "frontend", "url": "https://...", "branch": "main", "language": "javascript" }
  ],
  "rest_endpoints": [
    { "id": "get-user", "method": "GET", "path": "/api/v1/users/{id}",
      "patterns": ["fetch('/api/v1/users/'", "axios.get('/api/v1/users/'"] }
  ],
  "attribute_mappings": [
    { "endpoint_id": "get-user", "rest_attribute": "user_name",
      "graphql_field": "userName", "graphql_type": "User" }
  ],
  "graphql_endpoint": "https://api.example.com/graphql",
  "graphql_schema_path": "./schema.graphql",
  "options": {
    "dry_run": false, "create_branches": true,
    "branch_prefix": "migration/rest-to-graphql",
    "max_concurrent_repos": 2, "model": "claude-sonnet-4-5-20250929",
    "max_turns_per_phase": 50
  }
}
```

---

## Implementation Order (TDD)

### Step 1: Project Scaffolding
- `pyproject.toml` (deps: `claude-agent-sdk`, `pydantic`, `pytest`, `pytest-asyncio`, `anyio`)
- `.gitignore`
- All `__init__.py` files
- `tests/conftest.py` with shared fixtures

### Step 2: Schema + Config (write tests first)
- `tests/unit/test_schema.py` → `src/migration_harness/schema.py`
- `tests/unit/test_config.py` → `src/migration_harness/config.py`
- `tests/fixtures/sample_config.json`

### Step 3: State Management (write tests first)
- `tests/unit/test_state_manager.py` → `src/migration_harness/state/manager.py`
- `tests/unit/test_progress.py` → `src/migration_harness/state/progress.py`

### Step 4: Validation Gates + Rollback (write tests first)
- `tests/unit/test_gates.py` → `src/migration_harness/pipeline/gates.py`
- `tests/unit/test_rollback.py` → `src/migration_harness/pipeline/rollback.py`

### Step 5: Custom Tools + Hooks
- `tests/unit/test_tools.py` → `src/migration_harness/tools/registry.py`
- `src/migration_harness/hooks/security.py`
- `src/migration_harness/hooks/validation_gates.py`

### Step 6: Agent Definitions + Phase Runner
- `src/migration_harness/agents/prompts.py` (all system prompts)
- `src/migration_harness/agents/definitions.py` (all `create_*_options` factories)
- `src/migration_harness/pipeline/runner.py`

### Step 7: Orchestrator + CLI
- `src/migration_harness/orchestrator.py`
- `src/migration_harness/main.py`

### Step 8: Test Fixtures + Integration Tests
- `tests/fixtures/js_repo/` and `tests/fixtures/java_repo/`
- `tests/fixtures/sample_discovery.json`, etc.
- `tests/integration/test_*_phase.py`

### Step 9: E2E Tests
- `tests/e2e/test_full_pipeline.py`

---

## Verification

1. **Unit tests**: `pytest tests/unit/ -v` — all pass, no SDK calls needed
2. **Integration tests**: `pytest tests/integration/ -v` — use mocked `ClaudeSDKClient`
3. **E2E test** (requires `ANTHROPIC_API_KEY`): `pytest tests/e2e/ -v -m e2e` — runs full pipeline against fixture repos
4. **Manual test**: `python -m migration_harness --config tests/fixtures/sample_config.json` — runs CLI against fixture repos, check `migration-progress.txt` for phase status
5. **Validate progress tracking**: After each phase, `migration-progress.txt` shows correct status markers and session log

---

## Sources
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Building Agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Claude Agent SDK Python (GitHub)](https://github.com/anthropics/claude-agent-sdk-python)
- [Claude Agent SDK (PyPI)](https://pypi.org/project/claude-agent-sdk/)
- [Agent SDK Reference - Python](https://platform.claude.com/docs/en/agent-sdk/python)
