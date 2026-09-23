#!/usr/bin/env python3
"""Default vNext smoke: autonomous convergence followed by stateless query."""

from __future__ import annotations

from pathlib import Path
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT / "examples"))

from tests.behavior.autonomous_loop_checks import (
    main as run_autonomous_loop,
)
from tests.adapter.query_checks import main as run_stateless_query


def main() -> None:
    run_autonomous_loop()
    run_stateless_query()
    print("\nvNext smoke passed: learning and query remain separate.")


if __name__ == "__main__":
    main()
