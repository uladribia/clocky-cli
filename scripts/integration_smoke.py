# SPDX-License-Identifier: MIT
"""Real integration smoke tests for clocky-cli.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from clocky.infra.cli_smoke import (  # noqa: E402
    DEFAULT_CASES,
    DEFAULT_HISTORY_LIMIT,
    build_smoke_plan,
    render_smoke_plan,
    run_integration_smoke,
)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Clocky CLI integration smoke tests")
    parser.add_argument(
        "--case",
        action="append",
        choices=DEFAULT_CASES,
        help="Case to run (repeatable). Defaults to all.",
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=DEFAULT_HISTORY_LIMIT,
        help="Reserved for compatibility; planning is log-driven.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Print the selected smoke plan and exit.",
    )
    return parser.parse_args()


def main() -> None:
    """Run integration smoke tests."""
    args = _parse_args()
    cases = args.case or list(DEFAULT_CASES)

    try:
        if args.plan:
            sys.stdout.write(render_smoke_plan(build_smoke_plan()))
            sys.exit(0)

        exit_code = run_integration_smoke(cases, args.history_limit)
    except RuntimeError as exc:
        sys.stderr.write(f"clocky integration: {exc}\n")
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
