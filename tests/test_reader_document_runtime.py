"""Runtime coverage for atomically publishing skeptic-approved reader prose."""

from __future__ import annotations

import sys
import tempfile
import unittest
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.autonomous_runtime import (
    HostRun,
    HostRuntimeCoordinator,
    RuntimeContractError,
)
from scripts.convergence import evaluate_convergence
from scripts.failures import MAX_AUTONOMOUS_CYCLES
from scripts.judgments import AUTONOMOUS_STAGES
from scripts.knowledge_publisher import KnowledgePublisher
from scripts.knowledge_schema import ConvergenceAssessment, TopicKnowledge
from scripts.knowledge_store import KnowledgeStore


def _topic() -> TopicKnowledge:
    return TopicKnowledge.from_dict(
        {
            "schema_version": 1,
            "topic_id": "reader-runtime",
            "title": "Reader runtime",
            "proposition": "Linked controls determine operating risk.",
            "version": 1,
            "coverage_dimensions": ["scope", "risk"],
            "claims": [
                {
                    "id": "claim-1",
                    "dimension": "scope",
                    "kind": "mechanism",
                    "statement": "Scope choices determine the risk envelope.",
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
            "created_at": "2026-09-23T00:00:00+00:00",
            "updated_at": "2026-09-23T00:00:00+00:00",
            "migration_metadata": {},
        }
    )


def _reader_document() -> dict[str, object]:
    return {
        "schema_version": 1,
        "overview": {
            "paragraphs": ["Scope and control choices determine operating risk."],
            "claim_ids": ["claim-1", "claim-2"],
            "evidence_ids": [],
        },
        "sections": [
            {
                "id": "scope",
                "heading": "Scope",
                "paragraphs": ["Scope defines the operating envelope."],
                "key_points": [],
                "dimension_refs": ["scope"],
                "claim_ids": ["claim-1"],
                "evidence_ids": [],
            },
            {
                "id": "risk",
                "heading": "Risk",
                "paragraphs": ["Controls must match the chosen scope."],
                "key_points": [],
                "dimension_refs": ["risk"],
                "claim_ids": ["claim-2"],
                "evidence_ids": [],
            },
        ],
        "synthesis": {
            "paragraphs": ["Evaluate scope and controls as one decision."],
            "claim_ids": ["claim-1", "claim-2"],
            "evidence_ids": [],
        },
        "application_guidance": [
            {
                "text": "Check scope before accepting the corresponding risk.",
                "claim_ids": ["claim-2"],
                "evidence_ids": [],
            }
        ],
        "boundary_notes": [
            {
                "text": "Unusual conditions require additional evaluation.",
                "claim_ids": ["claim-2"],
                "gap_ids": [],
            }
        ],
    }


def _convergence_ready_topic() -> TopicKnowledge:
    claims = [
        {
            "id": f"{dimension}-{kind}",
            "dimension": dimension,
            "kind": kind,
            "statement": f"{dimension.title()} {kind} is established.",
            "confidence": "medium" if kind == "synthesis" else "low",
            "evidence_ids": [f"evidence-{dimension}"]
            if kind == "synthesis"
            else [],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        }
        for dimension in ("scope", "risk")
        for kind in ("mechanism", "condition", "boundary", "synthesis")
    ]
    return TopicKnowledge.from_dict(
        {
            "schema_version": 1,
            "topic_id": "convergence-ready",
            "title": "Convergence ready",
            "proposition": "Complete coverage permits convergence.",
            "version": 3,
            "coverage_dimensions": ["scope", "risk"],
            "claims": claims,
            "evidence": [
                {
                    "id": f"evidence-{dimension}",
                    "source": f"Evidence for {dimension}.",
                    "supports_claim_ids": [f"{dimension}-synthesis"],
                }
                for dimension in ("scope", "risk")
            ],
            "gaps": [],
            "counterexamples": [],
            "convergence_history": [
                {
                    "cycle": cycle,
                    "phase": "post_baseline",
                    "delta": {},
                    "gain_level": "low",
                    "skeptic_structural_hit": False,
                }
                for cycle in (1, 2)
            ],
            "created_at": "2026-09-23T00:00:00+00:00",
            "updated_at": "2026-09-23T00:00:00+00:00",
            "migration_metadata": {},
        }
    )


def _complete_reader_document() -> dict[str, object]:
    claim_ids = [
        f"{dimension}-{kind}"
        for dimension in ("scope", "risk")
        for kind in ("mechanism", "condition", "boundary", "synthesis")
    ]
    evidence_ids = ["evidence-scope", "evidence-risk"]
    return {
        "schema_version": 1,
        "overview": {
            "paragraphs": ["Scope and risk coverage is complete."],
            "claim_ids": claim_ids,
            "evidence_ids": evidence_ids,
        },
        "sections": [
            {
                "id": "scope-and-risk",
                "heading": "Scope and risk",
                "paragraphs": ["Each dimension includes all required facets."],
                "key_points": [],
                "dimension_refs": ["scope", "risk"],
                "claim_ids": claim_ids,
                "evidence_ids": evidence_ids,
            }
        ],
        "synthesis": {
            "paragraphs": ["The facets jointly support the stop decision."],
            "claim_ids": claim_ids,
            "evidence_ids": evidence_ids,
        },
        "application_guidance": [
            {
                "text": "Use the covered facets to assess new cases.",
                "claim_ids": claim_ids,
                "evidence_ids": evidence_ids,
            }
        ],
        "boundary_notes": [
            {
                "text": "No unresolved boundaries remain for this baseline.",
                "claim_ids": claim_ids,
                "gap_ids": [],
            }
        ],
    }


def _converged_assessment() -> ConvergenceAssessment:
    return ConvergenceAssessment.from_dict(
        {
            "gain_level": "low",
            "open_high_value_gap_ids": [],
            "evidence_deficit_claim_ids": [],
            "structural_hit": False,
            "continue_learning": False,
            "reason": "No further high-value knowledge remains after complete coverage.",
        }
    )


def _integration(document: object | None = None) -> dict[str, object]:
    return {
        "delta": {
            "new_claim_ids": ["claim-2"],
            "revised_claim_ids": [],
            "retired_claim_ids": [],
            "new_evidence_ids": [],
            "resolved_gap_ids": [],
            "new_gap_ids": [],
            "counterexample_hits": [],
        },
        "claims": [
            {
                "id": "claim-2",
                "dimension": "risk",
                "kind": "condition",
                "statement": "Controls must match the selected scope.",
                "confidence": "medium",
                "evidence_ids": [],
                "counterexample_ids": [],
                "related_claim_refs": [],
                "status": "active",
                "introduced_version": 0,
                "updated_version": 0,
            }
        ],
        "evidence": [],
        "gaps": [],
        "counterexamples": [],
        "phase": "post_baseline",
        "gain_level": "medium",
        "reader_document": _reader_document() if document is None else document,
    }


class ReaderDocumentRuntimeTests(unittest.TestCase):
    def _coordinator(self) -> tuple[HostRuntimeCoordinator, HostRun]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        store = KnowledgeStore(directory.name)
        store.create(_topic())
        run = HostRun.new(
            topic_id="reader-runtime",
            knowledge_root=str(Path(directory.name).resolve()),
            base_version=1,
        )
        return HostRuntimeCoordinator(store), run

    def _integrate_cursor(
        self, coordinator: HostRuntimeCoordinator, run: HostRun
    ):
        cursor = coordinator.begin_learning(run)
        cursor = coordinator.advance_learning(cursor, {"accepted": True})
        cursor = coordinator.advance_learning(cursor, {"plan": "Inspect controls."})
        return cursor

    def _commit_cursor(
        self,
        coordinator: HostRuntimeCoordinator,
        run: HostRun,
        integration: dict[str, object],
        skeptic: dict[str, object],
    ):
        cursor = self._integrate_cursor(coordinator, run)
        cursor = coordinator.advance_learning(cursor, integration)
        self.assertEqual(cursor.stage, "skeptic_review")
        cursor = coordinator.advance_learning(cursor, skeptic)
        self.assertEqual(cursor.stage, "commit_learning")
        return cursor

    def test_requests_require_and_carry_complete_reader_document(self) -> None:
        coordinator, run = self._coordinator()
        cursor = self._integrate_cursor(coordinator, run)

        request = coordinator.learning_request(cursor)
        self.assertIn("reader_document", request.required_fields)
        self.assertIn("reader_document", request.response_template)
        self.assertEqual(
            set(request.response_template["reader_document"]),
            {
                "schema_version",
                "overview",
                "sections",
                "synthesis",
                "application_guidance",
                "boundary_notes",
            },
        )
        self.assertIn("reader_document", request.state_snapshot)
        self.assertIsNone(request.state_snapshot["reader_document"])

        skeptic_cursor = coordinator.advance_learning(cursor, _integration())
        skeptic_request = coordinator.learning_request(skeptic_cursor)
        self.assertEqual(
            skeptic_request.context["integration_proposal"]["reader_document"],
            _reader_document(),
        )

    def test_missing_or_invalid_reader_document_does_not_publish(self) -> None:
        coordinator, run = self._coordinator()
        missing = _integration()
        missing.pop("reader_document")
        cursor = self._integrate_cursor(coordinator, run)
        with self.assertRaises(RuntimeContractError):
            coordinator.advance_learning(cursor, missing)
        self.assertEqual(coordinator.store.load(run.topic_id).version, 1)

        invalid = _integration({"schema_version": 1})
        commit = self._commit_cursor(
            coordinator,
            run,
            invalid,
            {
                "structural_hit": False,
                "reader_document_approved": True,
                "reader_document_defects": [],
            },
        )
        returned = coordinator.commit_learning(commit)
        self.assertEqual(returned.stage, "integrate_learning")
        self.assertEqual(coordinator.store.load(run.topic_id).version, 1)

    def test_explicit_approval_publishes_schema_v2_atomically(self) -> None:
        coordinator, run = self._coordinator()
        commit = self._commit_cursor(
            coordinator,
            run,
            _integration(),
            {
                "structural_hit": False,
                "reader_document_approved": True,
                "reader_document_defects": [],
            },
        )

        next_cursor = coordinator.commit_learning(commit)
        topic = coordinator.store.load(run.topic_id)
        self.assertEqual(next_cursor.stage, "assess_convergence")
        self.assertEqual(topic.version, 2)
        self.assertEqual(topic.schema_version, 2)
        self.assertEqual(topic.reader_document, _reader_document())
        self.assertEqual({claim.id for claim in topic.claims}, {"claim-1", "claim-2"})
        audit_dir = coordinator.store.root / "topics" / run.topic_id / "audit"
        for state in ("reviewed", "published"):
            audit_record = json.loads(
                next(audit_dir.glob(f"*-{state}.json")).read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(audit_record["review"]["reader_document_approved"])
            self.assertEqual(
                audit_record["review"]["reader_document_defects"], []
            )

    def test_document_rejection_returns_to_integrate_with_defects(self) -> None:
        coordinator, run = self._coordinator()
        commit = self._commit_cursor(
            coordinator,
            run,
            _integration(),
            {
                "structural_hit": False,
                "reader_document_approved": False,
                "reader_document_defects": ["The synthesis omits a condition."],
            },
        )

        returned = coordinator.commit_learning(commit)
        self.assertEqual(returned.stage, "integrate_learning")
        self.assertEqual(
            returned.payload["reader_document_defects"],
            ["The synthesis omits a condition."],
        )
        self.assertEqual(coordinator.store.load(run.topic_id).version, 1)

    def test_direct_publisher_rejects_empty_document_defects(self) -> None:
        coordinator, run = self._coordinator()

        outcome = coordinator.publisher.publish_or_reject(
            topic_id=run.topic_id,
            base_version=1,
            candidate=_integration(),
            review={
                "approved": True,
                "structural_hit": False,
                "reason": "The candidate passed skeptical review.",
                "reader_document_approved": False,
                "reader_document_defects": [],
            },
            candidate_id="empty-reader-document-defects",
        )

        self.assertEqual(outcome.state, "rejected")
        self.assertEqual(outcome.rejection_code, "invalid_review")
        self.assertEqual(coordinator.store.load(run.topic_id).version, 1)

    def test_rejected_lifecycle_audit_preserves_document_review(self) -> None:
        coordinator, run = self._coordinator()
        defects = ["The synthesis omits a condition."]
        commit = self._commit_cursor(
            coordinator,
            run,
            _integration(),
            {
                "structural_hit": False,
                "reader_document_approved": False,
                "reader_document_defects": defects,
            },
        )

        coordinator.commit_learning(commit)

        audit_dir = coordinator.store.root / "topics" / run.topic_id / "audit"
        for state in ("reviewed", "rejected"):
            audit_record = json.loads(
                next(audit_dir.glob(f"*-{state}.json")).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                audit_record["review"]["reader_document_approved"],
                False,
            )
            self.assertEqual(
                audit_record["review"]["reader_document_defects"],
                defects,
            )

    def test_direct_retirement_invalidates_document_and_advances_once(self) -> None:
        coordinator, run = self._coordinator()
        integration = _integration()
        integration["cycle"] = 1
        integration["skeptic_structural_hit"] = False
        bypassed = coordinator.publisher.publish_or_reject(
            topic_id=run.topic_id,
            base_version=1,
            candidate=integration,
            review={
                "approved": True,
                "structural_hit": False,
                "reason": "The candidate passed skeptical review.",
            },
            candidate_id="missing-reader-review",
        )
        self.assertEqual(bypassed.state, "rejected")
        self.assertEqual(bypassed.rejection_code, "invalid_review")
        self.assertEqual(coordinator.store.load(run.topic_id).version, 1)

        published = coordinator.publisher.publish_or_reject(
            topic_id=run.topic_id,
            base_version=1,
            candidate=integration,
            review={
                "approved": True,
                "structural_hit": False,
                "reason": "The candidate passed skeptical review.",
                "reader_document_approved": True,
                "reader_document_defects": [],
            },
            candidate_id="seed-reader-document",
        )
        self.assertEqual(published.state, "published")

        retired = KnowledgePublisher(coordinator.store).retire(
            topic_id=run.topic_id,
            base_version=2,
            claim_ids=["claim-2"],
            candidate_id="direct-retirement",
        )

        topic = coordinator.store.load(run.topic_id)
        self.assertEqual(retired.state, "retired")
        self.assertEqual(topic.version, 3)
        self.assertEqual(topic.schema_version, 2)
        self.assertIsNone(topic.reader_document)
        self.assertEqual(
            next(
                claim.status for claim in topic.claims if claim.id == "claim-2"
            ),
            "retired",
        )
        decision = evaluate_convergence(
            topic,
            ConvergenceAssessment.from_dict(
                {
                    "gain_level": "low",
                    "open_high_value_gap_ids": [],
                    "evidence_deficit_claim_ids": ["claim-1"],
                    "structural_hit": False,
                    "continue_learning": False,
                    "reason": "No further high-value knowledge remains.",
                }
            ),
        )
        self.assertFalse(decision.converged)
        self.assertEqual(decision.reason_code, "reader_document_not_ready")

        retried = KnowledgePublisher(coordinator.store).retire(
            topic_id=run.topic_id,
            base_version=2,
            claim_ids=["claim-2"],
            candidate_id="direct-retirement",
        )
        self.assertEqual(retried.state, "retired")
        self.assertEqual(coordinator.store.load(run.topic_id).version, 3)

    def test_schema_v1_cannot_converge_without_reader_document(self) -> None:
        decision = evaluate_convergence(_convergence_ready_topic(), _converged_assessment())

        self.assertFalse(decision.converged)
        self.assertEqual(decision.reason_code, "reader_document_not_ready")

    def test_schema_v2_unready_document_cannot_converge(self) -> None:
        source = _convergence_ready_topic().to_dict()
        source["schema_version"] = 2
        topic = TopicKnowledge.from_dict(source)

        decision = evaluate_convergence(topic, _converged_assessment())

        self.assertFalse(decision.converged)
        self.assertEqual(decision.reason_code, "reader_document_not_ready")

    def test_safety_checkpoint_precedes_unready_reader_document(self) -> None:
        source = _convergence_ready_topic().to_dict()
        source["schema_version"] = 2
        source["convergence_history"] = [
            {
                "cycle": cycle,
                "phase": "post_baseline",
                "delta": {},
                "gain_level": "low",
                "skeptic_structural_hit": False,
            }
            for cycle in range(1, MAX_AUTONOMOUS_CYCLES + 1)
        ]
        topic = TopicKnowledge.from_dict(source)

        decision = evaluate_convergence(topic, _converged_assessment())

        self.assertFalse(decision.converged)
        self.assertEqual(decision.reason_code, "safety_checkpoint")
        self.assertTrue(decision.checkpoint_required)

    def test_schema_v2_complete_valid_document_converges(self) -> None:
        source = _convergence_ready_topic().to_dict()
        source["schema_version"] = 2
        source["reader_document"] = _complete_reader_document()
        topic = TopicKnowledge.from_dict(source)

        decision = evaluate_convergence(topic, _converged_assessment())

        self.assertTrue(decision.converged)
        self.assertEqual(decision.reason_code, "converged")

    def test_vnext_stage_graph_remains_eight_stages(self) -> None:
        self.assertEqual(len(AUTONOMOUS_STAGES), 8)
        self.assertNotIn("reader_document_review", AUTONOMOUS_STAGES)


if __name__ == "__main__":
    unittest.main()
