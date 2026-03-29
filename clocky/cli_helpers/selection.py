# SPDX-License-Identifier: MIT
"""Fuzzy selection helpers for CLI commands.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import sys
from typing import TypeVar

import questionary

from clocky.fuzzy import fuzzy_choices

T = TypeVar("T")


def pick_one[T](
    matches: list[tuple[T, float]],
    attr: str,
    *,
    non_interactive: bool = False,
) -> T | None:
    """Select one item from ranked fuzzy matches.

    The same ranked fuzzy results are used in both interactive and
    non-interactive flows. Interactive mode prompts when multiple matches are
    available; non-interactive mode returns the top-ranked match.

    Args:
        matches: Ranked ``(item, score)`` tuples from fuzzy search.
        attr: Attribute name to display for interactive choices.
        non_interactive: If ``True``, never prompt and return the top match.

    Returns:
        The selected item, or ``None`` when cancelled.

    """
    if non_interactive or not sys.stdin.isatty():
        return matches[0][0] if matches else None

    if len(matches) == 1:
        return matches[0][0]

    choices = fuzzy_choices(matches, attr)
    choices.append(questionary.Choice("[Cancel]", value=None))
    return questionary.select("Pick one:", choices=choices).ask()
