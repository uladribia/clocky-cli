# SYSTEM — clocky-cli coding practices

Keep changes small, typed, tested, and documented.

## Stack

- Python 3.12+
- CLI: typer + rich
- Config/models: pydantic + pydantic-settings
- HTTP: httpx
- Fuzzy: rapidfuzz
- Quality gates: ruff (format+lint) + ty (typecheck) + pytest

## Non-negotiables

- Use `uv` only (no pip/poetry/conda; avoid `uv pip ...`).
- Every module/function/class has a meaningful Google-style docstring.
- Type annotations everywhere; `from __future__ import annotations` in every `.py`.
- Tests are offline and use mocks from `clocky/testing.py` (no mocks in `api.py`).
- Secrets are never committed. `.env` is ignored; provide `.env.example`.
- Licensing: repo has `LICENSE` and each `.py`/`.sh` includes `SPDX-License-Identifier: MIT`.

## Commands

- Dev sync: `uv sync`
- Run CLI: `uv run clocky --help`
- Full checks (after code changes): `./check.sh`

## check.sh (must stay green)

- `uv sync --quiet`
- `ruff format .`
- `ruff check . --fix`
- `ty check .`
- `pytest`

## Commits

After checks pass:

- `git add -A`
- `git commit -m "feat: ..."` (or `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)
