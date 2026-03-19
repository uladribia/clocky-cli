---
description: Run the real integration smoke tests against Clockify.
---

# Integration smoke tests

Use the integration smoke test script to validate real CLI behavior against your
Clockify account. The script is fully non-interactive and selects the most
recent projects that satisfy each case. The `start_stop` case cleans up after
itself by deleting the created time entry.

## TL;DR

```bash
uv run python scripts/integration_smoke.py
```

## What it covers

| Case | Purpose | Notes |
|------|---------|-------|
| `start_stop` | Start → status → stop | Uses latest project with tag mapping or recent tagged history |
| `missing_tag` | Missing tag sentinel | Expects `CLOCKY_ERROR_MISSING_TAG_MAP` |
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

By default the script runs `uv run clocky`. To point at a different executable,
set `CLOCKY_INTEGRATION_CLI`:

```bash
CLOCKY_INTEGRATION_CLI="clocky" uv run python scripts/integration_smoke.py
```

## Adjust history lookback

```bash
uv run python scripts/integration_smoke.py --history-limit 150
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | All cases passed |
| 1 | At least one case failed |
