"""Schema coverage for the canonical reader document."""

from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.knowledge_schema import (
    KnowledgeSchemaError,
    PublicationRecord,
    TopicKnowledge,
)
from scripts.reader_document import reader_document_ready


def _topic_data(schema_version: int = 2) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "topic_id": "reader-document",
        "title": "Reader document",
        "proposition": "Linked controls determine the operating risk.",
        "version": 1,
        "coverage_dimensions": ["scope", "risk"],
        "claims": [
            {
                "id": "claim-1",
                "dimension": "scope",
                "kind": "mechanism",
                "statement": "Scope choices determine the risk envelope.",
                "confidence": "high",
                "evidence_ids": ["evidence-1"],
                "counterexample_ids": [],
                "related_claim_refs": [],
                "status": "active",
                "introduced_version": 1,
                "updated_version": 1,
            },
            {
                "id": "claim-2",
                "dimension": "risk",
                "kind": "condition",
                "statement": "Risk is controlled when controls match scope.",
                "confidence": "medium",
                "evidence_ids": [],
                "counterexample_ids": ["counterexample-1"],
                "related_claim_refs": [],
                "status": "disputed",
                "introduced_version": 1,
                "updated_version": 1,
            },
        ],
        "evidence": [
            {
                "id": "evidence-1",
                "source": "A reviewed source.",
                "supports_claim_ids": ["claim-1"],
            }
        ],
        "gaps": [
            {
                "id": "gap-1",
                "question": "How do unusual conditions affect controls?",
                "dimension": "risk",
                "priority": "high",
                "expected_gain": "medium",
                "reason": "The exception boundary remains uncertain.",
                "status": "open",
                "resolution_claim_ids": [],
                "defer_reason": "",
            }
        ],
        "counterexamples": [
            {
                "id": "counterexample-1",
                "statement": "Controls can fail under unusual conditions.",
                "claim_ids": ["claim-2"],
            }
        ],
        "convergence_history": [],
        "created_at": "2026-09-23T00:00:00+00:00",
        "updated_at": "2026-09-23T00:00:00+00:00",
        "migration_metadata": {},
    }


def _reader_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "overview": {
            "paragraphs": ["The proposition depends on linked controls."],
            "claim_ids": ["claim-1"],
            "evidence_ids": ["evidence-1"],
        },
        "sections": [
            {
                "id": "scope-and-risk",
                "heading": "Scope and risk",
                "paragraphs": ["Scope choices determine the risk envelope."],
                "key_points": ["Treat the two dimensions as one decision."],
                "dimension_refs": ["scope", "risk"],
                "claim_ids": ["claim-1", "claim-2"],
                "evidence_ids": ["evidence-1"],
            }
        ],
        "synthesis": {
            "paragraphs": ["The dimensions must be evaluated together."],
            "claim_ids": ["claim-1"],
            "evidence_ids": ["evidence-1"],
        },
        "application_guidance": [
            {
                "text": "Check the operating scope before accepting risk.",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
            }
        ],
        "boundary_notes": [
            {
                "text": "Evidence is still limited for unusual conditions.",
                "claim_ids": ["claim-2"],
                "gap_ids": ["gap-1"],
            }
        ],
    }


def _schema_v2_topic() -> dict[str, object]:
    topic = _topic_data()
    topic["reader_document"] = _reader_document()
    return topic


def _audit_record(
    state: str,
    review: dict[str, object],
) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": 1,
        "record_id": f"audit-{state}",
        "candidate_id": "candidate-1",
        "topic_id": "reader-document",
        "state": state,
        "base_version": 1,
        "created_at": "2026-09-23T00:00:00+00:00",
        "delta": {},
        "integration": {},
        "review": review,
        "rejection": None,
        "published_version": None,
    }
    if state == "rejected":
        record["rejection"] = {"code": "rejected", "reason": "Rejected."}
    if state == "published":
        record["published_version"] = 2
    return record


class ReaderDocumentSchemaTests(unittest.TestCase):
    def test_schema_v1_keeps_no_reader_document_and_round_trips(self) -> None:
        topic = TopicKnowledge.from_dict(_topic_data(schema_version=1))

        self.assertIsNone(topic.reader_document)
        self.assertNotIn("reader_document", topic.to_dict())
        self.assertEqual(
            TopicKnowledge.from_dict(topic.to_dict()).to_dict(),
            topic.to_dict(),
        )

    def test_schema_v2_reader_document_round_trips_and_is_ready(self) -> None:
        source = _schema_v2_topic()

        topic = TopicKnowledge.from_dict(source)

        self.assertEqual(topic.to_dict(), source)
        self.assertTrue(reader_document_ready(topic))

    def test_reader_document_requires_schema_v2(self) -> None:
        source = _schema_v2_topic()
        source["schema_version"] = 1

        with self.assertRaisesRegex(KnowledgeSchemaError, "schema_version"):
            TopicKnowledge.from_dict(source)

    def test_reader_document_schema_version_rejects_non_integer_one(self) -> None:
        for invalid_version in (True, 1.0):
            with self.subTest(invalid_version=invalid_version):
                source = _schema_v2_topic()
                document = source["reader_document"]
                self.assertIsInstance(document, dict)
                document["schema_version"] = invalid_version

                with self.assertRaisesRegex(KnowledgeSchemaError, "schema_version"):
                    TopicKnowledge.from_dict(source)

    def test_reader_document_rejects_invalid_references_and_coverage(self) -> None:
        cases = {
            "duplicate section IDs": lambda document: document["sections"].append(
                copy.deepcopy(document["sections"][0])
            ),
            "unknown claim": lambda document: document["sections"][0].update(
                {"claim_ids": ["missing-claim"]}
            ),
            "retired claim": lambda document: document["sections"][0].update(
                {"claim_ids": ["claim-1"]}
            ),
            "mismatched evidence": lambda document: document["sections"][0].update(
                {"claim_ids": ["claim-2"], "evidence_ids": ["evidence-1"]}
            ),
            "uncovered dimension": lambda document: document["sections"][0].update(
                {"dimension_refs": ["scope"]}
            ),
            "unknown gap": lambda document: document["boundary_notes"][0].update(
                {"gap_ids": ["missing-gap"]}
            ),
            "resolved gap": lambda document: document["boundary_notes"][0].update(
                {"gap_ids": ["gap-1"]}
            ),
        }

        for name, mutate in cases.items():
            with self.subTest(name=name):
                source = _schema_v2_topic()
                document = source["reader_document"]
                self.assertIsInstance(document, dict)
                mutate(document)
                if name == "retired claim":
                    source["claims"][0]["status"] = "retired"
                if name == "resolved gap":
                    source["gaps"][0]["status"] = "resolved"
                    source["gaps"][0]["resolution_claim_ids"] = ["claim-2"]

                with self.assertRaises(KnowledgeSchemaError):
                    TopicKnowledge.from_dict(source)

    def test_reader_document_rejects_active_claim_only_in_overview(self) -> None:
        source = _schema_v2_topic()
        source["claims"][1]["status"] = "active"
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        document["overview"]["claim_ids"].append("claim-2")
        document["sections"][0]["claim_ids"] = ["claim-1"]
        document["synthesis"]["claim_ids"] = ["claim-1"]
        document["application_guidance"][0]["claim_ids"] = ["claim-1"]
        document["boundary_notes"][0]["claim_ids"] = ["claim-1"]
        document["boundary_notes"][0]["gap_ids"] = []

        with self.assertRaisesRegex(KnowledgeSchemaError, "active claims"):
            TopicKnowledge.from_dict(source)

    def test_reader_document_rejects_boundary_gap_with_unrelated_dimension(self) -> None:
        source = _schema_v2_topic()
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        document["boundary_notes"][0]["claim_ids"] = ["claim-1"]

        with self.assertRaisesRegex(KnowledgeSchemaError, "unrelated gap"):
            TopicKnowledge.from_dict(source)

    def test_audit_reader_review_fields_round_trip_for_terminal_states(self) -> None:
        review = {
            "approved": True,
            "structural_hit": False,
            "reason": "The candidate passed skeptical review.",
            "reader_document_approved": True,
            "reader_document_defects": [],
        }

        for state in ("reviewed", "rejected", "published"):
            with self.subTest(state=state):
                record = PublicationRecord.from_dict(_audit_record(state, review))
                self.assertEqual(record.to_dict()["review"], review)

    def test_audit_reader_review_rejects_malformed_new_fields(self) -> None:
        cases = (
            {"reader_document_approved": True},
            {
                "reader_document_approved": "yes",
                "reader_document_defects": [],
            },
            {
                "reader_document_approved": True,
                "reader_document_defects": "none",
            },
            {
                "reader_document_approved": True,
                "reader_document_defects": ["Missing boundary."],
            },
            {
                "reader_document_approved": False,
                "reader_document_defects": [],
            },
            {
                "reader_document_approved": False,
                "reader_document_defects": ["  "],
            },
        )
        base_review = {
            "approved": True,
            "structural_hit": False,
            "reason": "The candidate passed skeptical review.",
        }

        legacy = PublicationRecord.from_dict(
            _audit_record("reviewed", base_review)
        )
        self.assertEqual(legacy.to_dict()["review"], base_review)
        for fields in cases:
            with self.subTest(fields=fields):
                with self.assertRaises(KnowledgeSchemaError):
                    PublicationRecord.from_dict(
                        _audit_record("reviewed", {**base_review, **fields})
                    )


if __name__ == "__main__":
    unittest.main()
