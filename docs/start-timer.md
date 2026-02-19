---
description: How to start a timer with fuzzy search, tags, and dry-run.
---

# Start a timer

## TL;DR

```bash
clocky start "web redesin"                          # fuzzy match, auto-tag
clocky start "mobile" --tag "billable" -d "standup"  # explicit tag + description
clocky start "mobile" --dry-run                      # preview only
```

## Fuzzy project matching

clocky uses [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) to match your input against all workspace projects. Typos and partial names work.

```bash
clocky start "cros-selling"   # matches "Cross-selling"
clocky start "web"            # matches "Website Redesign"
```

**Multiple matches** → interactive picker (unless `--non-interactive`).

**No matches** → exit code 2.

## Tag resolution

Tags are resolved in this priority order:

| Priority | Source | Example |
|----------|--------|---------|
| 1 | Explicit `--tag` flag | `--tag "billable"` |
| 2 | Stored project→tag mapping | Set via `clocky tag-map pick` |
| 3 | History inference (`--auto-tag`) | Most common tag from last 50 entries |
| 4 | Interactive prompt | Asked when TTY and no tag found |

If none resolves and `--non-interactive` is set, clocky exits with code 1 and prints `CLOCKY_ERROR_MISSING_TAG_MAP` to stderr (used by launchers).

### Persist a tag mapping

```bash
# Interactive picker
clocky tag-map pick

# Or let clocky learn: pass --tag once, it saves the mapping
clocky start "Cross-selling" --tag "Comercial"
# Next time, just:
clocky start "Cross-selling"  # uses saved mapping
```

See [tag-map.md](tag-map.md) for full details.

## Dry run

Preview the resolved project, tags, and description without creating a timer:

```bash
clocky start "mobile" --dry-run
# Dry run — no timer started.
#   Project:     Mobile App
#   Description: —
#   Tags:        billable

# JSON dry run
clocky --json start "mobile" --dry-run --non-interactive
# {"dry_run": true, "project": "Mobile App", ...}
```

## Non-interactive mode

For scripts and launchers. Auto-picks the best fuzzy match without prompting:

```bash
clocky start --non-interactive "cros-selling"
```

## Full options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `<project>` | | required | Project name (fuzzy) |
| `--description` | `-d` | `""` | Timer description |
| `--tag` | `-t` | auto | Tag name(s), repeatable |
| `--auto-tag / --no-auto-tag` | | `--auto-tag` | Infer from history |
| `--non-interactive / --interactive` | | `--interactive` | Auto-pick best match |
| `--dry-run` | | off | Preview without starting |
