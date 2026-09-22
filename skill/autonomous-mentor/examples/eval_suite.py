#!/usr/bin/env python3
"""Default vNext evaluation suite for knowledge-first behavior."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from tests.behavior.autonomous_loop_checks import (
    main as run_autonomous_loop,
)
from knowledge_first_acceptance_checks import main as run_acceptance
from query_checks import main as run_stateless_query


def main() -> int:
    run_acceptance()
    run_autonomous_loop()
    run_stateless_query()
    print("\nvNext eval passed: convergence and query contain no teaching path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
