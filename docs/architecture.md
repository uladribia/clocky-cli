---
description: Code structure and module responsibilities for clocky-cli.
---

# Architecture

## TL;DR

`clocky/cli` → `clocky/app` → `clocky/infra` → Clockify REST API.
`clocky/domain` holds the pure models/ranking logic and `clocky/ui` handles
terminal presentation.

## Module map

| Module | Responsibility |
|--------|---------------|
| `cli/` | Typer entrypoints, `tag-map` commands, JSON output, setup flow |
| `app/services/` | Timer/project application services and service errors |
| `domain/` | Pydantic models, weighted fuzzy ranking, lookup helpers |
| `infra/` | API/config/context/gateway adapters plus smoke/setup persistence |
| `ui/` | Rich console output helpers |
| `testing/` | Offline gateway fake + fixture data for tests |
| `cli_helpers/` | Shared interactive selection/tagging helpers |

## Request flow

```
User input
  → `clocky/cli/main.py` (parse args, global flags)
    → `clocky/infra/context.py` (load settings, create gateway, resolve workspace)
      → `clocky/app/services/*` (application workflow)
        → `clocky/infra/api.py` (HTTP request to Clockify)
          → `clocky/domain/models.py` (validate response)
    → `clocky/cli/output.py` (check `--json` / `--quiet` mode)
    → `clocky/ui/display.py` (Rich output) OR `clocky/cli/output.py` (JSON output)
```

## Key design decisions

| Decision | Rationale |
|----------|-----------|
| `infra/api.py` uses `httpx.Client` (sync) | CLI is sequential; async adds complexity |
| Global output mode via `cli/output.py` singleton | Avoids threading mode through every function |
| `infra/gateway.py` protocol + `testing/fakes.py` | Tests can substitute the API without inheriting from the HTTP client |
| `infra/tag_map.py` uses a frozen dataclass | Immutable `.set()` returns new instance; explicit `.save()` |
| `domain/fuzzy.py` adds recent-usage priors | Better typo tolerance while preferring projects and tags you actually use |

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
