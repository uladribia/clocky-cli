# AGENTS — clocky-cli agent workflow

This file is for coding agents and AI assistants working in this repository.

## Mission

Make small, focused, typed, tested, and documented changes.

## Required workflow

1. Sync dependencies with `uv sync`.
2. Implement changes with full type annotations and meaningful Google-style docstrings.
3. Keep tests offline and use mocks from `clocky/testing.py` (do not place mocks in `api.py`).
4. Run full checks with `./check.sh`.
5. Commit only after checks pass, using conventional commit prefixes.

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

## Useful commands

- Dev sync: `uv sync`
- Run CLI: `uv run clocky --help`
- Full checks: `./check.sh`

## Commit style

Use one of: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
