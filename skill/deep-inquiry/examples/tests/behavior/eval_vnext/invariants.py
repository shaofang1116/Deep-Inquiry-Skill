"""Compute prose-independent invariants from a validated vNext replay."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


REQUIRED_FACETS = {"mechanism", "condition", "boundary", "synthesis"}
GAP_FACETS = {
    1: "mechanism",
    2: "condition",
    3: "boundary",
}
FORBIDDEN_STAGES = {
    "teach",
    "feedback",
    "assess_user",
    "plan_teaching",
    "teach_reply",
}
DELTA_FIELDS = (
    "new_claim_ids",
    "revised_claim_ids",
    "retired_claim_ids",
    "new_evidence_ids",
    "resolved_gap_ids",
    "new_gap_ids",
    "counterexample_hits",
)
GENERATED_ID_FIELDS = {
    "new_claim_ids",
    "new_evidence_ids",
    "new_gap_ids",
}
REQUIRED_CROSS_MODEL_CASES = {
    "mechanism",
    "concept",
    "controversy",
    "unfamiliar_empirical",
}


def compare_cross_model_artifacts(
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Replay and compare one complete raw-event capture per model and case."""
    from .artifacts import ArtifactValidationError, validate_artifact

    if len(artifacts) != 8:
        raise ArtifactValidationError(
            "cross-model comparison requires exactly 8 artifacts"
        )

    profiles: dict[str, dict[str, dict[str, Any]]] = {}
    sessions_by_model: dict[str, set[str]] = {}
    for artifact in artifacts:
        if artifact.get("artifact_origin") != "external_response_capture":
            raise ArtifactValidationError(
                "cross-model artifacts must use external_response_capture"
            )
        if artifact.get("collection_protocol") != "raw_events_v1":
            raise ArtifactValidationError(
                "cross-model artifacts must use raw_events_v1"
            )
        provenance = artifact.get("declared_provenance", {})
        model = provenance.get("model")
        session_label = provenance.get("session_label")
        if not isinstance(model, str) or not model.strip():
            raise ArtifactValidationError(
                "cross-model artifacts require a declared model"
            )
        if not isinstance(session_label, str) or not session_label.strip():
            raise ArtifactValidationError(
                "cross-model artifacts require a session_label"
            )
        case_id = artifact.get("case_id")
        if case_id not in REQUIRED_CROSS_MODEL_CASES:
            raise ArtifactValidationError(
                f"unexpected cross-model case {case_id!r}"
            )
        model_profiles = profiles.setdefault(model, {})
        if case_id in model_profiles:
            raise ArtifactValidationError(
                f"duplicate artifact for {model}/{case_id}"
            )
        report = validate_artifact(artifact)
        model_profiles[case_id] = normalize_cross_model_profile(
            report["invariant_profile"]
        )
        sessions_by_model.setdefault(model, set()).add(session_label)

    if len(profiles) != 2:
        raise ArtifactValidationError(
            "cross-model comparison requires exactly 2 distinct models"
        )
    session_labels = set().union(*sessions_by_model.values())
    if len(session_labels) != 2 or any(
        len(labels) != 1 for labels in sessions_by_model.values()
    ):
        raise ArtifactValidationError(
            "each model must use one distinct independent session_label"
        )
    for model, model_profiles in profiles.items():
        if set(model_profiles) != REQUIRED_CROSS_MODEL_CASES:
            raise ArtifactValidationError(
                f"{model} does not contain exactly the four required cases"
            )

    models = sorted(profiles)
    for case_id in sorted(REQUIRED_CROSS_MODEL_CASES):
        if profiles[models[0]][case_id] != profiles[models[1]][case_id]:
            raise ArtifactValidationError(
                f"normalized invariant mismatch for case {case_id}"
            )
    return {
        "status": "PASS",
        "models": models,
        "sessions": sorted(session_labels),
        "cases_compared": sorted(REQUIRED_CROSS_MODEL_CASES),
        "artifacts_replayed": len(artifacts),
        "normalization": (
            "generated claim, evidence, and gap identifiers compared by count; "
            "all convergence, stage, gain, revision, retirement, resolution, "
            "and counterexample fields compared exactly"
        ),
    }


def normalize_cross_model_profile(
    profile: dict[str, Any],
) -> dict[str, Any]:
    """Remove model-chosen entity names while preserving behavioral shape."""
    normalized = deepcopy(profile)
    for delta in normalized.get("delta_shapes", []):
        for field_name in GENERATED_ID_FIELDS:
            if field_name in delta:
                delta[field_name] = len(delta[field_name])
    if "new_evidence_ids" in normalized:
        normalized["new_evidence_count"] = len(
            normalized.pop("new_evidence_ids")
        )
    return normalized


def build_invariant_profile(
    artifact: dict[str, Any],
    replay: dict[str, Any],
) -> dict[str, Any]:
    """Assert required behavior and return only prose-independent values."""
    events = artifact["events"]
    result = replay["result"]
    final_topic = replay["final_topic"]
    integrations = [
        event["response"]
        for event in events
        if event["stage"] == "integrate_learning"
    ]
    assert len(integrations) >= 3, "evaluation must exercise multiple cycles"
    assert all(
        any(response["delta"][field] for field in DELTA_FIELDS)
        for response in integrations
    ), "every cycle must contain a non-empty delta"

    initial_topic_id = artifact["initial_topic"]["topic_id"]
    assert final_topic["topic_id"] == initial_topic_id
    assert result["topic_id"] == initial_topic_id
    assert final_topic["version"] == (
        artifact["initial_topic"]["version"] + len(integrations)
    )
    assert result["knowledge_version"] == final_topic["version"]
    assert result["delta_history"] == final_topic["convergence_history"]

    assess_codes = [
        event["reason_code"]
        for event in result["trace"]
        if event["stage"] == "assess_convergence"
    ]
    assert assess_codes[:2] == [
        "open_high_value_gap",
        "open_high_value_gap",
    ]
    assert assess_codes[-1] == "converged"

    history = final_topic["convergence_history"]
    assert len(history) == len(integrations)
    assert all(record["phase"] == "post_baseline" for record in history)
    assert [record["gain_level"] for record in history[-2:]] == ["low", "low"]
    assert not any(
        gap["status"] == "open"
        and (
            gap["priority"] == "high"
            or gap["expected_gain"] == "high"
        )
        for gap in final_topic["gaps"]
    )
    assert history[-1]["skeptic_structural_hit"] is False

    claims_by_id = {
        claim["id"]: claim for claim in final_topic["claims"]
    }
    for gap in final_topic["gaps"]:
        if gap["status"] != "resolved":
            continue
        gap_number = int(gap["id"].rsplit("-", 1)[1])
        expected_facet = GAP_FACETS[gap_number]
        resolution_facets = {
            claims_by_id[claim_id]["kind"]
            for claim_id in gap["resolution_claim_ids"]
        }
        assert resolution_facets == {expected_facet}, (
            f"{gap['id']} must resolve through {expected_facet}, "
            f"got {sorted(resolution_facets)}"
        )

    for dimension in final_topic["coverage_dimensions"]:
        facets = {
            claim["kind"]
            for claim in final_topic["claims"]
            if claim["dimension"] == dimension and claim["status"] == "active"
        }
        assert REQUIRED_FACETS <= facets
        syntheses = [
            claim
            for claim in final_topic["claims"]
            if claim["dimension"] == dimension
            and claim["kind"] == "synthesis"
            and claim["status"] == "active"
        ]
        assert any(claim["evidence_ids"] for claim in syntheses)

    event_stages = [event["stage"] for event in events]
    trace_stages = [event["stage"] for event in result["trace"]]
    assert not (FORBIDDEN_STAGES & set(event_stages))
    assert not (FORBIDDEN_STAGES & set(trace_stages))

    new_evidence_ids = {
        evidence_id
        for integration in integrations
        for evidence_id in integration["delta"]["new_evidence_ids"]
    }
    canonical_evidence = {
        evidence["id"]: evidence for evidence in final_topic["evidence"]
    }
    assert new_evidence_ids <= canonical_evidence.keys()
    if artifact["case_id"] == "unfamiliar_empirical":
        assert new_evidence_ids
        assert all(
            canonical_evidence[evidence_id]["source"].startswith(
                ("http://", "https://")
            )
            for evidence_id in new_evidence_ids
        )

    delta_shapes = [
        {
            field: tuple(response["delta"][field])
            for field in DELTA_FIELDS
        }
        for response in integrations
    ]
    return {
        "case_id": artifact["case_id"],
        "cycles": len(integrations),
        "agent_stage_sequence": event_stages,
        "assessment_codes": assess_codes,
        "gain_sequence": [
            record["gain_level"] for record in history
        ],
        "delta_shapes": delta_shapes,
        "final_version": final_topic["version"],
        "open_high_value_gap_count": 0,
        "latest_structural_hit": False,
        "required_facets_present": True,
        "new_evidence_ids": sorted(new_evidence_ids),
        "converged": result["convergence_reason"]["code"] == "converged",
    }
