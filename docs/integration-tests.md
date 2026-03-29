---
description: Run the real integration smoke tests against Clockify.
---

# Integration smoke tests

Use the integration smoke test script to validate real CLI behavior against your
Clockify account. The script is fully non-interactive. It first inspects recent
usage logs to pick representative Dribia-flavoured smoke inputs, then falls
back to stable defaults like `Cross-selling` and `Brokerages` when logs are
missing or incomplete. The `start_stop` case cleans up after itself by deleting
its created time entry.

## TL;DR

```bash
uv run python scripts/integration_smoke.py
```

The script prepends the repository root to `sys.path`, so direct execution works
reliably from the repo checkout.

## What it covers

| Case | Purpose | Notes |
|------|---------|-------|
| `start_stop` | Start → status → stop | Uses recent logged Dribia command hints or falls back to `Cross-selling` |
| `missing_tag` | Missing tag sentinel | Uses logged hints or falls back to `Brokerages` |
| `list_entries` | List recent entries | Validates table output |
| `status_json` | JSON output | Ensures JSON parses |

## Run all cases

```bash
clocky integration-test
```

```bash
uv run python scripts/integration_smoke.py
```

## Run a single case

```bash
clocky integration-test --case start_stop
```

```bash
uv run python scripts/integration_smoke.py --case start_stop
```

## Inspect the selected plan

```bash
clocky integration-test --plan
uv run python scripts/integration_smoke.py --plan
```

This prints the chosen projects, the log files inspected, fallback cases, and up
to five recent representative commands per smoke case.

## Override project selection

Set environment variables to force the project names used by the script:

| Variable | Description |
|----------|-------------|
| `CLOCKY_TEST_PROJECT` | Project name for `start_stop` |
| `CLOCKY_TEST_PROJECT_MISSING_TAG` | Project name for `missing_tag` |

Example:

```bash
CLOCKY_TEST_PROJECT="Cross-selling" \
CLOCKY_TEST_PROJECT_MISSING_TAG="Brokerages" \
uv run python scripts/integration_smoke.py
```

## Change the CLI binary

By default the smoke runner now uses `python -m clocky.cli` from the active
environment. To point at a different executable, set `CLOCKY_INTEGRATION_CLI`:

```bash
CLOCKY_INTEGRATION_CLI="clocky" uv run python scripts/integration_smoke.py
```

## Notes

- `--history-limit` is kept for CLI compatibility, but planning is now log-driven.
- When no logs exist, smoke tests use the Dribia defaults above.
- The `missing_tag` case probes recent candidates with `start --dry-run` and only
  uses one that still emits `CLOCKY_ERROR_MISSING_TAG_MAP`.
- Representative commands influence test inputs only; assertions stay deterministic.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All cases passed |
| 1 | At least one case failed |
