"""Runtime coverage for skeptic-reviewed cognitive reader documents."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.autonomous_runtime import (
    HostRun,
    HostRuntimeCoordinator,
    PendingCursor,
)
from scripts.knowledge_schema import (
    READER_DOCUMENT_DEFECT_CATEGORIES,
    TopicKnowledge,
)
from scripts.knowledge_store import KnowledgeStore
from scripts.vnext_host import VNextHost
from tests.test_cognitive_reader_document_schema import _reader_document_v2
from tests.test_reader_document_schema import _topic_data


def _integration() -> dict[str, object]:
    return {
        "delta": {
            "new_claim_ids": [],
            "revised_claim_ids": [],
            "retired_claim_ids": [],
            "new_evidence_ids": [],
            "resolved_gap_ids": [],
            "new_gap_ids": [],
            "counterexample_hits": [],
        },
        "claims": [],
        "evidence": [],
        "gaps": [],
        "counterexamples": [],
        "phase": "post_baseline",
        "gain_level": "medium",
        "reader_document": _reader_document_v2(),
    }


def _document_review(
    defect_category: str | None = None,
) -> dict[str, object]:
    defects = {
        category: [] for category in READER_DOCUMENT_DEFECT_CATEGORIES
    }
    if defect_category is not None:
        defects[defect_category] = [
            f"{defect_category} requires reader-document revision."
        ]
    return {
        "approved": defect_category is None,
        "defects": defects,
    }


class CognitiveReaderDocumentRuntimeTests(unittest.TestCase):
    def _coordinator(self) -> tuple[HostRuntimeCoordinator, HostRun]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = KnowledgeStore(directory.name)
        topic_data = _topic_data(schema_version=1)
        store.create(TopicKnowledge.from_dict(topic_data))
        run = HostRun.new(
            topic_id="reader-document",
            knowledge_root=str(Path(directory.name).resolve()),
            base_version=1,
        )
        return HostRuntimeCoordinator(store), run

    def _commit_cursor(
        self,
        coordinator: HostRuntimeCoordinator,
        run: HostRun,
        document_review: dict[str, object],
    ):
        cursor = coordinator.begin_learning(run)
        cursor = coordinator.advance_learning(cursor, {"accepted": True})
        cursor = coordinator.advance_learning(cursor, {"plan": "Inspect controls."})
        cursor = coordinator.advance_learning(cursor, _integration())
        self.assertEqual(cursor.stage, "skeptic_review")
        cursor = coordinator.advance_learning(
            cursor,
            {
                "structural_hit": False,
                "reader_document_review": document_review,
            },
        )
        self.assertEqual(cursor.stage, "commit_learning")
        return cursor

    def _audit_reviews(
        self,
        coordinator: HostRuntimeCoordinator,
        topic_id: str,
        states: tuple[str, ...],
    ) -> list[dict[str, object]]:
        audit_dir = coordinator.store.root / "topics" / topic_id / "audit"
        return [
            json.loads(next(audit_dir.glob(f"*-{state}.json")).read_text(
                encoding="utf-8"
            ))["review"]
            for state in states
        ]

    def _legacy_flat_commit_cursor(
        self,
        host: VNextHost,
        run: HostRun,
    ) -> PendingCursor:
        cursor = host.coordinator.begin_learning(run)
        cursor = host.coordinator.advance_learning(cursor, {"accepted": True})
        cursor = host.coordinator.advance_learning(
            cursor, {"plan": "Inspect controls."}
        )
        cursor = host.coordinator.advance_learning(cursor, _integration())
        cursor = host.coordinator.advance_learning(
            cursor,
            {
                "structural_hit": False,
                "reader_document_review": _document_review(),
            },
        )
        document_review = cursor.payload["reader_document_review"]
        payload = {
            key: value
            for key, value in cursor.payload.items()
            if key != "reader_document_review"
        }
        payload["reader_document_approved"] = document_review["approved"]
        payload["reader_document_defects"] = []
        return PendingCursor(
            schema_version=cursor.schema_version,
            runtime_kind=cursor.runtime_kind,
            run_id=cursor.run_id,
            topic_id=cursor.topic_id,
            knowledge_root=cursor.knowledge_root,
            stage=cursor.stage,
            expected_version=cursor.expected_version,
            commit_marker=host.coordinator._commit_marker(payload),
            payload=payload,
        )

    def test_requests_require_v2_document_and_structured_cognitive_review(self) -> None:
        coordinator, run = self._coordinator()
        cursor = coordinator.begin_learning(run)
        cursor = coordinator.advance_learning(cursor, {"accepted": True})
        cursor = coordinator.advance_learning(cursor, {"plan": "Inspect controls."})

        integration_request = coordinator.learning_request(cursor)
        self.assertEqual(
            integration_request.response_template["reader_document"]["schema_version"],
            2,
        )
        self.assertEqual(
            set(integration_request.response_template["reader_document"]),
            {
                "schema_version",
                "orientation",
                "domain_map",
                "sections",
                "synthesis",
                "transfer_guidance",
                "boundary_notes",
                "further_learning",
            },
        )

        skeptic_cursor = coordinator.advance_learning(cursor, _integration())
        skeptic_request = coordinator.learning_request(skeptic_cursor)
        self.assertIn("reader_document_review", skeptic_request.required_fields)
        self.assertEqual(
            set(skeptic_request.response_template["reader_document_review"]),
            {"approved", "defects"},
        )
        self.assertEqual(
            set(
                skeptic_request.response_template["reader_document_review"][
                    "defects"
                ]
            ),
            set(READER_DOCUMENT_DEFECT_CATEGORIES),
        )

    def test_approved_cognitive_document_publishes_schema_v3_and_audits_decision(
        self,
    ) -> None:
        coordinator, run = self._coordinator()
        review = _document_review()
        cursor = self._commit_cursor(coordinator, run, review)

        next_cursor = coordinator.commit_learning(cursor)

        self.assertEqual(next_cursor.stage, "assess_convergence")
        topic = coordinator.store.load(run.topic_id)
        self.assertEqual(topic.version, 2)
        self.assertEqual(topic.schema_version, 3)
        for audit_review in self._audit_reviews(
            coordinator, run.topic_id, ("reviewed", "published")
        ):
            self.assertEqual(audit_review["reader_document_review"], review)

    def test_each_cognitive_defect_rejects_and_audits_decision(self) -> None:
        for category in READER_DOCUMENT_DEFECT_CATEGORIES:
            with self.subTest(category=category):
                coordinator, run = self._coordinator()
                review = _document_review(category)
                cursor = self._commit_cursor(coordinator, run, review)

                returned = coordinator.commit_learning(cursor)

                self.assertEqual(returned.stage, "integrate_learning")
                self.assertEqual(
                    returned.payload["reader_document_review"],
                    review,
                )
                self.assertEqual(coordinator.store.load(run.topic_id).version, 1)
                for audit_review in self._audit_reviews(
                    coordinator, run.topic_id, ("reviewed", "rejected")
                ):
                    self.assertEqual(
                        audit_review["reader_document_review"],
                        review,
                    )
                audit_dir = coordinator.store.root / "topics" / run.topic_id / "audit"
                rejected = json.loads(
                    next(audit_dir.glob("*-rejected.json")).read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(
                    rejected["rejection"]["code"],
                    "reader_document_review_rejected",
                )

    def test_structural_hit_precedes_reader_document_rejection(self) -> None:
        coordinator, run = self._coordinator()
        review = _document_review("synthesis")

        outcome = coordinator.publisher.publish_or_reject(
            topic_id=run.topic_id,
            base_version=1,
            candidate=_integration(),
            review={
                "approved": False,
                "structural_hit": True,
                "reason": "A structural contradiction blocks publication.",
                "reader_document_review": review,
            },
            candidate_id="structural-hit-precedes-document-defect",
        )

        self.assertEqual(outcome.state, "rejected")
        self.assertEqual(outcome.rejection_code, "skeptic_structural_hit")
        self.assertEqual(coordinator.store.load(run.topic_id).version, 1)

    def test_resume_legacy_flat_commit_cursor_restarts_v2_integration_without_audit(
        self,
    ) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        host = VNextHost(
            state_path=str(root / "state.json"),
            knowledge_root=str(root / "knowledge"),
        )
        topic = TopicKnowledge.from_dict(_topic_data(schema_version=1))
        host.knowledge.create(topic)
        run = HostRun.new(
            topic_id=topic.topic_id,
            knowledge_root=str(host.knowledge.root.resolve()),
            base_version=topic.version,
        )
        host._save_run(run)
        legacy_cursor = self._legacy_flat_commit_cursor(host, run)
        host.runtime.save_pending(legacy_cursor.to_dict())

        outcome = host._resume(run)
        resumed_cursor = host._load_cursor()

        self.assertEqual(outcome.status, "pending")
        self.assertEqual(outcome.request.name, "integrate_learning")
        self.assertEqual(resumed_cursor.stage, "integrate_learning")
        self.assertEqual(
            set(resumed_cursor.payload),
            {"cycle", "selected_gap", "plan"},
        )
        self.assertEqual(
            outcome.request.response_template["reader_document"]["schema_version"],
            2,
        )
        self.assertEqual(host._load_run().status, "active")
        self.assertEqual(host.knowledge.load(topic.topic_id).version, 1)
        audit_dir = host.knowledge.root / "topics" / topic.topic_id / "audit"
        self.assertFalse(audit_dir.exists())

        retried = host._resume(run)

        self.assertEqual(retried.status, "pending")
        self.assertEqual(retried.request.name, "integrate_learning")
        self.assertEqual(host._load_cursor().to_dict(), resumed_cursor.to_dict())
        self.assertFalse(audit_dir.exists())


if __name__ == "__main__":
    unittest.main()
