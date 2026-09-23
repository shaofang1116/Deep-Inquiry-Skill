"""Regression coverage for rejecting contradictory low-gain deltas."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.knowledge_publisher import KnowledgePublisher
from scripts.knowledge_schema import TopicKnowledge
from scripts.knowledge_store import KnowledgeStore
from scripts.learner import Learner


def _topic() -> TopicKnowledge:
    return TopicKnowledge.from_dict(
        {
            "schema_version": 1,
            "topic_id": "gain-validation",
            "title": "Gain validation",
            "proposition": "A proposition for validating learning deltas.",
            "version": 1,
            "coverage_dimensions": ["scope", "risk"],
            "claims": [
                {
                    "id": "claim-1",
                    "dimension": "scope",
                    "kind": "mechanism",
                    "statement": "The initial claim.",
                    "confidence": "low",
                    "evidence_ids": [],
                    "counterexample_ids": [],
                    "related_claim_refs": [],
                    "status": "active",
                    "introduced_version": 1,
                    "updated_version": 1,
                }
            ],
            "evidence": [],
            "gaps": [],
            "counterexamples": [
                {
                    "id": "counterexample-1",
                    "statement": "A counterexample.",
                    "claim_ids": [],
                }
            ],
            "convergence_history": [],
            "created_at": "2026-09-23T00:00:00+00:00",
            "updated_at": "2026-09-23T00:00:00+00:00",
            "migration_metadata": {},
        }
    )


def _update(delta: dict[str, list[str]], **overrides: object) -> dict[str, object]:
    return {
        "delta": {
            "new_claim_ids": [],
            "revised_claim_ids": [],
            "retired_claim_ids": [],
            "new_evidence_ids": [],
            "resolved_gap_ids": [],
            "new_gap_ids": [],
            "counterexample_hits": [],
            **delta,
        },
        "claims": [],
        "evidence": [],
        "gaps": [],
        "counterexamples": [],
        "cycle": 1,
        "phase": "post_baseline",
        "gain_level": "low",
        "skeptic_structural_hit": False,
        **overrides,
    }


class LowGainMajorDeltaTests(unittest.TestCase):
    def test_low_gain_rejects_each_major_change_type(self) -> None:
        cases = (
            _update(
                {"revised_claim_ids": ["claim-1"]},
                claims=[
                    {
                        **_topic().claims[0].to_dict(),
                        "statement": "The revised claim.",
                    }
                ],
            ),
            _update({"retired_claim_ids": ["claim-1"]}),
            _update({"counterexample_hits": ["counterexample-1"]}),
            _update(
                {"new_gap_ids": ["gap-1"]},
                gaps=[
                    {
                        "id": "gap-1",
                        "question": "What remains unknown?",
                        "dimension": "risk",
                        "priority": "high",
                        "expected_gain": "low",
                        "reason": "The gap changes the decision boundary.",
                        "status": "open",
                        "resolution_claim_ids": [],
                        "defer_reason": "",
                    }
                ],
            ),
        )

        for update in cases:
            with self.subTest(update=update["delta"]):
                with self.assertRaisesRegex(ValueError, "low-gain delta"):
                    Learner().build_knowledge_candidate(_topic(), update=update)

    def test_low_gain_without_major_change_remains_valid(self) -> None:
        candidate = Learner().build_knowledge_candidate(
            _topic(), update=_update({})
        )

        self.assertEqual(candidate.version, 2)
        self.assertEqual(candidate.convergence_history[-1].gain_level, "low")

    def test_publisher_rejects_before_advancing_canonical_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = KnowledgeStore(directory)
            store.create(_topic())
            outcome = KnowledgePublisher(store).publish_or_reject(
                topic_id="gain-validation",
                base_version=1,
                candidate=_update({"retired_claim_ids": ["claim-1"]}),
                review={
                    "approved": True,
                    "structural_hit": False,
                    "reason": "The candidate passed skeptical review.",
                },
                candidate_id="invalid-low-gain-retirement",
            )

            self.assertEqual(outcome.state, "rejected")
            self.assertEqual(outcome.rejection_code, "invalid_candidate")
            self.assertEqual(store.load("gain-validation").version, 1)


if __name__ == "__main__":
    unittest.main()
