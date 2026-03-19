# SPDX-License-Identifier: MIT
"""Real integration smoke tests for clocky-cli.

SPDX-License-Identifier: MIT
"""

from __future__ import annotations

import argparse
import sys

from clocky.integration_smoke import (
    DEFAULT_CASES,
    DEFAULT_HISTORY_LIMIT,
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
        help="Number of recent time entries to inspect for project selection.",
    )
    return parser.parse_args()


def main() -> None:
    """Run integration smoke tests."""
    args = _parse_args()
    cases = args.case or list(DEFAULT_CASES)

    try:
        exit_code = run_integration_smoke(cases, args.history_limit)
    except RuntimeError as exc:
        sys.stderr.write(f"clocky integration: {exc}\n")
        sys.exit(1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
