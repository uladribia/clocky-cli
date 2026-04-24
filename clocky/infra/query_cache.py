# SPDX-License-Identifier: MIT
"""Persistent cache for repeated start-query resolutions.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from clocky.domain.fuzzy import normalize_text


def _cache_path() -> Path:
    """Return the on-disk path for the query cache."""
    return Path.home() / ".cache" / "clocky" / "query-cache.json"


@dataclass(frozen=True)
class QueryCacheEntry:
    """Cached resolution for a normalized start query."""

    query: str
    project_id: str
    project_name: str
    tag_ids: list[str]
    tag_names: list[str]
    hit_count: int
    updated_at: str


@dataclass(frozen=True)
class QueryCache:
    """Simple JSON-backed cache for repeated start queries."""

    entries: dict[str, QueryCacheEntry]

    @classmethod
    def load(cls) -> QueryCache:
        """Load the query cache from disk."""
        path = _cache_path()
        if not path.exists():
            return cls(entries={})
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return cls(entries={})
        if not isinstance(data, dict):
            return cls(entries={})

        entries: dict[str, QueryCacheEntry] = {}
        for key, value in data.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            try:
                entries[key] = QueryCacheEntry(
                    query=str(value["query"]),
                    project_id=str(value["project_id"]),
                    project_name=str(value["project_name"]),
                    tag_ids=[str(tag_id) for tag_id in value.get("tag_ids", [])],
                    tag_names=[str(tag_name) for tag_name in value.get("tag_names", [])],
                    hit_count=int(value.get("hit_count", 0)),
                    updated_at=str(value.get("updated_at", "")),
                )
            except (KeyError, TypeError, ValueError):
                continue
        return cls(entries=entries)

    def get(self, query: str) -> QueryCacheEntry | None:
        """Return the cached entry for a normalized query, if any."""
        normalized_query = normalize_text(query)
        if not normalized_query:
            return None
        return self.entries.get(normalized_query)

    def remember(
        self,
        query: str,
        *,
        project_id: str,
        project_name: str,
        tag_ids: list[str],
        tag_names: list[str],
    ) -> QueryCache:
        """Return a new cache with a remembered query resolution."""
        normalized_query = normalize_text(query)
        if not normalized_query:
            return self

        existing = self.entries.get(normalized_query)
        entry = QueryCacheEntry(
            query=normalized_query,
            project_id=project_id,
            project_name=project_name,
            tag_ids=list(tag_ids),
            tag_names=list(tag_names),
            hit_count=(existing.hit_count + 1) if existing else 1,
            updated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )
        updated = dict(self.entries)
        updated[normalized_query] = entry
        return QueryCache(entries=updated)

    def save(self) -> None:
        """Persist the query cache to disk."""
        path = _cache_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: asdict(value) for key, value in sorted(self.entries.items())}
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        try:
            path.chmod(0o600)
        except PermissionError:
            pass


def query_cache_path() -> Path:
    """Return the path to the persisted query cache file."""
    return _cache_path()
