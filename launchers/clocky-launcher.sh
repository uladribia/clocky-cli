#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# clocky-launcher.sh — Ubuntu launcher for clocky-cli.
#
# Triggered by a keyboard shortcut (e.g., Super+C). Opens a zenity entry dialog
# to fuzzy-search a project, picks from matches, and starts a timer with
# auto-inferred tag based on history.
#
# Dependencies: zenity (pre-installed on Ubuntu), clocky (installed via uv tool)
#
# Usage: bind this script to a keyboard shortcut in Ubuntu Settings →
#        Keyboard → Custom Shortcuts.

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send --icon=clock "Clocky" "$1"
    fi
}

die() {
    zenity --error --title="Clocky Error" --text="$1" 2>/dev/null || true
    exit 1
}

# Check if clocky is installed
if ! command -v clocky &>/dev/null; then
    die "clocky is not installed.\n\nRun: uv tool install /path/to/clocky-cli"
fi

# ---------------------------------------------------------------------------
# 1. Ask user for a project search term
# ---------------------------------------------------------------------------

QUERY=$(zenity \
    --entry \
    --title="Clocky — Start Timer" \
    --text="Search for a project:" \
    --entry-text="" \
    --width=400 \
    2>/dev/null) || exit 0

[[ -z "$QUERY" ]] && exit 0

# ---------------------------------------------------------------------------
# 2. Run fuzzy search via clocky and capture matches
# ---------------------------------------------------------------------------

MATCHES=$(python3 << PYEOF
import sys
from pathlib import Path

# Find config
env_file = None
for p in [Path.cwd() / ".env", Path.home() / ".config" / "clocky" / ".env", Path.home() / ".clocky.env"]:
    if p.exists():
        env_file = p
        break

if not env_file:
    print("NO_CONFIG", file=sys.stderr)
    sys.exit(1)

from dotenv import dotenv_values
values = dotenv_values(env_file)
api_key = values.get("CLOCKIFY_API_KEY", "")
if not api_key or api_key == "your_api_key_here":
    print("BAD_KEY", file=sys.stderr)
    sys.exit(1)

from clocky.api import ClockifyAPI
from clocky.fuzzy import fuzzy_search

api = ClockifyAPI(api_key)
user = api.get_user()
ws = values.get("CLOCKIFY_WORKSPACE_ID") or user.default_workspace
projects = api.get_projects(ws)
results = fuzzy_search("$QUERY", projects, key=lambda p: p.name)

for project, score in results[:10]:
    client = project.client_name or "—"
    print(f"{project.id}|{project.name}|{client}|{score:.0f}")
PYEOF
) || die "Failed to fetch projects. Run 'clocky setup' to configure."

if [[ -z "$MATCHES" ]]; then
    zenity --info \
        --title="Clocky" \
        --text="No projects matched '$QUERY'." \
        --width=300 \
        2>/dev/null || true
    exit 0
fi

# ---------------------------------------------------------------------------
# 3. Build zenity list: ID (hidden) | Name | Client | Score
# ---------------------------------------------------------------------------

ZENITY_ARGS=()
while IFS='|' read -r proj_id proj_name client score; do
    ZENITY_ARGS+=("$proj_id" "$proj_name" "$client" "${score}%")
done <<< "$MATCHES"

CHOSEN_ID=$(zenity \
    --list \
    --title="Clocky — Select Project" \
    --text="Choose a project:" \
    --column="ID" \
    --column="Project" \
    --column="Client" \
    --column="Match" \
    --hide-column=1 \
    --print-column=1 \
    --width=500 \
    --height=400 \
    "${ZENITY_ARGS[@]}" \
    2>/dev/null) || exit 0

[[ -z "$CHOSEN_ID" ]] && exit 0

# Get project name for notification
CHOSEN_NAME=$(echo "$MATCHES" | grep "^$CHOSEN_ID|" | cut -d'|' -f2)

# ---------------------------------------------------------------------------
# 4. Optionally ask for a description
# ---------------------------------------------------------------------------

DESCRIPTION=$(zenity \
    --entry \
    --title="Clocky — Description" \
    --text="Description (optional):" \
    --entry-text="" \
    --width=400 \
    2>/dev/null) || DESCRIPTION=""

# ---------------------------------------------------------------------------
# 5. Start the timer with auto-tag inference
# ---------------------------------------------------------------------------

# Build command
CMD="clocky start --project '$CHOSEN_ID'"
if [[ -n "$DESCRIPTION" ]]; then
    CMD="$CMD --description '$DESCRIPTION'"
fi

# Run in background and capture output
OUTPUT=$(eval "$CMD" 2>&1) || {
    notify "Failed to start timer: $OUTPUT"
    exit 1
}

# Extract tag info from output if present
TAG_INFO=""
if echo "$OUTPUT" | grep -q "Tag (auto):"; then
    TAG_INFO=$(echo "$OUTPUT" | grep "Tag (auto):" | sed 's/.*Tag (auto): //')
fi

# Notification
MSG="Timer started: $CHOSEN_NAME"
[[ -n "$TAG_INFO" ]] && MSG="$MSG\nTag: $TAG_INFO"
[[ -n "$DESCRIPTION" ]] && MSG="$MSG\n$DESCRIPTION"

notify "$MSG"
