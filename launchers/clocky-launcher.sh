#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# clocky-launcher.sh — Ubuntu launcher for clocky-cli.
#
# Simple GUI flow:
# 1) Ask for a project name (fuzzy query)
# 2) Ask for an optional description
# 3) Run `clocky start <query> ...`
#
# Notes:
# - This launcher intentionally does NOT call system python.
# - If multiple projects match, `clocky` will ask for clarification in-terminal.

set -euo pipefail

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send --icon=clock "Clocky" "$1"
    fi
}

die() {
    zenity --error --title="Clocky Error" --text="$1" 2>/dev/null || true
    exit 1
}

if ! command -v clocky &>/dev/null; then
    die "clocky is not installed.\n\nRun: uv tool install /path/to/clocky-cli"
fi

QUERY=$(zenity \
    --entry \
    --title="Clocky — Start Timer" \
    --text="Project name (fuzzy search):" \
    --entry-text="" \
    --width=420 \
    2>/dev/null) || exit 0

[[ -z "$QUERY" ]] && exit 0

DESCRIPTION=$(zenity \
    --entry \
    --title="Clocky — Description" \
    --text="Description (optional):" \
    --entry-text="" \
    --width=420 \
    2>/dev/null) || DESCRIPTION=""

if [[ -n "$DESCRIPTION" ]]; then
    OUTPUT=$(clocky start "$QUERY" --description "$DESCRIPTION" 2>&1) || {
        notify "Failed to start timer: $OUTPUT"
        exit 1
    }
else
    OUTPUT=$(clocky start "$QUERY" 2>&1) || {
        notify "Failed to start timer: $OUTPUT"
        exit 1
    }
fi

# Best-effort notification. (Project name is already printed by clocky if run in a terminal.)
if echo "$OUTPUT" | grep -q "✔"; then
    notify "Timer started"
else
    notify "clocky start finished"
fi
