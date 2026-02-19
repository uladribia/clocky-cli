---
description: Code structure and module responsibilities for clocky-cli.
---

# Architecture

## TL;DR

Typer CLI → API client → Clockify REST API. Rich for display, rapidfuzz for search, pydantic for models.

## Module map

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Typer commands, global flags, orchestration |
| `cli_tag_map.py` | `tag-map` subcommands (show/edit/pick/set/remove) |
| `api.py` | HTTP client for Clockify REST API (`ClockifyAPI`) |
| `models.py` | Pydantic models (User, Project, TimeEntry, Tag, etc.) |
| `config.py` | Settings from `.env` via pydantic-settings |
| `context.py` | `AppContext` dataclass (API + user + workspace) |
| `display.py` | Rich console output (tables, status, errors) |
| `output.py` | Global `--json`/`--quiet` state, JSON serialisation |
| `fuzzy.py` | `fuzzy_search`, `fuzzy_best`, `fuzzy_choices` |
| `tag_map.py` | Persistent project→tag JSON file |
| `setup.py` | Interactive first-run setup wizard |
| `browser.py` | `open_browser()` helper (xdg-open / webbrowser) |
| `testing.py` | `MockClockifyAPI` + fixture data for tests |

## Request flow

```
User input
  → cli.py (parse args, global flags)
    → context.py (load settings, create API client, resolve workspace)
      → api.py (HTTP request to Clockify)
        → models.py (validate response)
    → output.py (check --json/--quiet mode)
    → display.py (Rich output) OR output.py (JSON output)
```

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| `ClockifyAPI` uses `httpx.Client` (sync) | CLI is sequential; async adds complexity |
| Global output mode via `output.py` singleton | Avoids threading mode through every function |
| `testing.py` with `MockClockifyAPI` | All tests run offline; no network mocking needed |
| `TagMap` is a frozen dataclass | Immutable `.set()` returns new instance; explicit `.save()` |
| Fuzzy search with `rapidfuzz.fuzz.WRatio` | Best general-purpose scorer for short strings |

## Dependencies

| Package | Purpose |
|---------|---------|
| typer | CLI framework |
| rich | Terminal tables, colours, panels |
| httpx | HTTP client |
| pydantic | Data models and validation |
| pydantic-settings | `.env` configuration loading |
| rapidfuzz | Fuzzy string matching |
| questionary | Interactive prompts (select, confirm) |
| python-dotenv | `.env` file loading |
