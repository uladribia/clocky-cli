"""Regression tests for service-layer workflows.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from clocky.app.services.errors import ServiceUsageError
from clocky.app.services.projects import list_projects
from clocky.app.services.timers import get_status_data, list_time_entries, start_timer, stop_timer
from clocky.domain.models import Project
from clocky.infra.context import AppContext
from clocky.testing import MOCK_TIME_ENTRIES, MockClockifyAPI


def build_ctx(api: MockClockifyAPI | None = None) -> AppContext:
    """Create an application context backed by the mock gateway."""
    mock_api = api or MockClockifyAPI()
    user = mock_api.get_user()
    return AppContext(api=mock_api, user=user, workspace_id=user.default_workspace)


def test_start_timer_dry_run_returns_resolved_payload() -> None:
    ctx = build_ctx()

    data = start_timer(
        ctx,
        "Website",
        "Planning",
        ["billable"],
        auto_tag=True,
        non_interactive=True,
        dry_run=True,
    )

    assert data is not None
    assert data.dry_run is True
    assert data.entry is None
    assert data.project.name == "Website Redesign"
    assert data.tag_names == ["billable"]


def test_start_timer_raises_usage_error_for_unknown_project() -> None:
    ctx = build_ctx()

    try:
        start_timer(
            ctx,
            "zzzz-nonexistent",
            "",
            None,
            auto_tag=True,
            non_interactive=True,
            dry_run=False,
        )
    except ServiceUsageError as exc:
        assert "No projects matching" in str(exc)
    else:
        raise AssertionError("ServiceUsageError not raised")


def test_stop_timer_resolves_names() -> None:
    api = MockClockifyAPI(running_timer=MOCK_TIME_ENTRIES[0])
    ctx = build_ctx(api)

    data = stop_timer(ctx)

    assert data.entry is not None
    assert data.project_name == "Website Redesign"
    assert data.tag_names == ["billable"]
    assert data.elapsed is not None


def test_list_time_entries_builds_lookup_maps() -> None:
    ctx = build_ctx()

    data = list_time_entries(ctx, limit=2)

    assert len(data.entries) == 2
    assert data.project_map["proj-001"] == "Website Redesign"
    assert data.tag_map["tag-001"] == "billable"


def test_list_projects_filters_client_and_search() -> None:
    ctx = build_ctx()

    data = list_projects(ctx, "Globex", "Pipeline")

    assert data is not None
    assert data.client_label == "Globex Inc"
    assert [project.name for project in data.projects] == ["Data Pipeline"]


def test_list_projects_excludes_archived_projects() -> None:
    api = MockClockifyAPI(
        projects=[
            Project(
                id="proj-active",
                name="Roadmap Active",
                client_id="cli-001",
                client_name="Acme Corp",
            ),
            Project(
                id="proj-archived",
                name="Roadmap Archived",
                client_id="cli-001",
                client_name="Acme Corp",
                archived=True,
            ),
        ]
    )
    ctx = build_ctx(api)

    data = list_projects(ctx, None, "")

    assert data is not None
    assert [project.name for project in data.projects] == ["Roadmap Active"]


def test_start_timer_ignores_archived_projects() -> None:
    api = MockClockifyAPI(
        projects=[
            Project(
                id="proj-archived",
                name="Legacy Portal",
                client_id="cli-001",
                client_name="Acme Corp",
                archived=True,
            )
        ]
    )
    ctx = build_ctx(api)

    try:
        start_timer(
            ctx,
            "Legacy Portal",
            "",
            None,
            auto_tag=True,
            non_interactive=True,
            dry_run=False,
        )
    except ServiceUsageError as exc:
        assert "No projects matching" in str(exc)
    else:
        raise AssertionError("ServiceUsageError not raised")


def test_get_status_data_returns_none_without_running_timer() -> None:
    ctx = build_ctx()

    data = get_status_data(ctx)

    assert data.entry is None
