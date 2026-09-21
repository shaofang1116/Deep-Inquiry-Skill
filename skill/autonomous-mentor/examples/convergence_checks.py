#!/usr/bin/env python3
"""Table-driven checks for the vNext autonomous convergence policy."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from fixtures.convergence_cases import EMPTY_DELTA, fully_converged  # noqa: E402
from scripts.knowledge_schema import (  # noqa: E402
    ConvergenceAssessment,
    TopicKnowledge,
)


def _convergence():
    path = SKILL_ROOT / "scripts" / "convergence.py"
    assert path.is_file(), (
        "Task 6 RED: convergence owner does not exist: scripts/convergence.py"
    )
    from scripts import convergence

    return convergence


def _evaluate(topic_data: dict, assessment_data: dict):
    convergence = _convergence()
    return convergence.evaluate_convergence(
        TopicKnowledge.from_dict(topic_data),
        ConvergenceAssessment.from_dict(assessment_data),
    )


def _expect_policy_error(topic_data: dict, assessment_data: dict) -> None:
    convergence = _convergence()
    try:
        _evaluate(topic_data, assessment_data)
        raise AssertionError("expected convergence policy rejection")
    except convergence.ConvergencePolicyError:
        return


def main() -> None:
    base = fully_converged()
    cases = []

    missing_facet = deepcopy(base)
    missing_facet["topic"]["claims"] = [
        claim
        for claim in missing_facet["topic"]["claims"]
        if claim["kind"] != "boundary"
    ]
    missing_facet["topic"]["evidence"] = [
        item
        for item in missing_facet["topic"]["evidence"]
        if item["id"] != "evidence-3"
    ]
    cases.append(("missing_required_facet", missing_facet))

    open_gap = deepcopy(base)
    open_gap["topic"]["gaps"] = [
        {
            "id": "gap-high",
            "question": "What boundary remains unexplained?",
            "dimension": open_gap["topic"]["coverage_dimensions"][0],
            "priority": "high",
            "expected_gain": "high",
            "reason": "A material boundary remains open.",
            "status": "open",
            "resolution_claim_ids": [],
            "defer_reason": "",
        }
    ]
    open_gap["assessment"]["open_high_value_gap_ids"] = ["gap-high"]
    cases.append(("open_high_value_gap", open_gap))

    structural_hit = deepcopy(base)
    structural_hit["topic"]["convergence_history"][-1][
        "skeptic_structural_hit"
    ] = True
    structural_hit["assessment"]["structural_hit"] = True
    cases.append(("structural_hit", structural_hit))

    insufficient_trend = deepcopy(base)
    insufficient_trend["topic"]["convergence_history"] = (
        insufficient_trend["topic"]["convergence_history"][:2]
    )
    cases.append(("insufficient_marginal_trend", insufficient_trend))

    gain_not_low = deepcopy(base)
    gain_not_low["topic"]["convergence_history"][-1]["gain_level"] = "medium"
    gain_not_low["assessment"]["gain_level"] = "medium"
    cases.append(("gain_not_low", gain_not_low))

    evidence_deficit = deepcopy(base)
    evidence_deficit["topic"]["claims"].append(
        {
            "id": "claim-deficit",
            "dimension": evidence_deficit["topic"]["coverage_dimensions"][0],
            "kind": "rule",
            "statement": "A material operational rule lacks evidence.",
            "confidence": "medium",
            "evidence_ids": [],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 3,
            "updated_version": 3,
        }
    )
    evidence_deficit["assessment"]["evidence_deficit_claim_ids"] = [
        "claim-deficit"
    ]
    cases.append(("evidence_deficit", evidence_deficit))

    weak_reason = deepcopy(base)
    weak_reason["assessment"]["reason"] = "done"
    cases.append(("insufficient_stop_reason", weak_reason))

    for index, (reason_code, case) in enumerate(cases, start=1):
        decision = _evaluate(case["topic"], case["assessment"])
        assert decision.converged is False
        assert decision.reason_code == reason_code, (
            f"expected {reason_code}, got {decision.reason_code}"
        )
        print(f"[{index}/10] {reason_code} blocks convergence")

    dishonest = deepcopy(base)
    dishonest["topic"]["convergence_history"][-1]["delta"][
        "revised_claim_ids"
    ] = ["claim-1"]
    _expect_policy_error(dishonest["topic"], dishonest["assessment"])
    print("[8/10] dishonest low-gain classification is rejected")

    converged = _evaluate(base["topic"], base["assessment"])
    assert converged.converged is True
    assert converged.reason_code == "converged"
    assert converged.checkpoint_required is False
    print("[9/10] all policy requirements produce convergence")

    capped = deepcopy(open_gap)
    capped["topic"]["convergence_history"] = []
    for cycle in range(1, 13):
        capped["topic"]["convergence_history"].append(
            {
                "cycle": cycle,
                "phase": "baseline" if cycle == 1 else "post_baseline",
                "delta": deepcopy(EMPTY_DELTA),
                "gain_level": "medium",
                "skeptic_structural_hit": False,
            }
        )
    capped["assessment"]["gain_level"] = "medium"
    capped_decision = _evaluate(capped["topic"], capped["assessment"])
    assert capped_decision.converged is False
    assert capped_decision.checkpoint_required is True
    assert capped_decision.reason_code == "safety_checkpoint"
    print("[10/10] safety cap checkpoints without false convergence")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nConvergence policy checks passed.")


if __name__ == "__main__":
    main()
