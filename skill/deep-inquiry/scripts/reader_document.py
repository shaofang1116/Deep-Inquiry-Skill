"""Canonical reader-document validation for durable topic knowledge."""

from __future__ import annotations

import json
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
) -> set[str]:
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
    if type(schema_version) is not int or schema_version != 1:
        raise ReaderDocumentError(
            "reader_document.schema_version must be integer 1"
        )

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
