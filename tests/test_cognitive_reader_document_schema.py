"""Schema-v3 coverage for reader-document v2 cognitive maps."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts.knowledge_publisher import KnowledgePublisher
from scripts.knowledge_schema import KnowledgeSchemaError, TopicKnowledge
from scripts.knowledge_store import KnowledgeStore
from scripts.learner import Learner
from scripts.reader_document import ReaderDocumentError, reader_document_from_dict
from tests.test_reader_document_schema import _reader_document, _topic_data


_FORBIDDEN_READER_PROSE = (
    "integrate_learning",
    "skeptic_review",
    "candidate_id",
    "convergence_history",
    "structural_hit",
    "publication_record",
    "audit_state",
    "audit-state",
    "audit record",
    "integrate learning",
    "skeptic review",
    "Convergence History",
    "candidate ID",
    "structural hit",
    "publication record",
    "audit state",
    "reader document approved",
    "reader document defects",
    "learning cycle",
    "cycle 1",
    "pending cursor",
    "completion cursor",
    "pending state",
    "host tool",
    "host run",
    "agent instruction",
)


def _reader_document_v2() -> dict[str, object]:
    return {
        "schema_version": 2,
        "orientation": {
            "central_question": "How do scope choices and controls shape risk?",
            "scope": "Operational decisions with incomplete evidence.",
            "current_conclusion": {
                "text": "Controls reduce risk only when they match the chosen scope.",
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
            },
            "paragraphs": ["Start by connecting scope, controls, and risk."],
            "claim_ids": ["claim-1"],
            "evidence_ids": ["evidence-1"],
        },
        "domain_map": {
            "concepts": [
                {
                    "id": "scope",
                    "label": "Scope",
                    "definition": "The operating conditions a decision covers.",
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                },
                {
                    "id": "controls",
                    "label": "Controls",
                    "definition": "Safeguards chosen for a stated scope.",
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                },
                {
                    "id": "risk",
                    "label": "Risk",
                    "definition": "The remaining exposure under those controls.",
                    "claim_ids": ["claim-2"],
                    "evidence_ids": [],
                },
            ],
            "relationships": [
                {
                    "id": "scope-depends-on-controls",
                    "type": "depends_on",
                    "from_concept_id": "scope",
                    "to_concept_id": "controls",
                    "condition": "When controls are selected for the scope.",
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                },
                {
                    "id": "controls-constrain-risk",
                    "type": "constrains",
                    "from_concept_id": "controls",
                    "to_concept_id": "risk",
                    "condition": "Under ordinary operating conditions.",
                    "claim_ids": ["claim-2"],
                    "evidence_ids": [],
                },
            ],
            "keystone_concept_ids": ["scope", "controls", "risk"],
            "prerequisite_edges": [
                {
                    "before_concept_id": "scope",
                    "after_concept_id": "controls",
                }
            ],
            "key_variables": [
                {
                    "name": "Scope variation",
                    "concept_refs": ["scope", "risk"],
                    "change_direction": "broader",
                    "effect": "A broader scope can increase the risk envelope.",
                    "claim_ids": ["claim-1"],
                    "evidence_ids": ["evidence-1"],
                    "project_input_required": True,
                }
            ],
        },
        "sections": [
            {
                "id": "scope",
                "heading": "Set the scope",
                "cognitive_question": "What conditions define the decision?",
                "concept_refs": ["scope"],
                "paragraphs": ["Scope defines the relevant risk envelope."],
                "mechanism_chain": [
                    "Scope choice",
                    "control selection",
                    "risk envelope",
                    "decision implication",
                ],
                "dimension_refs": ["scope"],
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
            },
            {
                "id": "controls",
                "heading": "Match controls",
                "cognitive_question": "How should controls follow the scope?",
                "concept_refs": ["controls"],
                "paragraphs": ["Controls must match the scope they protect."],
                "mechanism_chain": [
                    "Chosen scope",
                    "matched controls",
                    "reduced exposure",
                    "operating implication",
                ],
                "dimension_refs": ["scope"],
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
            },
            {
                "id": "risk",
                "heading": "Assess residual risk",
                "cognitive_question": "What risk remains after controls?",
                "concept_refs": ["risk"],
                "paragraphs": ["Unusual conditions can still defeat controls."],
                "mechanism_chain": [
                    "Unusual condition",
                    "control mismatch",
                    "residual risk",
                    "escalation implication",
                ],
                "dimension_refs": ["risk"],
                "claim_ids": ["claim-2"],
                "evidence_ids": [],
            },
        ],
        "synthesis": {
            "paragraphs": [
                "Scope and controls must be evaluated together before risk is accepted."
            ],
            "claim_ids": ["claim-1", "claim-2"],
            "evidence_ids": ["evidence-1"],
        },
        "transfer_guidance": [
            {
                "prompt": "Apply the scope-control-risk model to a new operating case.",
                "reusable_model": "The dependency between scope, controls, and risk.",
                "reevaluate": ["Scope variation for the new case."],
                "concept_refs": ["scope", "controls", "risk"],
                "claim_ids": ["claim-1"],
                "evidence_ids": ["evidence-1"],
            }
        ],
        "boundary_notes": [
            {
                "type": "evidence_limit",
                "text": "Evidence remains limited for unusual conditions.",
                "claim_ids": ["claim-2"],
                "evidence_ids": [],
                "gap_ids": ["gap-1"],
            }
        ],
        "further_learning": [
            {
                "direction": "Test controls under unusual conditions.",
                "claim_ids": ["claim-2"],
                "evidence_ids": [],
                "gap_ids": ["gap-1"],
            }
        ],
    }


def _schema_v3_topic() -> dict[str, object]:
    topic = _topic_data()
    topic["schema_version"] = 3
    topic["reader_document"] = _reader_document_v2()
    return topic


class CognitiveReaderDocumentSchemaTests(unittest.TestCase):
    def test_schema_v3_reader_document_v2_round_trips(self) -> None:
        source = _schema_v3_topic()

        topic = TopicKnowledge.from_dict(source)

        self.assertEqual(topic.to_dict(), source)

    def test_v2_normalizes_optional_evidence_ids_for_renderer_blocks(self) -> None:
        source = _schema_v3_topic()
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        orientation = document["orientation"]
        self.assertIsInstance(orientation, dict)
        current_conclusion = orientation["current_conclusion"]
        self.assertIsInstance(current_conclusion, dict)
        domain_map = document["domain_map"]
        self.assertIsInstance(domain_map, dict)
        concepts = domain_map["concepts"]
        relationships = domain_map["relationships"]
        variables = domain_map["key_variables"]
        sections = document["sections"]
        transfer_guidance = document["transfer_guidance"]
        boundary_notes = document["boundary_notes"]
        further_learning = document["further_learning"]
        self.assertTrue(
            all(
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
        )
        blocks = (
            current_conclusion,
            concepts[0],
            relationships[0],
            variables[0],
            sections[0],
            transfer_guidance[0],
            boundary_notes[0],
            further_learning[0],
        )
        for block in blocks:
            self.assertIsInstance(block, dict)
            block.pop("evidence_ids", None)

        topic = TopicKnowledge.from_dict(source)
        normalized = topic.reader_document
        self.assertIsInstance(normalized, dict)
        normalized_orientation = normalized["orientation"]
        self.assertIsInstance(normalized_orientation, dict)
        normalized_domain_map = normalized["domain_map"]
        self.assertIsInstance(normalized_domain_map, dict)
        normalized_blocks = (
            normalized_orientation["current_conclusion"],
            normalized_domain_map["concepts"][0],
            normalized_domain_map["relationships"][0],
            normalized_domain_map["key_variables"][0],
            normalized["sections"][0],
            normalized["transfer_guidance"][0],
            normalized["boundary_notes"][0],
            normalized["further_learning"][0],
        )
        for block in normalized_blocks:
            self.assertIsInstance(block, dict)
            self.assertEqual(block["evidence_ids"], [])

    def test_v2_optional_evidence_ids_do_not_make_claim_ids_optional(self) -> None:
        document = _reader_document_v2()
        orientation = document["orientation"]
        self.assertIsInstance(orientation, dict)
        current_conclusion = orientation["current_conclusion"]
        self.assertIsInstance(current_conclusion, dict)
        current_conclusion.pop("evidence_ids")
        current_conclusion.pop("claim_ids")
        topic = TopicKnowledge.from_dict(_topic_data())

        with self.assertRaisesRegex(ReaderDocumentError, "claim_ids must be"):
            reader_document_from_dict(
                document,
                topic=topic,
                require_complete=True,
            )

    def test_retirement_downgrades_schema_v3_v2_document_to_schema_v2_carrier(
        self,
    ) -> None:
        source = TopicKnowledge.from_dict(_schema_v3_topic())
        with tempfile.TemporaryDirectory() as directory:
            store = KnowledgeStore(directory)
            store.create(source)

            retired = KnowledgePublisher(store).retire(
                topic_id=source.topic_id,
                base_version=source.version,
                claim_ids=["claim-1"],
                candidate_id="retire-v3-v2-document",
            )

            compatibility_carrier = store.load(source.topic_id)

        self.assertEqual(retired.state, "retired")
        self.assertEqual(compatibility_carrier.schema_version, 2)
        self.assertIsNone(compatibility_carrier.reader_document)

    def test_schema_v3_candidate_cannot_use_retirement_missing_document_flag(
        self,
    ) -> None:
        current = TopicKnowledge.from_dict(_schema_v3_topic())
        update = {
            "delta": {},
            "cycle": 1,
            "phase": "baseline",
            "gain_level": "high",
            "skeptic_structural_hit": False,
        }

        with self.assertRaisesRegex(ValueError, "invalid reader_document"):
            Learner().build_knowledge_candidate(current, update=update)

        with self.assertRaisesRegex(
            TypeError,
            "allow_missing_reader_document",
        ):
            Learner().build_knowledge_candidate(
                current,
                update=update,
                allow_missing_reader_document=True,
            )

    def test_v2_rejects_invalid_cognitive_map_contracts(self) -> None:
        cases = {
            "unknown concept": lambda document: document["domain_map"][
                "relationships"
            ][0].update({"to_concept_id": "missing"}),
            "unsupported relation type": lambda document: document["domain_map"][
                "relationships"
            ][0].update({"type": "correlates_with"}),
            "ungrounded relation": lambda document: document["domain_map"][
                "relationships"
            ][0].update({"claim_ids": []}),
            "prerequisite cycle": lambda document: document["domain_map"][
                "prerequisite_edges"
            ].append(
                {
                    "before_concept_id": "controls",
                    "after_concept_id": "scope",
                }
            ),
            "section order violation": lambda document: document["sections"].reverse(),
            "missing keystone mechanism": lambda document: document["sections"][1].pop(
                "mechanism_chain"
            ),
            "missing transfer prompt": lambda document: document.update(
                {"transfer_guidance": []}
            ),
            "invalid boundary type": lambda document: document["boundary_notes"][
                0
            ].update({"type": "unsupported"}),
        }

        for name, mutate in cases.items():
            with self.subTest(name=name):
                source = _schema_v3_topic()
                document = source["reader_document"]
                self.assertIsInstance(document, dict)
                mutate(document)

                with self.assertRaises(KnowledgeSchemaError):
                    TopicKnowledge.from_dict(source)

    def test_v2_rejects_multidimension_synthesis_with_one_claim_dimension(
        self,
    ) -> None:
        source = _schema_v3_topic()
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        synthesis = document["synthesis"]
        self.assertIsInstance(synthesis, dict)
        synthesis["claim_ids"] = ["claim-1"]
        synthesis["evidence_ids"] = ["evidence-1"]

        with self.assertRaisesRegex(
            KnowledgeSchemaError,
            "synthesis must reference claims from at least two coverage dimensions",
        ):
            TopicKnowledge.from_dict(source)

    def test_v2_allows_single_dimension_synthesis_for_narrow_topic(self) -> None:
        source = _schema_v3_topic()
        source["coverage_dimensions"] = ["scope"]
        source["claims"] = [source["claims"][0]]
        source["gaps"] = []
        source["counterexamples"] = []
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        orientation = document["orientation"]
        domain_map = document["domain_map"]
        self.assertIsInstance(orientation, dict)
        self.assertIsInstance(domain_map, dict)
        orientation["narrow_proposition"] = True
        domain_map["concepts"] = domain_map["concepts"][:2]
        domain_map["relationships"] = domain_map["relationships"][:1]
        domain_map["keystone_concept_ids"] = ["scope", "controls"]
        domain_map["key_variables"][0]["concept_refs"] = ["scope", "controls"]
        document["sections"] = document["sections"][:2]
        document["synthesis"]["claim_ids"] = ["claim-1"]
        document["synthesis"]["evidence_ids"] = ["evidence-1"]
        document["transfer_guidance"][0]["concept_refs"] = ["scope", "controls"]
        document["boundary_notes"][0]["claim_ids"] = ["claim-1"]
        document["boundary_notes"][0]["evidence_ids"] = ["evidence-1"]
        document["boundary_notes"][0]["gap_ids"] = []
        document["further_learning"][0]["claim_ids"] = ["claim-1"]
        document["further_learning"][0]["evidence_ids"] = ["evidence-1"]
        document["further_learning"][0]["gap_ids"] = []

        topic = TopicKnowledge.from_dict(source)

        self.assertEqual(topic.coverage_dimensions, ["scope"])

    def test_v2_rejects_empty_key_variables(self) -> None:
        source = _schema_v3_topic()
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        document["domain_map"]["key_variables"] = []

        with self.assertRaisesRegex(
            KnowledgeSchemaError,
            "key_variables must be a non-empty list",
        ):
            TopicKnowledge.from_dict(source)

    def test_v2_rejects_every_forbidden_internal_term_in_reader_visible_prose(
        self,
    ) -> None:
        topic = TopicKnowledge.from_dict(_topic_data())
        for term in _FORBIDDEN_READER_PROSE:
            with self.subTest(term=term):
                document = _reader_document_v2()
                orientation = document["orientation"]
                self.assertIsInstance(orientation, dict)
                orientation["paragraphs"] = [
                    f"Readers should not see {term} in the explanation."
                ]

                with self.assertRaisesRegex(
                    ReaderDocumentError,
                    "internal workflow or audit term",
                ):
                    reader_document_from_dict(
                        document,
                        topic=topic,
                        require_complete=True,
                    )

    def test_v2_allows_ordinary_domain_terms_near_forbidden_phrases(self) -> None:
        topic = TopicKnowledge.from_dict(_topic_data())
        document = _reader_document_v2()
        orientation = document["orientation"]
        self.assertIsInstance(orientation, dict)
        orientation["paragraphs"] = [
            "A literature review can explain a water cycle and database cursor.",
            "Candidate identity differs from a publication recorder.",
        ]

        self.assertIsNotNone(
            reader_document_from_dict(
                document,
                topic=topic,
                require_complete=True,
            )
        )

    def test_v2_scans_every_reader_visible_prose_field(self) -> None:
        topic = TopicKnowledge.from_dict(_topic_data())
        cases = {
            "central question": lambda document: document["orientation"].update(
                {"central_question": "candidate ID"}
            ),
            "scope": lambda document: document["orientation"].update(
                {"scope": "candidate ID"}
            ),
            "current conclusion": lambda document: document["orientation"][
                "current_conclusion"
            ].update({"text": "candidate ID"}),
            "orientation paragraph": lambda document: document["orientation"].update(
                {"paragraphs": ["candidate ID"]}
            ),
            "concept label": lambda document: document["domain_map"]["concepts"][0].update(
                {"label": "candidate ID"}
            ),
            "concept definition": lambda document: document["domain_map"][
                "concepts"
            ][0].update({"definition": "candidate ID"}),
            "relationship condition": lambda document: document["domain_map"][
                "relationships"
            ][0].update({"condition": "candidate ID"}),
            "variable name": lambda document: document["domain_map"][
                "key_variables"
            ][0].update({"name": "candidate ID"}),
            "variable direction": lambda document: document["domain_map"][
                "key_variables"
            ][0].update({"change_direction": "candidate ID"}),
            "variable effect": lambda document: document["domain_map"][
                "key_variables"
            ][0].update({"effect": "candidate ID"}),
            "section heading": lambda document: document["sections"][0].update(
                {"heading": "candidate ID"}
            ),
            "cognitive question": lambda document: document["sections"][0].update(
                {"cognitive_question": "candidate ID"}
            ),
            "section paragraph": lambda document: document["sections"][0].update(
                {"paragraphs": ["candidate ID"]}
            ),
            "mechanism chain": lambda document: document["sections"][0].update(
                {
                    "mechanism_chain": [
                        "candidate ID",
                        "control selection",
                        "risk envelope",
                        "decision implication",
                    ]
                }
            ),
            "synthesis paragraph": lambda document: document["synthesis"].update(
                {"paragraphs": ["candidate ID"]}
            ),
            "transfer prompt": lambda document: document["transfer_guidance"][0].update(
                {"prompt": "candidate ID"}
            ),
            "reusable model": lambda document: document["transfer_guidance"][0].update(
                {"reusable_model": "candidate ID"}
            ),
            "reevaluate": lambda document: document["transfer_guidance"][0].update(
                {"reevaluate": ["candidate ID"]}
            ),
            "boundary note": lambda document: document["boundary_notes"][0].update(
                {"text": "candidate ID"}
            ),
            "further learning": lambda document: document["further_learning"][0].update(
                {"direction": "candidate ID"}
            ),
        }

        for name, mutate in cases.items():
            with self.subTest(name=name):
                document = _reader_document_v2()
                mutate(document)

                with self.assertRaises(ReaderDocumentError):
                    reader_document_from_dict(
                        document,
                        topic=topic,
                        require_complete=True,
                    )

    def test_v2_rejects_resolved_further_learning_gap(self) -> None:
        source = _schema_v3_topic()
        source["gaps"][0]["status"] = "resolved"
        source["gaps"][0]["resolution_claim_ids"] = ["claim-2"]
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        document["boundary_notes"][0]["gap_ids"] = []

        with self.assertRaisesRegex(KnowledgeSchemaError, "non-open gap"):
            TopicKnowledge.from_dict(source)

    def test_v2_rejects_further_learning_gap_with_unrelated_claim(self) -> None:
        source = _schema_v3_topic()
        document = source["reader_document"]
        self.assertIsInstance(document, dict)
        document["further_learning"][0]["claim_ids"] = ["claim-1"]

        with self.assertRaisesRegex(KnowledgeSchemaError, "unrelated gap"):
            TopicKnowledge.from_dict(source)

    def test_complete_v2_document_upgrades_candidate_to_schema_v3(self) -> None:
        current = TopicKnowledge.from_dict(_topic_data(schema_version=2))
        candidate = Learner().build_knowledge_candidate(
            current,
            update={
                "delta": {},
                "cycle": 1,
                "phase": "baseline",
                "gain_level": "high",
                "skeptic_structural_hit": False,
                "reader_document": _reader_document_v2(),
            },
        )

        self.assertEqual(candidate.schema_version, 3)
        self.assertEqual(candidate.reader_document["schema_version"], 2)

    def test_schema_v3_candidate_rejects_v1_reader_document_downgrade(self) -> None:
        current = TopicKnowledge.from_dict(_schema_v3_topic())

        with self.assertRaisesRegex(
            ValueError,
            "schema-v3 topic cannot use reader_document.schema_version 1",
        ):
            Learner().build_knowledge_candidate(
                current,
                update={
                    "delta": {},
                    "cycle": 1,
                    "phase": "baseline",
                    "gain_level": "high",
                    "skeptic_structural_hit": False,
                    "reader_document": _reader_document(),
                },
            )


if __name__ == "__main__":
    unittest.main()
