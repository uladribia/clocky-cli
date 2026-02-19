---
description: How to manage the persistent project→tag mapping.
---

# Manage tag mappings

## TL;DR

```bash
clocky tag-map show    # view all mappings (names)
clocky tag-map pick    # interactive fuzzy picker
clocky tag-map edit    # open in $EDITOR
```

## What is the tag map?

A JSON file at `~/.config/clocky/tag-map.json` that maps project IDs to tag IDs. When you start a timer, clocky checks this mapping before falling back to history inference.

**Why?** Most projects have one primary tag (e.g., "Cross-selling" → "Comercial"). The mapping avoids repeated prompts.

## Commands

### `tag-map show`

Displays all mappings with resolved names (not raw IDs):

```bash
clocky tag-map show
# {
#   "Cross-selling": "Comercial",
#   "Website Redesign": "billable"
# }
# Path: ~/.config/clocky/tag-map.json
```

### `tag-map pick`

Interactive flow: fuzzy-search a project, then fuzzy-search a tag, and save:

```bash
clocky tag-map pick
# Project (fuzzy): cross
# Pick project: Cross-selling (95%)
# Tag for 'Cross-selling' (fuzzy): com
# Pick tag: Comercial (92%)
# Mapped Cross-selling → Comercial
```

### `tag-map edit`

Opens the raw JSON in `$EDITOR`. Validates on save:

```bash
clocky tag-map edit
```

### `tag-map set <project-id> <tag-id>`

Set a mapping by raw IDs. Prefer `pick` for name-based flow:

```bash
clocky tag-map set proj-001 tag-001
# Mapped Website Redesign → billable
```

### `tag-map remove <project-id>`

Remove a mapping:

```bash
clocky tag-map remove proj-001
# Removed mapping for Website Redesign
```

## Auto-learning

When you pass `--tag` to `clocky start` with exactly one tag, the mapping is saved automatically:

```bash
clocky start "Cross-selling" --tag "Comercial"
# Saves: Cross-selling → Comercial
# Next time just: clocky start "Cross-selling"
```

## File format

`~/.config/clocky/tag-map.json` — plain JSON object, project ID → tag ID:

```json
{
  "64abc123def456": "64xyz789ghi012"
}
```

File permissions are set to `0600` on save.
