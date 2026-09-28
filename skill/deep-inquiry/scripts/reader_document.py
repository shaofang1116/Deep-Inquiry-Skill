"""Canonical reader-document validation for durable topic knowledge."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from .knowledge_schema import TopicKnowledge


class ReaderDocumentError(ValueError):
    """A reader document violates the canonical document contract."""


def _required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReaderDocumentError(f"{field_name} must be a non-empty string")
    return value


def _required_object(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReaderDocumentError(f"{field_name} must be an object")
    return value


def _required_list(value: object, field_name: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise ReaderDocumentError(f"{field_name} must be a non-empty list")
    return value


def _text_list(value: object, field_name: str, *, required: bool) -> list[str]:
    if not isinstance(value, list) or (required and not value):
        qualifier = "a non-empty list" if required else "a list"
        raise ReaderDocumentError(f"{field_name} must be {qualifier}")
    result = [_required_text(item, f"{field_name} item") for item in value]
    if len(result) != len(set(result)):
        raise ReaderDocumentError(f"{field_name} contains duplicate values")
    return result


def _json_object(value: object, field_name: str) -> dict[str, Any]:
    source = _required_object(value, field_name)
    try:
        encoded = json.dumps(
            source,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ReaderDocumentError(
            f"{field_name} must contain JSON-compatible values"
        ) from exc
    return json.loads(encoded)


def _validate_references(
    block: dict[str, Any],
    *,
    field_name: str,
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
    require_claims: bool = True,
    allow_missing_evidence_ids: bool = False,
    normalize_missing_evidence_ids: bool = False,
) -> set[str]:
    if normalize_missing_evidence_ids and "evidence_ids" not in block:
        block["evidence_ids"] = []
    claim_ids = _text_list(
        block.get("claim_ids"),
        f"{field_name}.claim_ids",
        required=require_claims,
    )
    available_claim_ids = set(claims_by_id)
    missing_claim_ids = set(claim_ids) - available_claim_ids
    if missing_claim_ids:
        raise ReaderDocumentError(
            f"{field_name} references unknown claims {sorted(missing_claim_ids)}"
        )
    retired_claim_ids = [
        claim_id
        for claim_id in claim_ids
        if claims_by_id[claim_id].status == "retired"
    ]
    if retired_claim_ids:
        raise ReaderDocumentError(
            f"{field_name} references retired claims {retired_claim_ids}"
        )

    evidence_ids = _text_list(
        block.get("evidence_ids", [] if allow_missing_evidence_ids else None),
        f"{field_name}.evidence_ids",
        required=False,
    )
    for evidence_id in evidence_ids:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            raise ReaderDocumentError(
                f"{field_name} references unknown evidence {evidence_id!r}"
            )
        if not set(evidence.supports_claim_ids).intersection(claim_ids):
            raise ReaderDocumentError(
                f"{field_name} evidence {evidence_id!r} is not linked to "
                "a referenced claim"
            )
    return set(claim_ids)


def _validate_text_block(
    value: object,
    *,
    field_name: str,
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> set[str]:
    block = _required_object(value, field_name)
    _text_list(block.get("paragraphs"), f"{field_name}.paragraphs", required=True)
    return _validate_references(
        block,
        field_name=field_name,
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
    )


def _validate_reader_document_v1(
    document: dict[str, Any],
    *,
    topic: TopicKnowledge,
) -> dict[str, object]:
    """Validate the schema-v1 compatibility document."""

    claims_by_id = {claim.id: claim for claim in topic.claims}
    evidence_by_id = {evidence.id: evidence for evidence in topic.evidence}
    gaps_by_id = {gap.id: gap for gap in topic.gaps}

    referenced_claim_ids = _validate_text_block(
        document.get("overview"),
        field_name="reader_document.overview",
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
    )
    disposition_claim_ids: set[str] = set()

    sections = _required_list(document.get("sections"), "reader_document.sections")
    section_ids: set[str] = set()
    represented_dimensions: set[str] = set()
    for index, value in enumerate(sections):
        field_name = f"reader_document.sections[{index}]"
        section = _required_object(value, field_name)
        section_id = _required_text(section.get("id"), f"{field_name}.id")
        if section_id in section_ids:
            raise ReaderDocumentError("reader_document.sections contains duplicate IDs")
        section_ids.add(section_id)
        _required_text(section.get("heading"), f"{field_name}.heading")
        _text_list(section.get("paragraphs"), f"{field_name}.paragraphs", required=True)
        _text_list(
            section.get("key_points"),
            f"{field_name}.key_points",
            required=False,
        )
        dimension_refs = _text_list(
            section.get("dimension_refs"),
            f"{field_name}.dimension_refs",
            required=True,
        )
        unknown_dimensions = set(dimension_refs) - set(topic.coverage_dimensions)
        if unknown_dimensions:
            raise ReaderDocumentError(
                f"{field_name} references unknown dimensions "
                f"{sorted(unknown_dimensions)}"
            )
        represented_dimensions.update(dimension_refs)
        section_claim_ids = _validate_references(
            section,
            field_name=field_name,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
        )
        referenced_claim_ids.update(section_claim_ids)
        disposition_claim_ids.update(section_claim_ids)

    missing_dimensions = set(topic.coverage_dimensions) - represented_dimensions
    if missing_dimensions:
        raise ReaderDocumentError(
            "reader_document does not represent coverage dimensions "
            f"{sorted(missing_dimensions)}"
        )

    synthesis_claim_ids = _validate_text_block(
        document.get("synthesis"),
        field_name="reader_document.synthesis",
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
    )
    referenced_claim_ids.update(synthesis_claim_ids)
    disposition_claim_ids.update(synthesis_claim_ids)

    application_guidance = _required_list(
        document.get("application_guidance"),
        "reader_document.application_guidance",
    )
    for index, value in enumerate(application_guidance):
        field_name = f"reader_document.application_guidance[{index}]"
        item = _required_object(value, field_name)
        _required_text(item.get("text"), f"{field_name}.text")
        application_claim_ids = _validate_references(
            item,
            field_name=field_name,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
        )
        referenced_claim_ids.update(application_claim_ids)
        disposition_claim_ids.update(application_claim_ids)

    boundary_notes = _required_list(
        document.get("boundary_notes"),
        "reader_document.boundary_notes",
    )
    for index, value in enumerate(boundary_notes):
        field_name = f"reader_document.boundary_notes[{index}]"
        note = _required_object(value, field_name)
        _required_text(note.get("text"), f"{field_name}.text")
        note_claim_ids = _validate_references(
            note,
            field_name=field_name,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
            allow_missing_evidence_ids=True,
        )
        referenced_claim_ids.update(note_claim_ids)
        disposition_claim_ids.update(note_claim_ids)
        gap_ids = _text_list(note.get("gap_ids"), f"{field_name}.gap_ids", required=False)
        for gap_id in gap_ids:
            gap = gaps_by_id.get(gap_id)
            if gap is None:
                raise ReaderDocumentError(
                    f"{field_name} references unknown gap {gap_id!r}"
                )
            if gap.status not in {"open", "deferred"}:
                raise ReaderDocumentError(
                    f"{field_name} references non-open gap {gap_id!r}"
                )
            if not any(
                claims_by_id[claim_id].dimension == gap.dimension
                for claim_id in note_claim_ids
            ):
                raise ReaderDocumentError(
                    f"{field_name} references unrelated gap {gap_id!r}"
                )

    active_claim_ids = {
        claim.id for claim in topic.claims if claim.status == "active"
    }
    missing_active_claim_ids = active_claim_ids - disposition_claim_ids
    if missing_active_claim_ids:
        raise ReaderDocumentError(
            "reader_document does not reference active claims "
            f"{sorted(missing_active_claim_ids)}"
        )
    return document


RELATIONSHIP_TYPES = (
    "depends_on",
    "causes",
    "constrains",
    "trades_off_with",
    "exception_to",
)
BOUNDARY_TYPES = (
    "knowledge_gap",
    "evidence_limit",
    "project_input",
    "professional_judgment",
    "frontier_dispute",
)
_INTERNAL_READER_PROSE_PHRASES = frozenset(
    {
        "agent instruction",
        "audit record",
        "audit state",
        "candidate id",
        "completion cursor",
        "convergence history",
        "host run",
        "host tool",
        "integrate learning",
        "learning cycle",
        "pending cursor",
        "pending state",
        "publication record",
        "reader document approved",
        "reader document defects",
        "skeptic review",
        "structural hit",
    }
)
_INTERNAL_READER_PROSE_PATTERNS = tuple(
    re.compile(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])")
    for phrase in sorted(_INTERNAL_READER_PROSE_PHRASES)
)
_NUMBERED_CYCLE_PATTERN = re.compile(r"(?<![a-z0-9])cycle [0-9]+(?![a-z0-9])")
_READER_VISIBLE_TEXT_FIELDS = {
    "central_question",
    "scope",
    "text",
    "paragraphs",
    "label",
    "definition",
    "condition",
    "name",
    "change_direction",
    "effect",
    "heading",
    "cognitive_question",
    "mechanism_chain",
    "prompt",
    "reusable_model",
    "reevaluate",
    "direction",
}


def _validate_statement_block(
    value: object,
    *,
    field_name: str,
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> set[str]:
    block = _required_object(value, field_name)
    _required_text(block.get("text"), f"{field_name}.text")
    return _validate_references(
        block,
        field_name=field_name,
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
        allow_missing_evidence_ids=True,
        normalize_missing_evidence_ids=True,
    )


def _validate_known_concepts(
    concept_refs: object,
    *,
    field_name: str,
    concept_ids: set[str],
) -> list[str]:
    refs = _text_list(concept_refs, field_name, required=True)
    unknown = set(refs) - concept_ids
    if unknown:
        raise ReaderDocumentError(
            f"{field_name} references unknown concepts {sorted(unknown)}"
        )
    return refs


def _validate_open_gap_references(
    gap_ids: object,
    *,
    field_name: str,
    gaps_by_id: dict[str, Any],
    claims_by_id: dict[str, Any],
    claim_ids: set[str],
) -> None:
    for gap_id in _text_list(gap_ids, f"{field_name}.gap_ids", required=False):
        gap = gaps_by_id.get(gap_id)
        if gap is None:
            raise ReaderDocumentError(
                f"{field_name} references unknown gap {gap_id!r}"
            )
        if gap.status not in {"open", "deferred"}:
            raise ReaderDocumentError(
                f"{field_name} references non-open gap {gap_id!r}"
            )
        if claim_ids and not any(
            claims_by_id[claim_id].dimension == gap.dimension
            for claim_id in claim_ids
        ):
            raise ReaderDocumentError(
                f"{field_name} references unrelated gap {gap_id!r}"
            )


def _validate_reader_visible_prose(
    value: object,
    *,
    field_name: str,
) -> None:
    if isinstance(value, str):
        normalized = re.sub(r"[_\s-]+", " ", value.casefold()).strip()
        for pattern in _INTERNAL_READER_PROSE_PATTERNS:
            if pattern.search(normalized):
                raise ReaderDocumentError(
                    f"{field_name} contains internal workflow or audit term "
                    f"{pattern.pattern!r}"
                )
        if _NUMBERED_CYCLE_PATTERN.search(normalized):
            raise ReaderDocumentError(
                f"{field_name} contains internal workflow or audit term "
                "'cycle <number>'"
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_reader_visible_prose(
                item,
                field_name=f"{field_name}[{index}]",
            )
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _READER_VISIBLE_TEXT_FIELDS:
                _validate_reader_visible_prose(
                    item,
                    field_name=f"{field_name}.{key}",
                )
            elif isinstance(item, dict):
                _validate_reader_visible_prose(
                    item,
                    field_name=f"{field_name}.{key}",
                )
            elif isinstance(item, list):
                for index, nested_item in enumerate(item):
                    if isinstance(nested_item, dict):
                        _validate_reader_visible_prose(
                            nested_item,
                            field_name=f"{field_name}.{key}[{index}]",
                        )


def _topological_concept_order(
    concept_ids: set[str],
    prerequisite_edges: list[tuple[str, str]],
) -> list[str]:
    """Return a deterministic prerequisite order or raise on a cycle."""
    successors = {concept_id: set() for concept_id in concept_ids}
    indegree = {concept_id: 0 for concept_id in concept_ids}
    for before_id, after_id in prerequisite_edges:
        if after_id not in successors[before_id]:
            successors[before_id].add(after_id)
            indegree[after_id] += 1

    ready = sorted(
        concept_id for concept_id, count in indegree.items() if count == 0
    )
    order: list[str] = []
    while ready:
        concept_id = ready.pop(0)
        order.append(concept_id)
        for successor in sorted(successors[concept_id]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort()
    if len(order) != len(concept_ids):
        raise ReaderDocumentError(
            "reader_document.domain_map.prerequisite_edges contains a cycle"
        )
    return order


def _validate_v2_orientation(
    document: dict[str, Any],
    *,
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> tuple[bool, set[str]]:
    orientation = _required_object(
        document.get("orientation"), "reader_document.orientation"
    )
    _required_text(
        orientation.get("central_question"),
        "reader_document.orientation.central_question",
    )
    _required_text(orientation.get("scope"), "reader_document.orientation.scope")
    narrow_proposition = orientation.get("narrow_proposition", False)
    if not isinstance(narrow_proposition, bool):
        raise ReaderDocumentError(
            "reader_document.orientation.narrow_proposition must be boolean"
        )
    grounded_claim_ids = _validate_statement_block(
        orientation.get("current_conclusion"),
        field_name="reader_document.orientation.current_conclusion",
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
    )
    _text_list(
        orientation.get("paragraphs"),
        "reader_document.orientation.paragraphs",
        required=True,
    )
    grounded_claim_ids.update(
        _validate_references(
            orientation,
            field_name="reader_document.orientation",
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
        )
    )
    return narrow_proposition, grounded_claim_ids


def _validate_v2_domain_map(
    document: dict[str, Any],
    *,
    narrow_proposition: bool,
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> tuple[set[str], list[str], list[tuple[str, str]], set[str]]:
    domain_map = _required_object(
        document.get("domain_map"), "reader_document.domain_map"
    )
    concepts = _required_list(
        domain_map.get("concepts"), "reader_document.domain_map.concepts"
    )
    concept_ids: set[str] = set()
    grounded_claim_ids: set[str] = set()
    for index, value in enumerate(concepts):
        field_name = f"reader_document.domain_map.concepts[{index}]"
        concept = _required_object(value, field_name)
        concept_id = _required_text(concept.get("id"), f"{field_name}.id")
        if concept_id in concept_ids:
            raise ReaderDocumentError(
                "reader_document.domain_map.concepts contains duplicate IDs"
            )
        concept_ids.add(concept_id)
        _required_text(concept.get("label"), f"{field_name}.label")
        _required_text(concept.get("definition"), f"{field_name}.definition")
        grounded_claim_ids.update(
            _validate_references(
                concept,
                field_name=field_name,
                claims_by_id=claims_by_id,
                evidence_by_id=evidence_by_id,
                allow_missing_evidence_ids=True,
                normalize_missing_evidence_ids=True,
            )
        )

    relationship_values = domain_map.get("relationships")
    if not isinstance(relationship_values, list):
        raise ReaderDocumentError(
            "reader_document.domain_map.relationships must be a list"
        )
    relationship_ids: set[str] = set()
    for index, value in enumerate(relationship_values):
        field_name = f"reader_document.domain_map.relationships[{index}]"
        relation = _required_object(value, field_name)
        relation_id = _required_text(relation.get("id"), f"{field_name}.id")
        if relation_id in relationship_ids:
            raise ReaderDocumentError(
                "reader_document.domain_map.relationships contains duplicate IDs"
            )
        relationship_ids.add(relation_id)
        relation_type = _required_text(relation.get("type"), f"{field_name}.type")
        if relation_type not in RELATIONSHIP_TYPES:
            raise ReaderDocumentError(
                f"{field_name}.type has invalid value {relation_type!r}; "
                f"expected {sorted(RELATIONSHIP_TYPES)}"
            )
        from_concept_id = _required_text(
            relation.get("from_concept_id"), f"{field_name}.from_concept_id"
        )
        to_concept_id = _required_text(
            relation.get("to_concept_id"), f"{field_name}.to_concept_id"
        )
        unknown_concepts = {from_concept_id, to_concept_id} - concept_ids
        if unknown_concepts:
            raise ReaderDocumentError(
                f"{field_name} references unknown concepts "
                f"{sorted(unknown_concepts)}"
            )
        condition = relation.get("condition")
        if condition is not None:
            _required_text(condition, f"{field_name}.condition")
        grounded_claim_ids.update(
            _validate_references(
                relation,
                field_name=field_name,
                claims_by_id=claims_by_id,
                evidence_by_id=evidence_by_id,
                allow_missing_evidence_ids=True,
                normalize_missing_evidence_ids=True,
            )
        )

    keystone_concept_ids = _validate_known_concepts(
        domain_map.get("keystone_concept_ids"),
        field_name="reader_document.domain_map.keystone_concept_ids",
        concept_ids=concept_ids,
    )
    minimum_keystones = 2 if narrow_proposition else 3
    if not minimum_keystones <= len(keystone_concept_ids) <= 7:
        raise ReaderDocumentError(
            "reader_document.domain_map.keystone_concept_ids must contain "
            f"between {minimum_keystones} and 7 concepts"
        )

    edge_values = domain_map.get("prerequisite_edges")
    if not isinstance(edge_values, list):
        raise ReaderDocumentError(
            "reader_document.domain_map.prerequisite_edges must be a list"
        )
    prerequisite_edges: list[tuple[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for index, value in enumerate(edge_values):
        field_name = f"reader_document.domain_map.prerequisite_edges[{index}]"
        edge = _required_object(value, field_name)
        before_id = _required_text(
            edge.get("before_concept_id"), f"{field_name}.before_concept_id"
        )
        after_id = _required_text(
            edge.get("after_concept_id"), f"{field_name}.after_concept_id"
        )
        unknown = {before_id, after_id} - concept_ids
        if unknown:
            raise ReaderDocumentError(
                f"{field_name} references unknown concepts {sorted(unknown)}"
            )
        if before_id == after_id:
            raise ReaderDocumentError(f"{field_name} cannot reference itself")
        edge_key = (before_id, after_id)
        if edge_key in seen_edges:
            raise ReaderDocumentError(
                "reader_document.domain_map.prerequisite_edges contains duplicates"
            )
        seen_edges.add(edge_key)
        prerequisite_edges.append(edge_key)
    _topological_concept_order(concept_ids, prerequisite_edges)

    variable_values = _required_list(
        domain_map.get("key_variables"),
        "reader_document.domain_map.key_variables",
    )
    variable_names: set[str] = set()
    for index, value in enumerate(variable_values):
        field_name = f"reader_document.domain_map.key_variables[{index}]"
        variable = _required_object(value, field_name)
        name = _required_text(variable.get("name"), f"{field_name}.name")
        if name in variable_names:
            raise ReaderDocumentError(
                "reader_document.domain_map.key_variables contains duplicate names"
            )
        variable_names.add(name)
        _validate_known_concepts(
            variable.get("concept_refs"),
            field_name=f"{field_name}.concept_refs",
            concept_ids=concept_ids,
        )
        _required_text(
            variable.get("change_direction"), f"{field_name}.change_direction"
        )
        _required_text(variable.get("effect"), f"{field_name}.effect")
        if not isinstance(variable.get("project_input_required"), bool):
            raise ReaderDocumentError(
                f"{field_name}.project_input_required must be boolean"
            )
        grounded_claim_ids.update(
            _validate_references(
                variable,
                field_name=field_name,
                claims_by_id=claims_by_id,
                evidence_by_id=evidence_by_id,
                allow_missing_evidence_ids=True,
                normalize_missing_evidence_ids=True,
            )
        )
    return (
        concept_ids,
        keystone_concept_ids,
        prerequisite_edges,
        grounded_claim_ids,
    )


def _validate_v2_sections(
    document: dict[str, Any],
    *,
    topic: TopicKnowledge,
    concept_ids: set[str],
    keystone_concept_ids: list[str],
    prerequisite_edges: list[tuple[str, str]],
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> set[str]:
    sections = _required_list(document.get("sections"), "reader_document.sections")
    section_ids: set[str] = set()
    represented_dimensions: set[str] = set()
    concept_section_indexes: dict[str, list[int]] = {}
    grounded_claim_ids: set[str] = set()
    for index, value in enumerate(sections):
        field_name = f"reader_document.sections[{index}]"
        section = _required_object(value, field_name)
        section_id = _required_text(section.get("id"), f"{field_name}.id")
        if section_id in section_ids:
            raise ReaderDocumentError("reader_document.sections contains duplicate IDs")
        section_ids.add(section_id)
        _required_text(section.get("heading"), f"{field_name}.heading")
        _required_text(
            section.get("cognitive_question"), f"{field_name}.cognitive_question"
        )
        section_concepts = _validate_known_concepts(
            section.get("concept_refs"),
            field_name=f"{field_name}.concept_refs",
            concept_ids=concept_ids,
        )
        for concept_id in section_concepts:
            concept_section_indexes.setdefault(concept_id, []).append(index)
        _text_list(section.get("paragraphs"), f"{field_name}.paragraphs", required=True)
        mechanism_chain = section.get("mechanism_chain")
        if set(section_concepts).intersection(keystone_concept_ids):
            if not isinstance(mechanism_chain, list) or len(mechanism_chain) != 4:
                raise ReaderDocumentError(
                    f"{field_name}.mechanism_chain must contain four steps "
                    "for a keystone concept"
                )
            _text_list(
                mechanism_chain, f"{field_name}.mechanism_chain", required=True
            )
        elif mechanism_chain is not None:
            if not isinstance(mechanism_chain, list) or len(mechanism_chain) != 4:
                raise ReaderDocumentError(
                    f"{field_name}.mechanism_chain must contain four steps"
                )
            _text_list(
                mechanism_chain, f"{field_name}.mechanism_chain", required=True
            )
        dimension_refs = _text_list(
            section.get("dimension_refs"),
            f"{field_name}.dimension_refs",
            required=True,
        )
        unknown_dimensions = set(dimension_refs) - set(topic.coverage_dimensions)
        if unknown_dimensions:
            raise ReaderDocumentError(
                f"{field_name} references unknown dimensions "
                f"{sorted(unknown_dimensions)}"
            )
        represented_dimensions.update(dimension_refs)
        grounded_claim_ids.update(
            _validate_references(
                section,
                field_name=field_name,
                claims_by_id=claims_by_id,
                evidence_by_id=evidence_by_id,
                allow_missing_evidence_ids=True,
                normalize_missing_evidence_ids=True,
            )
        )

    for keystone_id in keystone_concept_ids:
        if keystone_id not in concept_section_indexes:
            raise ReaderDocumentError(
                f"reader_document keystone concept {keystone_id!r} has no section"
            )
    for before_id, after_id in prerequisite_edges:
        before_indexes = concept_section_indexes.get(before_id, [])
        after_indexes = concept_section_indexes.get(after_id, [])
        if before_indexes and after_indexes and min(before_indexes) >= min(after_indexes):
            raise ReaderDocumentError(
                "reader_document.sections violates prerequisite order "
                f"{before_id!r} before {after_id!r}"
            )

    missing_dimensions = set(topic.coverage_dimensions) - represented_dimensions
    if missing_dimensions:
        raise ReaderDocumentError(
            "reader_document does not represent coverage dimensions "
            f"{sorted(missing_dimensions)}"
        )
    return grounded_claim_ids


def _validate_v2_transfer_guidance(
    document: dict[str, Any],
    *,
    concept_ids: set[str],
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> set[str]:
    transfer_guidance = _required_list(
        document.get("transfer_guidance"), "reader_document.transfer_guidance"
    )
    grounded_claim_ids: set[str] = set()
    for index, value in enumerate(transfer_guidance):
        field_name = f"reader_document.transfer_guidance[{index}]"
        item = _required_object(value, field_name)
        _required_text(item.get("prompt"), f"{field_name}.prompt")
        _required_text(item.get("reusable_model"), f"{field_name}.reusable_model")
        _text_list(item.get("reevaluate"), f"{field_name}.reevaluate", required=True)
        _validate_known_concepts(
            item.get("concept_refs"),
            field_name=f"{field_name}.concept_refs",
            concept_ids=concept_ids,
        )
        grounded_claim_ids.update(
            _validate_references(
                item,
                field_name=field_name,
                claims_by_id=claims_by_id,
                evidence_by_id=evidence_by_id,
                allow_missing_evidence_ids=True,
                normalize_missing_evidence_ids=True,
            )
        )
    return grounded_claim_ids


def _validate_v2_boundary_notes(
    document: dict[str, Any],
    *,
    gaps_by_id: dict[str, Any],
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> set[str]:
    boundary_notes = _required_list(
        document.get("boundary_notes"), "reader_document.boundary_notes"
    )
    grounded_claim_ids: set[str] = set()
    for index, value in enumerate(boundary_notes):
        field_name = f"reader_document.boundary_notes[{index}]"
        note = _required_object(value, field_name)
        boundary_type = _required_text(note.get("type"), f"{field_name}.type")
        if boundary_type not in BOUNDARY_TYPES:
            raise ReaderDocumentError(
                f"{field_name}.type has invalid value {boundary_type!r}; "
                f"expected {sorted(BOUNDARY_TYPES)}"
            )
        _required_text(note.get("text"), f"{field_name}.text")
        note_claim_ids = _validate_references(
            note,
            field_name=field_name,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
            allow_missing_evidence_ids=True,
            normalize_missing_evidence_ids=True,
        )
        grounded_claim_ids.update(note_claim_ids)
        _validate_open_gap_references(
            note.get("gap_ids", []),
            field_name=field_name,
            gaps_by_id=gaps_by_id,
            claims_by_id=claims_by_id,
            claim_ids=note_claim_ids,
        )
    return grounded_claim_ids


def _validate_v2_further_learning(
    document: dict[str, Any],
    *,
    gaps_by_id: dict[str, Any],
    claims_by_id: dict[str, Any],
    evidence_by_id: dict[str, Any],
) -> set[str]:
    further_learning = document.get("further_learning")
    if not isinstance(further_learning, list):
        raise ReaderDocumentError("reader_document.further_learning must be a list")
    grounded_claim_ids: set[str] = set()
    for index, value in enumerate(further_learning):
        field_name = f"reader_document.further_learning[{index}]"
        item = _required_object(value, field_name)
        _required_text(item.get("direction"), f"{field_name}.direction")
        further_claim_ids = _validate_references(
            item,
            field_name=field_name,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
            allow_missing_evidence_ids=True,
            normalize_missing_evidence_ids=True,
        )
        grounded_claim_ids.update(further_claim_ids)
        _validate_open_gap_references(
            item.get("gap_ids", []),
            field_name=field_name,
            gaps_by_id=gaps_by_id,
            claims_by_id=claims_by_id,
            claim_ids=further_claim_ids,
        )
    return grounded_claim_ids


def _validate_reader_document_v2(
    document: dict[str, Any],
    *,
    topic: TopicKnowledge,
) -> dict[str, object]:
    """Validate the schema-v2 cognitive reader document."""
    claims_by_id = {claim.id: claim for claim in topic.claims}
    evidence_by_id = {evidence.id: evidence for evidence in topic.evidence}
    gaps_by_id = {gap.id: gap for gap in topic.gaps}
    narrow_proposition, grounded_claim_ids = _validate_v2_orientation(
        document,
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
    )
    (
        concept_ids,
        keystone_concept_ids,
        prerequisite_edges,
        domain_map_claim_ids,
    ) = _validate_v2_domain_map(
        document,
        narrow_proposition=narrow_proposition,
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
    )
    grounded_claim_ids.update(domain_map_claim_ids)
    grounded_claim_ids.update(
        _validate_v2_sections(
            document,
            topic=topic,
            concept_ids=concept_ids,
            keystone_concept_ids=keystone_concept_ids,
            prerequisite_edges=prerequisite_edges,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
        )
    )

    synthesis_claim_ids = _validate_text_block(
        document.get("synthesis"),
        field_name="reader_document.synthesis",
        claims_by_id=claims_by_id,
        evidence_by_id=evidence_by_id,
    )
    if len(topic.coverage_dimensions) > 1:
        synthesis_dimensions = {
            claims_by_id[claim_id].dimension for claim_id in synthesis_claim_ids
        }
        if len(synthesis_dimensions) < 2:
            raise ReaderDocumentError(
                "reader_document.synthesis must reference claims from at least "
                "two coverage dimensions for a multi-dimension topic"
            )
    grounded_claim_ids.update(synthesis_claim_ids)
    grounded_claim_ids.update(
        _validate_v2_transfer_guidance(
            document,
            concept_ids=concept_ids,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
        )
    )
    grounded_claim_ids.update(
        _validate_v2_boundary_notes(
            document,
            gaps_by_id=gaps_by_id,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
        )
    )
    grounded_claim_ids.update(
        _validate_v2_further_learning(
            document,
            gaps_by_id=gaps_by_id,
            claims_by_id=claims_by_id,
            evidence_by_id=evidence_by_id,
        )
    )

    active_claim_ids = {
        claim.id for claim in topic.claims if claim.status == "active"
    }
    missing_active_claim_ids = active_claim_ids - grounded_claim_ids
    if missing_active_claim_ids:
        raise ReaderDocumentError(
            "reader_document does not reference active claims "
            f"{sorted(missing_active_claim_ids)}"
        )
    _validate_reader_visible_prose(document, field_name="reader_document")
    return document


def reader_document_from_dict(
    data: object,
    *,
    topic: TopicKnowledge,
    require_complete: bool,
) -> dict[str, object] | None:
    """Normalize and validate a reader document against a topic graph."""
    if data is None:
        if require_complete:
            raise ReaderDocumentError("reader_document is required")
        return None

    document = _json_object(data, "reader_document")
    schema_version = document.get("schema_version")
    if type(schema_version) is not int or schema_version not in {1, 2}:
        raise ReaderDocumentError(
            "reader_document.schema_version must be integer 1 or 2"
        )
    if schema_version == 1:
        return _validate_reader_document_v1(
            document,
            topic=topic,
        )
    return _validate_reader_document_v2(document, topic=topic)


def reader_document_to_dict(
    document: dict[str, object] | None,
) -> dict[str, object] | None:
    """Return a JSON-safe copy of a validated reader document."""
    if document is None:
        return None
    return _json_object(document, "reader_document")


def reader_document_ready(topic: TopicKnowledge) -> bool:
    """Return whether a topic carries a complete, valid reader document."""
    try:
        return (
            topic.reader_document is not None
            and reader_document_from_dict(
                topic.reader_document,
                topic=topic,
                require_complete=True,
            )
            is not None
        )
    except ReaderDocumentError:
        return False
