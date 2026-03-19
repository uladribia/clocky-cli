# SPDX-License-Identifier: MIT
"""Centralized Rich console instances.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import os

from rich.console import Console

_no_color = bool(os.environ.get("NO_COLOR"))

# Main console for stdout
console = Console(no_color=_no_color)

# Error console for stderr
err_console = Console(stderr=True, no_color=_no_color)
