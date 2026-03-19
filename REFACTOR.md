# Refactor plan

This plan focuses on maintainability, readability, and reduced cognitive debt. Each step must keep the CLI behavior unchanged. After every step, run checks plus unit and integration tests: `./check.sh` and `clocky integration-test`.

## Step 0 — Baseline verification

- Run `./check.sh`.
- Run `clocky integration-test` (all cases). If missing-tag case cannot be auto-selected, set `CLOCKY_TEST_PROJECT_MISSING_TAG`.

## Step 1 — Extract command helpers from `clocky/cli.py`

**Goal:** Reduce command complexity and duplication in `cli.py`.

- Create `clocky/cli_helpers/selection.py` for fuzzy selection rules (`_pick_one`).
- Create `clocky/cli_helpers/tagging.py` for tag inference/resolution (`_infer_tag_for_project`, `_resolve_tag_ids`).
- Keep `cli.py` as a command layer that delegates to helpers.

**Tests:** Run `./check.sh` and `clocky integration-test` after this step.

## Step 2 — Consolidate lookup utilities

**Goal:** Remove repeated mapping logic for projects/tags.

- Add `clocky/lookup.py` with helpers:
  - `build_project_map(api, workspace_id)`
  - `build_tag_map(api, workspace_id)`
  - `resolve_project_name(project_map, project_id)`
  - `resolve_tag_names(tag_map, tag_ids)`
- Replace repeated dict comprehensions in commands with these helpers.

**Tests:** Run `./check.sh` and `clocky integration-test` after this step.

## Step 3 — Introduce a minimal service layer

**Goal:** Separate CLI I/O from API orchestration.

- Add `clocky/services/time_entries.py` with pure functions for:
  - `start_timer_flow(...)`
  - `stop_timer_flow(...)`
  - `status_flow(...)`
  - `list_entries_flow(...)`
- These functions return data structures (no Rich output), leaving formatting to `display.py`.

**Tests:** Run `./check.sh` and `clocky integration-test` after this step.

## Step 4 — Centralize error formatting

**Goal:** Make error output consistent.

- Add `clocky/errors.py` with `cli_error(message: str, code: int = 1) -> NoReturn`.
- Ensure errors follow:
  - `clocky: <message>`
  - `Try 'clocky <command> --help'`
- Update CLI commands to call the helper.

**Tests:** Run `./check.sh` and `clocky integration-test` after this step.

## Step 5 — Centralize Rich consoles

**Goal:** Reduce duplication and improve consistency.

- Add `clocky/console.py` with `console`, `err_console`, and `NO_COLOR` handling.
- Replace per-module `Console` instantiation in `display.py`, `cli.py`, and `config.py`.

**Tests:** Run `./check.sh` and `clocky integration-test` after this step.

## Step 6 — Replace global output mode state

**Goal:** Remove hidden global state for output mode.

- Replace `output._mode` with an `OutputMode` instance passed through helpers/flows.
- Provide a lightweight context object to commands to carry mode + console.

**Tests:** Run `./check.sh` and `clocky integration-test` after this step.

## Step 7 — Standardize integration entrypoints

**Goal:** Keep integration smoke tests reliable after refactors.

- Ensure `clocky integration-test` still runs the same cases.
- Add a short note in `docs/integration-tests.md` if any CLI flags change (should not).

**Tests:** Run `./check.sh` and `clocky integration-test` after this step.

---

## Guardrails

- Keep public CLI surface unchanged unless documented.
- Update docs in `docs/` whenever CLI surface or behavior changes.
- Preserve SPDX headers.
- Keep changes small and reviewable per step.
