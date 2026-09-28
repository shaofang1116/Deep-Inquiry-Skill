"""Public protocol parity for the schema-v3 cognitive reader document."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "deep-inquiry"))

from scripts import judgments, reader_document


ENGLISH_PROTOCOL = ROOT / "skill" / "deep-inquiry" / "SKILL.md"
CHINESE_PROTOCOL = ROOT / "skill" / "deep-inquiry" / "SKILL.zh-CN.md"
README = ROOT / "README.md"

EXPLICIT_PROTOCOL_STRUCTURE = {
    "contract": "reader_document_v2",
    "schema_version": 2,
    "field_sets": {
        "document": [
            "schema_version",
            "orientation",
            "domain_map",
            "sections",
            "synthesis",
            "transfer_guidance",
            "boundary_notes",
            "further_learning",
        ],
        "orientation": [
            "central_question",
            "scope",
            "current_conclusion",
            "paragraphs",
            "claim_ids",
            "evidence_ids",
            "narrow_proposition",
        ],
        "domain_map": [
            "concepts",
            "relationships",
            "keystone_concept_ids",
            "prerequisite_edges",
            "key_variables",
        ],
        "concept": ["id", "label", "definition", "claim_ids", "evidence_ids"],
        "relationship": [
            "id",
            "type",
            "from_concept_id",
            "to_concept_id",
            "condition",
            "claim_ids",
            "evidence_ids",
        ],
        "prerequisite_edge": ["before_concept_id", "after_concept_id"],
        "key_variable": [
            "name",
            "concept_refs",
            "change_direction",
            "effect",
            "project_input_required",
            "claim_ids",
            "evidence_ids",
        ],
        "section": [
            "id",
            "heading",
            "cognitive_question",
            "concept_refs",
            "paragraphs",
            "mechanism_chain",
            "dimension_refs",
            "claim_ids",
            "evidence_ids",
        ],
        "text_block": ["text", "claim_ids", "evidence_ids"],
        "transfer_guidance": [
            "prompt",
            "reusable_model",
            "reevaluate",
            "concept_refs",
            "claim_ids",
            "evidence_ids",
        ],
        "boundary_note": ["type", "text", "claim_ids", "evidence_ids", "gap_ids"],
        "further_learning": ["direction", "claim_ids", "evidence_ids", "gap_ids"],
    },
    "keystone_concept_ids": {
        "normal_range": [3, 7],
        "two_requires_narrow_proposition": True,
    },
    "unready_reason_code": "reader_document_not_ready",
}


def _runtime_backed_contract() -> dict[str, object]:
    return {
        **EXPLICIT_PROTOCOL_STRUCTURE,
        "relationship_types": list(reader_document.RELATIONSHIP_TYPES),
        "boundary_types": list(reader_document.BOUNDARY_TYPES),
        "reader_document_review_defects": list(
            judgments.READER_DOCUMENT_DEFECT_CATEGORIES
        ),
        "lifecycle": {
            "autonomous_stages": list(judgments.AUTONOMOUS_STAGES),
        },
    }


def _canonical_contract(protocol: str, heading: str) -> dict[str, object]:
    marker = f"### {heading}"
    lines = protocol.splitlines(keepends=True)
    heading_indexes = [
        index for index, line in enumerate(lines) if line.rstrip("\r\n") == marker
    ]
    if len(heading_indexes) != 1:
        raise AssertionError(
            f"canonical contract heading must appear exactly once: {heading}"
        )

    section_start = heading_indexes[0] + 1
    section_end = next(
        (
            index
            for index in range(section_start, len(lines))
            if lines[index].startswith("### ")
        ),
        len(lines),
    )
    section = "".join(lines[section_start:section_end])
    opening_fence = "```json\n"
    manifest_section = section.lstrip()
    if not manifest_section.startswith(opening_fence):
        raise AssertionError(
            f"canonical contract must immediately follow heading in one JSON fence: "
            f"{heading}"
        )
    payload_start = len(opening_fence)
    payload_end = manifest_section.find("\n```", payload_start)
    if payload_end < 0:
        raise AssertionError(f"unterminated JSON canonical contract block: {heading}")
    if "```" in manifest_section[payload_end + len("\n```") :]:
        raise AssertionError(
            f"canonical contract section must not contain additional fences: {heading}"
        )

    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise AssertionError(
                    f"duplicate key in canonical contract JSON: {key}"
                )
            result[key] = value
        return result

    return json.loads(
        manifest_section[payload_start:payload_end],
        object_pairs_hook=reject_duplicate_keys,
    )


class CognitiveReaderReportProtocolTests(unittest.TestCase):
    def test_english_canonical_contract_and_chinese_complete_mirror_are_isomorphic(
        self,
    ) -> None:
        english = ENGLISH_PROTOCOL.read_text(encoding="utf-8")
        chinese = CHINESE_PROTOCOL.read_text(encoding="utf-8")

        self.assertIn(
            "The JSON manifest below is the canonical reader-document v2 contract.",
            english,
        )
        self.assertIn(
            "下方 JSON 清单是英文 canonical reader-document v2 契约的完整镜像",
            " ".join(chinese.split()),
        )
        english_contract = _canonical_contract(
            english,
            "Canonical Reader-Document v2 Contract",
        )
        chinese_contract = _canonical_contract(
            chinese,
            "Canonical Reader-Document v2 Contract（规范镜像）",
        )

        self.assertEqual(_runtime_backed_contract(), english_contract)
        self.assertEqual(english_contract, chinese_contract)

        with self.subTest("relationship runtime drift"):
            with patch.object(
                reader_document,
                "RELATIONSHIP_TYPES",
                (*reader_document.RELATIONSHIP_TYPES, "runtime_only_relation"),
            ):
                with self.assertRaises(AssertionError):
                    self.assertEqual(_runtime_backed_contract(), english_contract)
        with self.subTest("boundary runtime drift"):
            with patch.object(
                reader_document,
                "BOUNDARY_TYPES",
                (*reader_document.BOUNDARY_TYPES, "runtime_only_boundary"),
            ):
                with self.assertRaises(AssertionError):
                    self.assertEqual(_runtime_backed_contract(), english_contract)
        with self.subTest("skeptic defect runtime drift"):
            with patch.object(
                judgments,
                "READER_DOCUMENT_DEFECT_CATEGORIES",
                (*judgments.READER_DOCUMENT_DEFECT_CATEGORIES, "runtime_only_defect"),
            ):
                with self.assertRaises(AssertionError):
                    self.assertEqual(_runtime_backed_contract(), english_contract)
        with self.subTest("autonomous lifecycle runtime drift"):
            with patch.object(
                judgments,
                "AUTONOMOUS_STAGES",
                (*judgments.AUTONOMOUS_STAGES, "runtime_only_stage"),
            ):
                with self.assertRaises(AssertionError):
                    self.assertEqual(_runtime_backed_contract(), english_contract)
        with self.subTest("autonomous lifecycle same-length name replacement"):
            stages = list(judgments.AUTONOMOUS_STAGES)
            stages[-1] = "runtime_replaced_stage"
            with patch.object(judgments, "AUTONOMOUS_STAGES", tuple(stages)):
                with self.assertRaises(AssertionError):
                    self.assertEqual(_runtime_backed_contract(), english_contract)

    def test_protocol_limits_legacy_document_to_compatibility_completion(self) -> None:
        english = ENGLISH_PROTOCOL.read_text(encoding="utf-8")
        chinese = CHINESE_PROTOCOL.read_text(encoding="utf-8")

        self.assertIn(
            "A schema-v2 topic carrying reader-document v1 may pass legacy "
            "readiness and complete through its compatibility path, including "
            "immutable report rendering; its legacy fields cannot serve as the "
            "contract for a new schema-v3 publication.",
            " ".join(english.split()),
        )
        self.assertIn(
            "携带 reader-document v1 的 schema-v2 topic 可通过 legacy "
            "readiness 在兼容路径完成，并渲染不可变报告；其旧字段不能作为新 "
            "schema-v3 发布的契约。",
            " ".join(chinese.split()),
        )
        self.assertNotIn("cannot produce a new converged report", english)
        self.assertNotIn("不能生成新的收敛报告", chinese)

    def test_canonical_contract_heading_must_be_unique(self) -> None:
        english = ENGLISH_PROTOCOL.read_text(encoding="utf-8")
        heading = "Canonical Reader-Document v2 Contract"

        with self.assertRaisesRegex(AssertionError, "exactly once"):
            _canonical_contract(english + f"\n### {heading}\n", heading)

    def test_canonical_contract_requires_one_adjacent_json_fence(self) -> None:
        english = ENGLISH_PROTOCOL.read_text(encoding="utf-8")
        heading = "Canonical Reader-Document v2 Contract"
        marker = f"### {heading}\n\n```json\n"

        with self.subTest("wrong fence language"):
            with self.assertRaisesRegex(AssertionError, "one JSON fence"):
                _canonical_contract(
                    english.replace(marker, f"### {heading}\n\n```yaml\n", 1),
                    heading,
                )
        with self.subTest("inserted text before manifest"):
            with self.assertRaisesRegex(AssertionError, "one JSON fence"):
                _canonical_contract(
                    english.replace(
                        marker,
                        f"### {heading}\n\nThis must not precede the manifest.\n\n"
                        "```json\n",
                        1,
                    ),
                    heading,
                )
        with self.subTest("additional fence in manifest section"):
            with self.assertRaisesRegex(AssertionError, "additional fences"):
                _canonical_contract(
                    english.replace(
                        "\n```\n\n`relationships`",
                        "\n```\n\n```text\nnot a manifest\n```\n\n`relationships`",
                        1,
                    ),
                    heading,
                )

    def test_canonical_contract_rejects_duplicate_json_keys_at_every_depth(
        self,
    ) -> None:
        english = ENGLISH_PROTOCOL.read_text(encoding="utf-8")
        heading = "Canonical Reader-Document v2 Contract"

        with self.subTest("top level"):
            with self.assertRaisesRegex(AssertionError, "duplicate key"):
                _canonical_contract(
                    english.replace(
                        '  "contract": "reader_document_v2",\n',
                        '  "contract": "reader_document_v2",\n'
                        '  "contract": "reader_document_v2",\n',
                        1,
                    ),
                    heading,
                )
        with self.subTest("nested object"):
            with self.assertRaisesRegex(AssertionError, "duplicate key"):
                _canonical_contract(
                    english.replace(
                        '  "lifecycle": {"autonomous_stages": ["anchor", "map_knowledge", "select_gap", "plan_investigation", "integrate_learning", "skeptic_review", "assess_convergence", "checkpoint_or_complete"]},\n',
                        '  "lifecycle": {"autonomous_stages": ["anchor", "map_knowledge", "select_gap", "plan_investigation", "integrate_learning", "skeptic_review", "assess_convergence", "checkpoint_or_complete"], "autonomous_stages": ["anchor", "map_knowledge", "select_gap", "plan_investigation", "integrate_learning", "skeptic_review", "assess_convergence", "checkpoint_or_complete"]},\n',
                        1,
                    ),
                    heading,
                )

    def test_examples_use_plain_reader_prose_without_internal_identifiers(self) -> None:
        english = ENGLISH_PROTOCOL.read_text(encoding="utf-8")
        chinese = CHINESE_PROTOCOL.read_text(encoding="utf-8")

        for protocol in (english, chinese):
            self.assertIn("Plain reader prose example", protocol)
            example = protocol.split("Plain reader prose example", maxsplit=1)[1]
            example = example.split("###", maxsplit=1)[0]
            self.assertNotIn("claim-", example)
            self.assertNotIn("evidence-", example)
            self.assertNotIn("gap-", example)
            self.assertNotIn("candidate_id", example)

    def test_readme_names_capability_without_deferred_product_promises(self) -> None:
        readme = README.read_text(encoding="utf-8").lower()

        self.assertIn("domain map", readme)
        self.assertIn("mechanism", readme)
        self.assertIn("transfer", readme)
        self.assertNotIn("graph visualization", readme)
        self.assertNotIn("mutable revision", readme)
        self.assertNotIn("separate knowledge model", readme)


if __name__ == "__main__":
    unittest.main()
