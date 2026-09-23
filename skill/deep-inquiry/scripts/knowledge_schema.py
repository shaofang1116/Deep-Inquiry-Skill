"""Durable knowledge contracts for the knowledge-first vNext architecture."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from typing import Any, Iterable


class KnowledgeSchemaError(ValueError):
    """A durable knowledge object violates its data contract."""


class ClaimKind(str, Enum):
    MECHANISM = "mechanism"
    CONDITION = "condition"
    BOUNDARY = "boundary"
    RULE = "rule"
    SYNTHESIS = "synthesis"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ClaimStatus(str, Enum):
    ACTIVE = "active"
    DISPUTED = "disputed"
    RETIRED = "retired"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GapStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DEFERRED = "deferred"


class GainLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConvergencePhase(str, Enum):
    BASELINE = "baseline"
    POST_BASELINE = "post_baseline"


class PublicationState(str, Enum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    REJECTED = "rejected"
    RETIRED = "retired"


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeSchemaError(f"{field_name} must be a non-empty string")
    return value


def _enum_value(value: Any, enum_type: type[Enum], field_name: str) -> str:
    raw = value.value if isinstance(value, enum_type) else value
    allowed = {member.value for member in enum_type}
    if not isinstance(raw, str) or raw not in allowed:
        raise KnowledgeSchemaError(
            f"{field_name} has invalid value {value!r}; expected {sorted(allowed)}"
        )
    return raw


def _json_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise KnowledgeSchemaError(f"{field_name} must be an object")
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        decoded = json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise KnowledgeSchemaError(
            f"{field_name} must contain JSON-compatible values"
        ) from exc
    if not isinstance(decoded, dict):
        raise KnowledgeSchemaError(f"{field_name} must be an object")
    return decoded


def _string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise KnowledgeSchemaError(f"{field_name} must be a list")
    result: list[str] = []
    for item in value:
        result.append(_required_text(item, f"{field_name} item"))
    if len(result) != len(set(result)):
        raise KnowledgeSchemaError(f"{field_name} contains duplicate values")
    return result


def _claim_ref_list(value: Any, field_name: str) -> list[str]:
    result = _string_list(value, field_name)
    for item in result:
        topic_id, separator, claim_id = item.partition("#")
        if (
            separator != "#"
            or not topic_id
            or not claim_id
            or "#" in claim_id
        ):
            raise KnowledgeSchemaError(
                f"{field_name} item {item!r} must use topic_id#claim_id"
            )
    return result


def _int_at_least(value: Any, minimum: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise KnowledgeSchemaError(
            f"{field_name} must be an integer greater than or equal to {minimum}"
        )
    return value


def _assert_unique_ids(items: Iterable[Any], collection_name: str) -> None:
    identifiers = [item.id for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise KnowledgeSchemaError(f"{collection_name} contains duplicate IDs")


def _metadata_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise KnowledgeSchemaError(f"{field_name} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise KnowledgeSchemaError(f"{field_name} keys must be strings")
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise KnowledgeSchemaError(
            f"{field_name} must contain JSON-compatible values"
        ) from exc
    return json.loads(encoded)


@dataclass
class Claim:
    id: str
    dimension: str
    kind: str
    statement: str
    confidence: str
    evidence_ids: list[str] = field(default_factory=list)
    counterexample_ids: list[str] = field(default_factory=list)
    related_claim_refs: list[str] = field(default_factory=list)
    status: str = ClaimStatus.ACTIVE.value
    introduced_version: int = 1
    updated_version: int = 1

    def validate(self) -> None:
        self.id = _required_text(self.id, "claim.id")
        self.dimension = _required_text(self.dimension, "claim.dimension")
        self.kind = _enum_value(self.kind, ClaimKind, "claim.kind")
        self.statement = _required_text(self.statement, "claim.statement")
        self.confidence = _enum_value(
            self.confidence, Confidence, "claim.confidence"
        )
        self.status = _enum_value(self.status, ClaimStatus, "claim.status")
        self.evidence_ids = _string_list(
            self.evidence_ids, "claim.evidence_ids"
        )
        self.counterexample_ids = _string_list(
            self.counterexample_ids, "claim.counterexample_ids"
        )
        self.related_claim_refs = _claim_ref_list(
            self.related_claim_refs, "claim.related_claim_refs"
        )
        self.introduced_version = _int_at_least(
            self.introduced_version, 1, "claim.introduced_version"
        )
        self.updated_version = _int_at_least(
            self.updated_version, self.introduced_version, "claim.updated_version"
        )
        if self.confidence == Confidence.HIGH.value and not self.evidence_ids:
            raise KnowledgeSchemaError(
                f"high-confidence claim {self.id!r} requires evidence"
            )
        if (
            self.status == ClaimStatus.DISPUTED.value
            and not self.counterexample_ids
        ):
            raise KnowledgeSchemaError(
                f"disputed claim {self.id!r} requires a counterexample"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "dimension": self.dimension,
            "kind": self.kind,
            "statement": self.statement,
            "confidence": self.confidence,
            "evidence_ids": list(self.evidence_ids),
            "counterexample_ids": list(self.counterexample_ids),
            "related_claim_refs": list(self.related_claim_refs),
            "status": self.status,
            "introduced_version": self.introduced_version,
            "updated_version": self.updated_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Claim":
        claim = cls(
            id=data.get("id", ""),
            dimension=data.get("dimension", ""),
            kind=data.get("kind", ""),
            statement=data.get("statement", ""),
            confidence=data.get("confidence", ""),
            evidence_ids=list(data.get("evidence_ids", [])),
            counterexample_ids=list(data.get("counterexample_ids", [])),
            related_claim_refs=list(data.get("related_claim_refs", [])),
            status=data.get("status", ClaimStatus.ACTIVE.value),
            introduced_version=data.get("introduced_version", 1),
            updated_version=data.get("updated_version", 1),
        )
        claim.validate()
        return claim


@dataclass
class Evidence:
    id: str
    source: str
    supports_claim_ids: list[str] = field(default_factory=list)

    def validate(self) -> None:
        self.id = _required_text(self.id, "evidence.id")
        self.source = _required_text(self.source, "evidence.source")
        self.supports_claim_ids = _string_list(
            self.supports_claim_ids, "evidence.supports_claim_ids"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "supports_claim_ids": list(self.supports_claim_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        evidence = cls(
            id=data.get("id", ""),
            source=data.get("source", ""),
            supports_claim_ids=list(data.get("supports_claim_ids", [])),
        )
        evidence.validate()
        return evidence


@dataclass
class KnowledgeGap:
    id: str
    question: str
    dimension: str
    priority: str
    expected_gain: str
    reason: str
    status: str = GapStatus.OPEN.value
    resolution_claim_ids: list[str] = field(default_factory=list)
    defer_reason: str = ""

    def validate(self) -> None:
        self.id = _required_text(self.id, "gap.id")
        self.question = _required_text(self.question, "gap.question")
        self.dimension = _required_text(self.dimension, "gap.dimension")
        self.priority = _enum_value(self.priority, Priority, "gap.priority")
        self.expected_gain = _enum_value(
            self.expected_gain, GainLevel, "gap.expected_gain"
        )
        self.reason = _required_text(self.reason, "gap.reason")
        self.status = _enum_value(self.status, GapStatus, "gap.status")
        self.resolution_claim_ids = _string_list(
            self.resolution_claim_ids, "gap.resolution_claim_ids"
        )
        if self.status == GapStatus.RESOLVED.value and not self.resolution_claim_ids:
            raise KnowledgeSchemaError(
                f"resolved gap {self.id!r} requires resolution claims"
            )
        if self.status == GapStatus.DEFERRED.value and not self.defer_reason.strip():
            raise KnowledgeSchemaError(
                f"deferred gap {self.id!r} requires a defer reason"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "dimension": self.dimension,
            "priority": self.priority,
            "expected_gain": self.expected_gain,
            "reason": self.reason,
            "status": self.status,
            "resolution_claim_ids": list(self.resolution_claim_ids),
            "defer_reason": self.defer_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KnowledgeGap":
        gap = cls(
            id=data.get("id", ""),
            question=data.get("question", ""),
            dimension=data.get("dimension", ""),
            priority=data.get("priority", ""),
            expected_gain=data.get("expected_gain", ""),
            reason=data.get("reason", ""),
            status=data.get("status", GapStatus.OPEN.value),
            resolution_claim_ids=list(data.get("resolution_claim_ids", [])),
            defer_reason=data.get("defer_reason", ""),
        )
        gap.validate()
        return gap


@dataclass
class Counterexample:
    id: str
    statement: str
    claim_ids: list[str] = field(default_factory=list)

    def validate(self) -> None:
        self.id = _required_text(self.id, "counterexample.id")
        self.statement = _required_text(
            self.statement, "counterexample.statement"
        )
        self.claim_ids = _string_list(
            self.claim_ids, "counterexample.claim_ids"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "statement": self.statement,
            "claim_ids": list(self.claim_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Counterexample":
        counterexample = cls(
            id=data.get("id", ""),
            statement=data.get("statement", ""),
            claim_ids=list(data.get("claim_ids", [])),
        )
        counterexample.validate()
        return counterexample


@dataclass
class LearningDelta:
    new_claim_ids: list[str] = field(default_factory=list)
    revised_claim_ids: list[str] = field(default_factory=list)
    retired_claim_ids: list[str] = field(default_factory=list)
    new_evidence_ids: list[str] = field(default_factory=list)
    resolved_gap_ids: list[str] = field(default_factory=list)
    new_gap_ids: list[str] = field(default_factory=list)
    counterexample_hits: list[str] = field(default_factory=list)

    def validate(self) -> None:
        for field_name in (
            "new_claim_ids",
            "revised_claim_ids",
            "retired_claim_ids",
            "new_evidence_ids",
            "resolved_gap_ids",
            "new_gap_ids",
            "counterexample_hits",
        ):
            setattr(
                self,
                field_name,
                _string_list(getattr(self, field_name), f"delta.{field_name}"),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_claim_ids": list(self.new_claim_ids),
            "revised_claim_ids": list(self.revised_claim_ids),
            "retired_claim_ids": list(self.retired_claim_ids),
            "new_evidence_ids": list(self.new_evidence_ids),
            "resolved_gap_ids": list(self.resolved_gap_ids),
            "new_gap_ids": list(self.new_gap_ids),
            "counterexample_hits": list(self.counterexample_hits),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearningDelta":
        delta = cls(
            new_claim_ids=list(data.get("new_claim_ids", [])),
            revised_claim_ids=list(data.get("revised_claim_ids", [])),
            retired_claim_ids=list(data.get("retired_claim_ids", [])),
            new_evidence_ids=list(data.get("new_evidence_ids", [])),
            resolved_gap_ids=list(data.get("resolved_gap_ids", [])),
            new_gap_ids=list(data.get("new_gap_ids", [])),
            counterexample_hits=list(data.get("counterexample_hits", [])),
        )
        delta.validate()
        return delta


@dataclass
class ConvergenceRecord:
    cycle: int
    phase: str
    delta: LearningDelta
    gain_level: str
    skeptic_structural_hit: bool

    def validate(self) -> None:
        self.cycle = _int_at_least(self.cycle, 1, "convergence_record.cycle")
        self.phase = _enum_value(
            self.phase, ConvergencePhase, "convergence_record.phase"
        )
        self.delta.validate()
        self.gain_level = _enum_value(
            self.gain_level, GainLevel, "convergence_record.gain_level"
        )
        if not isinstance(self.skeptic_structural_hit, bool):
            raise KnowledgeSchemaError(
                "convergence_record.skeptic_structural_hit must be boolean"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "phase": self.phase,
            "delta": self.delta.to_dict(),
            "gain_level": self.gain_level,
            "skeptic_structural_hit": self.skeptic_structural_hit,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConvergenceRecord":
        record = cls(
            cycle=data.get("cycle", 0),
            phase=data.get("phase", ""),
            delta=LearningDelta.from_dict(data.get("delta", {})),
            gain_level=data.get("gain_level", ""),
            skeptic_structural_hit=data.get("skeptic_structural_hit", False),
        )
        record.validate()
        return record


@dataclass
class ConvergenceAssessment:
    gain_level: str
    open_high_value_gap_ids: list[str]
    evidence_deficit_claim_ids: list[str]
    structural_hit: bool
    continue_learning: bool
    reason: str

    def validate(self) -> None:
        self.gain_level = _enum_value(
            self.gain_level, GainLevel, "assessment.gain_level"
        )
        self.open_high_value_gap_ids = _string_list(
            self.open_high_value_gap_ids,
            "assessment.open_high_value_gap_ids",
        )
        self.evidence_deficit_claim_ids = _string_list(
            self.evidence_deficit_claim_ids,
            "assessment.evidence_deficit_claim_ids",
        )
        if not isinstance(self.structural_hit, bool):
            raise KnowledgeSchemaError("assessment.structural_hit must be boolean")
        if not isinstance(self.continue_learning, bool):
            raise KnowledgeSchemaError(
                "assessment.continue_learning must be boolean"
            )
        self.reason = _required_text(self.reason, "assessment.reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "gain_level": self.gain_level,
            "open_high_value_gap_ids": list(self.open_high_value_gap_ids),
            "evidence_deficit_claim_ids": list(
                self.evidence_deficit_claim_ids
            ),
            "structural_hit": self.structural_hit,
            "continue_learning": self.continue_learning,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConvergenceAssessment":
        assessment = cls(
            gain_level=data.get("gain_level", ""),
            open_high_value_gap_ids=list(
                data.get("open_high_value_gap_ids", [])
            ),
            evidence_deficit_claim_ids=list(
                data.get("evidence_deficit_claim_ids", [])
            ),
            structural_hit=data.get("structural_hit", False),
            continue_learning=data.get("continue_learning", True),
            reason=data.get("reason", ""),
        )
        assessment.validate()
        return assessment


@dataclass
class PublicationRecord:
    schema_version: int
    record_id: str
    candidate_id: str
    topic_id: str
    state: str
    base_version: int
    created_at: str
    delta: dict[str, Any]
    integration: dict[str, Any]
    review: dict[str, Any] | None
    rejection: dict[str, str] | None
    published_version: int | None

    def validate(self) -> None:
        self.schema_version = _int_at_least(
            self.schema_version, 1, "publication_record.schema_version"
        )
        self.record_id = _required_text(
            self.record_id, "publication_record.record_id"
        )
        self.candidate_id = _required_text(
            self.candidate_id, "publication_record.candidate_id"
        )
        self.topic_id = _required_text(
            self.topic_id, "publication_record.topic_id"
        )
        self.state = _enum_value(
            self.state, PublicationState, "publication_record.state"
        )
        self.base_version = _int_at_least(
            self.base_version, 1, "publication_record.base_version"
        )
        self.created_at = _required_text(
            self.created_at, "publication_record.created_at"
        )
        self.delta = _json_object(self.delta, "publication_record.delta")
        self.integration = _json_object(
            self.integration, "publication_record.integration"
        )
        if self.review is not None:
            self.review = _json_object(
                self.review, "publication_record.review"
            )
        if self.rejection is not None:
            self.rejection = _json_object(
                self.rejection, "publication_record.rejection"
            )
            code = self.rejection.get("code")
            reason = self.rejection.get("reason")
            if not isinstance(code, str) or not code.strip():
                raise KnowledgeSchemaError(
                    "publication_record.rejection.code must be non-empty"
                )
            if not isinstance(reason, str) or not reason.strip():
                raise KnowledgeSchemaError(
                    "publication_record.rejection.reason must be non-empty"
                )
        if self.published_version is not None:
            self.published_version = _int_at_least(
                self.published_version,
                1,
                "publication_record.published_version",
            )

        if self.state == PublicationState.PROPOSED.value:
            if self.review is not None or self.rejection is not None:
                raise KnowledgeSchemaError(
                    "proposed record cannot contain review or rejection"
                )
        elif self.state == PublicationState.REVIEWED.value:
            if self.review is None or self.rejection is not None:
                raise KnowledgeSchemaError(
                    "reviewed record requires review and no rejection"
                )
        elif self.state == PublicationState.PUBLISHED.value:
            if self.review is None or self.published_version is None:
                raise KnowledgeSchemaError(
                    "published record requires review and published_version"
                )
            if self.rejection is not None:
                raise KnowledgeSchemaError(
                    "published record cannot contain rejection"
                )
        elif self.state == PublicationState.REJECTED.value:
            if self.rejection is None or self.published_version is not None:
                raise KnowledgeSchemaError(
                    "rejected record requires rejection and no published_version"
                )
        elif self.state == PublicationState.RETIRED.value:
            if self.published_version is None:
                raise KnowledgeSchemaError(
                    "retired record requires published_version"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "record_id": self.record_id,
            "candidate_id": self.candidate_id,
            "topic_id": self.topic_id,
            "state": self.state,
            "base_version": self.base_version,
            "created_at": self.created_at,
            "delta": dict(self.delta),
            "integration": dict(self.integration),
            "review": None if self.review is None else dict(self.review),
            "rejection": (
                None if self.rejection is None else dict(self.rejection)
            ),
            "published_version": self.published_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PublicationRecord":
        record = cls(
            schema_version=data.get("schema_version", 0),
            record_id=data.get("record_id", ""),
            candidate_id=data.get("candidate_id", ""),
            topic_id=data.get("topic_id", ""),
            state=data.get("state", ""),
            base_version=data.get("base_version", 0),
            created_at=data.get("created_at", ""),
            delta=data.get("delta", {}),
            integration=data.get("integration", {}),
            review=data.get("review"),
            rejection=data.get("rejection"),
            published_version=data.get("published_version"),
        )
        record.validate()
        return record


@dataclass
class TopicKnowledge:
    schema_version: int
    topic_id: str
    title: str
    proposition: str
    version: int
    coverage_dimensions: list[str]
    claims: list[Claim]
    evidence: list[Evidence]
    gaps: list[KnowledgeGap]
    counterexamples: list[Counterexample]
    convergence_history: list[ConvergenceRecord]
    created_at: str
    updated_at: str
    migration_metadata: dict[str, Any] = field(default_factory=dict)
    origin_metadata: dict[str, Any] | None = None

    def validate(self) -> None:
        self.schema_version = _int_at_least(
            self.schema_version, 1, "topic.schema_version"
        )
        self.topic_id = _required_text(self.topic_id, "topic.topic_id")
        self.title = _required_text(self.title, "topic.title")
        self.proposition = _required_text(
            self.proposition, "topic.proposition"
        )
        self.version = _int_at_least(self.version, 1, "topic.version")
        self.coverage_dimensions = _string_list(
            self.coverage_dimensions, "topic.coverage_dimensions"
        )
        self.created_at = _required_text(self.created_at, "topic.created_at")
        self.updated_at = _required_text(self.updated_at, "topic.updated_at")
        self.migration_metadata = _metadata_object(
            self.migration_metadata, "topic.migration_metadata"
        )
        if self.origin_metadata is not None:
            self.origin_metadata = _metadata_object(
                self.origin_metadata, "topic.origin_metadata"
            )

        for item in self.claims:
            item.validate()
        for item in self.evidence:
            item.validate()
        for item in self.gaps:
            item.validate()
        for item in self.counterexamples:
            item.validate()
        for item in self.convergence_history:
            item.validate()

        _assert_unique_ids(self.claims, "claims")
        _assert_unique_ids(self.evidence, "evidence")
        _assert_unique_ids(self.gaps, "gaps")
        _assert_unique_ids(self.counterexamples, "counterexamples")
        all_ids = [
            *(item.id for item in self.claims),
            *(item.id for item in self.evidence),
            *(item.id for item in self.gaps),
            *(item.id for item in self.counterexamples),
        ]
        if len(all_ids) != len(set(all_ids)):
            raise KnowledgeSchemaError("topic contains duplicate entity IDs")

        dimension_ids = set(self.coverage_dimensions)
        claim_ids = {item.id for item in self.claims}
        evidence_ids = {item.id for item in self.evidence}
        gap_ids = {item.id for item in self.gaps}
        counterexample_ids = {item.id for item in self.counterexamples}
        claims_by_id = {item.id: item for item in self.claims}
        evidence_by_id = {item.id: item for item in self.evidence}
        counterexamples_by_id = {
            item.id: item for item in self.counterexamples
        }

        for claim in self.claims:
            if claim.dimension not in dimension_ids:
                raise KnowledgeSchemaError(
                    f"claim {claim.id!r} references unknown dimension "
                    f"{claim.dimension!r}"
                )
            for evidence_id in claim.evidence_ids:
                if evidence_id not in evidence_ids:
                    raise KnowledgeSchemaError(
                        f"claim {claim.id!r} references missing evidence "
                        f"{evidence_id!r}"
                    )
                if claim.id not in evidence_by_id[evidence_id].supports_claim_ids:
                    raise KnowledgeSchemaError(
                        f"claim {claim.id!r} and evidence {evidence_id!r} "
                        "must reference each other"
                    )
            for counterexample_id in claim.counterexample_ids:
                if counterexample_id not in counterexample_ids:
                    raise KnowledgeSchemaError(
                        f"claim {claim.id!r} references missing counterexample "
                        f"{counterexample_id!r}"
                    )
                if claim.id not in counterexamples_by_id[counterexample_id].claim_ids:
                    raise KnowledgeSchemaError(
                        f"claim {claim.id!r} and counterexample "
                        f"{counterexample_id!r} must reference each other"
                    )

        for evidence_item in self.evidence:
            for claim_id in evidence_item.supports_claim_ids:
                if claim_id not in claim_ids:
                    raise KnowledgeSchemaError(
                        f"evidence {evidence_item.id!r} references missing claim "
                        f"{claim_id!r}"
                    )
                if evidence_item.id not in claims_by_id[claim_id].evidence_ids:
                    raise KnowledgeSchemaError(
                        f"evidence {evidence_item.id!r} and claim {claim_id!r} "
                        "must reference each other"
                    )

        for counterexample in self.counterexamples:
            for claim_id in counterexample.claim_ids:
                if claim_id not in claim_ids:
                    raise KnowledgeSchemaError(
                        f"counterexample {counterexample.id!r} references "
                        f"missing claim {claim_id!r}"
                    )

        for gap in self.gaps:
            if gap.dimension not in dimension_ids:
                raise KnowledgeSchemaError(
                    f"gap {gap.id!r} references unknown dimension "
                    f"{gap.dimension!r}"
                )
            missing_claims = set(gap.resolution_claim_ids) - claim_ids
            if missing_claims:
                raise KnowledgeSchemaError(
                    f"gap {gap.id!r} references missing resolution claims "
                    f"{sorted(missing_claims)}"
                )

        cycles = [record.cycle for record in self.convergence_history]
        if len(cycles) != len(set(cycles)):
            raise KnowledgeSchemaError(
                "convergence_history contains duplicate cycle numbers"
            )
        if cycles != sorted(cycles):
            raise KnowledgeSchemaError(
                "convergence_history cycles must be increasing"
            )
        for record in self.convergence_history:
            delta = record.delta
            self._validate_delta_references(
                delta, claim_ids, evidence_ids, gap_ids, counterexample_ids
            )

    @staticmethod
    def _validate_delta_references(
        delta: LearningDelta,
        claim_ids: set[str],
        evidence_ids: set[str],
        gap_ids: set[str],
        counterexample_ids: set[str],
    ) -> None:
        checks = (
            ("claim", delta.new_claim_ids, claim_ids),
            ("claim", delta.revised_claim_ids, claim_ids),
            ("claim", delta.retired_claim_ids, claim_ids),
            ("evidence", delta.new_evidence_ids, evidence_ids),
            ("gap", delta.resolved_gap_ids, gap_ids),
            ("gap", delta.new_gap_ids, gap_ids),
            ("counterexample", delta.counterexample_hits, counterexample_ids),
        )
        for entity_name, identifiers, available in checks:
            missing = set(identifiers) - available
            if missing:
                raise KnowledgeSchemaError(
                    f"learning delta references missing {entity_name} IDs "
                    f"{sorted(missing)}"
                )

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "topic_id": self.topic_id,
            "title": self.title,
            "proposition": self.proposition,
            "version": self.version,
            "coverage_dimensions": list(self.coverage_dimensions),
            "claims": [item.to_dict() for item in self.claims],
            "evidence": [item.to_dict() for item in self.evidence],
            "gaps": [item.to_dict() for item in self.gaps],
            "counterexamples": [
                item.to_dict() for item in self.counterexamples
            ],
            "convergence_history": [
                item.to_dict() for item in self.convergence_history
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "migration_metadata": dict(self.migration_metadata),
        }
        if self.origin_metadata is not None:
            payload["origin_metadata"] = dict(self.origin_metadata)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopicKnowledge":
        topic = cls(
            schema_version=data.get("schema_version", 1),
            topic_id=data.get("topic_id", ""),
            title=data.get("title", ""),
            proposition=data.get("proposition", ""),
            version=data.get("version", 0),
            coverage_dimensions=list(data.get("coverage_dimensions", [])),
            claims=[Claim.from_dict(item) for item in data.get("claims", [])],
            evidence=[
                Evidence.from_dict(item) for item in data.get("evidence", [])
            ],
            gaps=[
                KnowledgeGap.from_dict(item) for item in data.get("gaps", [])
            ],
            counterexamples=[
                Counterexample.from_dict(item)
                for item in data.get("counterexamples", [])
            ],
            convergence_history=[
                ConvergenceRecord.from_dict(item)
                for item in data.get("convergence_history", [])
            ],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            migration_metadata=data.get("migration_metadata", {}),
            origin_metadata=data.get("origin_metadata"),
        )
        topic.validate()
        return topic
