"""Tests for fuzzy search utilities."""

from __future__ import annotations

from clocky.fuzzy import fuzzy_best, fuzzy_search
from clocky.testing import MOCK_CLIENTS, MOCK_PROJECTS


class TestFuzzySearch:
    """Tests for fuzzy_search()."""

    def test_exact_match_first(self) -> None:
        results = fuzzy_search("Website Redesign", MOCK_PROJECTS, lambda p: p.name)
        assert results[0][0].name == "Website Redesign"

    def test_typo_matches(self) -> None:
        results = fuzzy_search("Webiste Redesin", MOCK_PROJECTS, lambda p: p.name)
        names = [p.name for p, _ in results]
        assert "Website Redesign" in names

    def test_partial_matches(self) -> None:
        results = fuzzy_search("Mobile", MOCK_PROJECTS, lambda p: p.name)
        names = [p.name for p, _ in results]
        assert "Mobile App" in names

    def test_empty_query_returns_all(self) -> None:
        results = fuzzy_search("", MOCK_PROJECTS, lambda p: p.name)
        assert len(results) == len(MOCK_PROJECTS)

    def test_no_match_below_cutoff(self) -> None:
        results = fuzzy_search("xyzzy12345", MOCK_PROJECTS, lambda p: p.name, cutoff=80)
        assert results == []

    def test_sorted_by_score(self) -> None:
        results = fuzzy_search("app", MOCK_PROJECTS, lambda p: p.name)
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)

    def test_reordered_words_match(self) -> None:
        results = fuzzy_search("Pipeline Data", MOCK_PROJECTS, lambda p: p.name)
        names = [p.name for p, _ in results]
        assert "Data Pipeline" in names

    def test_token_set_ratio_extra_words(self) -> None:
        # Test case where query is a subset of the target with token_set_ratio
        results = fuzzy_search("Data Pipe", MOCK_PROJECTS, lambda p: p.name)
        names = [p.name for p, _ in results]
        assert "Data Pipe New" in names
        # Also assert it's the top match
        assert results[0][0].name == "Data Pipe New"

    def test_limit_respected(self) -> None:
        results = fuzzy_search("a", MOCK_PROJECTS, lambda p: p.name, limit=2)
        assert len(results) <= 2

    def test_client_search(self) -> None:
        results = fuzzy_search("Acme", MOCK_CLIENTS, lambda c: c.name)
        assert results[0][0].name == "Acme Corp"

    def test_client_typo(self) -> None:
        results = fuzzy_search("Globx", MOCK_CLIENTS, lambda c: c.name)
        names = [c.name for c, _ in results]
        assert "Globex Inc" in names


class TestFuzzyBest:
    """Tests for fuzzy_best()."""

    def test_returns_best(self) -> None:
        result = fuzzy_best("Data Pipelin", MOCK_PROJECTS, lambda p: p.name)
        assert result is not None
        assert result.name == "Data Pipeline"

    def test_returns_none_no_match(self) -> None:
        result = fuzzy_best("zzzunknown", MOCK_PROJECTS, lambda p: p.name, cutoff=90)
        assert result is None

    def test_exact_match(self) -> None:
        result = fuzzy_best("Internal Tools", MOCK_PROJECTS, lambda p: p.name)
        assert result is not None
        assert result.name == "Internal Tools"
