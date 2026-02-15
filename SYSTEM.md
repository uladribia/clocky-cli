# SYSTEM — clocky-cli coding practices

Repository-level standards and technical baseline for humans and agents.

## Stack

- Python 3.12+
- CLI: typer + rich
- Config/models: pydantic + pydantic-settings
- HTTP: httpx
- Fuzzy: rapidfuzz
- Quality gates: ruff (format+lint) + ty (typecheck) + pytest

## Policy summary

- Keep changes small, typed, tested, and documented.
- Use `uv` as the project package/task runner.
- Maintain offline, deterministic tests.
- Keep licensing and secret-handling requirements intact.

## Agent-specific execution guide

See `AGENTS.md` for operational workflow, guardrails, checks, and commit conventions.
