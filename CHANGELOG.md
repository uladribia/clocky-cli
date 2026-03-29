# Changelog

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
