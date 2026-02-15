#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# clocky-launcher.sh — Ubuntu launcher for clocky-cli.
#
# GUI flow (desktop-safe):
# 1) Ask for project query (zenity entry)
# 2) Try to start timer non-interactively (best fuzzy match)
# 3) If tag mapping is missing, ask for tag query (zenity entry) and retry
# 4) Show a notification with the chosen project/tag

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
    clocky_log "zenity project cancelled"
    exit 0
}

if [[ -z "$QUERY" ]]; then
    clocky_log "empty project query"
    exit 0
fi
clocky_log "query=$QUERY"

OUTPUT=$(clocky start --non-interactive "$QUERY" 2>&1) || {
    clocky_log "clocky start failed: $OUTPUT"

    if echo "$OUTPUT" | grep -q "CLOCKY_ERROR_MISSING_TAG_MAP"; then
        # Try to suggest a tag based on history (if any).
        SUGGESTED_TAG=$(clocky list --limit 30 2>/dev/null | awk 'NR>3 {print $3}' | head -1)
        DEFAULT_TAG=""
        if [[ -n "$SUGGESTED_TAG" && "$SUGGESTED_TAG" != "—" ]]; then
            DEFAULT_TAG="$SUGGESTED_TAG"
        fi

        TAG_QUERY=$(zenity \
            --entry \
            --title="Clocky — Tag" \
            --text="No tag mapped for this project. Enter a tag (fuzzy):" \
            --entry-text="$DEFAULT_TAG" \
            --width=420 \
            2>/dev/null) || {
            clocky_log "zenity tag cancelled"
            exit 0
        }

        if [[ -z "$TAG_QUERY" ]]; then
            clocky_log "empty tag query"
            exit 0
        fi
        clocky_log "tag_query=$TAG_QUERY"

        # Retry with tag. Non-interactive will pick best fuzzy match.
        OUTPUT=$(clocky start --non-interactive "$QUERY" --tag "$TAG_QUERY" 2>&1) || {
            clocky_log "clocky start (with tag) failed: $OUTPUT"
            notify "Failed to start timer: $OUTPUT"
            exit 1
        }
    else
        notify "Failed to start timer: $OUTPUT"
        exit 1
    fi
}

clocky_log "clocky start output: $OUTPUT"

CHOSEN_PROJECT=$(echo "$OUTPUT" | sed -n 's/.*Project:[[:space:]]*//p' | head -1)
CHOSEN_TAG=$(echo "$OUTPUT" | sed -n 's/.*Tag:[[:space:]]*//p' | head -1)

if [[ -n "$CHOSEN_PROJECT" && -n "$CHOSEN_TAG" ]]; then
    notify "Timer started: $CHOSEN_PROJECT\nTag: $CHOSEN_TAG"
elif [[ -n "$CHOSEN_PROJECT" ]]; then
    notify "Timer started: $CHOSEN_PROJECT"
else
    notify "Timer started"
fi
