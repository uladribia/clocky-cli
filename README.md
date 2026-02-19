# clocky-cli

A command-line interface for [Clockify](https://clockify.me) — start/stop timers, browse projects, and view time entries directly from your terminal. Includes Ubuntu desktop launchers to trigger timers from a keyboard shortcut using a small `zenity` GUI flow.

---

## Features

- **Start a timer** with fuzzy project search — handles typos and partial names
- **Stop** the currently running timer (with safety prompt for long-running timers)
- **Status** — see what's running and for how long
- **List** recent time entries in a formatted table
- **Delete** a time entry by ID (with confirmation)
- **Browse projects** for a client or list all projects
- **`--json` output** for scripting and piping to `jq`
- **`--quiet` mode** to suppress informational output
- **`--dry-run`** to preview `start` without creating a timer
- **`NO_COLOR`** env variable respected
- **Ubuntu launchers** — bind `Super+C` / `Super+X` to start/stop timers via a GUI dialog
- No local data persistence — only your API key is stored (in `.env`)

---

## Requirements

- Python ≥ 3.12
- [`uv`](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- `zenity` (pre-installed on Ubuntu) — only needed for desktop launchers

---

## Installation

> Version: **v2.1.0**

### 1. Clone the repository

```bash
git clone https://github.com/youruser/clocky-cli.git
cd clocky-cli
```

### 2. Create and configure your `.env` file

clocky looks for `.env` in these locations (in order):
1. Current directory (and parent directories)
2. `~/.config/clocky/.env` (recommended for global install)
3. `~/.clocky.env`

**For global installation**, use the XDG config location:

```bash
mkdir -p ~/.config/clocky
echo "CLOCKIFY_API_KEY=your_api_key_here" > ~/.config/clocky/.env
```

**For project-local use**:

```bash
cp .env.example .env
```

Get your API key at **[Profile Settings → API](https://app.clockify.me/user/settings#apiKey)**.

```env
CLOCKIFY_API_KEY=your_api_key_here

# Optional: pin a specific workspace ID
# CLOCKIFY_WORKSPACE_ID=your_workspace_id_here
```

> **First run without a key?** clocky will detect the missing key, print setup
> instructions, and offer to open the Clockify API key page in your browser automatically.

### 3. Install

#### Option A (recommended): one-step installer

```bash
./install.sh
```

#### Option B: local development install

```bash
uv sync
uv run clocky --help
```

### 4. Manual global install (alternative)

```bash
uv tool install .
clocky setup
clocky --install-completion
```

### 5. Shell completion (optional but recommended)

```bash
uv run clocky --install-completion
```

Then restart your shell or source the relevant file (`~/.bashrc`, `~/.zshrc`, etc.).

---

## Usage

### Global flags

These flags work with any command:

| Flag | Description |
|------|-------------|
| `--json` | Output JSON to stdout (implies `--quiet`) |
| `--quiet` / `-q` | Suppress informational output |
| `--version` / `-V` | Show version and exit |
| `--help` | Show help |

### Start a timer

```bash
# Fuzzy project search (interactive pick list if multiple matches)
clocky start "web redesin"

# With a description
clocky start "mobile app" --description "Sprint planning"

# With explicit tags
clocky start "mobile" --tag "billable" --tag "meeting"

# Disable auto-tag inference
clocky start "mobile" --no-auto-tag

# Non-interactive (best match, no prompts — for scripts/launchers)
clocky start --non-interactive "cros-selling"

# Preview without starting
clocky start --dry-run "mobile app"

# JSON output
clocky --json start "mobile" --non-interactive
```

### Stop the running timer

```bash
clocky stop

# Skip confirmation on long-running timers (>8h)
clocky stop --force
```

### Check current timer status

```bash
clocky status
clocky --json status
```

### List recent time entries

```bash
clocky list
clocky list --limit 25
clocky --json list | jq '.[].project_name'
```

### Browse projects

```bash
# List all projects
clocky projects

# Filter by client (fuzzy)
clocky projects "Dribia"

# Filter by client + project name
clocky projects "Dribia" --search "pipeline"

# JSON output
clocky --json projects
```

### Delete a time entry

```bash
# Interactive confirmation
clocky delete entry-abc123

# Skip confirmation
clocky delete entry-abc123 --force
```

### Manage project→tag mapping

```bash
clocky tag-map show
clocky tag-map edit
clocky tag-map pick
clocky tag-map set <project-id> <tag-id>
clocky tag-map remove <project-id>
```

---

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime error (API failure, no timer running, etc.) |
| 2 | Usage error (no fuzzy match found, bad input) |

---

## Ubuntu Launchers (Windows key shortcuts)

The `launchers/` directory contains shell scripts and `.desktop` files to control Clockify from a keyboard shortcut.

### How it works

Press **Super+C** (or your chosen shortcut) to:
1. Open a dialog to type a project name (fuzzy)
2. Start the timer using the best fuzzy match (no terminal prompts)
3. If no tag is mapped yet, ask for a tag (free text, fuzzy matched)
4. Show a notification with the chosen project and tag

Press **Super+X** to instantly stop the timer with a notification.

The auto-tag feature uses (in order):
1. A persisted 1:1 **project→tag mapping** (recommended)
2. Your last 50 entries for the project (history-based inference)

### Setup

The `./install.sh` script handles this automatically, or manually:

```bash
mkdir -p ~/.local/share/clocky
cp launchers/clocky-launcher.sh launchers/clocky-stop.sh ~/.local/share/clocky/
cp launchers/lib.sh ~/.local/share/clocky/
chmod +x ~/.local/share/clocky/*.sh
```

Then add keyboard shortcuts in **Settings → Keyboard → Custom Shortcuts**:

| Name | Command | Shortcut |
|------|---------|----------|
| Clocky Start Timer | `~/.local/share/clocky/clocky-launcher.sh` | `Super+C` |
| Clocky Stop Timer | `~/.local/share/clocky/clocky-stop.sh` | `Super+X` |

---

## Project structure

```
clocky-cli/
├── clocky/
│   ├── api.py           # ClockifyAPI HTTP client
│   ├── cli.py           # Typer CLI commands
│   ├── cli_tag_map.py   # Tag-map subcommands
│   ├── config.py        # Settings via pydantic-settings + .env
│   ├── context.py       # AppContext (user + workspace resolution)
│   ├── display.py       # Rich-based terminal output
│   ├── fuzzy.py         # rapidfuzz search utilities
│   ├── models.py        # Pydantic data models
│   ├── output.py        # JSON output and mode state
│   ├── setup.py         # Interactive setup wizard
│   ├── tag_map.py       # Persistent project→tag mapping
│   └── testing.py       # Mock API for offline tests
├── launchers/           # Ubuntu .desktop files and shell scripts
├── tests/               # pytest test suite
├── check.sh             # Format → lint → typecheck → test
├── install.sh           # One-step global installer
├── pyproject.toml
├── AGENTS.md            # Agent/AI workflow instructions
└── README.md
```

---

## Development

```bash
./check.sh
```

Runs: `ruff format .` → `ruff check . --fix` → `ty check .` → `pytest`

---

## Authentication

All API calls use the `X-Api-Key` header. Your key is read from `CLOCKIFY_API_KEY` (environment variable or `.env`). It is never stored anywhere else or logged.
