---
description: How to start a timer with fuzzy search, tags, and dry-run.
---

# Start a timer

## TL;DR

```bash
clocky start "web redesin"                            # fuzzy match, auto-tag
clocky start "mobile" --tag "billable" --description "standup"
clocky start "mobile" --dry-run                        # preview only
```

## Fuzzy project matching

clocky uses [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) with a weighted ranking model. Typos, prefixes, token order, and your recent project/tag history all contribute to the final score.

Only **active** projects are considered. Archived projects are excluded from every project search.

```bash
clocky start "cros-selling"   # matches "Cross-selling"
clocky start "web"            # matches "Website Redesign"
```

**Multiple matches** → interactive picker, unless `--non-interactive` is set.

**No matches** → exit code 2.

## Tag resolution

Tags are resolved in this priority order:

| Priority | Source | Example |
|----------|--------|---------|
| 1 | Explicit `--tag` flag | `--tag "billable"` |
| 2 | Stored project→tag mapping | Set via `clocky tag-map pick` |
| 3 | History inference (`--auto-tag`) | Most common tag from last 50 entries |
| 4 | Interactive prompt | Asked when TTY and no tag found |

If none resolves and `--non-interactive` is set, clocky exits with code 1 and prints `CLOCKY_ERROR_MISSING_TAG_MAP` to stderr.

### Persist a tag mapping

```bash
clocky tag-map pick
clocky start "Cross-selling" --tag "Comercial"
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

clocky --json start "mobile" --dry-run --non-interactive
# {"dry_run": true, "project": "Mobile App", ...}
```

## Non-interactive mode

For scripts and launchers. It uses the same weighted ranking as interactive mode and auto-picks the top active project instead of prompting:

```bash
clocky start --non-interactive "cros-selling"
```

## Full options

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `<project>` | | required | Active project name (fuzzy) |
| `--description` | `-d` | `""` | Timer description |
| `--tag` | `-t` | auto | Tag name(s), repeatable |
| `--auto-tag / --no-auto-tag` | | `--auto-tag` | Infer from history |
| `--non-interactive / --interactive` | | `--interactive` | Auto-pick top weighted match |
| `--dry-run` | | off | Preview without starting |
