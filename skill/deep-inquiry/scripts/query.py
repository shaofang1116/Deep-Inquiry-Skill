"""Stateless projections over canonical durable topic knowledge."""

from __future__ import annotations

from typing import Any

from .knowledge_schema import ClaimStatus, GapStatus
from .knowledge_store import KnowledgeStore


class QueryError(ValueError):
    """A query request is structurally invalid."""


def query_knowledge(
    store: KnowledgeStore,
    topic_id: str,
    question: str,
) -> dict[str, Any]:
    """Read one current topic version without creating or mutating session state."""
    normalized_question = " ".join((question or "").split())
    if not normalized_question:
        raise QueryError("query question cannot be empty")

    topic = store.load(topic_id)
    claims = sorted(
        (
            claim
            for claim in topic.claims
            if claim.status == ClaimStatus.ACTIVE.value
        ),
        key=lambda claim: (claim.dimension, claim.kind, claim.id),
    )
    claim_ids = {claim.id for claim in claims}
    evidence = sorted(
        (
            item
            for item in topic.evidence
            if claim_ids.intersection(item.supports_claim_ids)
        ),
        key=lambda item: item.id,
    )
    unresolved_gaps = sorted(
        (
            gap
            for gap in topic.gaps
            if gap.status
            in {GapStatus.OPEN.value, GapStatus.DEFERRED.value}
        ),
        key=lambda gap: gap.id,
    )
    return {
        "status": "query_result",
        "query_mode": "stateless",
        "topic_id": topic.topic_id,
        "knowledge_version": topic.version,
        "question": normalized_question,
        "claims": [claim.to_dict() for claim in claims],
        "evidence": [item.to_dict() for item in evidence],
        "unresolved_gaps": [gap.to_dict() for gap in unresolved_gaps],
    }
