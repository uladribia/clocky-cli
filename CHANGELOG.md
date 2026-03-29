# Changelog

## 2.5.0 - 2026-03-29

### Changed
- Reorganized the internal package layout into layered `app`, `cli`, `domain`, `infra`, `testing`, and `ui` packages.
- Moved the console script entrypoint to `clocky.cli.main:main` and added `python -m clocky.cli` package execution support.
- Updated tests and architecture documentation to reflect the new package structure.

## 2.4.0 - 2026-03-29

### Added
- Protocol- and service-based architecture boundaries for timer and project workflows.
- Log-driven smoke planning plus runtime validation for `missing_tag` candidates.
- API contract tests, service-layer tests, launcher script tests, setup tests, and entrypoint tests.

### Changed
- `integration-test` now defaults to `python -m clocky.cli` for more reliable local execution.
- `scripts/integration_smoke.py` now bootstraps the repo path when run directly from the checkout.
- Setup/config logic is split into purer helpers, and `tag-map` commands have clearer parsing helpers.

### Fixed
- Full-duration parsing in the stop launcher notification flow.
- Live smoke failures caused by stale log-derived `missing_tag` candidates.

## 2.3.0 - 2026-03-29

### Added
- Weighted fuzzy ranking for projects and tags using rapidfuzz plus recent usage priors.
- Project-specific tag ranking that prefers tags recently used with the chosen project.
- Offline tests covering weighted ranking, short-prefix matches, and consistent selection ordering.

### Changed
- `start`, `projects --search`, and `tag-map pick` now use the same weighted fuzzy schema.
- Interactive and non-interactive flows now share the same ranked fuzzy results; non-interactive mode auto-picks the top-ranked match.
- Fuzzy matching now handles short prefixes like `web` more reliably than the previous token-set-only approach.

### Fixed
- Removed the non-interactive single-match bypass from selection flow by using one shared ranking path.
- Aligned architecture and output-mode docs with the actual fuzzy-matching behaviour.
