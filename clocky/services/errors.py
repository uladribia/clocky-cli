# SPDX-License-Identifier: MIT
"""Shared service-layer exceptions.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations


class ServiceUsageError(Exception):
    """Raised when user-facing input does not resolve to a valid action."""
