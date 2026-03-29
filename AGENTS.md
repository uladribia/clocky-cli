# AGENTS — clocky-cli workflow and coding practices

This file is for coding agents and AI assistants working in this repository.

## Mission

Make small, focused, typed, tested, and documented changes.

## Stack

- Python 3.12+
- CLI: typer + rich
- Config/models: pydantic + pydantic-settings
- HTTP: httpx
- Fuzzy: rapidfuzz
- Quality gates: ruff (format+lint) + ty (typecheck) + pytest

## Policy summary

- Keep changes small, typed, tested, and documented.
- Use `uv` as the project package and task runner.
- Maintain offline, deterministic tests.
- Keep licensing and secret-handling requirements intact.

## Required workflow

1. Create a dedicated git branch for the work before making code changes.
2. Sync dependencies with `uv sync`.
3. Implement changes with full type annotations and meaningful Google-style docstrings.
4. Keep tests offline and use mocks from `clocky/testing.py` (do not place mocks in `api.py`).
5. Run full checks with `./check.sh`.
6. Update documentation after each major code change (see [Documentation](#documentation)).
7. Commit only after checks and docs pass (see [Commit style](#commit-style)).
8. Before opening a pull request, squash the branch history into a clean, reviewable set of commits.
9. Prepare a clear pull request summary that explains the problem, approach, validation, and any follow-up work.
10. Open and submit the pull request once the branch is ready for review.

## Guardrails

- Use `uv` only (no pip/poetry/conda); use `uvx` for tool execution instead of `uv pip`.
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

```text
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

1. Create and switch to a focused branch, for example `git switch -c feat/short-name`.
2. Review `git status` and `git diff` to understand what changed.
3. Stage only the intended files (`git add -p` when mixing concerns).
4. Run `git commit -m "<type>(<scope>): <summary>"`.
5. Keep branch history tidy; squash or reword intermediate commits before review.
6. Do not add `Signed-off-by` or breaking-change footers.

### Pull request workflow

1. Ensure `./check.sh` passes and docs are up to date.
2. Push the branch and prepare a pull request.
3. Write a concise, high-signal PR summary covering:
   - what changed
   - why it changed
   - how it was validated
   - any risks, limitations, or follow-up tasks
4. Squash commit history as needed so reviewers see a clean final history.
5. Submit the pull request when the branch is ready for review.
6. Remote operations are allowed when explicitly requested, including pushing branches, deleting fully merged remote branches, and other necessary remote-state updates related to the task.

## Useful commands

| Task | Command |
|------|---------|
| Dev sync | `uv sync` |
| Run CLI | `uv run clocky --help` |
| Full checks | `./check.sh` |
| Run single test | `uv run pytest tests/test_foo.py -v` |
