"""Entry point shim — delegates to the clocky CLI package."""

from __future__ import annotations

from clocky.cli import main

if __name__ == "__main__":
    main()
