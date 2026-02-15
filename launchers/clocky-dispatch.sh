#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# clocky-dispatch.sh — Desktop entry dispatcher for clocky.
#
# Supports Ubuntu "Super" launcher invocation via additional arguments.
#
# Usage examples (from a .desktop Exec line):
#   clocky-dispatch.sh start
#   clocky-dispatch.sh stop
#   clocky-dispatch.sh start "Cross-selling"
#
# If no subcommand is given, it opens a GUI picker (same as clocky-launcher).

set -euo pipefail

subcommand="${1:-}"
shift || true

# If invoked via .desktop with %U, GNOME may pass a URI-like argument.
# We ignore those and only keep plain args.
filtered_args=()
for a in "$@"; do
  if [[ "$a" == *"://"* ]]; then
    continue
  fi
  filtered_args+=("$a")
done

case "$subcommand" in
  ""|start)
    # If a project argument is provided, ask for optional description and start directly.
    if [[ ${#filtered_args[@]} -ge 1 ]]; then
      project_query="${filtered_args[*]}"
      desc=$(zenity --entry --title="Clocky — Description" --text="Description (optional):" --width=400 2>/dev/null || true)
      if [[ -n "$desc" ]]; then
        clocky start "$project_query" --description "$desc" >/dev/null 2>&1 || true
      else
        clocky start "$project_query" >/dev/null 2>&1 || true
      fi
      exit 0
    fi

    # Otherwise fall back to full GUI flow.
    exec "$HOME/.local/share/clocky/clocky-launcher.sh"
    ;;

  stop)
    exec "$HOME/.local/share/clocky/clocky-stop.sh"
    ;;

  setup)
    # Terminal-less; just run interactive setup in the terminal is not possible.
    zenity --info --title="Clocky" --text="Run 'clocky setup' in a terminal to configure API key." 2>/dev/null || true
    ;;

  *)
    zenity --error --title="Clocky" --text="Unknown clocky command: $subcommand" 2>/dev/null || true
    exit 1
    ;;
esac
