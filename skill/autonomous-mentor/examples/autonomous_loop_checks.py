#!/usr/bin/env python3
"""End-to-end checks for the durable autonomous learning loop."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from fixtures.knowledge_first_cases import complete_topic  # noqa: E402
from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore  # noqa: E402
from scripts.loop import AutonomousLearningLoop  # noqa: E402


TOPIC_ID = "three-cycle-topic"
EXPECTED_GAPS = ["gap-high-high", "gap-high-medium", "gap-medium-high"]
FORBIDDEN_TEACHING_ACTIONS = {
    "ask",
    "feedback",
    "assess_user",
    "plan_teaching",
    "teach",
    "teach_reply",
}


def _empty_delta(**overrides: list[str]) -> dict[str, list[str]]:
    delta = {
        "new_claim_ids": [],
        "revised_claim_ids": [],
        "retired_claim_ids": [],
        "new_evidence_ids": [],
        "resolved_gap_ids": [],
        "new_gap_ids": [],
        "counterexample_hits": [],
    }
    delta.update(overrides)
    return delta


def _topic() -> TopicKnowledge:
    payload = complete_topic()
    payload.update(
        {
            "topic_id": TOPIC_ID,
            "version": 1,
            "gaps": [
                {
                    "id": "gap-high-medium",
                    "question": "Which high-priority boundary remains?",
                    "dimension": "optical-mechanism",
                    "priority": "high",
                    "expected_gain": "medium",
                    "reason": "A high-priority boundary needs explicit closure.",
                    "status": "open",
                    "resolution_claim_ids": [],
                    "defer_reason": "",
                },
                {
                    "id": "gap-medium-high",
                    "question": "Which high-gain condition remains?",
                    "dimension": "optical-mechanism",
                    "priority": "medium",
                    "expected_gain": "high",
                    "reason": "A high-gain condition needs explicit closure.",
                    "status": "open",
                    "resolution_claim_ids": [],
                    "defer_reason": "",
                },
                {
                    "id": "gap-high-high",
                    "question": "Which top-value mechanism remains?",
                    "dimension": "optical-mechanism",
                    "priority": "high",
                    "expected_gain": "high",
                    "reason": "This is the highest-value remaining gap.",
                    "status": "open",
                    "resolution_claim_ids": [],
                    "defer_reason": "",
                },
            ],
            "convergence_history": [
                {
                    "cycle": 1,
                    "phase": "baseline",
                    "delta": _empty_delta(),
                    "gain_level": "medium",
                    "skeptic_structural_hit": False,
                }
            ],
        }
    )
    return TopicKnowledge.from_dict(payload)


class ScriptedAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((stage, deepcopy(context)))
        if stage in {"anchor", "map_knowledge"}:
            return {"accepted": True}
        if stage == "plan_investigation":
            gap = context["selected_gap"]
            return {"plan": f"Investigate and resolve {gap['id']}."}
        if stage == "integrate_learning":
            gap = context["selected_gap"]
            assert context["investigation_plan"].endswith(f"{gap['id']}.")
            resolved = {
                **gap,
                "status": "resolved",
                "resolution_claim_ids": ["claim-1"],
            }
            return {
                "delta": _empty_delta(resolved_gap_ids=[gap["id"]]),
                "claims": [],
                "evidence": [],
                "gaps": [resolved],
                "counterexamples": [],
                "phase": "post_baseline",
                "gain_level": "low",
            }
        if stage == "skeptic_review":
            return {"structural_hit": False}
        if stage == "assess_convergence":
            topic = context["topic"]
            open_high_value = sorted(
                gap["id"]
                for gap in topic["gaps"]
                if gap["status"] == "open"
                and (
                    gap["priority"] == "high"
                    or gap["expected_gain"] == "high"
                )
            )
            return {
                "gain_level": "low",
                "open_high_value_gap_ids": open_high_value,
                "evidence_deficit_claim_ids": [],
                "structural_hit": False,
                "continue_learning": bool(open_high_value),
                "reason": (
                    "High-value gaps remain and justify another cycle."
                    if open_high_value
                    else "All required facets are evidenced and the latest two "
                    "post-baseline cycles produced only low marginal gain."
                ),
            }
        raise AssertionError(f"unexpected agent stage: {stage}")


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [
            *(str(key) for key in value),
            *(
                item
                for child in value.values()
                for item in _flatten_strings(child)
            ),
        ]
    if isinstance(value, (list, tuple, set)):
        return [item for child in value for item in _flatten_strings(child)]
    return [value] if isinstance(value, str) else []


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mentor-loop-") as tmp:
        store = KnowledgeStore(Path(tmp) / "knowledge")
        store.create(_topic())
        agent = ScriptedAgent()

        result = AutonomousLearningLoop(store, agent).run(TOPIC_ID)
        final_topic = store.load(TOPIC_ID)

    plan_calls = [
        context
        for stage, context in agent.calls
        if stage == "plan_investigation"
    ]
    integrate_calls = [
        context
        for stage, context in agent.calls
        if stage == "integrate_learning"
    ]
    assert [call["selected_gap"]["id"] for call in plan_calls] == EXPECTED_GAPS
    assert len(integrate_calls) == 3
    print("[1/5] each cycle selects exactly one highest-value gap")

    call_stages = [stage for stage, _ in agent.calls]
    for plan_index in (
        index
        for index, stage in enumerate(call_stages)
        if stage == "plan_investigation"
    ):
        assert call_stages[plan_index + 1] == "integrate_learning"
    assert all(call["investigation_plan"] for call in integrate_calls)
    print("[2/5] investigation plans are exposed before integration")

    assert final_topic.version == 4
    assert len(final_topic.convergence_history) == 4
    assert [record.cycle for record in final_topic.convergence_history] == [
        1,
        2,
        3,
        4,
    ]
    print("[3/5] three cycles commit exactly three versions and deltas")

    expected_fields = {
        "topic_id",
        "knowledge_version",
        "delta_history",
        "unresolved_deferred_gaps",
        "convergence_reason",
        "trace",
    }
    assert expected_fields <= result.keys()
    assert result["knowledge_version"] == 4
    assert result["convergence_reason"]["code"] == "converged"
    expected_trace = ["anchor", "map_knowledge"]
    expected_trace.extend(
        [
            stage
            for _ in range(3)
            for stage in (
                "select_gap",
                "plan_investigation",
                "integrate_learning",
                "skeptic_review",
                "assess_convergence",
                "checkpoint_or_complete",
            )
        ]
    )
    assert [event["stage"] for event in result["trace"]] == expected_trace
    print("[4/5] completion exposes the durable result and stage trace")

    result_tokens = {token.lower() for token in _flatten_strings(result)}
    assert not (FORBIDDEN_TEACHING_ACTIONS & result_tokens)
    print("[5/5] autonomous completion contains no teaching action")

    print("\nAutonomous loop checks passed.")


if __name__ == "__main__":
    main()
