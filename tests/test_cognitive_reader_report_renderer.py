"""Renderer coverage for schema-v3 cognitive reader reports."""

from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.knowledge_schema import TopicKnowledge
from scripts.reader_document import reader_document_ready
from scripts.renderer import render_knowledge_report
from tests.test_cognitive_reader_document_schema import _schema_v3_topic


def _topic() -> TopicKnowledge:
    source = _schema_v3_topic()
    source["evidence"].append(
        {
            "id": "evidence-2",
            "source": "Residual-risk field study.",
            "supports_claim_ids": ["claim-2"],
        }
    )
    source["claims"][1]["evidence_ids"] = ["evidence-2"]
    document = source["reader_document"]
    assert isinstance(document, dict)
    domain_map = document["domain_map"]
    assert isinstance(domain_map, dict)
    concepts = domain_map["concepts"]
    assert isinstance(concepts, list)
    concepts[2]["evidence_ids"] = ["evidence-2"]
    relationships = domain_map["relationships"]
    assert isinstance(relationships, list)
    relationships[1]["evidence_ids"] = ["evidence-2"]
    sections = document["sections"]
    assert isinstance(sections, list)
    sections[2]["evidence_ids"] = ["evidence-2"]
    boundary_notes = document["boundary_notes"]
    assert isinstance(boundary_notes, list)
    boundary_notes[0]["evidence_ids"] = ["evidence-2"]
    further_learning = document["further_learning"]
    assert isinstance(further_learning, list)
    further_learning[0]["evidence_ids"] = ["evidence-2"]
    return TopicKnowledge.from_dict(source)


class CognitiveReaderReportRendererTests(unittest.TestCase):
    def test_schema_v3_renders_cognitive_document_in_reader_order(self) -> None:
        topic = _topic()

        first = render_knowledge_report(topic)
        second = render_knowledge_report(topic)
        report = first.decode("utf-8")

        self.assertEqual(first, second)
        for text in (
            "## Orientation",
            "**Central question:** How do scope choices and controls shape risk?",
            "**Scope:** Operational decisions with incomplete evidence.",
            "Controls reduce risk only when they match the chosen scope. [1]",
            "## Domain Map",
            "| Concept | Definition |",
            "| Scope | The operating conditions a decision covers. [1] |",
            "Scope --depends on--> Controls",
            "## Set the scope",
            "**Question:** What conditions define the decision?",
            "Scope choice -> control selection -> risk envelope -> decision implication",
            "## Match controls",
            "## Assess residual risk",
            "**Boundary (evidence limit):** Evidence remains limited for unusual conditions. [2]",
            "## Synthesis",
            "## Transfer the Model",
            "**Try it:** Apply the scope-control-risk model to a new operating case. [1]",
            "## Further Learning",
            "## Sources",
            "[1] A reviewed source.",
            "[2] Residual-risk field study.",
        ):
            self.assertIn(text, report)

        ordered_text = (
            "## Orientation",
            "## Domain Map",
            "| Scope |",
            "| Controls |",
            "| Risk |",
            "Scope --depends on--> Controls",
            "Controls --constrains--> Risk",
            "## Set the scope",
            "## Match controls",
            "## Assess residual risk",
            "**Boundary (evidence limit):**",
            "## Synthesis",
            "## Transfer the Model",
            "## Further Learning",
            "## Sources",
        )
        offsets = [report.index(text) for text in ordered_text]
        self.assertEqual(offsets, sorted(offsets))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "schema-v3-report.md"
            output.write_bytes(first)
            rendered_output = output.read_text(encoding="utf-8")
        for forbidden in (
            "Convergence History",
            "Knowledge Gaps",
            "Topic ID",
            "claim-1",
            "claim-2",
            "evidence-1",
            "evidence-2",
            "gap-1",
            "skeptic review",
            "audit record",
            "pending cursor",
            "completion cursor",
        ):
            self.assertNotIn(forbidden.casefold(), rendered_output.casefold())
        self.assertNotRegex(rendered_output, r"(?i)\bCycle\s+\d+\b")

    def test_schema_v3_rejects_an_incomplete_v2_reader_document(self) -> None:
        topic = _topic()
        topic.reader_document = copy.deepcopy(topic.reader_document)
        assert topic.reader_document is not None
        orientation = topic.reader_document["orientation"]
        assert isinstance(orientation, dict)
        del orientation["central_question"]

        with self.assertRaisesRegex(ValueError, "ready reader document"):
            render_knowledge_report(topic)

    def test_schema_v3_renders_normalized_optional_evidence_ids(self) -> None:
        source = _schema_v3_topic()
        document = source["reader_document"]
        assert isinstance(document, dict)
        orientation = document["orientation"]
        assert isinstance(orientation, dict)
        current_conclusion = orientation["current_conclusion"]
        assert isinstance(current_conclusion, dict)
        domain_map = document["domain_map"]
        assert isinstance(domain_map, dict)
        concepts = domain_map["concepts"]
        relationships = domain_map["relationships"]
        variables = domain_map["key_variables"]
        sections = document["sections"]
        transfer_guidance = document["transfer_guidance"]
        boundary_notes = document["boundary_notes"]
        further_learning = document["further_learning"]
        assert all(
            isinstance(value, list)
            for value in (
                concepts,
                relationships,
                variables,
                sections,
                transfer_guidance,
                boundary_notes,
                further_learning,
            )
        )
        for block in (
            current_conclusion,
            concepts[0],
            relationships[0],
            variables[0],
            sections[0],
            transfer_guidance[0],
            boundary_notes[0],
            further_learning[0],
        ):
            assert isinstance(block, dict)
            block.pop("evidence_ids", None)

        topic = TopicKnowledge.from_dict(source)
        self.assertTrue(reader_document_ready(topic))

        report = render_knowledge_report(topic).decode("utf-8")

        self.assertIn("## Sources", report)
        self.assertIn("[1] A reviewed source.", report)
        self.assertNotIn("[2]", report)


if __name__ == "__main__":
    unittest.main()
