#!/usr/bin/env python3
"""RED acceptance checks for the vNext knowledge-first product correction."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from typing import Any

sys.dont_write_bytecode = True

from fixtures.convergence_cases import all_cases


SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))
REQUIRED_OWNERS = {
    "knowledge contracts": SKILL_ROOT / "scripts" / "knowledge_schema.py",
    "convergence policy": SKILL_ROOT / "scripts" / "convergence.py",
}
FORBIDDEN_TEACHING_ACTIONS = {
    "ask",
    "feedback",
    "assess_user",
    "plan_teaching",
    "teach",
    "teach_reply",
}


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        strings = [str(key) for key in value]
        for child in value.values():
            strings.extend(_flatten_strings(child))
        return strings
    if isinstance(value, (list, tuple, set)):
        strings: list[str] = []
        for child in value:
            strings.extend(_flatten_strings(child))
        return strings
    return [value] if isinstance(value, str) else []


def main() -> None:
    missing = [name for name, path in REQUIRED_OWNERS.items() if not path.is_file()]
    assert not missing, (
        "vNext RED: canonical owners are not implemented yet: "
        + ", ".join(missing)
    )

    schema = importlib.import_module("scripts.knowledge_schema")
    convergence = importlib.import_module("scripts.convergence")
    loop = importlib.import_module("scripts.loop")

    for index, case in enumerate(all_cases(), start=1):
        topic = schema.TopicKnowledge.from_dict(case["topic"])
        assessment = schema.ConvergenceAssessment.from_dict(case["assessment"])
        decision = convergence.evaluate_convergence(topic, assessment)
        assert decision.converged is case["expected_converged"], (
            f"{case['name']}: expected converged={case['expected_converged']}, "
            f"got {decision.converged}"
        )
        assert decision.reason_code == case["expected_reason_code"], (
            f"{case['name']}: expected reason {case['expected_reason_code']}, "
            f"got {decision.reason_code}"
        )
        print(f"[{index}/4] {case['name']} -> {decision.reason_code}")

    converged_case = all_cases()[-1]
    topic = schema.TopicKnowledge.from_dict(converged_case["topic"])
    assessment = schema.ConvergenceAssessment.from_dict(
        converged_case["assessment"]
    )
    decision = convergence.evaluate_convergence(topic, assessment)
    result = loop.build_learning_result(topic=topic, convergence=decision)

    required_result_fields = {
        "topic_id",
        "knowledge_version",
        "delta_history",
        "unresolved_deferred_gaps",
        "convergence_reason",
    }
    assert required_result_fields <= result.keys(), (
        f"default learning result missing fields: "
        f"{sorted(required_result_fields - result.keys())}"
    )
    result_tokens = {token.lower() for token in _flatten_strings(result)}
    leaked_actions = FORBIDDEN_TEACHING_ACTIONS & result_tokens
    assert not leaked_actions, (
        f"default learning result must not contain teaching actions: "
        f"{sorted(leaked_actions)}"
    )
    print("[4/4] default learning result contains no teaching action")

    print("\nKnowledge-first vNext acceptance checks passed.")


if __name__ == "__main__":
    main()
