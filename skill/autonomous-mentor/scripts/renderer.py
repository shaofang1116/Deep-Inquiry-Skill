"""Deterministic human-readable projections of durable topic knowledge."""

from __future__ import annotations

from .knowledge_schema import TopicKnowledge


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
