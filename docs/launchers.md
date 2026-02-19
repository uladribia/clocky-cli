---
description: How to set up Ubuntu desktop launchers and keyboard shortcuts.
---

# Ubuntu launchers

## TL;DR

```bash
./install.sh   # installs launchers automatically
```

Then bind **Super+C** → start timer, **Super+X** → stop timer.

## How it works

| Shortcut | Script | Action |
|----------|--------|--------|
| Super+C | `clocky-launcher.sh` | Zenity dialog → fuzzy project → start timer → notification |
| Super+X | `clocky-stop.sh` | Stop timer → notification with duration |

The launcher runs `clocky start --non-interactive` under the hood. No terminal needed.

## Flow: start timer (Super+C)

1. Zenity text entry: "Project name (fuzzy search)"
2. `clocky start --non-interactive "<query>"` with best fuzzy match
3. If `CLOCKY_ERROR_MISSING_TAG_MAP` detected → Zenity asks for a tag
4. Retry with `--tag "<tag_query>"`
5. Desktop notification: "Timer started: Project Name / Tag: TagName"

## Flow: stop timer (Super+X)

1. `clocky stop`
2. Desktop notification: "Timer stopped / Duration: 2h 15m 3s"

## Manual setup

### 1. Copy scripts

```bash
mkdir -p ~/.local/share/clocky
cp launchers/clocky-launcher.sh ~/.local/share/clocky/
cp launchers/clocky-stop.sh ~/.local/share/clocky/
cp launchers/clocky-dispatch.sh ~/.local/share/clocky/
cp launchers/lib.sh ~/.local/share/clocky/
chmod +x ~/.local/share/clocky/*.sh
```

### 2. Write config

```bash
cat > ~/.local/share/clocky/clocky.conf << EOF
CLOCKY_REPO_DIR=/path/to/clocky-cli
EOF
```

### 3. Add keyboard shortcuts

**Settings → Keyboard → Custom Shortcuts:**

| Name | Command | Shortcut |
|------|---------|----------|
| Clocky Start Timer | `~/.local/share/clocky/clocky-launcher.sh` | Super+C |
| Clocky Stop Timer | `~/.local/share/clocky/clocky-stop.sh` | Super+X |

### 4. (Optional) App menu entries

```bash
cp launchers/clocky-start.desktop ~/.local/share/applications/
cp launchers/clocky-stop.desktop ~/.local/share/applications/
```

Then search "clocky start" / "clocky stop" in the Ubuntu app menu.

## Dispatch entry

`clocky-dispatch.sh` supports `.desktop` Exec arguments:

```bash
clocky-dispatch.sh start              # full GUI flow
clocky-dispatch.sh start "Cross-sell" # direct start with project
clocky-dispatch.sh stop               # stop timer
```

## Logging

Launcher logs go to `<repo>/logs/launcher.log` (or `~/.local/state/clocky/launcher.log` as fallback). Auto-rotated at 500KB.

## Contracts

Launchers depend on these clocky CLI behaviours. **Do not change without updating launchers:**

| Contract | Used by |
|----------|---------|
| `--non-interactive` auto-picks best match | `clocky-launcher.sh` |
| `CLOCKY_ERROR_MISSING_TAG_MAP` on stderr | `clocky-launcher.sh` |
| Stdout `Project:` / `Tag:` lines | `clocky-launcher.sh` (sed parsing) |
| `clocky stop` exit 0 with "No timer" | `clocky-stop.sh` |
