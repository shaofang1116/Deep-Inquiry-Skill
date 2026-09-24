"""Reader-facing report rendering coverage."""

from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.knowledge_schema import TopicKnowledge
from scripts import renderer
from scripts.renderer import render_knowledge_report


def _topic_data(schema_version: int = 2) -> dict[str, object]:
    topic: dict[str, object] = {
        "schema_version": schema_version,
        "topic_id": "internal-topic-id",
        "title": "Reader *report*",
        "proposition": "Internal proposition must not become report prose.",
        "version": 2,
        "coverage_dimensions": ["mechanism", "conditions"],
        "claims": [
            {
                "id": "claim-alpha",
                "dimension": "mechanism",
                "kind": "mechanism",
                "statement": "The mechanism operates through linked controls.",
                "confidence": "high",
                "evidence_ids": ["evidence-primary"],
                "counterexample_ids": [],
                "related_claim_refs": [],
                "status": "active",
                "introduced_version": 1,
                "updated_version": 2,
            },
            {
                "id": "claim-beta",
                "dimension": "conditions",
                "kind": "condition",
                "statement": "The outcome depends on operating conditions.",
                "confidence": "medium",
                "evidence_ids": ["evidence-secondary"],
                "counterexample_ids": ["counterexample-1"],
                "related_claim_refs": [],
                "status": "active",
                "introduced_version": 1,
                "updated_version": 2,
            },
        ],
        "evidence": [
            {
                "id": "evidence-primary",
                "source": "Primary [source] *one*.",
                "supports_claim_ids": ["claim-alpha"],
            },
            {
                "id": "evidence-secondary",
                "source": "Unused secondary source.",
                "supports_claim_ids": ["claim-beta"],
            },
        ],
        "gaps": [
            {
                "id": "gap-1",
                "question": "Where does the mechanism stop applying?",
                "dimension": "conditions",
                "priority": "high",
                "expected_gain": "medium",
                "reason": "The exceptional condition is unresolved.",
                "status": "open",
                "resolution_claim_ids": [],
                "defer_reason": "",
            }
        ],
        "counterexamples": [
            {
                "id": "counterexample-1",
                "statement": "The mechanism can fail in exceptional settings.",
                "claim_ids": ["claim-beta"],
            }
        ],
        "convergence_history": [],
        "created_at": "2026-09-23T00:00:00+00:00",
        "updated_at": "2026-09-23T00:00:00+00:00",
        "migration_metadata": {},
    }
    if schema_version == 2:
        topic["reader_document"] = {
            "schema_version": 1,
            "overview": {
                "paragraphs": ["Overview prose with *Markdown*."],
                "claim_ids": ["claim-alpha"],
                "evidence_ids": ["evidence-primary"],
            },
            "sections": [
                {
                    "id": "mechanism",
                    "heading": "How it *works*",
                    "paragraphs": ["Section prose comes after the overview."],
                    "key_points": ["Keep the linked controls aligned."],
                    "dimension_refs": ["mechanism"],
                    "claim_ids": ["claim-alpha"],
                    "evidence_ids": ["evidence-primary"],
                },
                {
                    "id": "conditions",
                    "heading": "When it applies",
                    "paragraphs": ["Conditions prose comes after the first section."],
                    "key_points": [],
                    "dimension_refs": ["conditions"],
                    "claim_ids": ["claim-beta"],
                    "evidence_ids": [],
                },
            ],
            "synthesis": {
                "paragraphs": ["Synthesis prose joins both dimensions."],
                "claim_ids": ["claim-alpha"],
                "evidence_ids": ["evidence-primary"],
            },
            "application_guidance": [
                {
                    "text": "Apply the controls before accepting the outcome.",
                    "claim_ids": ["claim-alpha"],
                    "evidence_ids": ["evidence-primary"],
                }
            ],
            "boundary_notes": [
                {
                    "text": "Do not generalize to exceptional conditions.",
                    "claim_ids": ["claim-beta"],
                    "gap_ids": ["gap-1"],
                }
            ],
        }
    return topic


class ReaderReportRendererTests(unittest.TestCase):
    def test_schema_v2_renderer_does_not_contain_audit_headings(self) -> None:
        source = inspect.getsource(renderer._render_schema_v2_reader_report)

        for audit_heading in (
            "Convergence History",
            "Knowledge by Dimension",
            "Topic ID",
        ):
            self.assertNotIn(audit_heading, source)
        compatibility_source = inspect.getsource(
            renderer._render_schema_v1_audit_compatibility
        )
        self.assertIn("Convergence History", compatibility_source)
        self.assertIn("Knowledge by Dimension", compatibility_source)
        self.assertIn("Topic ID", compatibility_source)

    def test_schema_v2_renders_ordered_reader_document_with_stable_sources(self) -> None:
        topic = TopicKnowledge.from_dict(_topic_data())

        first = render_knowledge_report(topic)
        second = render_knowledge_report(topic)
        report = first.decode("utf-8")

        self.assertEqual(first, second)
        for heading in (
            "## Overview",
            "## How it \\*works\\*",
            "## When it applies",
            "## Synthesis",
            "## Applying the Knowledge",
            "## Boundaries and Uncertainty",
            "## Sources",
        ):
            self.assertIn(heading, report)
        ordered_prose = (
            "Overview prose",
            "Section prose",
            "Conditions prose",
            "Synthesis prose",
            "Apply the controls",
            "Do not generalize",
            "Primary \\[source\\] \\*one\\*.",
        )
        offsets = [report.index(text) for text in ordered_prose]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn("Overview prose with \\*Markdown\\*. [1]", report)
        self.assertIn("[1] Primary \\[source\\] \\*one\\*.", report)
        self.assertNotIn("Unused secondary source.", report)

        for forbidden in (
            "Convergence History",
            "Knowledge by Dimension",
            "Topic ID",
            "Kind:",
            "Confidence:",
            "Status:",
            "claim-alpha",
            "claim-beta",
            "evidence-primary",
            "evidence-secondary",
            "gap-1",
            "counterexample-1",
        ):
            self.assertNotIn(forbidden, report)

    def test_schema_v2_requires_ready_reader_document(self) -> None:
        data = _topic_data()
        data.pop("reader_document")
        topic = TopicKnowledge.from_dict(data)

        with self.assertRaisesRegex(ValueError, "reader document"):
            render_knowledge_report(topic)

    def test_schema_v1_uses_audit_compatibility_without_reader_headings(self) -> None:
        topic = TopicKnowledge.from_dict(_topic_data(schema_version=1))

        report = render_knowledge_report(topic).decode("utf-8")

        self.assertIn("## Knowledge by Dimension", report)
        self.assertIn("- Topic ID:", report)
        self.assertNotIn("## Overview", report)
        self.assertNotIn("## Applying the Knowledge", report)
        self.assertNotIn("## Sources", report)


if __name__ == "__main__":
    unittest.main()
