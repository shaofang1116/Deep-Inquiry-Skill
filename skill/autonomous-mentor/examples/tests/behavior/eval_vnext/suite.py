"""Scripted-profile orchestration and negative checks for vNext artifacts."""

from __future__ import annotations

import argparse
from copy import deepcopy
import inspect
from pathlib import Path
import tempfile
from typing import Any

from .artifacts import (
    ArtifactValidationError,
    capture_artifact,
    finalize_external_capture,
    validate_artifact,
    write_artifact,
)
from .cases import (
    CASE_SPECS,
    EMPIRICAL_EXCERPT,
    EMPIRICAL_SOURCE,
    PROFILE_IDS,
    RETRIEVED_AT,
    ProfileAgent,
    build_initial_topic,
)
from .invariants import (
    compare_cross_model_artifacts,
    normalize_cross_model_profile,
)


def run_suite(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate scripted vNext profiles and validate them through the "
            "recorded-artifact replayer."
        )
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        help="keep generated scripted_profile artifacts in this directory",
    )
    args = parser.parse_args(argv)
    _assert_spec_contracts()
    _assert_cross_model_normalization()

    temporary = None
    artifact_dir = args.artifact_dir
    if artifact_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="mentor-vnext-suite-")
        artifact_dir = Path(temporary.name)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict[str, Any]] = []
    profiles_by_case: dict[str, list[dict[str, Any]]] = {}
    for case_id, spec in CASE_SPECS.items():
        for profile_id in PROFILE_IDS:
            initial_topic = build_initial_topic(case_id)
            artifact = capture_artifact(
                case_id=case_id,
                profile_id=profile_id,
                initial_topic=initial_topic,
                agent=ProfileAgent(case_id, profile_id),
                source_receipts=spec.source_receipts,
            )
            assert artifact["source_receipts"] == spec.source_receipts
            path = artifact_dir / f"{case_id}-{profile_id}.json"
            write_artifact(path, artifact)
            report = validate_artifact(artifact)
            artifacts.append(artifact)
            profiles_by_case.setdefault(case_id, []).append(
                report["invariant_profile"]
            )
            print(
                f"[PASS] scripted_profile {case_id}/{profile_id}: "
                f"{report['events_consumed']} recorded responses replayed"
            )

    for case_id, profiles in profiles_by_case.items():
        assert len(profiles) >= 2
        assert all(profile == profiles[0] for profile in profiles[1:])
        print(f"[PASS] {case_id}: prose profiles share one invariant profile")

    _assert_external_capture_finisher(artifacts[0])
    _assert_cross_model_gate(artifacts)
    _run_negative_checks(artifacts)
    print(
        "\nPASS: 4 case classes x 2 prose profiles; validation mode is "
        "recorded_artifact_replay."
    )
    print(
        "External model call attestation: NOT VERIFIED. Receipt hashes prove "
        "artifact-internal consistency, not remote authenticity."
    )
    if args.artifact_dir is not None:
        print(f"Artifacts: {artifact_dir}")
    if temporary is not None:
        temporary.cleanup()


def _assert_spec_contracts() -> None:
    failures = []
    required_facets = {"mechanism", "condition", "boundary", "synthesis"}
    inherited_terms = ("rainbow", "refraction", "droplet optics", "observer geometry")
    for case_id, spec in CASE_SPECS.items():
        topic = build_initial_topic(case_id)
        if not hasattr(spec, "facets"):
            failures.append(f"{case_id} has no canonical facets")
            continue
        if set(spec.facets) != required_facets:
            failures.append(f"{case_id} does not define exactly four canonical facets")
        actual_facets = {
            claim["kind"]: claim["statement"] for claim in topic["claims"]
        }
        if actual_facets != spec.facets:
            failures.append(f"{case_id} claims do not match canonical facets")
        if topic["evidence"] != spec.base_evidence:
            failures.append(f"{case_id} evidence is not case-specific")
        if topic["gaps"] != spec.gaps:
            failures.append(f"{case_id} gaps are not case-specific")
        serialized_topic = repr(topic).lower()
        if any(term in serialized_topic for term in inherited_terms):
            failures.append(f"{case_id} retains inherited rainbow semantics")
        receipt_sources = {
            receipt.get("source") for receipt in spec.source_receipts
        }
        if receipt_sources != {spec.integration_source}:
            failures.append(f"{case_id} receipts do not match new evidence source")
    parameters = inspect.signature(capture_artifact).parameters
    if "source_receipts" not in parameters:
        failures.append("capture_artifact does not require explicit source_receipts")
    elif parameters["source_receipts"].default is not inspect.Parameter.empty:
        failures.append("capture_artifact source_receipts must not have a default")
    empirical = CASE_SPECS["unfamiliar_empirical"]
    receipt = empirical.source_receipts[0]
    if empirical.integration_source != EMPIRICAL_SOURCE:
        failures.append("empirical new evidence does not use the frozen DOI")
    if receipt.get("source") != EMPIRICAL_SOURCE:
        failures.append("empirical receipt does not cover the frozen DOI")
    if receipt.get("excerpt") != EMPIRICAL_EXCERPT:
        failures.append("empirical receipt excerpt is not the frozen quotation")
    if receipt.get("retrieved_at") != RETRIEVED_AT:
        failures.append("empirical receipt retrieved_at is not frozen")
    if receipt.get("citation") != (
        "Knop et al., Nature 548, 206–209 (2017), "
        "DOI 10.1038/nature23288."
    ):
        failures.append("empirical receipt citation is not canonical")
    assert not failures, "; ".join(failures)


def _assert_cross_model_normalization() -> None:
    left = {
        "agent_stage_sequence": ["anchor", "assess_convergence"],
        "assessment_codes": ["open_high_value_gap", "converged"],
        "gain_sequence": ["medium", "low", "low"],
        "cycles": 3,
        "final_version": 4,
        "required_facets_present": True,
        "delta_shapes": [
            {
                "new_claim_ids": [],
                "new_evidence_ids": ["evidence-a"],
                "new_gap_ids": [],
                "counterexample_hits": [],
                "revised_claim_ids": ["claim-1"],
                "retired_claim_ids": [],
                "resolved_gap_ids": ["gap-1"],
            }
        ],
        "new_evidence_ids": ["evidence-a"],
    }
    right = deepcopy(left)
    right["delta_shapes"][0]["new_evidence_ids"] = ["evidence-b"]
    right["new_evidence_ids"] = ["evidence-b"]
    assert normalize_cross_model_profile(left) == normalize_cross_model_profile(
        right
    )

    left["delta_shapes"][0]["counterexample_hits"] = ["counterexample-a"]
    right["delta_shapes"][0]["counterexample_hits"] = ["counterexample-b"]
    assert normalize_cross_model_profile(left) != normalize_cross_model_profile(
        right
    ), "existing counterexample references must remain exact"

    for field_name, changed in (
        ("agent_stage_sequence", ["anchor", "skeptic_review"]),
        ("assessment_codes", ["converged"]),
        ("gain_sequence", ["low", "low"]),
        ("cycles", 2),
        ("final_version", 5),
        ("required_facets_present", False),
    ):
        candidate = deepcopy(left)
        candidate[field_name] = changed
        assert normalize_cross_model_profile(left) != (
            normalize_cross_model_profile(candidate)
        ), f"{field_name} must remain exact"

    for field_name in (
        "revised_claim_ids",
        "retired_claim_ids",
        "resolved_gap_ids",
    ):
        candidate = deepcopy(left)
        candidate["delta_shapes"][0][field_name] = ["different-id"]
        assert normalize_cross_model_profile(left) != (
            normalize_cross_model_profile(candidate)
        ), f"{field_name} must remain exact"


def _assert_cross_model_gate(
    scripted_artifacts: list[dict[str, Any]],
) -> None:
    external = deepcopy(scripted_artifacts)
    for artifact in external:
        model = f"model-{artifact['profile_id']}"
        artifact["artifact_origin"] = "external_response_capture"
        artifact["collection_protocol"] = "raw_events_v1"
        artifact["declared_provenance"] = {
            "host": "test-host",
            "model": model,
            "session_label": model,
            "time": "2026-09-17T00:00:00+00:00",
        }
    report = compare_cross_model_artifacts(external)
    assert report["status"] == "PASS"
    assert report["models"] == ["model-concise", "model-elaborate"]
    assert report["cases_compared"] == sorted(CASE_SPECS)

    _expect_cross_model_rejected(
        external[:4],
        "one model",
    )

    same_model = deepcopy(external)
    for artifact in same_model[4:]:
        artifact["declared_provenance"]["model"] = "model-concise"
    _expect_cross_model_rejected(same_model, "duplicate model declaration")

    missing_case = [
        artifact
        for artifact in external
        if not (
            artifact["declared_provenance"]["model"] == "model-elaborate"
            and artifact["case_id"] == "concept"
        )
    ]
    _expect_cross_model_rejected(missing_case, "missing model/case pair")

    mismatched = deepcopy(external)
    candidate = next(
        artifact
        for artifact in mismatched
        if artifact["declared_provenance"]["model"] == "model-elaborate"
        and artifact["case_id"] == "concept"
    )
    different_profile = next(
        artifact
        for artifact in external
        if artifact["declared_provenance"]["model"] == "model-elaborate"
        and artifact["case_id"] == "mechanism"
    )
    candidate.clear()
    candidate.update(deepcopy(different_profile))
    candidate["case_id"] = "concept"
    _expect_cross_model_rejected(mismatched, "invariant mismatch")

    scripted = deepcopy(external)
    scripted[0]["artifact_origin"] = "scripted_profile"
    _expect_cross_model_rejected(scripted, "scripted artifact")


def _assert_external_capture_finisher(
    scripted_artifact: dict[str, Any],
) -> None:
    raw_capture = {
        key: deepcopy(scripted_artifact[key])
        for key in (
            "schema_version",
            "declared_provenance",
            "case_id",
            "profile_id",
            "initial_topic",
            "events",
            "source_receipts",
        )
    }
    raw_capture["declared_provenance"] = {
        "host": "test-host",
        "model": "test-model",
        "session_label": "test-session",
        "time": "2026-09-17T00:00:00+00:00",
    }
    finalized = finalize_external_capture(raw_capture)
    assert finalized["artifact_origin"] == "external_response_capture"
    assert finalized["collection_protocol"] == "raw_events_v1"
    assert finalized["external_model_call_verified"] is False
    assert finalized["result"] == scripted_artifact["result"]
    assert validate_artifact(finalized)["status"] == "PASS"

    injected = deepcopy(raw_capture)
    injected["result"] = scripted_artifact["result"]
    try:
        finalize_external_capture(injected)
    except ArtifactValidationError:
        print("[PASS] raw-event finisher rejected injected result")
    else:
        raise AssertionError("raw-event finisher accepted injected result")


def _expect_cross_model_rejected(
    artifacts: list[dict[str, Any]],
    label: str,
) -> None:
    try:
        compare_cross_model_artifacts(artifacts)
    except (ArtifactValidationError, AssertionError, ValueError):
        print(f"[PASS] cross-model gate rejected {label}")
        return
    raise AssertionError(f"cross-model gate accepted {label}")


def _run_negative_checks(artifacts: list[dict[str, Any]]) -> None:
    empirical = next(
        artifact
        for artifact in artifacts
        if artifact["case_id"] == "unfamiliar_empirical"
    )
    bad_hash = deepcopy(empirical)
    bad_hash["source_receipts"][0]["sha256"] = "0" * 64
    _expect_rejected(bad_hash, "invalid receipt hash")

    missing_receipt = deepcopy(empirical)
    missing_receipt["source_receipts"] = []
    _expect_rejected(missing_receipt, "missing source receipt")

    mismatched_receipt = deepcopy(empirical)
    mismatched_receipt["source_receipts"][0]["source"] = (
        "https://doi.org/10.1038/not-the-recorded-source"
    )
    _expect_rejected(mismatched_receipt, "source/receipt mismatch")

    non_url = deepcopy(empirical)
    integration = next(
        event["response"]
        for event in non_url["events"]
        if event["stage"] == "integrate_learning"
        and event["response"]["delta"]["new_evidence_ids"]
    )
    integration["evidence"][0]["source"] = "local-unattested-note"
    _expect_rejected(non_url, "non-URL unfamiliar empirical evidence")

    teaching = deepcopy(artifacts[0])
    teaching["events"][0]["stage"] = "teach"
    _expect_rejected(teaching, "teaching stage")

    extra = deepcopy(artifacts[0])
    extra["events"].append(
        {"stage": "anchor", "response": {"accepted": True}}
    )
    _expect_rejected(extra, "unused extra response")

    truncated = deepcopy(artifacts[0])
    truncated["events"].pop()
    _expect_rejected(truncated, "missing response")


def _expect_rejected(artifact: dict[str, Any], label: str) -> None:
    try:
        validate_artifact(artifact)
    except (ArtifactValidationError, AssertionError, ValueError):
        print(f"[PASS] rejected {label}")
        return
    raise AssertionError(f"validator accepted {label}")
