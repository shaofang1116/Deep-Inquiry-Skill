#!/usr/bin/env python3
"""Contract checks for immutable durable publication lifecycle records."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))

from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore, KnowledgeStoreError  # noqa: E402


def _publisher():
    path = SKILL_ROOT / "scripts" / "knowledge_publisher.py"
    assert path.is_file(), (
        "Task 1 RED: publication lifecycle owner does not exist: "
        "scripts/knowledge_publisher.py"
    )
    from scripts.knowledge_publisher import KnowledgePublisher

    return KnowledgePublisher


def _topic() -> TopicKnowledge:
    return TopicKnowledge.from_dict(
        {
            "schema_version": 1,
            "topic_id": "publication-topic",
            "title": "Publication topic",
            "proposition": "Durable changes have immutable audit records.",
            "version": 1,
            "coverage_dimensions": ["mechanism"],
            "claims": [
                {
                    "id": "claim-1",
                    "dimension": "mechanism",
                    "kind": "mechanism",
                    "statement": "Initial durable mechanism.",
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
            "gaps": [],
            "counterexamples": [],
            "convergence_history": [],
            "created_at": "2026-09-22T10:00:00+00:00",
            "updated_at": "2026-09-22T10:00:00+00:00",
        }
    )


def _delta(
    *,
    cycle: int = 1,
    claim_id: str = "claim-2",
    evidence_id: str = "evidence-2",
) -> dict:
    return {
        "delta": {
            "new_claim_ids": [claim_id],
            "revised_claim_ids": [],
            "retired_claim_ids": [],
            "new_evidence_ids": [evidence_id],
            "resolved_gap_ids": [],
            "new_gap_ids": [],
            "counterexample_hits": [],
        },
        "claims": [
            {
                "id": claim_id,
                "dimension": "mechanism",
                "kind": "condition",
                "statement": "The mechanism requires evidence-backed review.",
                "confidence": "high",
                "evidence_ids": [evidence_id],
                "counterexample_ids": [],
                "related_claim_refs": [],
                "status": "active",
                "introduced_version": 2,
                "updated_version": 2,
            }
        ],
        "evidence": [
            {
                "id": evidence_id,
                "source": f"https://example.test/{evidence_id}",
                "supports_claim_ids": [claim_id],
            }
        ],
        "gaps": [],
        "counterexamples": [],
        "cycle": cycle,
        "phase": "baseline",
        "gain_level": "high",
        "skeptic_structural_hit": False,
    }


def _review(*, structural_hit: bool = False) -> dict:
    return {
        "approved": not structural_hit,
        "structural_hit": structural_hit,
        "reason": (
            "A structural contradiction was found."
            if structural_hit
            else "Skeptic review accepted the candidate."
        ),
    }


def _audit(topic_dir: Path) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((topic_dir / "audit").glob("*.json"))
    ]


def main() -> None:
    KnowledgePublisher = _publisher()

    with tempfile.TemporaryDirectory(prefix="mentor-publication-") as tmp:
        root = Path(tmp) / "knowledge"
        store = KnowledgeStore(root)
        store.create(_topic())
        publisher = KnowledgePublisher(store)
        topic_dir = root / "topics" / "publication-topic"
        current_path = topic_dir / "knowledge.json"
        v1_bytes = current_path.read_bytes()

        published = publisher.publish_or_reject(
            topic_id="publication-topic",
            base_version=1,
            candidate=_delta(),
            review=_review(),
            candidate_id="candidate-published",
        )
        assert published.state == "published"
        assert published.topic is not None and published.topic.version == 2
        records = _audit(topic_dir)
        assert [record["state"] for record in records] == [
            "proposed",
            "reviewed",
            "published",
        ]
        assert records[-1]["published_version"] == 2
        assert (topic_dir / "history" / "v000002.json").is_file()
        print("[1/7] published candidate has one snapshot and audit chain")

        retried = publisher.publish_or_reject(
            topic_id="publication-topic",
            base_version=1,
            candidate=_delta(),
            review=_review(),
            candidate_id="candidate-published",
        )
        assert retried.state == "published"
        assert len(_audit(topic_dir)) == 3
        assert store.load("publication-topic").version == 2
        print("[2/7] duplicate candidate retry returns its terminal record")

        rejected_before = current_path.read_bytes()
        rejected = publisher.publish_or_reject(
            topic_id="publication-topic",
            base_version=2,
            candidate=_delta(cycle=2),
            review=_review(structural_hit=True),
            candidate_id="candidate-skeptic-rejected",
        )
        assert rejected.state == "rejected"
        assert rejected.rejection_code == "skeptic_structural_hit"
        assert current_path.read_bytes() == rejected_before
        assert store.load("publication-topic").version == 2
        assert [record["state"] for record in _audit(topic_dir)][-3:] == [
            "proposed",
            "reviewed",
            "rejected",
        ]
        print("[3/7] skeptic rejection leaves the published projection unchanged")

        malformed = publisher.publish_or_reject(
            topic_id="publication-topic",
            base_version=2,
            candidate={"delta": {"new_claim_ids": ["missing-payload"]}},
            review=_review(),
            candidate_id="candidate-malformed",
        )
        assert malformed.state == "rejected"
        assert malformed.rejection_code == "invalid_candidate"
        assert current_path.read_bytes() == rejected_before
        assert store.load("publication-topic").version == 2
        print("[4/7] malformed candidate becomes a durable non-mutating rejection")

        stale = publisher.publish_or_reject(
            topic_id="publication-topic",
            base_version=1,
            candidate=_delta(
                cycle=3,
                claim_id="claim-stale",
                evidence_id="evidence-stale",
            ),
            review=_review(),
            candidate_id="candidate-stale",
        )
        assert stale.state == "rejected"
        assert stale.rejection_code == "version_conflict"
        assert store.load("publication-topic").version == 2
        print("[5/7] stale base version becomes a durable rejection")

        original_append = store._append_audit_record
        failed_once = False

        def interrupt_published_record(topic_dir_arg, record):
            nonlocal failed_once
            if record.state == "published" and not failed_once:
                failed_once = True
                raise OSError("simulated interruption after snapshot")
            return original_append(topic_dir_arg, record)

        store._append_audit_record = interrupt_published_record
        try:
            publisher.publish_or_reject(
                topic_id="publication-topic",
                base_version=2,
                candidate=_delta(
                    cycle=4,
                    claim_id="claim-recovery",
                    evidence_id="evidence-recovery",
                ),
                review=_review(),
                candidate_id="candidate-recovery",
            )
            raise AssertionError("expected simulated publication interruption")
        except KnowledgeStoreError:
            pass
        finally:
            store._append_audit_record = original_append

        recovered = publisher.publish_or_reject(
            topic_id="publication-topic",
            base_version=2,
            candidate=_delta(
                cycle=4,
                claim_id="claim-recovery",
                evidence_id="evidence-recovery",
            ),
            review=_review(),
            candidate_id="candidate-recovery",
        )
        assert recovered.state == "published"
        assert recovered.topic is not None and recovered.topic.version == 3
        recovery_records = [
            record
            for record in _audit(topic_dir)
            if record["candidate_id"] == "candidate-recovery"
        ]
        assert [record["state"] for record in recovery_records] == [
            "proposed",
            "reviewed",
            "published",
        ]
        assert (topic_dir / "history" / "v000003.json").is_file()
        print("[6/7] retry completes an interrupted snapshot publication")

        retired = publisher.retire(
            topic_id="publication-topic",
            base_version=3,
            claim_ids=["claim-2"],
            candidate_id="candidate-retirement",
        )
        assert retired.state == "retired"
        assert retired.topic is not None and retired.topic.version == 4
        assert next(
            claim for claim in retired.topic.claims if claim.id == "claim-2"
        ).status == "retired"
        assert _audit(topic_dir)[-1]["state"] == "retired"
        assert v1_bytes == (topic_dir / "history" / "v000001.json").read_bytes()
        print("[7/7] retirement records a new published projection")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nPublication lifecycle checks passed.")


if __name__ == "__main__":
    main()
