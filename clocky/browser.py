# SPDX-License-Identifier: MIT
"""Browser-opening utility shared across clocky modules.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import subprocess
import webbrowser

CLOCKIFY_API_KEY_URL = "https://app.clockify.me/user/settings#apiKey"


def open_browser(url: str) -> None:
    """Open a URL in the default browser.

    Tries ``xdg-open`` first (Linux/desktop), then falls back to the
    stdlib ``webbrowser`` module.

    Args:
        url: URL to open.

    """
    try:
        subprocess.run(["xdg-open", url], check=True, capture_output=True)  # noqa: S603, S607
    except (FileNotFoundError, subprocess.CalledProcessError):
        webbrowser.open(url)
