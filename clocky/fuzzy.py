# SPDX-License-Identifier: MIT
"""Fuzzy search utilities using rapidfuzz.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from collections.abc import Callable

import questionary
from rapidfuzz import fuzz, process

DEFAULT_CUTOFF = 40
DEFAULT_LIMIT = 10


def fuzzy_search[T](
    query: str,
    items: list[T],
    key: Callable[[T], str],
    *,
    cutoff: float = DEFAULT_CUTOFF,
    limit: int = DEFAULT_LIMIT,
) -> list[tuple[T, float]]:
    """Fuzzy-search a list of objects.

    Args:
        query: Search string (may be misspelled).
        items: Objects to search through.
        key: Function to extract the searchable string from each item.
        cutoff: Minimum score (0–100) to include a result.
        limit: Maximum results to return.

    Returns:
        List of (item, score) tuples, sorted by descending score.
        Returns all items with score 100 if query is empty.

    """
    if not query:
        return [(item, 100.0) for item in items]

    choices = {i: key(item) for i, item in enumerate(items)}
    results = process.extract(
        query,
        choices,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=cutoff,
        limit=limit,
    )
    return [(items[idx], score) for (_, score, idx) in results]


def fuzzy_best[T](
    query: str,
    items: list[T],
    key: Callable[[T], str],
    *,
    cutoff: float = DEFAULT_CUTOFF,
) -> T | None:
    """Return the single best fuzzy match, or None if nothing meets the cutoff."""
    results = fuzzy_search(query, items, key, cutoff=cutoff, limit=1)
    return results[0][0] if results else None


def fuzzy_choices[T](
    matches: list[tuple[T, float]],
    attr: str = "name",
) -> list[questionary.Choice]:
    """Build a questionary Choice list from fuzzy match results.

    Args:
        matches: List of (item, score) tuples from :func:`fuzzy_search`.
        attr: Attribute name to use as the choice label.

    Returns:
        List of ``questionary.Choice`` objects annotated with match percentage.

    """
    return [
        questionary.Choice(f"{getattr(item, attr)} ({score:.0f}%)", value=item)
        for item, score in matches
    ]
