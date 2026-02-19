---
description: Complete reference for all clocky CLI commands and flags.
---

# Commands reference

## TL;DR

```bash
clocky start <project>     # start timer
clocky stop                # stop timer
clocky status              # show running timer
clocky list                # recent entries
clocky projects            # list projects
clocky delete <id>         # delete entry
clocky tag-map show        # view tag mappings
clocky setup               # configure API key
```

## Global flags

| Flag | Short | Description |
|------|-------|-------------|
| `--json` | | JSON output to stdout (implies `--quiet`) |
| `--quiet` | `-q` | Suppress informational output |
| `--version` | `-V` | Show version and exit |
| `--help` | | Show help |

## Commands

### `start <project>`

Start a timer with fuzzy project matching.

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--description` | `-d` | `""` | Timer description |
| `--tag` | `-t` | auto | Tag name(s), repeatable |
| `--auto-tag / --no-auto-tag` | | `--auto-tag` | Infer tag from history |
| `--non-interactive / --interactive` | | `--interactive` | Auto-pick best match |
| `--dry-run` | | off | Preview without starting |

### `stop`

Stop the running timer.

| Option | Short | Description |
|--------|-------|-------------|
| `--force` | `-f` | Skip confirmation for timers >8h |

### `status`

Show the currently running timer. No options.

### `list`

List recent time entries.

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--limit` | `-n` | 10 | Number of entries to show |

### `projects [client]`

List projects. Client argument is optional (lists all when omitted).

| Option | Short | Description |
|--------|-------|-------------|
| `--search` | `-s` | Fuzzy-filter project names |

### `delete <entry-id>`

Delete a time entry by ID.

| Option | Short | Description |
|--------|-------|-------------|
| `--force` | `-f` | Skip confirmation prompt |

### `tag-map` subcommands

See [tag-map.md](tag-map.md) for full details.

| Subcommand | Description |
|------------|-------------|
| `show` | Display current mappings (names, not IDs) |
| `edit` | Open mapping in `$EDITOR` |
| `pick` | Interactive fuzzy picker |
| `set <project-id> <tag-id>` | Set mapping by IDs |
| `remove <project-id>` | Remove a mapping |

### `setup`

Run interactive setup to configure your API key. See [install.md](install.md).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime error (API failure, no timer running) |
| 2 | Usage error (no fuzzy match, bad input) |
