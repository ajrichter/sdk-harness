# Plan: Multi-JSON Pipeline, Client Mapping, HOW-TO-USE, and uv Integration

## Context

The migration harness on branch `claude/python-sdk-agent-flow-DP72N` has a working 5-phase pipeline (141 tests passing), but currently only accepts a single monolithic `config.json`. The user wants to:

1. **Write a HOW-TO-USE.md** to the repo on the branch
2. **Add `uv` commands** for running everything (install, test, lint, CLI)
3. **Enhance JSON parsing** to support a multi-JSON pipeline (separate files for endpoints, attributes, mappings)
4. **Add client_id → endpoint_id mapping** so users can group endpoints by client/service
5. **Add rules matching** to validate discovered endpoints against expected per-client rules
6. **Keep it flexible** — no rigid Pydantic schema required for input files; CSV support

Main branch (`origin/main`) has only the initial commit. All work stays on `claude/python-sdk-agent-flow-DP72N`.

---

## Files to Create

| File | Purpose |
|------|---------|
| `HOW-TO-USE.md` | User-facing guide: setup with uv, config format, CLI usage, outputs |
| `src/migration_harness/loaders.py` | `FlexibleLoader` — parse JSON/CSV/JSONL without rigid schema |
| `src/migration_harness/mapping.py` | `ClientEndpointMap` + `RulesMatcher` — client_id → endpoint_id[] resolution + rules matching |
| `tests/unit/test_loaders.py` | Tests for FlexibleLoader (JSON arrays, CSV, JSONL, key validation) |
| `tests/unit/test_mapping.py` | Tests for client mapping, rules matching, coverage reports |
| `tests/fixtures/endpoints.json` | Sample multi-JSON: standalone endpoints list |
| `tests/fixtures/attributes.csv` | Sample CSV: attribute mappings |
| `tests/fixtures/client_mapping.json` | Sample: client_id → [endpoint_ids] |
| `tests/fixtures/rules.json` | Sample: expected endpoints per client for validation |

## Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `[tool.uv]` section, add `uv` scripts/commands in comments |
| `src/migration_harness/config.py` | Extend `load_config()` to accept multi-file mode via `data_dir` |
| `src/migration_harness/tools/registry.py` | Add `get_client_endpoints()`, `get_rules_report()`, `validate_rules()` tools |
| `src/migration_harness/pipeline/gates.py` | Add `validate_rules_gate()` for rules matching after discovery |
| `src/migration_harness/schema.py` | Add `ClientMapping`, `RulesReport` models (lightweight, `extra="allow"`) |
| `src/migration_harness/state/manager.py` | Add `save_rules_report()` / `get_rules_report()` |
| `tests/conftest.py` | Add fixtures for client mapping and rules data |

---

## Implementation Steps

### Step 1: HOW-TO-USE.md + uv integration

Create `HOW-TO-USE.md` with:
- Prerequisites (Python 3.11+, uv)
- Quick start with `uv`
- All CLI commands using `uv run`
- Config file format (single-file and multi-file modes)
- Understanding pipeline output
- Example end-to-end workflow

Update `pyproject.toml`:
- Add `[project.scripts]` entry for `migration-harness`
- Document uv commands in HOW-TO-USE.md:
  ```bash
  uv sync                          # Install deps
  uv run pytest tests/unit/ -v     # Unit tests
  uv run pytest tests/ -v          # All tests
  uv run migration-harness --config config.json
  uv run ruff check src/           # Lint
  uv run black src/ tests/         # Format
  ```

### Step 2: FlexibleLoader (`loaders.py`)

A loader that reads JSON/CSV/JSONL without requiring a Pydantic model:

```python
class FlexibleLoader:
    @staticmethod
    def load_json(path: str) -> List[Dict[str, Any]]:
        """Load JSON file. Handles: array, single object (wraps in list), nested key."""

    @staticmethod
    def load_csv(path: str) -> List[Dict[str, Any]]:
        """Load CSV with header row using stdlib csv.DictReader."""

    @staticmethod
    def load_jsonl(path: str) -> List[Dict[str, Any]]:
        """Load newline-delimited JSON."""

    @staticmethod
    def load_auto(path: str) -> List[Dict[str, Any]]:
        """Auto-detect format from extension (.json, .csv, .jsonl)."""

    @staticmethod
    def validate_keys(data: List[Dict], required_keys: Set[str]) -> List[str]:
        """Check required keys exist in every row. Returns list of error messages."""
```

Key design: returns `List[Dict[str, Any]]` — generic dicts with extra fields preserved. No Pydantic required. The `validate_keys()` method lets callers say "this file must have endpoint_id and method columns" without a full schema.

### Step 3: Client-Endpoint Mapping (`mapping.py`)

```python
class ClientEndpointMap:
    """Resolves client_id → endpoint_id[] from a mapping file."""

    @classmethod
    def from_file(cls, path: str) -> "ClientEndpointMap":
        """Load from JSON or CSV. Expects 'client_id' and 'endpoint_id' columns."""

    def get_endpoints(self, client_id: str) -> List[str]:
        """Return endpoint_ids for a client."""

    def get_clients(self, endpoint_id: str) -> List[str]:
        """Reverse lookup: which clients use this endpoint."""

    def all_client_ids(self) -> List[str]
    def all_endpoint_ids(self) -> List[str]

class RulesMatcher:
    """Validates discovered endpoints against expected rules per client."""

    def __init__(self, client_map: ClientEndpointMap): ...

    def match(self, discovered_endpoint_ids: Set[str], client_id: str) -> RulesReport:
        """Compare discovered vs expected. Returns found/missing/unexpected."""

    def match_all(self, discovered: Set[str]) -> Dict[str, RulesReport]:
        """Run match() for every client_id."""
```

`RulesReport` is a simple dataclass:
```python
class RulesReport(BaseModel):
    client_id: str
    expected: List[str]
    found: List[str]
    missing: List[str]
    unexpected: List[str]
    coverage_pct: float  # found / expected * 100
```

### Step 4: Extend config.py for multi-file mode

```python
def load_config(config_source: Union[str, Dict]) -> Config:
    """Existing — single JSON file."""

def load_multi_config(
    config_path: str,
    endpoints_path: str | None = None,
    attributes_path: str | None = None,
    client_mapping_path: str | None = None,
) -> Tuple[Config, ClientEndpointMap | None]:
    """Load config + optional sidecar files."""
```

If `endpoints_path` is provided, its contents override `config.rest_endpoints`. Same for `attributes_path` → `config.attribute_mappings`. The base config still provides `project_name`, `work_dir`, `repositories`, etc.

### Step 5: Wire into tools, gates, and state

- **ToolRegistry**: Add `get_client_endpoints(client_id)`, `get_rules_report()`, `validate_rules(discovered_ids)`
- **Gates**: Add `validate_rules_gate(rules_report)` — fails if any client has 0% coverage
- **StateManager**: Add `save_rules_report()` / `get_rules_report()` for persistence

### Step 6: Test fixtures + tests

Create fixture files:
- `endpoints.json` — array of endpoint dicts with extra fields
- `attributes.csv` — CSV with header: endpoint_id,rest_attribute,graphql_field,graphql_type
- `client_mapping.json` — `{"client_a": ["get-user", "create-post"], "client_b": ["get-user"]}`
- `rules.json` — same format, used for validation

Write tests:
- `test_loaders.py`: JSON array, JSON object, CSV, JSONL, auto-detect, key validation, malformed input
- `test_mapping.py`: Load from JSON, load from CSV, get_endpoints, get_clients, reverse lookup, match found/missing/unexpected, match_all, coverage percentage, empty mapping

---

## Verification

```bash
# Install with uv
uv sync

# Run all unit tests (should be ~165+ passing)
uv run pytest tests/unit/ -v

# Run specific new tests
uv run pytest tests/unit/test_loaders.py tests/unit/test_mapping.py -v

# Run full suite
uv run pytest tests/ -v

# Verify CLI still works
uv run migration-harness --config tests/fixtures/sample_config.json --status

# Lint
uv run ruff check src/
```

All existing 141 tests must still pass. New tests add ~25-30 more.

---

## What This Does NOT Change

- Existing Config/schema.py models remain backward-compatible
- Existing single-file `load_config()` still works
- Pipeline phases (discovery → validation) unchanged
- Orchestrator loop unchanged
- All existing tests unmodified
