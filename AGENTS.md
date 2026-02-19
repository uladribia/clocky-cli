# AGENTS — clocky-cli agent workflow

This file is for coding agents and AI assistants working in this repository.

## Mission

Make small, focused, typed, tested, and documented changes.

## Required workflow

1. Sync dependencies with `uv sync`.
2. Implement changes with full type annotations and meaningful Google-style docstrings.
3. Keep tests offline and use mocks from `clocky/testing.py` (do not place mocks in `api.py`).
4. Run full checks with `./check.sh`.
5. Update documentation after each major code change (see [Documentation](#documentation)).
6. Commit only after checks and docs pass (see [Commit style](#commit-style)).

## Guardrails

- Use `uv` only (no pip/poetry/conda; avoid `uv pip ...`).
- Add `from __future__ import annotations` in every `.py` file.
- Do not commit secrets; keep `.env` ignored and maintain `.env.example`.
- Preserve SPDX license headers in `.py`/`.sh` files: `SPDX-License-Identifier: MIT`.

## Quality gate details

`check.sh` must remain green and runs:

- `uv sync --quiet`
- `ruff format .`
- `ruff check . --fix`
- `ty check .`
- `pytest`

## CLI design conventions

Follow these rules when adding or changing CLI commands, flags, or output:

| Rule | Detail |
|------|--------|
| Long options preferred | `--description` not `-d` (short aliases allowed as extras) |
| stdout for data | stderr for progress/errors |
| Exit codes | 0 = success, 1 = runtime error, 2 = usage error |
| Standard flags | Every command must support `--help`; top-level supports `--json`, `--quiet` |
| Validate early | Fail fast on bad input before making API calls |
| `NO_COLOR` | Respect the `NO_COLOR` env variable — disable colour when set |

### Output modes

- **Default:** human-readable Rich tables/messages.
- **`--json`:** JSON to stdout, implies `--quiet`. Must be valid, parseable JSON.
- **`--quiet` / `-q`:** suppress informational output; errors still go to stderr.

### Destructive / stateful operations

- Confirm on TTY (e.g. `delete`, long-running `stop`).
- `--force` / `-f` skips confirmation.
- `--dry-run` previews the action without side-effects.

### Error format

Errors printed to stderr should follow:

```
clocky: <message>
Try 'clocky <command> --help'
```

### Launcher safety

Ubuntu `.desktop` launchers and shell scripts in `launchers/` depend on:

- `--non-interactive` flag behaviour and best-fuzzy-match auto-pick.
- `CLOCKY_ERROR_MISSING_TAG_MAP` sentinel on stderr.
- Stdout lines matching `Project:` and `Tag:` parsed by `sed`.

**Do not change these contracts** without updating every launcher script.

## Documentation

After every major code change (new command, new flag, changed behaviour), update docs:

- Max 150 lines per doc file, one concept per file.
- Start each doc with a YAML `description:` frontmatter or a TL;DR section.
- No duplicated content — define once, link elsewhere.
- Use tables for structured data (parameters, config, flags).
- Include concrete, copy-pasteable examples.
- Name files by task: `{verb}-{noun}.md` for how-tos, `{noun}.md` for reference.
- Keep `README.md` as the directory overview and entry point.
- Update `README.md` whenever the CLI surface changes (new commands, removed flags, etc.).

## Commit style

Use Conventional Commits format: `<type>(<scope>): <summary>`

| Field | Rule |
|-------|------|
| `type` | **Required.** One of: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf` |
| `scope` | Optional. Short noun for the affected area, e.g. `cli`, `api`, `display` |
| `summary` | **Required.** Imperative, ≤ 72 chars, no trailing period |
| Body | Optional. Blank line after subject, then short paragraphs |

### Commit workflow

1. Review `git status` and `git diff` to understand what changed.
2. Stage only the intended files (`git add -p` when mixing concerns).
3. Run `git commit -m "<type>(<scope>): <summary>"`.
4. **Do not push** — only commit.
5. Do not add `Signed-off-by` or breaking-change footers.

## Useful commands

| Task | Command |
|------|---------|
| Dev sync | `uv sync` |
| Run CLI | `uv run clocky --help` |
| Full checks | `./check.sh` |
| Run single test | `uv run pytest tests/test_foo.py -v` |
