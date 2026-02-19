---
description: How to use --json, --quiet, and NO_COLOR output modes.
---

# Output modes

## TL;DR

```bash
clocky --json status              # JSON to stdout
clocky --quiet start "web" --non-interactive  # minimal output
NO_COLOR=1 clocky list            # no ANSI colours
```

## Default mode

Human-readable Rich tables and styled messages. Colours and Unicode symbols enabled.

## `--json`

Outputs valid JSON to stdout. Implies `--quiet` (no informational messages).

```bash
# Get running timer as JSON
clocky --json status | jq '.project_name'

# List entries and filter
clocky --json list --limit 5 | jq '.[].description'

# All projects as JSON array
clocky --json projects

# Start returns the created entry
clocky --json start "mobile" --non-interactive

# Delete returns confirmation
clocky --json delete entry-abc --force
# {"deleted": "entry-abc"}
```

### JSON schemas

**Time entry** (used by `status`, `start`, `stop`, `list`):

```json
{
  "id": "entry-001",
  "description": "Fix login bug",
  "project_id": "proj-001",
  "project_name": "Website Redesign",
  "tag_ids": ["tag-001"],
  "tag_names": ["billable"],
  "start": "2024-01-15T09:00:00+00:00",
  "end": "2024-01-15T11:00:00+00:00",
  "duration": "PT2H"
}
```

**Project** (used by `projects`):

```json
{
  "id": "proj-001",
  "name": "Website Redesign",
  "client_id": "cli-001",
  "client_name": "Acme Corp",
  "archived": false
}
```

**Null** — returned by `status` and `stop` when no timer is running.

## `--quiet` / `-q`

Suppresses informational output (`Project:`, `Tag:` lines). Errors still go to stderr. Success messages still print.

```bash
clocky --quiet start "web" --non-interactive
# Only prints: ✔ Timer started (id: entry-new)
```

## `NO_COLOR`

When the `NO_COLOR` environment variable is set (any value), all ANSI colour codes are stripped.

```bash
export NO_COLOR=1
clocky status    # plain text, no colours
```

Follows the [no-color.org](https://no-color.org) convention.

## Combining modes

| Flags | Behaviour |
|-------|-----------|
| (none) | Rich tables, colours, informational lines |
| `--quiet` | No info lines, colours still active |
| `--json` | JSON to stdout, no info lines, no colours |
| `NO_COLOR=1` | Tables but no ANSI escapes |
| `--json` + `NO_COLOR=1` | JSON (NO_COLOR is irrelevant for JSON) |
