#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# clocky-launcher.sh — Ubuntu launcher for clocky-cli.
#
# Simple GUI flow:
# 1) Ask for a project name (fuzzy query)
# 2) Ask for an optional description
# 3) Run `clocky start --non-interactive <query> ...`
#
# This avoids terminal prompts (questionary) which do not work from .desktop.

set -euo pipefail

# shellcheck source=/dev/null
source "$(dirname "$0")/lib.sh"

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send --icon=clock "Clocky" "$1"
    fi
}

die() {
    zenity --error --title="Clocky Error" --text="$1" 2>/dev/null || true
    exit 1
}

clocky_log "launcher=start"
clocky_log_env_snapshot

if ! command -v clocky &>/dev/null; then
    clocky_log "ERROR: clocky not found"
    die "clocky is not installed.\n\nRun: uv tool install /path/to/clocky-cli"
fi

QUERY=$(zenity \
    --entry \
    --title="Clocky — Start Timer" \
    --text="Project name (fuzzy search):" \
    --entry-text="" \
    --width=420 \
    2>/dev/null) || {
    clocky_log "zenity query cancelled"
    exit 0
}

if [[ -z "$QUERY" ]]; then
    clocky_log "empty query"
    exit 0
fi
clocky_log "query=$QUERY"

# Do not prompt for description in launcher mode.
OUTPUT=$(clocky start --non-interactive "$QUERY" 2>&1) || {
    clocky_log "clocky start failed: $OUTPUT"
    notify "Failed to start timer: $OUTPUT"
    exit 1
}

clocky_log "clocky start output: $OUTPUT"

# Extract chosen project name for notification.
# `clocky start` prints a line: "Project: <name>".
CHOSEN_PROJECT=$(echo "$OUTPUT" | sed -n 's/.*Project:[[:space:]]*//p' | head -1)
if [[ -n "$CHOSEN_PROJECT" ]]; then
    notify "Timer started: $CHOSEN_PROJECT"
else
    notify "Timer started"
fi
