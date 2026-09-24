"""Deterministic convergence policy for autonomous knowledge acquisition."""

from __future__ import annotations

from dataclasses import dataclass, field

from .failures import MAX_AUTONOMOUS_CYCLES
from .knowledge_schema import (
    ClaimKind,
    ClaimStatus,
    Confidence,
    ConvergenceAssessment,
    ConvergencePhase,
    GainLevel,
    GapStatus,
    Priority,
    TopicKnowledge,
)
from .reader_document import reader_document_ready


REQUIRED_FACETS = {
    ClaimKind.MECHANISM.value,
    ClaimKind.CONDITION.value,
    ClaimKind.BOUNDARY.value,
    ClaimKind.SYNTHESIS.value,
}


class ConvergencePolicyError(ValueError):
    """An agent assessment contradicts observable durable topic state."""


@dataclass(frozen=True)
class ConvergenceDecision:
    converged: bool
    reason_code: str
    reason: str
    checkpoint_required: bool = False
    blocking_ids: list[str] = field(default_factory=list)


def evaluate_convergence(
    topic: TopicKnowledge,
    assessment: ConvergenceAssessment,
) -> ConvergenceDecision:
    """Evaluate all stop conditions against canonical topic state."""
    topic.validate()
    assessment.validate()

    high_value_gaps = sorted(
        gap.id
        for gap in topic.gaps
        if gap.status == GapStatus.OPEN.value
        and (
            gap.priority == Priority.HIGH.value
            or gap.expected_gain == GainLevel.HIGH.value
        )
    )
    evidence_deficits = sorted(
        claim.id
        for claim in topic.claims
        if claim.status == ClaimStatus.ACTIVE.value
        and claim.confidence
        in {Confidence.MEDIUM.value, Confidence.HIGH.value}
        and not claim.evidence_ids
    )
    latest_structural_hit = bool(
        topic.convergence_history
        and topic.convergence_history[-1].skeptic_structural_hit
    )

    _require_assessment_match(
        "open high-value gaps",
        sorted(assessment.open_high_value_gap_ids),
        high_value_gaps,
    )
    _require_assessment_match(
        "evidence deficits",
        sorted(assessment.evidence_deficit_claim_ids),
        evidence_deficits,
    )
    if assessment.structural_hit != latest_structural_hit:
        raise ConvergencePolicyError(
            "assessment structural_hit does not match the latest skeptic record"
        )

    post_baseline = [
        record
        for record in topic.convergence_history
        if record.phase == ConvergencePhase.POST_BASELINE.value
    ]
    latest_two = post_baseline[-2:]
    for record in latest_two:
        if (
            record.gain_level == GainLevel.LOW.value
            and _contains_major_change(topic, record.delta)
        ):
            raise ConvergencePolicyError(
                f"cycle {record.cycle} is classified low gain but contains "
                "a major revision, retirement, counterexample, or "
                "high-priority gap"
            )

    if len(topic.convergence_history) >= MAX_AUTONOMOUS_CYCLES:
        return ConvergenceDecision(
            converged=False,
            reason_code="safety_checkpoint",
            reason=(
                f"Reached the safety limit of {MAX_AUTONOMOUS_CYCLES} "
                "knowledge cycles without satisfying convergence."
            ),
            checkpoint_required=True,
        )

    if not reader_document_ready(topic):
        return _blocked(
            "reader_document_not_ready",
            "Knowledge requires a complete reader document before convergence.",
        )

    missing_facets = _missing_facets(topic)
    if missing_facets:
        return _blocked(
            "missing_required_facet",
            "One or more coverage dimensions lack required active facets.",
            missing_facets,
        )
    if high_value_gaps:
        return _blocked(
            "open_high_value_gap",
            "High-priority or high-gain knowledge gaps remain open.",
            high_value_gaps,
        )
    if latest_structural_hit:
        return _blocked(
            "structural_hit",
            "The latest skeptic pass found an unresolved structural issue.",
        )
    if len(latest_two) < 2:
        return _blocked(
            "insufficient_marginal_trend",
            "Two post-baseline observations are required.",
        )
    if any(record.gain_level != GainLevel.LOW.value for record in latest_two):
        return _blocked(
            "gain_not_low",
            "The latest two post-baseline deltas are not both low gain.",
        )
    if evidence_deficits:
        return _blocked(
            "evidence_deficit",
            "Material active claims still lack evidence.",
            evidence_deficits,
        )
    if assessment.continue_learning:
        return _blocked(
            "agent_requests_continue",
            "The semantic assessment still recommends further learning.",
        )
    if not _specific_stop_reason(assessment.reason):
        return _blocked(
            "insufficient_stop_reason",
            "The stop reason must specifically justify lower expected value.",
        )
    return ConvergenceDecision(
        converged=True,
        reason_code="converged",
        reason=assessment.reason,
    )


def _missing_facets(topic: TopicKnowledge) -> list[str]:
    missing: list[str] = []
    for dimension in topic.coverage_dimensions:
        claims = [
            claim
            for claim in topic.claims
            if claim.dimension == dimension
            and claim.status == ClaimStatus.ACTIVE.value
        ]
        kinds = {claim.kind for claim in claims}
        for kind in sorted(REQUIRED_FACETS - kinds):
            missing.append(f"{dimension}#{kind}")
        synthesis = [
            claim
            for claim in claims
            if claim.kind == ClaimKind.SYNTHESIS.value
        ]
        if synthesis and not any(claim.evidence_ids for claim in synthesis):
            missing.append(f"{dimension}#evidence-backed-synthesis")
    return missing


def _contains_major_change(topic: TopicKnowledge, delta) -> bool:
    if (
        delta.revised_claim_ids
        or delta.retired_claim_ids
        or delta.counterexample_hits
    ):
        return True
    gaps = {gap.id: gap for gap in topic.gaps}
    return any(
        gap_id in gaps
        and (
            gaps[gap_id].priority == Priority.HIGH.value
            or gaps[gap_id].expected_gain == GainLevel.HIGH.value
        )
        for gap_id in delta.new_gap_ids
    )


def _specific_stop_reason(reason: str) -> bool:
    normalized = " ".join(reason.split())
    return len(normalized) >= 20 and normalized.lower() not in {
        "done",
        "complete",
        "converged",
        "no more work",
    }


def _require_assessment_match(
    label: str,
    reported: list[str],
    actual: list[str],
) -> None:
    if reported != actual:
        raise ConvergencePolicyError(
            f"assessment {label} do not match canonical state: "
            f"reported={reported}, actual={actual}"
        )


def _blocked(
    reason_code: str,
    reason: str,
    blocking_ids: list[str] | None = None,
) -> ConvergenceDecision:
    return ConvergenceDecision(
        converged=False,
        reason_code=reason_code,
        reason=reason,
        blocking_ids=list(blocking_ids or []),
    )
