#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# clocky-stop.sh — Ubuntu launcher to stop the currently running Clockify timer.
#
# Triggered by a keyboard shortcut. Stops the active timer and shows a
# desktop notification with the elapsed duration.

set -euo pipefail

notify() {
    if command -v notify-send &>/dev/null; then
        notify-send --icon=clock "Clocky" "$1"
    fi
}

# Check if clocky is installed
if ! command -v clocky &>/dev/null; then
    notify "clocky is not installed"
    exit 1
fi

# Run stop command and capture output
OUTPUT=$(clocky stop 2>&1) || {
    if echo "$OUTPUT" | grep -q "No timer"; then
        notify "No timer is currently running"
    else
        notify "Failed to stop timer"
    fi
    exit 0
}

# Extract duration from output
if echo "$OUTPUT" | grep -q "Duration:"; then
    DURATION=$(echo "$OUTPUT" | grep -oP 'Duration: \K[^\s]+' | head -1)
    notify "Timer stopped\nDuration: $DURATION"
else
    notify "Timer stopped"
fi
