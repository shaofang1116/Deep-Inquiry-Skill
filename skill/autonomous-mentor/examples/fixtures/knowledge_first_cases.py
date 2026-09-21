"""Reusable topic fixtures for the vNext knowledge-first acceptance checks."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


TOPIC_ID = "mechanism-of-rainbows"
DIMENSION = "optical-mechanism"


def complete_topic() -> dict[str, Any]:
    """Return a topic with every required facet backed by evidence."""
    evidence = [
        {
            "id": f"evidence-{index}",
            "source": f"https://example.test/rainbow/{index}",
            "supports_claim_ids": [f"claim-{index}"],
        }
        for index in range(1, 5)
    ]
    claims = [
        {
            "id": "claim-1",
            "dimension": DIMENSION,
            "kind": "mechanism",
            "statement": "Refraction and internal reflection separate wavelengths.",
            "confidence": "high",
            "evidence_ids": ["evidence-1"],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        },
        {
            "id": "claim-2",
            "dimension": DIMENSION,
            "kind": "condition",
            "statement": "Suspended droplets and a suitable viewing angle are required.",
            "confidence": "high",
            "evidence_ids": ["evidence-2"],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        },
        {
            "id": "claim-3",
            "dimension": DIMENSION,
            "kind": "boundary",
            "statement": "The apparent bow disappears outside the angular viewing range.",
            "confidence": "high",
            "evidence_ids": ["evidence-3"],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        },
        {
            "id": "claim-4",
            "dimension": DIMENSION,
            "kind": "synthesis",
            "statement": "Droplet optics and observer geometry jointly determine the bow.",
            "confidence": "high",
            "evidence_ids": ["evidence-4"],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        },
    ]
    return {
        "schema_version": 1,
        "topic_id": TOPIC_ID,
        "title": "Rainbow formation",
        "proposition": "A rainbow is an observer-dependent optical phenomenon.",
        "version": 3,
        "coverage_dimensions": [DIMENSION],
        "claims": claims,
        "evidence": evidence,
        "gaps": [],
        "counterexamples": [],
        "convergence_history": [],
        "created_at": "2026-09-17T00:00:00+00:00",
        "updated_at": "2026-09-17T00:02:00+00:00",
        "migration_metadata": {},
    }


def topic_with_open_high_value_gap() -> dict[str, Any]:
    topic = deepcopy(complete_topic())
    topic["gaps"] = [
        {
            "id": "gap-high-1",
            "question": "How do non-spherical droplets alter the observed bow?",
            "dimension": DIMENSION,
            "priority": "high",
            "expected_gain": "high",
            "reason": "The current synthesis assumes spherical droplets.",
            "status": "open",
            "resolution_claim_ids": [],
            "defer_reason": "",
        }
    ]
    return topic
