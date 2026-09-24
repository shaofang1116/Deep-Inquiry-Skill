"""End-to-end host coverage for immutable reader report completion."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.autonomous_runtime import HostRun, PendingCursor
from scripts.knowledge_schema import TopicKnowledge
from scripts.knowledge_store import KnowledgeStoreError
from scripts.renderer import render_knowledge_report
from scripts.vnext_host import VNextHost, VNextHostError


def _topic(*, schema_version: int = 2, ready: bool = True) -> TopicKnowledge:
    data: dict[str, object] = {
        "schema_version": schema_version,
        "topic_id": "reader-report-e2e",
        "title": "Reader report completion",
        "proposition": "This metadata must not be the reader report.",
        "version": 1,
        "coverage_dimensions": ["mechanism"],
        "claims": [
            {
                "id": "claim-1",
                "dimension": "mechanism",
                "kind": "mechanism",
                "statement": "A durable claim supports the report.",
                "confidence": "high",
                "evidence_ids": ["evidence-1"],
                "counterexample_ids": [],
                "related_claim_refs": [],
                "status": "active",
                "introduced_version": 1,
                "updated_version": 1,
            }
        ],
        "evidence": [
            {
                "id": "evidence-1",
                "source": "Reviewed source.",
                "supports_claim_ids": ["claim-1"],
            }
        ],
        "gaps": [],
        "counterexamples": [],
        "convergence_history": [],
        "created_at": "2026-09-23T00:00:00+00:00",
        "updated_at": "2026-09-23T00:00:00+00:00",
        "migration_metadata": {},
    }
    if schema_version == 2 and ready:
        data["reader_document"] = {
            "schema_version": 1,
            "overview": {
                "paragraphs": ["Reader-facing overview."],
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
            },
            "sections": [
                {
                    "id": "mechanism",
                    "heading": "Mechanism",
                    "paragraphs": ["The mechanism is explained for readers."],
                    "key_points": [],
                    "dimension_refs": ["mechanism"],
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                }
            ],
            "synthesis": {
                "paragraphs": ["The explanation connects the material."],
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
            },
            "application_guidance": [
                {
                    "text": "Apply the mechanism to the observed case.",
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                }
            ],
            "boundary_notes": [
                {
                    "text": "Evidence may not cover every setting.",
                    "claim_ids": ["claim-1"],
                    "gap_ids": [],
                }
            ],
        }
    return TopicKnowledge.from_dict(data)


def _domain_topic(
    *,
    topic_id: str,
    title: str,
    dimensions: list[str],
    sections: list[tuple[str, str, str]],
    overview: str,
    synthesis: str,
    application: str,
    boundary: str,
) -> TopicKnowledge:
    claims = [
        {
            "id": f"claim-{index}",
            "dimension": dimension,
            "kind": "mechanism",
            "statement": paragraph,
            "confidence": "high",
            "evidence_ids": [f"evidence-{index}"],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        }
        for index, (dimension, _, paragraph) in enumerate(sections, start=1)
    ]
    evidence = [
        {
            "id": f"evidence-{index}",
            "source": f"Reviewed {dimension} source.",
            "supports_claim_ids": [f"claim-{index}"],
        }
        for index, dimension in enumerate(dimensions, start=1)
    ]
    claim_ids = [claim["id"] for claim in claims]
    evidence_ids = [item["id"] for item in evidence]
    return TopicKnowledge.from_dict(
        {
            "schema_version": 2,
            "topic_id": topic_id,
            "title": title,
            "proposition": "Internal proposition metadata is not report prose.",
            "version": 1,
            "coverage_dimensions": dimensions,
            "claims": claims,
            "evidence": evidence,
            "gaps": [],
            "counterexamples": [],
            "convergence_history": [],
            "created_at": "2026-09-23T00:00:00+00:00",
            "updated_at": "2026-09-23T00:00:00+00:00",
            "migration_metadata": {},
            "reader_document": {
                "schema_version": 1,
                "overview": {
                    "paragraphs": [overview],
                    "claim_ids": claim_ids,
                    "evidence_ids": evidence_ids,
                },
                "sections": [
                    {
                        "id": dimension,
                        "heading": heading,
                        "paragraphs": [paragraph],
                        "key_points": [],
                        "dimension_refs": [dimension],
                        "claim_ids": [f"claim-{index}"],
                        "evidence_ids": [f"evidence-{index}"],
                    }
                    for index, (dimension, heading, paragraph) in enumerate(
                        sections, start=1
                    )
                ],
                "synthesis": {
                    "paragraphs": [synthesis],
                    "claim_ids": claim_ids,
                    "evidence_ids": evidence_ids,
                },
                "application_guidance": [
                    {
                        "text": application,
                        "claim_ids": claim_ids,
                        "evidence_ids": evidence_ids,
                    }
                ],
                "boundary_notes": [
                    {
                        "text": boundary,
                        "claim_ids": claim_ids,
                        "gap_ids": [],
                    }
                ],
            },
        }
    )


class ReaderReportE2ETests(unittest.TestCase):
    def _host_and_cursor(
        self,
        *,
        schema_version: int = 2,
        ready: bool = True,
        converged: bool = True,
        checkpoint_required: bool = False,
    ) -> tuple[VNextHost, HostRun, PendingCursor]:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        host = VNextHost(
            state_path=str(root / "state.json"),
            knowledge_root=str(root / "knowledge"),
        )
        topic = _topic(schema_version=schema_version, ready=ready)
        host.knowledge.create(topic)
        run = HostRun.new(
            topic_id=topic.topic_id,
            knowledge_root=str(host.knowledge.root.resolve()),
            base_version=topic.version,
        )
        host._save_run(run)
        cursor = PendingCursor(
            schema_version=1,
            runtime_kind="vnext_host_pending",
            run_id=run.run_id,
            topic_id=topic.topic_id,
            knowledge_root=run.knowledge_root,
            stage="checkpoint_or_complete",
            expected_version=topic.version,
            commit_marker=None,
            payload={
                "cycle": 1,
                "convergence": {
                    "converged": converged,
                    "reason_code": "converged" if converged else "checkpoint",
                    "reason": "The test controls the final decision.",
                    "checkpoint_required": checkpoint_required,
                    "blocking_ids": [],
                },
            },
        )
        return host, run, cursor

    def test_converged_schema_v2_writes_immutable_reader_report(self) -> None:
        host, run, cursor = self._host_and_cursor()

        first = host._advance_internal(cursor, run, discard_judgment=False)
        report_path = Path(first.result["report_path"])
        first_bytes = report_path.read_bytes()
        second = host._result(cursor)

        self.assertEqual(first.status, "done")
        self.assertTrue(report_path.is_absolute())
        self.assertEqual(second["report_path"], str(report_path))
        self.assertEqual(first_bytes, report_path.read_bytes())
        report = first_bytes.decode("utf-8")
        self.assertIn("## Overview", report)
        self.assertIn("## Applying the Knowledge", report)
        self.assertIn("## Sources", report)
        self.assertNotIn("## Convergence History", report)
        self.assertNotIn("## Knowledge by Dimension", report)
        self.assertNotIn("Topic ID", report)

    def test_checkpoint_has_no_report_path(self) -> None:
        host, run, cursor = self._host_and_cursor(
            converged=False,
            checkpoint_required=True,
        )

        outcome = host._advance_internal(cursor, run, discard_judgment=False)

        self.assertEqual(outcome.status, "done")
        self.assertNotIn("report_path", outcome.result)
        self.assertFalse((host.knowledge.root / "reader-report-e2e" / "reports").exists())

    def test_schema_v1_or_unready_schema_v2_cannot_complete_report(self) -> None:
        for label, kwargs in (
            ("schema-v1", {"schema_version": 1, "ready": False}),
            ("unready-schema-v2", {"schema_version": 2, "ready": False}),
        ):
            with self.subTest(label=label):
                host, run, cursor = self._host_and_cursor(**kwargs)

                with self.assertRaises(VNextHostError):
                    host._advance_internal(cursor, run, discard_judgment=False)

                self.assertEqual(host._load_run().status, "active")
                self.assertEqual(host._load_cursor().to_dict(), cursor.to_dict())

    def test_report_write_failure_preserves_active_run_and_cursor(self) -> None:
        host, run, cursor = self._host_and_cursor()

        with patch.object(
            host.knowledge,
            "write_markdown_report",
            side_effect=KnowledgeStoreError("disk unavailable"),
        ):
            with self.assertRaisesRegex(VNextHostError, "cannot write"):
                host._advance_internal(cursor, run, discard_judgment=False)

        self.assertEqual(host._load_run().status, "active")
        self.assertEqual(host._load_cursor().to_dict(), cursor.to_dict())

    def test_lodging_and_climbing_robot_reader_acceptance(self) -> None:
        """Reader review: mechanism, conditions, action, synthesis, no internals PASS."""
        topics = (
            _domain_topic(
                topic_id="lodging-construction",
                title="Small lodging construction",
                dimensions=["stages", "constraints", "regulation"],
                sections=[
                    (
                        "stages",
                        "Build sequence",
                        "Site work, structure, enclosure, and commissioning must proceed in dependency order.",
                    ),
                    (
                        "constraints",
                        "Project constraints",
                        "Budget, seasonal access, and local labor capacity constrain each stage.",
                    ),
                    (
                        "regulation",
                        "Regulatory boundary",
                        "Permits and fire-safety requirements must be confirmed before irreversible work.",
                    ),
                ],
                overview="A viable lodging project coordinates construction order with operational constraints.",
                synthesis="The schedule is reliable only when construction dependencies, resource limits, and approvals agree.",
                application="Validate permits, critical-path dependencies, and seasonal constraints before committing a build package.",
                boundary="Local codes and site conditions can invalidate a generic construction sequence.",
            ),
            _domain_topic(
                topic_id="climbing-camera-robot",
                title="Small climbing camera robot",
                dimensions=["mechanics", "power", "communication", "field-limitations"],
                sections=[
                    (
                        "mechanics",
                        "Attachment mechanics",
                        "The gripper must hold safely without damaging bark across changing branch diameters.",
                    ),
                    (
                        "power",
                        "Power budget",
                        "Actuation, sensing, and imaging loads determine whether a usable observation window is possible.",
                    ),
                    (
                        "communication",
                        "Forest communication",
                        "Link reliability depends on canopy attenuation, antenna placement, and recovery behavior.",
                    ),
                    (
                        "field-limitations",
                        "Field limitations",
                        "Rain, uneven bark, and branch motion can exceed laboratory attachment and navigation assumptions.",
                    ),
                ],
                overview="A climbing camera robot is feasible only when attachment, energy, communication, and field conditions are designed together.",
                synthesis="Mechanical safety consumes energy and can reduce link quality, so subsystem choices must be evaluated as one operating envelope.",
                application="Test bark damage, duty-cycle runtime, and link recovery together on representative trees before field deployment.",
                boundary="Laboratory results do not establish safety or reliability under wet, moving, or species-variable field conditions.",
            ),
        )

        for topic in topics:
            with self.subTest(topic=topic.topic_id):
                report = render_knowledge_report(topic).decode("utf-8")
                # PASS: the five blind-reader questions in the design spec.
                for heading in (
                    "## Overview",
                    "## Synthesis",
                    "## Applying the Knowledge",
                    "## Boundaries and Uncertainty",
                    "## Sources",
                ):
                    self.assertIn(heading, report)
                for dimension in topic.coverage_dimensions:
                    self.assertIn(
                        topic.reader_document["sections"][
                            topic.coverage_dimensions.index(dimension)
                        ]["heading"],
                        report,
                    )
                for internal in (
                    "Convergence History",
                    "Knowledge by Dimension",
                    "Topic ID",
                    "claim-",
                    "evidence-",
                ):
                    self.assertNotIn(internal, report)


if __name__ == "__main__":
    unittest.main()
