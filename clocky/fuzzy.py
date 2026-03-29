# SPDX-License-Identifier: MIT
"""Weighted fuzzy search utilities using rapidfuzz.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

import questionary
from rapidfuzz import fuzz

from clocky.models import Project, Tag, TimeEntry

DEFAULT_CUTOFF = 40.0
DEFAULT_LIMIT = 10
SEARCH_HISTORY_LIMIT = 200
_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class UsageStats:
    """Recent usage statistics derived from time entries.

    Attributes:
        reference_time: Newest entry timestamp, used as the recency baseline.
        project_counts: Number of recent entries per project.
        project_last_used: Most recent usage timestamp per project.
        tag_counts: Number of recent entries per tag.
        tag_last_used: Most recent usage timestamp per tag.
        project_tag_counts: Number of recent entries for each project-tag pair.
        project_tag_last_used: Most recent usage timestamp for each project-tag pair.

    """

    reference_time: datetime
    project_counts: dict[str, int]
    project_last_used: dict[str, datetime]
    tag_counts: dict[str, int]
    tag_last_used: dict[str, datetime]
    project_tag_counts: dict[tuple[str, str], int]
    project_tag_last_used: dict[tuple[str, str], datetime]


@dataclass(frozen=True)
class ScoreDetails:
    """Score breakdown for a weighted fuzzy match.

    Attributes:
        lexical: Combined typo-tolerant lexical similarity score.
        token_prefix: Query-token coverage over candidate tokens.
        starts_with: Prefix-match indicator for the whole candidate.
        recency: Usage-recency prior.
        frequency: Usage-frequency prior.
        final: Final weighted score.

    """

    lexical: float
    token_prefix: float
    starts_with: float
    recency: float
    frequency: float
    final: float


@dataclass(frozen=True)
class WeightedMatch[T]:
    """Weighted fuzzy match result.

    Attributes:
        item: Matched item.
        score: Final score in the 0-100 range.
        details: Score breakdown used for ranking.

    """

    item: T
    score: float
    details: ScoreDetails


def normalize_text(text: str) -> str:
    """Normalize text for deterministic matching.

    Args:
        text: Raw input string.

    Returns:
        Lower-cased alphanumeric text with punctuation collapsed to spaces.

    """
    tokens = _WORD_RE.findall(text.casefold())
    return " ".join(tokens)


def tokenize(text: str) -> list[str]:
    """Return normalized alphanumeric tokens for ``text``.

    Args:
        text: Raw input string.

    Returns:
        List of normalized tokens.

    """
    normalized = normalize_text(text)
    return normalized.split() if normalized else []


def build_usage_stats(entries: Iterable[TimeEntry]) -> UsageStats:
    """Build project and tag usage statistics from recent entries.

    Args:
        entries: Recent time entries ordered arbitrarily.

    Returns:
        Aggregated project/tag usage statistics.

    """
    project_counts: dict[str, int] = {}
    project_last_used: dict[str, datetime] = {}
    tag_counts: dict[str, int] = {}
    tag_last_used: dict[str, datetime] = {}
    project_tag_counts: dict[tuple[str, str], int] = {}
    project_tag_last_used: dict[tuple[str, str], datetime] = {}
    reference_time = datetime.now(UTC)

    for entry in entries:
        started_at = _coerce_utc(entry.time_interval.start)
        if started_at > reference_time:
            reference_time = started_at

        if entry.project_id:
            project_counts[entry.project_id] = project_counts.get(entry.project_id, 0) + 1
            project_last_used[entry.project_id] = _latest_datetime(
                project_last_used.get(entry.project_id),
                started_at,
            )

        for tag_id in entry.tag_ids:
            tag_counts[tag_id] = tag_counts.get(tag_id, 0) + 1
            tag_last_used[tag_id] = _latest_datetime(tag_last_used.get(tag_id), started_at)

            if entry.project_id:
                pair = (entry.project_id, tag_id)
                project_tag_counts[pair] = project_tag_counts.get(pair, 0) + 1
                project_tag_last_used[pair] = _latest_datetime(
                    project_tag_last_used.get(pair),
                    started_at,
                )

    return UsageStats(
        reference_time=reference_time,
        project_counts=project_counts,
        project_last_used=project_last_used,
        tag_counts=tag_counts,
        tag_last_used=tag_last_used,
        project_tag_counts=project_tag_counts,
        project_tag_last_used=project_tag_last_used,
    )


def fuzzy_search[T](
    query: str,
    items: list[T],
    key: Callable[[T], str],
    *,
    cutoff: float = DEFAULT_CUTOFF,
    limit: int = DEFAULT_LIMIT,
    alias: Callable[[T], str] | None = None,
) -> list[tuple[T, float]]:
    """Fuzzy-search a list of objects using weighted lexical scoring.

    Args:
        query: Search string, potentially partial or misspelled.
        items: Objects to search through.
        key: Function extracting the primary searchable string.
        cutoff: Minimum score (0-100) required to keep a result.
        limit: Maximum number of results to return.
        alias: Optional secondary searchable string, such as a client name.

    Returns:
        List of ``(item, score)`` tuples sorted by descending score.

    """
    matches = weighted_fuzzy_search(query, items, key, cutoff=cutoff, limit=limit, alias=alias)
    return [(match.item, match.score) for match in matches]


def fuzzy_search_projects(
    query: str,
    projects: list[Project],
    entries: Iterable[TimeEntry],
    *,
    cutoff: float = DEFAULT_CUTOFF,
    limit: int = DEFAULT_LIMIT,
) -> list[tuple[Project, float]]:
    """Fuzzy-search projects using lexical and recent-usage signals.

    Args:
        query: User project query.
        projects: Available workspace projects.
        entries: Recent time entries used to derive usage priors.
        cutoff: Minimum weighted score.
        limit: Maximum number of matches.

    Returns:
        List of ``(project, score)`` tuples sorted by descending score.

    """
    usage = build_usage_stats(entries)
    matches = weighted_fuzzy_search(
        query,
        projects,
        lambda project: project.name,
        cutoff=cutoff,
        limit=limit,
        alias=lambda project: f"{project.client_name or ''} {project.name}".strip(),
        scorer=lambda q, project: _score_project_match(q, project, usage),
    )
    return [(match.item, match.score) for match in matches]


def fuzzy_search_tags(
    query: str,
    tags: list[Tag],
    entries: Iterable[TimeEntry],
    *,
    project_id: str | None = None,
    cutoff: float = DEFAULT_CUTOFF,
    limit: int = DEFAULT_LIMIT,
) -> list[tuple[Tag, float]]:
    """Fuzzy-search tags using lexical and project-specific history.

    Args:
        query: User tag query.
        tags: Available workspace tags.
        entries: Recent time entries used to derive usage priors.
        project_id: Optional chosen project ID for project-specific tag ranking.
        cutoff: Minimum weighted score.
        limit: Maximum number of matches.

    Returns:
        List of ``(tag, score)`` tuples sorted by descending score.

    """
    usage = build_usage_stats(entries)
    matches = weighted_fuzzy_search(
        query,
        tags,
        lambda tag: tag.name,
        cutoff=cutoff,
        limit=limit,
        scorer=lambda q, tag: _score_tag_match(q, tag, usage, project_id=project_id),
    )
    return [(match.item, match.score) for match in matches]


def weighted_fuzzy_search[T](
    query: str,
    items: list[T],
    key: Callable[[T], str],
    *,
    cutoff: float = DEFAULT_CUTOFF,
    limit: int = DEFAULT_LIMIT,
    alias: Callable[[T], str] | None = None,
    scorer: Callable[[str, T], ScoreDetails] | None = None,
) -> list[WeightedMatch[T]]:
    """Return weighted fuzzy matches with score breakdowns.

    Args:
        query: User search query.
        items: Searchable items.
        key: Function extracting the display text.
        cutoff: Minimum weighted score in the 0-100 range.
        limit: Maximum number of results.
        alias: Optional secondary searchable string.
        scorer: Optional custom scorer. Defaults to lexical-only scoring.

    Returns:
        Weighted matches sorted by descending score.

    """
    if not query:
        return [
            WeightedMatch(
                item=item,
                score=100.0,
                details=ScoreDetails(
                    lexical=1.0,
                    token_prefix=1.0,
                    starts_with=1.0,
                    recency=0.0,
                    frequency=0.0,
                    final=1.0,
                ),
            )
            for item in items[:limit]
        ]

    query_norm = normalize_text(query)
    if not query_norm:
        return []

    score_match = scorer or (
        lambda normalized_query, item: _score_lexical_match(
            normalized_query,
            key(item),
            alias_text=alias(item) if alias else None,
        )
    )

    matches: list[WeightedMatch[T]] = []
    for item in items:
        details = score_match(query_norm, item)
        score = details.final * 100.0
        if score < cutoff:
            continue
        matches.append(WeightedMatch(item=item, score=score, details=details))

    matches.sort(
        key=lambda match: (
            match.score,
            match.details.lexical,
            match.details.token_prefix,
            key(match.item).casefold(),
        ),
        reverse=True,
    )
    return matches[:limit]


def fuzzy_best[T](
    query: str,
    items: list[T],
    key: Callable[[T], str],
    *,
    cutoff: float = DEFAULT_CUTOFF,
) -> T | None:
    """Return the single best fuzzy match, or ``None`` below the cutoff.

    Args:
        query: Search string.
        items: Searchable items.
        key: Function extracting the searchable string.
        cutoff: Minimum score in the 0-100 range.

    Returns:
        Best matching item or ``None``.

    """
    results = fuzzy_search(query, items, key, cutoff=cutoff, limit=1)
    return results[0][0] if results else None


def fuzzy_choices[T](
    matches: list[tuple[T, float]],
    attr: str = "name",
) -> list[questionary.Choice]:
    """Build a questionary Choice list from fuzzy match results.

    Args:
        matches: List of ``(item, score)`` tuples from a fuzzy search.
        attr: Attribute name to use as the choice label.

    Returns:
        Choice objects annotated with the weighted match percentage.

    """
    return [
        questionary.Choice(f"{getattr(item, attr)} ({score:.0f}%)", value=item)
        for item, score in matches
    ]


def _score_project_match(query_norm: str, project: Project, usage: UsageStats) -> ScoreDetails:
    """Score a project match using lexical and recent-usage priors.

    Args:
        query_norm: Normalized user query.
        project: Candidate project.
        usage: Recent usage statistics.

    Returns:
        Score breakdown for the candidate project.

    """
    lexical = _score_lexical_match(
        query_norm,
        project.name,
        alias_text=f"{project.client_name or ''} {project.name}".strip(),
    )
    recency = _recency_score(usage.project_last_used.get(project.id), usage.reference_time)
    frequency = _frequency_score(project.id, usage.project_counts)
    archived_penalty = 0.08 if project.archived else 0.0
    final = max(
        0.0,
        (0.68 * lexical.lexical)
        + (0.12 * lexical.token_prefix)
        + (0.06 * lexical.starts_with)
        + (0.10 * recency)
        + (0.08 * frequency)
        - archived_penalty,
    )
    return ScoreDetails(
        lexical=lexical.lexical,
        token_prefix=lexical.token_prefix,
        starts_with=lexical.starts_with,
        recency=recency,
        frequency=frequency,
        final=min(final, 1.0),
    )


def _score_tag_match(
    query_norm: str,
    tag: Tag,
    usage: UsageStats,
    *,
    project_id: str | None,
) -> ScoreDetails:
    """Score a tag match using lexical and project-specific history.

    Args:
        query_norm: Normalized user query.
        tag: Candidate tag.
        usage: Recent usage statistics.
        project_id: Selected project ID, when available.

    Returns:
        Score breakdown for the candidate tag.

    """
    lexical = _score_lexical_match(query_norm, tag.name)
    project_pair = (project_id, tag.id) if project_id else None
    project_frequency = (
        _frequency_score(project_pair, usage.project_tag_counts) if project_pair else 0.0
    )
    project_recency = (
        _recency_score(usage.project_tag_last_used.get(project_pair), usage.reference_time)
        if project_pair
        else 0.0
    )
    global_frequency = _frequency_score(tag.id, usage.tag_counts)
    global_recency = _recency_score(usage.tag_last_used.get(tag.id), usage.reference_time)
    recency = max(project_recency, global_recency * 0.4)
    frequency = max(project_frequency, global_frequency * 0.35)
    final = min(
        (0.58 * lexical.lexical)
        + (0.12 * lexical.token_prefix)
        + (0.05 * lexical.starts_with)
        + (0.17 * project_frequency)
        + (0.05 * project_recency)
        + (0.02 * global_frequency)
        + (0.01 * global_recency),
        1.0,
    )
    return ScoreDetails(
        lexical=lexical.lexical,
        token_prefix=lexical.token_prefix,
        starts_with=lexical.starts_with,
        recency=recency,
        frequency=frequency,
        final=final,
    )


def _score_lexical_match(
    query_norm: str,
    text: str,
    *,
    alias_text: str | None = None,
) -> ScoreDetails:
    """Score lexical similarity between a normalized query and candidate text.

    Args:
        query_norm: Normalized user query.
        text: Candidate text.
        alias_text: Optional secondary text to search against.

    Returns:
        Lexical score details with zeroed usage priors.

    """
    text_norm = normalize_text(text)
    if not text_norm:
        return ScoreDetails(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    primary = _lexical_components(query_norm, text_norm)
    if alias_text:
        alias_norm = normalize_text(alias_text)
        alias_components = _lexical_components(query_norm, alias_norm)
        lexical = max(primary[0], alias_components[0])
        token_prefix = max(primary[1], alias_components[1])
        starts_with = max(primary[2], alias_components[2])
    else:
        lexical, token_prefix, starts_with = primary

    final = min((0.82 * lexical) + (0.12 * token_prefix) + (0.06 * starts_with), 1.0)
    return ScoreDetails(
        lexical=lexical,
        token_prefix=token_prefix,
        starts_with=starts_with,
        recency=0.0,
        frequency=0.0,
        final=final,
    )


def _lexical_components(query_norm: str, candidate_norm: str) -> tuple[float, float, float]:
    """Compute lexical similarity components for a normalized candidate.

    Args:
        query_norm: Normalized user query.
        candidate_norm: Normalized candidate string.

    Returns:
        Tuple of ``(lexical, token_prefix, starts_with)`` scores.

    """
    if query_norm == candidate_norm:
        return (1.0, 1.0, 1.0)

    query_tokens = query_norm.split()
    candidate_tokens = candidate_norm.split()
    token_prefix = _token_prefix_score(query_tokens, candidate_tokens)
    starts_with = 1.0 if candidate_norm.startswith(query_norm) else 0.0
    exact_token_subset = (
        1.0 if query_tokens and all(token in candidate_tokens for token in query_tokens) else 0.0
    )

    wratio = fuzz.WRatio(query_norm, candidate_norm) / 100.0
    partial = fuzz.partial_ratio(query_norm, candidate_norm) / 100.0
    token_sort = fuzz.token_sort_ratio(query_norm, candidate_norm) / 100.0
    ratio = fuzz.ratio(query_norm, candidate_norm) / 100.0

    lexical = max(
        0.42 * wratio + 0.23 * partial + 0.20 * token_sort + 0.10 * token_prefix + 0.05 * ratio,
        0.94 if starts_with and len(query_norm) >= 4 else 0.0,
        0.90 if exact_token_subset and len(query_tokens) > 1 else 0.0,
        0.86 if token_prefix == 1.0 and query_tokens else 0.0,
    )
    return (min(lexical, 1.0), token_prefix, starts_with)


def _token_prefix_score(query_tokens: list[str], candidate_tokens: list[str]) -> float:
    """Return the fraction of query tokens matching candidate token prefixes.

    Args:
        query_tokens: Normalized query tokens.
        candidate_tokens: Normalized candidate tokens.

    Returns:
        Fraction in the ``0-1`` range.

    """
    if not query_tokens:
        return 0.0

    matched = 0
    for token in query_tokens:
        if any(candidate.startswith(token) for candidate in candidate_tokens):
            matched += 1
    return matched / len(query_tokens)


def _coerce_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime.

    Args:
        value: Input datetime.

    Returns:
        UTC-normalized datetime.

    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _latest_datetime(current: datetime | None, new_value: datetime) -> datetime:
    """Return the later of two datetimes.

    Args:
        current: Current stored datetime, if any.
        new_value: Candidate datetime.

    Returns:
        The later datetime.

    """
    if current is None or new_value > current:
        return new_value
    return current


def _recency_score(last_used: datetime | None, reference_time: datetime) -> float:
    """Convert a last-used timestamp into an exponential recency score.

    Args:
        last_used: Most recent usage timestamp.
        reference_time: Baseline time used for decay.

    Returns:
        Score in the ``0-1`` range.

    """
    if last_used is None:
        return 0.0
    age_days = max((reference_time - last_used).total_seconds(), 0.0) / 86_400.0
    return math.exp(-age_days / 30.0)


def _frequency_score[TKey](key: TKey, counts: dict[TKey, int]) -> float:
    """Convert occurrence counts into a normalized frequency score.

    Args:
        key: Project, tag, or project-tag key.
        counts: Count mapping for that key family.

    Returns:
        Score in the ``0-1`` range.

    """
    if not counts or key not in counts:
        return 0.0
    max_count = max(counts.values())
    if max_count <= 0:
        return 0.0
    return math.log1p(counts[key]) / math.log1p(max_count)
