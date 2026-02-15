#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# clocky-stop.sh — Ubuntu launcher to stop the currently running Clockify timer.
#
# Triggered by a keyboard shortcut / .desktop entry. Stops the active timer and
# shows a desktop notification with the elapsed duration.

set -euo pipefail

# shellcheck source=/dev/null
source "$(dirname "$0")/lib.sh"

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send --icon=clock "Clocky" "$1"
    fi
}

clocky_log "launcher=stop"
clocky_log_env_snapshot

# Check if clocky is installed
if ! command -v clocky &>/dev/null; then
    clocky_log "ERROR: clocky not found"
    notify "clocky is not installed"
    exit 1
fi

# Run stop command and capture output
OUTPUT=$(clocky stop 2>&1) || {
    clocky_log "clocky stop failed: $OUTPUT"
    if echo "$OUTPUT" | grep -q "No timer"; then
        notify "No timer is currently running"
    else
        notify "Failed to stop timer"
    fi
    exit 0
}

clocky_log "clocky stop output: $OUTPUT"

# Extract duration from output
if echo "$OUTPUT" | grep -q "Duration:"; then
    DURATION=$(echo "$OUTPUT" | grep -oP 'Duration: \K[^\s]+' | head -1)
    notify "Timer stopped\nDuration: $DURATION"
else
    notify "Timer stopped"
fi
