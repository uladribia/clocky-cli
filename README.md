# clocky-cli

A command-line interface for [Clockify](https://clockify.me) — start/stop timers, browse projects, and view time entries directly from your terminal. Includes Ubuntu desktop launchers to trigger timers from a keyboard shortcut using a small `zenity` GUI flow.

---

## Features

- **Start a timer** with fuzzy project search — handles typos and partial names
- **Stop** the currently running timer
- **Status** — see what's running and for how long
- **List** recent time entries in a formatted table
- **Browse projects** for a client (with optional fuzzy search)
- **Ubuntu launchers** — bind `Super+C` / `Super+X` to start/stop timers via a GUI dialog
- No local data persistence — only your API key is stored (in `.env`)

---

## Requirements

- Python ≥ 3.12
- [`uv`](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- `zenity` (pre-installed on Ubuntu) — only needed for desktop launchers

---

## Installation

> Version: **v1.1.0**

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
# Create the venv and install all dependencies
uv sync

# Run from the project
uv run clocky --help
```

### 5. Shell completion (optional but recommended)

Clocky uses [Typer](https://typer.tiangolo.com/) which provides native completion
for **bash**, **zsh**, and **fish**.

#### One-command install (auto-detects your shell)

```bash
uv run clocky --install-completion
```

Then restart your shell or source the relevant file:

```bash
# bash
source ~/.bashrc

# zsh
source ~/.zshrc

# fish
source ~/.config/fish/config.fish
```

#### Manual setup — bash

```bash
# Generate the script and append to .bashrc
uv run clocky --show-completion >> ~/.bashrc
source ~/.bashrc
```

#### Manual setup — zsh

```bash
uv run clocky --show-completion >> ~/.zshrc
source ~/.zshrc
```

#### Manual setup — fish

```bash
uv run clocky --show-completion > ~/.config/fish/completions/clocky.fish
```

#### Verify completion is working

```bash
clocky <TAB>          # shows: start  stop  status  list  projects
clocky start --<TAB>  # shows: --description  --tag  --no-auto-tag
```

### 4. Manual global install (alternative)

```bash
# Install globally
uv tool install .

# Run setup
clocky setup

# Install completion
clocky --install-completion
```

After install, `clocky` works from any directory:

```bash
clocky --help
```

---

## Usage

### Start a timer

```bash
# Start with fuzzy project search (interactive pick list if multiple matches)
# Tags are auto-inferred from your recent entries for this project!
clocky start "web redesin"

# With a description
clocky start "mobile app" --description "Sprint planning"

# With explicit tags (overrides auto-tag)
clocky start "mobile" --tag "billable" --tag "meeting"

# Disable auto-tag inference
clocky start "mobile" --no-auto-tag

# Non-interactive mode (best match only; no prompts)
# Useful for scripts and launchers.
clocky start --non-interactive "cros-selling"
```

### Stop the running timer

```bash
clocky stop
```

### Check current timer status

```bash
clocky status
```

### List recent time entries

```bash
# Default: last 10 entries
clocky list

# Custom limit
clocky list --limit 25
```

### Browse projects

```bash
# List projects for a client (fuzzy client match)
clocky projects "Dribia"

# Filter projects by name within that client
clocky projects "Dribia" --search "pipeline"
```

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

If neither is available:
- In a terminal: clocky prompts you for a tag (fuzzy), then saves the mapping.
- In a launcher (.desktop): the launcher prompts you for a tag (free text + confirmation), then clocky saves the mapping.

You can view/edit the mapping:

```bash
clocky tag-map show
clocky tag-map edit
clocky tag-map pick
```

This matches the typical Dribia workflow where each project usually maps to one tag (e.g., "Cross-selling" → "Comercial").

### Setup

The `./install.sh` script handles this automatically, but you can also set it up manually:

#### 1. Install launchers

```bash
mkdir -p ~/.local/share/clocky
cp launchers/clocky-launcher.sh ~/.local/share/clocky/
cp launchers/clocky-stop.sh ~/.local/share/clocky/
chmod +x ~/.local/share/clocky/*.sh
```

#### 2. Register keyboard shortcuts in Ubuntu

Go to **Settings → Keyboard → Keyboard Shortcuts → Custom Shortcuts** and add:

| Name | Command | Shortcut |
|---|---|---|
| Clocky Start Timer | `~/.local/share/clocky/clocky-launcher.sh` | `Super+C` |
| Clocky Stop Timer | `~/.local/share/clocky/clocky-stop.sh` | `Super+X` |

Now you can press **Super+C** from anywhere to start a timer!

---

## Project structure

```
clocky-cli/
├── clocky/
│   ├── __init__.py
│   ├── api.py          # ClockifyAPI + MockClockifyAPI
│   ├── cli.py          # Typer CLI commands
│   ├── config.py       # Settings via pydantic-settings + .env
│   ├── context.py      # AppContext (user + workspace resolution)
│   ├── display.py      # Rich-based terminal output helpers
│   ├── fuzzy.py        # rapidfuzz search utilities
│   └── models.py       # Pydantic data models
├── launchers/
│   ├── clocky-launcher.sh       # Start timer launcher (zenity)
│   ├── clocky-stop.sh           # Stop timer launcher
│   ├── clocky-start-timer.desktop
│   └── clocky-stop-timer.desktop
├── tests/
│   ├── test_api_mock.py
│   ├── test_fuzzy.py
│   └── test_models.py
├── .env.example
├── .gitignore
├── check.sh            # Postprocessing: format → lint → typecheck → test
├── pyproject.toml
├── README.md
└── SYSTEM.md
```

---

## Development

Run the full check suite after every change:

```bash
./check.sh
```

This runs in order:
1. `ruff format .` — auto-format
2. `ruff check . --fix` — lint + auto-fix
3. `ty check .` — static type checking
4. `pytest` — full test suite

---

## Authentication

All API calls use the `X-Api-Key` header. Your key is read from the `CLOCKIFY_API_KEY` environment variable (or `.env` file). It is **never** stored anywhere else or logged.
