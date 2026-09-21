"""Convergence scenarios shared by the vNext acceptance checks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fixtures.knowledge_first_cases import (
    complete_topic,
    topic_with_open_high_value_gap,
)


EMPTY_DELTA = {
    "new_claim_ids": [],
    "revised_claim_ids": [],
    "retired_claim_ids": [],
    "new_evidence_ids": [],
    "resolved_gap_ids": [],
    "new_gap_ids": [],
    "counterexample_hits": [],
}


def _record(cycle: int, phase: str, gain_level: str) -> dict[str, Any]:
    return {
        "cycle": cycle,
        "phase": phase,
        "delta": deepcopy(EMPTY_DELTA),
        "gain_level": gain_level,
        "skeptic_structural_hit": False,
    }


def _assessment(reason: str) -> dict[str, Any]:
    return {
        "gain_level": "low",
        "open_high_value_gap_ids": [],
        "evidence_deficit_claim_ids": [],
        "structural_hit": False,
        "continue_learning": False,
        "reason": reason,
    }


def single_cycle_attempt() -> dict[str, Any]:
    topic = complete_topic()
    topic["convergence_history"] = [
        _record(cycle=1, phase="baseline", gain_level="medium"),
    ]
    return {
        "name": "single cycle cannot establish marginal trend",
        "topic": topic,
        "assessment": _assessment(
            "No open gaps remain, so learning should stop after the baseline."
        ),
        "expected_converged": False,
        "expected_reason_code": "insufficient_marginal_trend",
    }


def high_priority_gap_attempt() -> dict[str, Any]:
    topic = topic_with_open_high_value_gap()
    topic["convergence_history"] = [
        _record(cycle=1, phase="baseline", gain_level="medium"),
        _record(cycle=2, phase="post_baseline", gain_level="low"),
        _record(cycle=3, phase="post_baseline", gain_level="low"),
    ]
    return {
        "name": "open high-value gap blocks convergence",
        "topic": topic,
        "assessment": {
            **_assessment("Recent deltas are low gain, so learning should stop."),
            "open_high_value_gap_ids": ["gap-high-1"],
        },
        "expected_converged": False,
        "expected_reason_code": "open_high_value_gap",
    }


def fully_converged() -> dict[str, Any]:
    topic = complete_topic()
    topic["convergence_history"] = [
        _record(cycle=1, phase="baseline", gain_level="medium"),
        _record(cycle=2, phase="post_baseline", gain_level="low"),
        _record(cycle=3, phase="post_baseline", gain_level="low"),
    ]
    return {
        "name": "complete knowledge with two low-gain deltas converges",
        "topic": topic,
        "assessment": _assessment(
            "All required facets are evidenced, the skeptic is stable, and "
            "two post-baseline cycles added no material knowledge."
        ),
        "expected_converged": True,
        "expected_reason_code": "converged",
    }


def all_cases() -> list[dict[str, Any]]:
    return [
        single_cycle_attempt(),
        high_priority_gap_attempt(),
        fully_converged(),
    ]
