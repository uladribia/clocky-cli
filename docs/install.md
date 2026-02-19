---
description: How to install and configure clocky-cli.
---

# Install clocky-cli

## TL;DR

```bash
git clone https://github.com/uladribia/clocky-cli.git
cd clocky-cli
./install.sh
```

## Requirements

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | ≥ 3.12 | Runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Package manager |
| zenity | any | Ubuntu launchers only |

## Install methods

### One-step installer (recommended)

```bash
./install.sh
```

This runs `uv tool install`, interactive setup, shell completion, and launcher install.

### Local development

```bash
uv sync
uv run clocky --help
```

### Global manual install

```bash
uv tool install .
clocky setup
clocky --install-completion
```

## Configuration

clocky reads settings from a `.env` file. Search order:

1. Current directory (and parents)
2. `~/.config/clocky/.env` ← recommended for global install
3. `~/.clocky.env`

### Create the config

```bash
mkdir -p ~/.config/clocky
cat > ~/.config/clocky/.env << 'EOF'
CLOCKIFY_API_KEY=your_api_key_here
# CLOCKIFY_WORKSPACE_ID=optional_workspace_id
EOF
```

### Get your API key

1. Go to [Profile Settings → API](https://app.clockify.me/user/settings#apiKey)
2. Generate or copy your key
3. Paste it into `.env`

Or run `clocky setup` for a guided flow.

### Environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CLOCKIFY_API_KEY` | Yes | — | Your Clockify API key |
| `CLOCKIFY_WORKSPACE_ID` | No | User's default | Pin a specific workspace |

## Shell completion

```bash
clocky --install-completion    # auto-detects bash/zsh/fish
```

Verify:

```bash
clocky <TAB>          # shows: start stop status list projects delete tag-map
clocky start --<TAB>  # shows: --description --tag --dry-run ...
```
