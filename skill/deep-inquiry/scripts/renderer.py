"""Deterministic human-readable projections of durable topic knowledge."""

from __future__ import annotations

import re

from .knowledge_schema import TopicKnowledge
from .reader_document import reader_document_ready


def _inline(value: str) -> str:
    """Keep durable text on one Markdown-safe line."""
    text = " ".join(value.split())
    for marker in ("\\", "`", "*", "_", "[", "]", "<", ">", "#", "|"):
        text = text.replace(marker, f"\\{marker}")
    if text.startswith(("- ", "+ ", "---")):
        text = f"\\{text}"
    text = re.sub(r"^([0-9]{1,9})([.)]) ", r"\1\\\2 ", text)
    return text


def _code(value: str) -> str:
    """Wrap an identifier in a code span that tolerates embedded backticks."""
    text = " ".join(value.split())
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    delimiter = "`" * (longest + 1)
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{delimiter}{padding}{text}{padding}{delimiter}"


def _refs(values: list[str]) -> str:
    return ", ".join(_code(value) for value in values) or "None"


def _paragraphs(
    values: list[object],
    source_numbers: dict[str, int],
    evidence_ids: list[object],
) -> list[str]:
    """Render reader paragraphs with compact source notes."""
    source_notes = _source_notes(evidence_ids, source_numbers)
    return [
        f"{_inline(value)}{source_notes}"
        for value in values
        if isinstance(value, str)
    ]


def _source_notes(
    evidence_ids: list[object],
    source_numbers: dict[str, int],
) -> str:
    numbers = [
        source_numbers[evidence_id]
        for evidence_id in evidence_ids
        if isinstance(evidence_id, str) and evidence_id in source_numbers
    ]
    return f" [{', '.join(str(number) for number in numbers)}]" if numbers else ""


def _reader_evidence_ids(document: dict[str, object]) -> list[str]:
    """Collect reader-document evidence IDs in displayed order."""
    blocks: list[object] = [
        document["overview"],
        *document["sections"],
        document["synthesis"],
        *document["application_guidance"],
        *document["boundary_notes"],
    ]
    evidence_ids: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        for evidence_id in block.get("evidence_ids", []):
            if isinstance(evidence_id, str) and evidence_id not in evidence_ids:
                evidence_ids.append(evidence_id)
    return evidence_ids


def _render_schema_v2_reader_report(topic: TopicKnowledge) -> bytes:
    """Render the reader-owned schema-v2 report projection."""
    if not reader_document_ready(topic):
        raise ValueError("schema version 2 topic requires a ready reader document")

    document = topic.reader_document
    if not isinstance(document, dict):
        raise ValueError("schema version 2 topic requires a ready reader document")
    evidence_by_id = {item.id: item for item in topic.evidence}
    evidence_ids = _reader_evidence_ids(document)
    source_numbers = {
        evidence_id: index
        for index, evidence_id in enumerate(evidence_ids, start=1)
    }

    overview = document["overview"]
    sections = document["sections"]
    synthesis = document["synthesis"]
    application_guidance = document["application_guidance"]
    boundary_notes = document["boundary_notes"]
    if not all(
        isinstance(value, list)
        for value in (sections, application_guidance, boundary_notes)
    ) or not all(
        isinstance(value, dict) for value in (overview, synthesis)
    ):
        raise ValueError("schema version 2 topic requires a ready reader document")

    lines = [f"# {_inline(topic.title)}", "", "## Overview", ""]
    lines.extend(
        _paragraphs(
            overview["paragraphs"], source_numbers, overview["evidence_ids"]
        )
    )
    for section in sections:
        if not isinstance(section, dict):
            continue
        lines.extend(["", f"## {_inline(section['heading'])}", ""])
        lines.extend(
            _paragraphs(
                section["paragraphs"],
                source_numbers,
                section["evidence_ids"],
            )
        )
        for point in section["key_points"]:
            lines.append(f"- {_inline(point)}")

    lines.extend(["", "## Synthesis", ""])
    lines.extend(
        _paragraphs(
            synthesis["paragraphs"], source_numbers, synthesis["evidence_ids"]
        )
    )
    lines.extend(["", "## Applying the Knowledge", ""])
    for guidance in application_guidance:
        if isinstance(guidance, dict):
            lines.append(
                f"- {_inline(guidance['text'])}"
                f"{_source_notes(guidance['evidence_ids'], source_numbers)}"
            )
    lines.extend(["", "## Boundaries and Uncertainty", ""])
    for note in boundary_notes:
        if isinstance(note, dict):
            lines.append(
                f"- {_inline(note['text'])}"
                f"{_source_notes(note.get('evidence_ids', []), source_numbers)}"
            )
    lines.extend(["", "## Sources", ""])
    for evidence_id in evidence_ids:
        lines.append(
            f"[{source_numbers[evidence_id]}] "
            f"{_inline(evidence_by_id[evidence_id].source)}"
        )
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _render_schema_v1_audit_compatibility(topic: TopicKnowledge) -> bytes:
    """Render the historical audit projection for schema-v1 topics only."""
    lines = [
        f"# {_inline(topic.title)}",
        "",
        f"- Topic ID: {_code(topic.topic_id)}",
        f"- Knowledge version: {topic.version}",
        f"- Updated at: {_code(topic.updated_at)}",
        "",
        "## Proposition",
        "",
        _inline(topic.proposition),
        "",
        "## Coverage Dimensions",
        "",
    ]
    lines.extend(
        f"- {_inline(dimension)}" for dimension in topic.coverage_dimensions
    )

    lines.extend(["", "## Knowledge by Dimension", ""])
    for dimension in topic.coverage_dimensions:
        lines.extend([f"### {_inline(dimension)}", ""])
        claims = sorted(
            (
                claim
                for claim in topic.claims
                if claim.dimension == dimension
            ),
            key=lambda claim: (claim.status, claim.id),
        )
        if not claims:
            lines.extend(["No claims recorded.", ""])
            continue
        for claim in claims:
            lines.extend(
                [
                    f"#### {_inline(claim.id)}",
                    "",
                    f"- Kind: {_code(claim.kind)}",
                    f"- Confidence: {_code(claim.confidence)}",
                    f"- Status: {_code(claim.status)}",
                    f"- Evidence: {_refs(claim.evidence_ids)}",
                    f"- Counterexamples: {_refs(claim.counterexample_ids)}",
                    f"- Related claims: {_refs(claim.related_claim_refs)}",
                    "",
                    _inline(claim.statement),
                    "",
                ]
            )

    lines.extend(["## Evidence", ""])
    if not topic.evidence:
        lines.extend(["No evidence recorded.", ""])
    for evidence in sorted(topic.evidence, key=lambda item: item.id):
        lines.extend(
            [
                f"- {_code(evidence.id)}: {_inline(evidence.source)}",
                f"  Supports: {_refs(evidence.supports_claim_ids)}",
            ]
        )

    lines.extend(["", "## Counterexamples", ""])
    if not topic.counterexamples:
        lines.extend(["No counterexamples recorded.", ""])
    for counterexample in sorted(
        topic.counterexamples, key=lambda item: item.id
    ):
        lines.extend(
            [
                f"- {_code(counterexample.id)}: "
                f"{_inline(counterexample.statement)}",
                f"  Challenges: {_refs(counterexample.claim_ids)}",
            ]
        )

    lines.extend(["", "## Knowledge Gaps", ""])
    if not topic.gaps:
        lines.extend(["No knowledge gaps recorded.", ""])
    for gap in sorted(topic.gaps, key=lambda item: item.id):
        lines.extend(
            [
                f"- {_code(gap.id)} [{_inline(gap.status)}, "
                f"{_inline(gap.priority)}]: {_inline(gap.question)}",
                f"  Dimension: {_code(gap.dimension)}",
                f"  Reason: {_inline(gap.reason)}",
                f"  Resolution claims: {_refs(gap.resolution_claim_ids)}",
            ]
        )
        if gap.defer_reason:
            lines.append(f"  Defer reason: {_inline(gap.defer_reason)}")

    lines.extend(["", "## Convergence History", ""])
    if not topic.convergence_history:
        lines.append("No convergence records.")
    for record in sorted(
        topic.convergence_history, key=lambda item: item.cycle
    ):
        delta = record.delta
        lines.extend(
            [
                f"### Cycle {record.cycle}",
                "",
                f"- Phase: {_code(record.phase)}",
                f"- Gain level: {_code(record.gain_level)}",
                f"- Skeptic structural hit: "
                f"{_code(str(record.skeptic_structural_hit).lower())}",
                f"- New claims: {_refs(delta.new_claim_ids)}",
                f"- Revised claims: {_refs(delta.revised_claim_ids)}",
                f"- Retired claims: {_refs(delta.retired_claim_ids)}",
                f"- New evidence: {_refs(delta.new_evidence_ids)}",
                f"- Resolved gaps: {_refs(delta.resolved_gap_ids)}",
                f"- New gaps: {_refs(delta.new_gap_ids)}",
                f"- Counterexample hits: {_refs(delta.counterexample_hits)}",
                "",
            ]
        )

    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def render_knowledge_report(topic: TopicKnowledge) -> bytes:
    """Render a deterministic reader report or schema-v1 audit compatibility."""
    topic.validate()
    if topic.schema_version == 1:
        return _render_schema_v1_audit_compatibility(topic)
    return _render_schema_v2_reader_report(topic)


def render_topic_summary(topic: TopicKnowledge, source_sha256: str) -> str:
    """Render a Markdown projection without creating new knowledge."""
    topic.validate()
    lines = [
        f"# {topic.title}",
        "",
        f"- Topic ID: `{topic.topic_id}`",
        f"- Version: {topic.version}",
        f"- Source SHA-256: `{source_sha256}`",
        "",
        "## Proposition",
        "",
        topic.proposition,
        "",
        "## Coverage Dimensions",
        "",
    ]
    if topic.coverage_dimensions:
        lines.extend(f"- {dimension}" for dimension in topic.coverage_dimensions)
    else:
        lines.append("- None")

    lines.extend(["", "## Claims", ""])
    if not topic.claims:
        lines.append("No claims recorded.")
    for claim in sorted(topic.claims, key=lambda item: item.id):
        lines.extend(
            [
                f"### {claim.id}",
                "",
                f"- Dimension: `{claim.dimension}`",
                f"- Kind: `{claim.kind}`",
                f"- Confidence: `{claim.confidence}`",
                f"- Status: `{claim.status}`",
                "",
                claim.statement,
            ]
        )
        if claim.evidence_ids:
            refs = ", ".join(f"`{item}`" for item in claim.evidence_ids)
            lines.append(f"- Evidence: {refs}")
        if claim.related_claim_refs:
            refs = ", ".join(
                f"`{item}`" for item in claim.related_claim_refs
            )
            lines.append(f"- Related claims: {refs}")
        lines.append("")

    lines.extend(["## Evidence", ""])
    if not topic.evidence:
        lines.append("No evidence recorded.")
    for evidence in sorted(topic.evidence, key=lambda item: item.id):
        supported = ", ".join(
            f"`{item}`" for item in evidence.supports_claim_ids
        )
        lines.append(f"- `{evidence.id}`: {evidence.source}")
        if supported:
            lines.append(f"  Supports: {supported}")

    lines.extend(["", "## Knowledge Gaps", ""])
    if not topic.gaps:
        lines.append("No knowledge gaps recorded.")
    for gap in sorted(topic.gaps, key=lambda item: item.id):
        lines.extend(
            [
                f"- `{gap.id}` [{gap.status}, {gap.priority}]: {gap.question}",
                f"  Reason: {gap.reason}",
            ]
        )

    lines.extend(["", "## Counterexamples", ""])
    if not topic.counterexamples:
        lines.append("No counterexamples recorded.")
    for counterexample in sorted(
        topic.counterexamples, key=lambda item: item.id
    ):
        claims = ", ".join(
            f"`{item}`" for item in counterexample.claim_ids
        )
        lines.append(f"- `{counterexample.id}`: {counterexample.statement}")
        if claims:
            lines.append(f"  Challenges: {claims}")

    return "\n".join(lines).rstrip() + "\n"
