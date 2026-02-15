#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Shared helpers for clocky launchers (logging + small utilities).

set -euo pipefail

# Read install-time config (written by install.sh)
CLOCKY_CONF_FILE="${CLOCKY_CONF_FILE:-$HOME/.local/share/clocky/clocky.conf}"
if [[ -f "$CLOCKY_CONF_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CLOCKY_CONF_FILE"
fi

CLOCKY_REPO_DIR="${CLOCKY_REPO_DIR:-}"

clocky_log_path() {
  if [[ -n "$CLOCKY_REPO_DIR" ]]; then
    echo "$CLOCKY_REPO_DIR/logs/launcher.log"
  else
    # Fallback (still bounded): per-user state
    echo "$HOME/.local/state/clocky/launcher.log"
  fi
}

CLOCKY_LOG_FILE="${CLOCKY_LOG_FILE:-$(clocky_log_path)}"
CLOCKY_LOG_MAX_BYTES="${CLOCKY_LOG_MAX_BYTES:-500000}" # 500KB

clocky_log_init() {
  local log_dir
  log_dir="$(dirname "$CLOCKY_LOG_FILE")"
  mkdir -p "$log_dir"
  if [[ ! -f "$CLOCKY_LOG_FILE" ]]; then
    : >"$CLOCKY_LOG_FILE"
  fi
}

clocky_log_rotate() {
  clocky_log_init
  local size
  size=$(wc -c <"$CLOCKY_LOG_FILE" 2>/dev/null || echo 0)
  if [[ "$size" -le "$CLOCKY_LOG_MAX_BYTES" ]]; then
    return
  fi

  # Keep last 50% of max bytes
  local keep
  keep=$((CLOCKY_LOG_MAX_BYTES / 2))

  if tail -c "$keep" "$CLOCKY_LOG_FILE" >"$CLOCKY_LOG_FILE.tmp" 2>/dev/null; then
    mv -f "$CLOCKY_LOG_FILE.tmp" "$CLOCKY_LOG_FILE" 2>/dev/null || true
  fi

  printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "[log rotated: kept last ${keep} bytes]" >>"$CLOCKY_LOG_FILE" || true
}

clocky_log() {
  local msg="$1"
  clocky_log_init
  printf '%s %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$msg" >>"$CLOCKY_LOG_FILE" || true
  clocky_log_rotate
}

clocky_log_env_snapshot() {
  clocky_log "user=$(id -un 2>/dev/null || true) uid=$(id -u 2>/dev/null || true)"
  clocky_log "cwd=$(pwd 2>/dev/null || true)"
  clocky_log "shell=${SHELL:-}"
  clocky_log "PATH=$PATH"
  clocky_log "display=${DISPLAY:-} wayland=${WAYLAND_DISPLAY:-} xdg_current_desktop=${XDG_CURRENT_DESKTOP:-}"
  clocky_log "clocky_in_path=$(command -v clocky 2>/dev/null || true)"
}
