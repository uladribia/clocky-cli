---
description: Code structure and module responsibilities for clocky-cli.
---

# Architecture

## TL;DR

Typer CLI → application services → gateway/repositories → Clockify REST API.
Rich handles display, rapidfuzz handles ranking, pydantic handles validation.

## Module map

| Module | Responsibility |
|--------|---------------|
| `cli.py` | Typer commands, global flags, orchestration |
| `cli_tag_map.py` | `tag-map` subcommands (show/edit/pick/set/remove) |
| `api.py` | HTTP adapter for Clockify REST API (`ClockifyAPI`) |
| `gateway.py` | Protocol boundary used by CLI/services/tests |
| `models.py` | Pydantic models (User, Project, TimeEntry, Tag, etc.) |
| `config.py` | Settings from `.env` via pydantic-settings |
| `context.py` | `AppContext` dataclass and lifecycle wrapper |
| `display.py` | Rich console output (tables, status, errors) |
| `output.py` | Global `--json`/`--quiet` state, JSON serialisation |
| `fuzzy.py` | Weighted ranking, `fuzzy_search*`, `fuzzy_best` |
| `tag_map.py` | Persistent project→tag JSON file |
| `services/` | Timer/project application services and service errors |
| `setup.py` | Interactive first-run setup CLI flow |
| `setup_service.py` | Pure helpers for setup persistence and connection checks |
| `smoke_planner.py` | Log-driven planning for real integration smoke tests |
| `browser.py` | `open_browser()` helper (xdg-open / webbrowser) |
| `testing.py` | Offline gateway fake + fixture data for tests |

## Request flow

```
User input
  → cli.py (parse args, global flags)
    → context.py (load settings, create gateway, resolve workspace)
      → services/* (application workflow)
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
| `gateway.py` protocol + offline fake | Tests can substitute the API without inheriting from the HTTP client |
| `TagMap` is a frozen dataclass | Immutable `.set()` returns new instance; explicit `.save()` |
| Weighted fuzzy search with rapidfuzz + recent usage priors | Better typo tolerance while preferring projects and tags you actually use |

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
