#!/usr/bin/env python3
"""Checks for validated, versioned durable knowledge-delta application."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore  # noqa: E402
from scripts.learner import Learner  # noqa: E402


def _base_topic() -> TopicKnowledge:
    return TopicKnowledge.from_dict(
        {
            "schema_version": 1,
            "topic_id": "delta-topic",
            "title": "Delta topic",
            "proposition": "Knowledge changes remain auditable.",
            "version": 1,
            "coverage_dimensions": ["mechanism"],
            "claims": [
                {
                    "id": "claim-1",
                    "dimension": "mechanism",
                    "kind": "mechanism",
                    "statement": "Initial mechanism.",
                    "confidence": "medium",
                    "evidence_ids": [],
                    "counterexample_ids": [],
                    "related_claim_refs": [],
                    "status": "active",
                    "introduced_version": 1,
                    "updated_version": 1,
                }
            ],
            "evidence": [],
            "gaps": [
                {
                    "id": "gap-1",
                    "question": "What evidence supports the mechanism?",
                    "dimension": "mechanism",
                    "priority": "high",
                    "expected_gain": "high",
                    "reason": "The initial claim lacks direct evidence.",
                    "status": "open",
                    "resolution_claim_ids": [],
                    "defer_reason": "",
                }
            ],
            "counterexamples": [],
            "convergence_history": [],
            "created_at": "2026-09-17T10:00:00+00:00",
            "updated_at": "2026-09-17T10:00:00+00:00",
        }
    )


def _envelope(
    delta: dict,
    *,
    claims: list[dict] | None = None,
    evidence: list[dict] | None = None,
    gaps: list[dict] | None = None,
    counterexamples: list[dict] | None = None,
    cycle: int,
    gain_level: str = "high",
) -> dict:
    return {
        "delta": delta,
        "claims": claims or [],
        "evidence": evidence or [],
        "gaps": gaps or [],
        "counterexamples": counterexamples or [],
        "cycle": cycle,
        "phase": "baseline",
        "gain_level": gain_level,
        "skeptic_structural_hit": False,
    }


def _empty_delta(**overrides) -> dict:
    result = {
        "new_claim_ids": [],
        "revised_claim_ids": [],
        "retired_claim_ids": [],
        "new_evidence_ids": [],
        "resolved_gap_ids": [],
        "new_gap_ids": [],
        "counterexample_hits": [],
    }
    result.update(overrides)
    return result


def _expect_error(action, expected_fragment: str) -> None:
    try:
        action()
        raise AssertionError("expected knowledge delta rejection")
    except ValueError as exc:
        assert expected_fragment in str(exc).lower(), (
            f"expected {expected_fragment!r} in error, got {exc!r}"
        )


def main() -> None:
    assert hasattr(Learner, "apply_knowledge_delta"), (
        "Task 5 RED: Learner.apply_knowledge_delta does not exist"
    )

    with tempfile.TemporaryDirectory(prefix="mentor-delta-") as tmp:
        store = KnowledgeStore(Path(tmp) / "knowledge")
        learner = Learner()
        current = store.create(_base_topic())

        current = learner.apply_knowledge_delta(
            store,
            "delta-topic",
            base_version=1,
            update=_envelope(
                _empty_delta(
                    new_claim_ids=["claim-2"],
                    new_evidence_ids=["evidence-2"],
                ),
                claims=[
                    {
                        "id": "claim-2",
                        "dimension": "mechanism",
                        "kind": "condition",
                        "statement": "The mechanism requires condition B.",
                        "confidence": "high",
                        "evidence_ids": ["evidence-2"],
                        "counterexample_ids": [],
                        "related_claim_refs": [],
                        "status": "active",
                        "introduced_version": 2,
                        "updated_version": 2,
                    }
                ],
                evidence=[
                    {
                        "id": "evidence-2",
                        "source": "https://example.test/evidence-2",
                        "supports_claim_ids": ["claim-2"],
                    }
                ],
                cycle=1,
            ),
        )
        assert current.version == 2
        assert {claim.id for claim in current.claims} == {"claim-1", "claim-2"}
        print("[1/7] new claims and evidence produce one new version")

        current = learner.apply_knowledge_delta(
            store,
            "delta-topic",
            base_version=2,
            update=_envelope(
                _empty_delta(
                    revised_claim_ids=["claim-1"],
                    new_evidence_ids=["evidence-1"],
                ),
                claims=[
                    {
                        "id": "claim-1",
                        "dimension": "mechanism",
                        "kind": "mechanism",
                        "statement": "Revised evidence-backed mechanism.",
                        "confidence": "high",
                        "evidence_ids": ["evidence-1"],
                        "counterexample_ids": [],
                        "related_claim_refs": [],
                        "status": "active",
                        "introduced_version": 1,
                        "updated_version": 3,
                    }
                ],
                evidence=[
                    {
                        "id": "evidence-1",
                        "source": "https://example.test/evidence-1",
                        "supports_claim_ids": ["claim-1"],
                    }
                ],
                cycle=2,
            ),
        )
        assert current.version == 3
        assert current.claims[0].statement.startswith("Revised")
        print("[2/7] existing claims can be revised with auditable evidence")

        unsupported_dispute = _envelope(
            _empty_delta(revised_claim_ids=["claim-1"]),
            claims=[
                {
                    **current.claims[0].to_dict(),
                    "status": "disputed",
                    "counterexample_ids": [],
                    "updated_version": 4,
                }
            ],
            cycle=3,
        )
        _expect_error(
            lambda: learner.apply_knowledge_delta(
                store,
                "delta-topic",
                base_version=3,
                update=unsupported_dispute,
            ),
            "disputed",
        )
        assert store.load("delta-topic").version == 3

        current = learner.apply_knowledge_delta(
            store,
            "delta-topic",
            base_version=3,
            update=_envelope(
                _empty_delta(
                    revised_claim_ids=["claim-1"],
                    counterexample_hits=["counterexample-1"],
                ),
                claims=[
                    {
                        **current.claims[0].to_dict(),
                        "status": "disputed",
                        "counterexample_ids": ["counterexample-1"],
                        "updated_version": 4,
                    }
                ],
                counterexamples=[
                    {
                        "id": "counterexample-1",
                        "statement": "Observed boundary case contradicts claim-1.",
                        "claim_ids": ["claim-1"],
                    }
                ],
                cycle=3,
            ),
        )
        assert current.claims[0].status == "disputed"
        assert current.counterexamples[0].id == "counterexample-1"
        print("[3/7] disputed claims require a linked counterexample")

        current = learner.apply_knowledge_delta(
            store,
            "delta-topic",
            base_version=4,
            update=_envelope(
                _empty_delta(retired_claim_ids=["claim-2"]),
                cycle=4,
                gain_level="medium",
            ),
        )
        claim_2 = next(claim for claim in current.claims if claim.id == "claim-2")
        assert claim_2.status == "retired"
        assert claim_2.updated_version == 5
        print("[4/7] retirement is an explicit status transition")

        invalid_resolution = _envelope(
            _empty_delta(resolved_gap_ids=["gap-1"]),
            gaps=[
                {
                    **current.gaps[0].to_dict(),
                    "status": "resolved",
                    "resolution_claim_ids": [],
                }
            ],
            cycle=5,
        )
        _expect_error(
            lambda: learner.apply_knowledge_delta(
                store,
                "delta-topic",
                base_version=5,
                update=invalid_resolution,
            ),
            "resolution claims",
        )
        assert store.load("delta-topic").version == 5
        print("[5/7] a gap cannot resolve without linked resolution claims")

        invalid_claim = {
            "id": "claim-3",
            "dimension": "mechanism",
            "kind": "mechanism",
            "statement": "Unsupported empirical conclusion.",
            "confidence": "high",
            "evidence_ids": [],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 6,
            "updated_version": 6,
        }
        _expect_error(
            lambda: learner.apply_knowledge_delta(
                store,
                "delta-topic",
                base_version=5,
                update=_envelope(
                    _empty_delta(new_claim_ids=["claim-3"]),
                    claims=[invalid_claim],
                    cycle=5,
                ),
            ),
            "requires evidence",
        )
        assert store.load("delta-topic").version == 5
        print("[6/7] high-confidence empirical claims require evidence")

        current = learner.apply_knowledge_delta(
            store,
            "delta-topic",
            base_version=5,
            update=_envelope(
                _empty_delta(resolved_gap_ids=["gap-1"]),
                gaps=[
                    {
                        **current.gaps[0].to_dict(),
                        "status": "resolved",
                        "resolution_claim_ids": ["claim-1"],
                    }
                ],
                cycle=5,
                gain_level="medium",
            ),
        )
        history = (
            Path(tmp)
            / "knowledge"
            / "topics"
            / "delta-topic"
            / "history"
        )
        assert current.version == 6
        assert [path.name for path in sorted(history.glob("v*.json"))] == [
            f"v{version:06d}.json" for version in range(1, 7)
        ]
        assert len(current.convergence_history) == 5
        print("[7/7] each accepted delta creates one immutable topic version")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nValidated learning-delta checks passed.")


if __name__ == "__main__":
    main()
