#!/usr/bin/env python3
"""Run the vNext scripted-profile artifact validation suite."""

from __future__ import annotations

from pathlib import Path
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from eval_vnext import run_suite  # noqa: E402


if __name__ == "__main__":
    run_suite()
