"""Case fixtures and prose-varying scripted agents for vNext evaluation."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from typing import Any

EMPIRICAL_SOURCE = "https://doi.org/10.1038/nature23288"
EMPIRICAL_EXCERPT = (
    "In artificially illuminated plant–pollinator communities, nocturnal "
    "visits to plants were reduced by 62% compared to dark areas."
)
RETRIEVED_AT = "2026-09-17T00:00:00+00:00"


@dataclass(frozen=True)
class CaseSpec:
    title: str
    proposition: str
    dimension: str
    facets: dict[str, str]
    base_evidence: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    integration_source: str
    integration_prose: dict[str, str]
    source_receipts: list[dict[str, str]]


def _receipt(
    source: str,
    excerpt: str,
    citation: str,
) -> dict[str, str]:
    return {
        "source": source,
        "retrieved_at": RETRIEVED_AT,
        "excerpt": excerpt,
        "citation": citation,
        "sha256": hashlib.sha256(excerpt.encode("utf-8")).hexdigest(),
    }


def _base_evidence(case_id: str, sources: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"evidence-{index}",
            "source": source,
            "supports_claim_ids": [f"claim-{index}"],
        }
        for index, source in enumerate(sources, start=1)
    ]


def _gap(
    case_id: str,
    number: int,
    dimension: str,
    priority: str,
    expected_gain: str,
    question: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "id": f"{case_id}-gap-{number}",
        "question": question,
        "dimension": dimension,
        "priority": priority,
        "expected_gain": expected_gain,
        "reason": reason,
        "status": "open",
        "resolution_claim_ids": [],
        "defer_reason": "",
    }


CASE_SPECS = {
    "mechanism": CaseSpec(
        title="Battery thermal runaway",
        proposition="Thermal runaway is sustained by coupled exothermic reactions.",
        dimension="reaction-cascade",
        facets={
            "mechanism": (
                "Cell heating accelerates exothermic decomposition, which "
                "releases more heat and reinforces the reaction cascade."
            ),
            "condition": (
                "Runaway begins when internal heat generation exceeds heat "
                "dissipation after a triggering fault or temperature threshold."
            ),
            "boundary": (
                "Cell chemistry, state of charge, cooling, and pack isolation "
                "limit whether one-cell failure propagates."
            ),
            "synthesis": (
                "Thermal runaway is a positive heat-reaction feedback whose "
                "onset and propagation depend on cell and pack conditions."
            ),
        },
        base_evidence=_base_evidence(
            "mechanism",
            [
                "fixture:thermal-runaway/heat-feedback",
                "fixture:thermal-runaway/onset-threshold",
                "fixture:thermal-runaway/propagation-boundary",
                "fixture:thermal-runaway/system-synthesis",
            ],
        ),
        gaps=[
            _gap(
                "mechanism",
                1,
                "reaction-cascade",
                "high",
                "high",
                "Which observation links decomposition heat to accelerating cell temperature?",
                "The feedback mechanism needs a directly recorded observation.",
            ),
            _gap(
                "mechanism",
                2,
                "reaction-cascade",
                "high",
                "medium",
                "Which operating conditions move a cell past the onset threshold?",
                "The onset claim needs its triggering conditions bounded.",
            ),
            _gap(
                "mechanism",
                3,
                "reaction-cascade",
                "medium",
                "high",
                "When does a cell-level runaway fail to propagate through a pack?",
                "The synthesis needs a pack-level propagation boundary.",
            ),
        ],
        integration_source="fixture:thermal-runaway/recorded-observation",
        integration_prose={
            "concise": "Recorded heating data supports the positive feedback mechanism.",
            "elaborate": (
                "The recorded heating observation connects decomposition heat "
                "to accelerating temperature and therefore supports the "
                "positive feedback mechanism."
            ),
        },
        source_receipts=[
            _receipt(
                "fixture:thermal-runaway/recorded-observation",
                "Recorded cell heating accelerated after exothermic decomposition began.",
                "Task11 mechanism scripted fixture.",
            )
        ],
    ),
    "concept": CaseSpec(
        title="Statistical calibration",
        proposition="Calibration relates stated probabilities to observed frequencies.",
        dimension="probability-calibration",
        facets={
            "mechanism": (
                "Calibration groups comparable probability forecasts and "
                "compares each stated probability with its observed frequency."
            ),
            "condition": (
                "The comparison is meaningful over a sufficiently large, "
                "relevant set of forecasts and outcomes."
            ),
            "boundary": (
                "Calibration alone does not establish discrimination, causal "
                "validity, or accuracy for an individual prediction."
            ),
            "synthesis": (
                "A calibrated forecaster aligns probabilities with frequencies "
                "while requiring separate measures for sharpness and ranking."
            ),
        },
        base_evidence=_base_evidence(
            "concept",
            [
                "fixture:calibration/frequency-comparison",
                "fixture:calibration/reference-class",
                "fixture:calibration/non-equivalence",
                "fixture:calibration/system-synthesis",
            ],
        ),
        gaps=[
            _gap(
                "concept",
                1,
                "probability-calibration",
                "high",
                "high",
                "How does a reliability bin connect stated probability to outcome frequency?",
                "The operational meaning of calibration needs a recorded example.",
            ),
            _gap(
                "concept",
                2,
                "probability-calibration",
                "high",
                "medium",
                "Which reference-class assumptions make calibration estimates meaningful?",
                "The condition facet needs its sampling assumptions bounded.",
            ),
            _gap(
                "concept",
                3,
                "probability-calibration",
                "medium",
                "high",
                "How can a calibrated model still have poor discrimination?",
                "The concept needs a counter-boundary against ranking quality.",
            ),
        ],
        integration_source="fixture:calibration/recorded-observation",
        integration_prose={
            "concise": "Recorded reliability bins support the frequency interpretation.",
            "elaborate": (
                "The recorded reliability-bin observation shows how stated "
                "probabilities are evaluated against observed frequencies."
            ),
        },
        source_receipts=[
            _receipt(
                "fixture:calibration/recorded-observation",
                "Forecasts in the 0.7 bin were compared with their observed event frequency.",
                "Task11 concept scripted fixture.",
            )
        ],
    ),
    "controversy": CaseSpec(
        title="Remote work productivity",
        proposition="Remote work effects depend on task, coordination, and measurement.",
        dimension="work-design",
        facets={
            "mechanism": (
                "Remote work trades fewer office interruptions and commuting "
                "costs against higher coordination and information-transfer costs."
            ),
            "condition": (
                "Productivity effects vary with task interdependence, team "
                "routines, home environment, and evaluation horizon."
            ),
            "boundary": (
                "Output metrics can miss innovation, mentoring, and selection "
                "effects, so no single measure settles the controversy."
            ),
            "synthesis": (
                "Remote work has heterogeneous productivity effects determined "
                "by work design and by what the evaluation counts as output."
            ),
        },
        base_evidence=_base_evidence(
            "controversy",
            [
                "fixture:remote-work/productivity-mechanisms",
                "fixture:remote-work/moderating-conditions",
                "fixture:remote-work/measurement-boundary",
                "fixture:remote-work/conditional-synthesis",
            ],
        ),
        gaps=[
            _gap(
                "controversy",
                1,
                "work-design",
                "high",
                "high",
                "Which observation separates focus gains from coordination losses?",
                "The competing mechanisms need evidence in the same frame.",
            ),
            _gap(
                "controversy",
                2,
                "work-design",
                "high",
                "medium",
                "Which task and team conditions reverse the measured effect?",
                "The controversy cannot be summarized without moderators.",
            ),
            _gap(
                "controversy",
                3,
                "work-design",
                "medium",
                "high",
                "Which productivity measures omit delayed collaboration outcomes?",
                "The synthesis needs an explicit measurement boundary.",
            ),
        ],
        integration_source="fixture:remote-work/recorded-observation",
        integration_prose={
            "concise": "Recorded outcomes separate focus gains from coordination costs.",
            "elaborate": (
                "The recorded outcomes distinguish individual focus gains from "
                "the coordination costs that emerge in interdependent work."
            ),
        },
        source_receipts=[
            _receipt(
                "fixture:remote-work/recorded-observation",
                "Individual output rose while coordination time increased for interdependent work.",
                "Task11 controversy scripted fixture.",
            )
        ],
    ),
    "unfamiliar_empirical": CaseSpec(
        title="Nocturnal pollinator networks",
        proposition="Artificial light can alter nocturnal plant-pollinator interactions.",
        dimension="nocturnal-ecology",
        facets={
            "mechanism": (
                "Artificial night lighting suppresses nocturnal flower visits, "
                "reducing interactions within plant-pollinator networks."
            ),
            "condition": (
                "The reported contrast compares artificially illuminated "
                "plant-pollinator communities with dark communities at night."
            ),
            "boundary": (
                "One field comparison does not establish the same effect size "
                "for every light spectrum, habitat, plant, or pollinator taxon."
            ),
            "synthesis": (
                "Observed visit reduction supports network disruption under "
                "artificial light while leaving ecological generality bounded."
            ),
        },
        base_evidence=_base_evidence(
            "unfamiliar_empirical",
            [EMPIRICAL_SOURCE] * 4,
        ),
        gaps=[
            _gap(
                "unfamiliar_empirical",
                1,
                "nocturnal-ecology",
                "high",
                "high",
                "What measured visit difference was observed between illuminated and dark areas?",
                "The empirical mechanism needs a directly quoted result.",
            ),
            _gap(
                "unfamiliar_empirical",
                2,
                "nocturnal-ecology",
                "high",
                "medium",
                "Which community comparison defines the reported lighting condition?",
                "The exposure contrast must be explicit.",
            ),
            _gap(
                "unfamiliar_empirical",
                3,
                "nocturnal-ecology",
                "medium",
                "high",
                "Which taxa and lighting contexts remain outside this observation?",
                "The synthesis must not overgeneralize one field result.",
            ),
        ],
        integration_source=EMPIRICAL_SOURCE,
        integration_prose={
            "concise": "The recorded 62% visit reduction supports the light-effect claim.",
            "elaborate": (
                "The recorded comparison found 62% fewer nocturnal visits in "
                "illuminated communities, supporting the bounded light-effect claim."
            ),
        },
        source_receipts=[
            _receipt(
                EMPIRICAL_SOURCE,
                EMPIRICAL_EXCERPT,
                (
                    "Knop et al., Nature 548, 206–209 (2017), "
                    "DOI 10.1038/nature23288."
                ),
            )
        ],
    ),
}
PROFILE_IDS = ("concise", "elaborate")


def build_initial_topic(case_id: str) -> dict[str, Any]:
    """Build one semantic version-1 topic with three resolvable gaps."""
    spec = CASE_SPECS[case_id]
    claims = [
        {
            "id": f"claim-{index}",
            "dimension": spec.dimension,
            "kind": kind,
            "statement": statement,
            "confidence": "high",
            "evidence_ids": [f"evidence-{index}"],
            "counterexample_ids": [],
            "related_claim_refs": [],
            "status": "active",
            "introduced_version": 1,
            "updated_version": 1,
        }
        for index, (kind, statement) in enumerate(spec.facets.items(), start=1)
    ]
    return {
        "schema_version": 1,
        "topic_id": f"eval-vnext-{case_id}",
        "title": spec.title,
        "proposition": spec.proposition,
        "version": 1,
        "coverage_dimensions": [spec.dimension],
        "claims": claims,
        "evidence": deepcopy(spec.base_evidence),
        "gaps": deepcopy(spec.gaps),
        "counterexamples": [],
        "convergence_history": [],
        "created_at": RETRIEVED_AT,
        "updated_at": RETRIEVED_AT,
        "migration_metadata": {},
    }


def _empty_delta(**overrides: list[str]) -> dict[str, list[str]]:
    delta = {
        "new_claim_ids": [],
        "revised_claim_ids": [],
        "retired_claim_ids": [],
        "new_evidence_ids": [],
        "resolved_gap_ids": [],
        "new_gap_ids": [],
        "counterexample_hits": [],
    }
    delta.update(overrides)
    return delta


@dataclass
class ProfileAgent:
    """Return structurally identical responses with profile-specific prose."""

    case_id: str
    profile_id: str

    def __call__(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        if stage in {"anchor", "map_knowledge"}:
            return {"accepted": True}
        if stage == "plan_investigation":
            gap_id = context["selected_gap"]["id"]
            if self.profile_id == "concise":
                return {"plan": f"Resolve {gap_id} from the recorded evidence."}
            return {
                "plan": (
                    f"Examine the recorded material for {gap_id}, connect it "
                    "to the canonical claims, and resolve only that gap."
                )
            }
        if stage == "integrate_learning":
            return self._integration(context)
        if stage == "skeptic_review":
            return {"structural_hit": False}
        if stage == "assess_convergence":
            return self._assessment(context["topic"])
        raise AssertionError(f"unexpected agent stage: {stage}")

    def _integration(self, context: dict[str, Any]) -> dict[str, Any]:
        gap = context["selected_gap"]
        gap_number = int(gap["id"].rsplit("-", 1)[1])
        resolved = {
            **gap,
            "status": "resolved",
            "resolution_claim_ids": [f"claim-{gap_number}"],
        }
        if gap_number != 1:
            return {
                "delta": _empty_delta(resolved_gap_ids=[gap["id"]]),
                "claims": [],
                "evidence": [],
                "gaps": [resolved],
                "counterexamples": [],
                "phase": "post_baseline",
                "gain_level": "low",
            }

        evidence_id = f"{self.case_id}-external-evidence"
        current_claim = next(
            claim
            for claim in context["topic"]["claims"]
            if claim["id"] == "claim-1"
        )
        spec = CASE_SPECS[self.case_id]
        prose = spec.integration_prose[self.profile_id]
        revised_claim = {
            **current_claim,
            "statement": prose,
            "evidence_ids": [*current_claim["evidence_ids"], evidence_id],
        }
        evidence = {
            "id": evidence_id,
            "source": spec.integration_source,
            "supports_claim_ids": ["claim-1"],
        }
        return {
            "delta": _empty_delta(
                revised_claim_ids=["claim-1"],
                new_evidence_ids=[evidence_id],
                resolved_gap_ids=[gap["id"]],
            ),
            "claims": [revised_claim],
            "evidence": [evidence],
            "gaps": [resolved],
            "counterexamples": [],
            "phase": "post_baseline",
            "gain_level": "medium",
        }

    def _assessment(self, topic: dict[str, Any]) -> dict[str, Any]:
        open_ids = sorted(
            gap["id"]
            for gap in topic["gaps"]
            if gap["status"] == "open"
            and (
                gap["priority"] == "high"
                or gap["expected_gain"] == "high"
            )
        )
        if open_ids:
            reason = {
                "concise": "Recorded high-value gaps still require resolution.",
                "elaborate": (
                    "The canonical map still contains high-value gaps, so the "
                    "next bounded investigation remains justified."
                ),
            }[self.profile_id]
        else:
            reason = {
                "concise": (
                    "All structural gates pass and two recent cycles add only "
                    "low marginal value."
                ),
                "elaborate": (
                    "Every required facet is evidenced, no valuable gap "
                    "remains, and both latest post-baseline cycles show low gain."
                ),
            }[self.profile_id]
        return {
            "gain_level": topic["convergence_history"][-1]["gain_level"],
            "open_high_value_gap_ids": open_ids,
            "evidence_deficit_claim_ids": [],
            "structural_hit": False,
            "continue_learning": bool(open_ids),
            "reason": reason,
        }
