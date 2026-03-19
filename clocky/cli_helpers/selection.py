# SPDX-License-Identifier: MIT
"""Fuzzy selection helpers for CLI commands.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, TypeVar

import questionary
import typer
from rich.console import Console

from clocky.display import print_error
from clocky.fuzzy import FUZZY_NON_INTERACTIVE_THRESHOLD, fuzzy_choices

if TYPE_CHECKING:
    pass

T = TypeVar("T")

_no_color = bool(__import__("os").environ.get("NO_COLOR"))
console = Console(no_color=_no_color)


def pick_one[T](
    matches: list[tuple[T, float]],
    attr: str,
    *,
    non_interactive: bool = False,
) -> T | None:
    """Select one item from fuzzy matches.

    Rules:
    - If there is only one match: return it.
    - If non-interactive: return best match.
    - If stdin is not a TTY (e.g. .desktop launch): return best match.
    - Otherwise: prompt user to pick.

    Args:
        matches: List of (item, score) tuples from fuzzy search.
        attr: Attribute name to display for the item.
        non_interactive: If True, never prompt and auto-pick best match.

    Returns:
        Selected item, or None if cancelled/unable.

    """
    if len(matches) == 1:
        return matches[0][0]

    if non_interactive or not sys.stdin.isatty():
        best_match, best_score = matches[0]
        if best_score < FUZZY_NON_INTERACTIVE_THRESHOLD:
            print_error(
                "No exact project match found in non-interactive mode. "
                f"Closest match was '{getattr(best_match, attr)}' (score: {best_score:.0f}%). "
                "Please use a more precise query or interactive mode."
            )
            raise typer.Exit(2)
        return best_match

    choices = fuzzy_choices(matches, attr)
    choices.append(questionary.Choice("[Cancel]", value=None))
    return questionary.select("Pick one:", choices=choices).ask()
