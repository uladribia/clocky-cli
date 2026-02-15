#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# install.sh — Install clocky-cli globally and run interactive setup.
#
# This script:
# 1. Installs clocky as a global tool via uv
# 2. Runs interactive setup to configure API key
# 3. Installs shell completion
# 4. Sets up Ubuntu keyboard shortcuts (optional)

set -euo pipefail

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📦  Installing clocky-cli..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check for uv
if ! command -v uv &>/dev/null; then
    echo "❌ uv is not installed."
    echo "   Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install globally
uv tool install "$SCRIPT_DIR" --force

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ⚙️  Running setup..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Run interactive setup
clocky setup

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🐚  Installing shell completion..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Detect shell and install completion
SHELL_NAME=$(basename "$SHELL")
case "$SHELL_NAME" in
    bash)
        clocky --install-completion bash 2>/dev/null || true
        echo "✓ Bash completion installed. Run: source ~/.bashrc"
        ;;
    zsh)
        clocky --install-completion zsh 2>/dev/null || true
        echo "✓ Zsh completion installed. Run: source ~/.zshrc"
        ;;
    fish)
        clocky --install-completion fish 2>/dev/null || true
        echo "✓ Fish completion installed."
        ;;
    *)
        echo "⚠ Unknown shell: $SHELL_NAME. Run 'clocky --install-completion' manually."
        ;;
esac

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀  Setting up Ubuntu launchers..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Copy launchers
LAUNCHER_DIR="$HOME/.local/share/clocky"
mkdir -p "$LAUNCHER_DIR"
cp "$SCRIPT_DIR/launchers/clocky-launcher.sh" "$LAUNCHER_DIR/"
cp "$SCRIPT_DIR/launchers/clocky-stop.sh" "$LAUNCHER_DIR/"
cp "$SCRIPT_DIR/launchers/clocky-dispatch.sh" "$LAUNCHER_DIR/"
chmod +x "$LAUNCHER_DIR"/*.sh

echo "✓ Launchers installed to: $LAUNCHER_DIR"

echo ""
echo "To add an app-menu entry (Super → type 'clocky'):"
echo "  cp $SCRIPT_DIR/launchers/clocky.desktop ~/.local/share/applications/"
echo ""
echo "To set up keyboard shortcuts:"
echo ""
echo "  1. Open Settings → Keyboard → Custom Shortcuts"
echo "  2. Add these shortcuts:"
echo ""
echo "     Name: Clocky Start Timer"
echo "     Command: $LAUNCHER_DIR/clocky-launcher.sh"
echo "     Shortcut: Super+C (or your choice)"
echo ""
echo "     Name: Clocky Stop Timer"  
echo "     Command: $LAUNCHER_DIR/clocky-stop.sh"
echo "     Shortcut: Super+X (or your choice)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  clocky status       — check running timer"
echo "  clocky start -p X   — start timer (auto-tags from history)"
echo "  clocky stop         — stop timer"
echo "  clocky projects     — list projects"
echo "  clocky --help       — all commands"
echo ""
