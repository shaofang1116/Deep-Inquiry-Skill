#!/usr/bin/env python3
"""Default vNext smoke: autonomous convergence followed by stateless query."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from tests.behavior.autonomous_loop_checks import (
    main as run_autonomous_loop,
)
from query_checks import main as run_stateless_query


def main() -> None:
    run_autonomous_loop()
    run_stateless_query()
    print("\nvNext smoke passed: learning and query remain separate.")


if __name__ == "__main__":
    main()
