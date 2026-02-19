---
description: Common issues and solutions for clocky-cli.
---

# Troubleshooting

## TL;DR

- `API key missing` → run `clocky setup` or check `.env`
- `No projects matching` → check spelling, try less specific query
- `CLOCKY_ERROR_MISSING_TAG_MAP` → `clocky tag-map pick` to create mapping
- `uv command not found` → install `uv` (see [install.md](install.md))
- `No colours` → check `NO_COLOR` env var
- `Completion not working` → restart shell, check install instructions

## API key issues

### `API key missing or placeholder`

```
⚠  API key not set
Found .env at: ~/.config/clocky/.env
but CLOCKIFY_API_KEY is missing or still a placeholder.

Fix:
  1. Go to Profile Settings → API on Clockify
  2. Generate or copy your key
  3. Add to ~/.config/clocky/.env:

     CLOCKIFY_API_KEY=your_key_here
```

**Solution**: Run `clocky setup` or manually edit your `.env` file at `~/.config/clocky/.env` (or project root) to include a valid `CLOCKIFY_API_KEY`.

### `httpx.HTTPStatusError: Client error '401 Unauthorized'`

Your API key is likely invalid or expired.

**Solution**: Generate a new API key in Clockify and update your `.env` file.

## Fuzzy search issues

### `No projects matching 'foobar'` / `No clients matching 'foobar'`

The fuzzy search couldn't find any close matches.

**Solution**:
- Double-check spelling.
- Try a less specific query (e.g., `web` instead of `website redesign`).
- List all projects/clients: `clocky projects` (for all projects) or `clocky projects "client name"` (for a specific client).

## Tag mapping issues

### `CLOCKY_ERROR_MISSING_TAG_MAP` (launcher/non-interactive)

This sentinel is emitted to stderr by `clocky start --non-interactive` when it cannot resolve a tag, and no interactive prompt is possible.

**Solution**: Create a tag mapping:
- Interactively: `clocky tag-map pick`
- By using `--tag` once: `clocky start "Project" --tag "MyTag"`

## Environment issues

### `uv command not found`

**Solution**: Install `uv`. See [install.md](install.md) for instructions.

### `No colours in output`

If you are seeing plain text without Rich formatting.

**Solution**: Check if the `NO_COLOR` environment variable is set. Unset it with `unset NO_COLOR` in your shell, or remove it from your shell's config file (`.bashrc`, `.zshrc`, etc.).

## Shell completion issues

### Completion not working after install

**Solution**: After running `clocky --install-completion`, you usually need to restart your shell session or `source` your shell's configuration file (e.g., `source ~/.bashrc` for Bash, `source ~/.zshrc` for Zsh).

If using Fish, the completion file is written to `~/.config/fish/completions/clocky.fish` and should be picked up automatically.

## Launcher issues

### Launchers not responding (Super+C, Super+X)

**Solution**:
- Ensure the scripts are executable: `chmod +x ~/.local/share/clocky/*.sh`
- Verify the paths in your Ubuntu Keyboard Shortcuts match the installed scripts.
- Check the launcher logs for errors: `tail -f ~/Repositories/ula/clocky-cli/logs/launcher.log` (or `~/.local/state/clocky/launcher.log`).
- Ensure `zenity` is installed: `which zenity`.
