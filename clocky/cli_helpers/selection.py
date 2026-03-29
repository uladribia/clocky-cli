# SPDX-License-Identifier: MIT
"""Fuzzy selection helpers for CLI commands.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import sys
from typing import TypeVar

import questionary

T = TypeVar("T")


def fuzzy_choices[T](
    matches: list[tuple[T, float]],
    attr: str = "name",
) -> list[questionary.Choice]:
    """Build prompt choices from ranked fuzzy matches.

    Args:
        matches: Ranked ``(item, score)`` tuples.
        attr: Attribute name used as the display label.

    Returns:
        Questionary choices annotated with percentage scores.

    """
    return [
        questionary.Choice(f"{getattr(item, attr)} ({score:.0f}%)", value=item)
        for item, score in matches
    ]


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
