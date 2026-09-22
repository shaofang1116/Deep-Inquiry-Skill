"""Lifecycle policy for durable knowledge publication."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .knowledge_schema import PublicationRecord, PublicationState, TopicKnowledge
from .knowledge_store import KnowledgeStore, VersionConflictError
from .learner import Learner


@dataclass(frozen=True)
class PublicationOutcome:
    """The immutable terminal result of one publication candidate."""

    state: str
    record: PublicationRecord
    topic: TopicKnowledge | None
    rejection_code: str | None = None


class KnowledgePublisher:
    """Decide lifecycle transitions while delegating all durable I/O to store."""

    def __init__(self, store: KnowledgeStore, *, learner: Learner | None = None):
        self._store = store
        self._learner = learner or Learner()

    def publish_or_reject(
        self,
        *,
        topic_id: str,
        base_version: int,
        candidate: dict[str, object],
        review: dict[str, object],
        candidate_id: str,
    ) -> PublicationOutcome:
        """Record a proposed candidate and return its immutable terminal result."""
        existing = self._store.lifecycle_terminal(topic_id, candidate_id)
        if existing is not None:
            return self._outcome(*existing)
        current = self._store.load(topic_id)
        try:
            candidate_base = (
                self._store.load_version(topic_id, base_version)
                if current.version > base_version
                else current
            )
        except ValueError:
            candidate_base = current
        proposed = self._record(
            topic_id=topic_id,
            candidate_id=candidate_id,
            state=PublicationState.PROPOSED,
            base_version=base_version,
            delta=self._candidate_delta(candidate),
            integration=self._integration(candidate),
        )

        try:
            approved, structural_hit, reason = self._review_decision(review)
        except ValueError as exc:
            return self._reject(
                current=current,
                proposed=proposed,
                review=None,
                code="invalid_review",
                reason=str(exc),
            )

        reviewed = self._record(
            topic_id=topic_id,
            candidate_id=candidate_id,
            state=PublicationState.REVIEWED,
            base_version=base_version,
            delta=proposed.delta,
            integration=proposed.integration,
            review={"approved": approved, "structural_hit": structural_hit, "reason": reason},
        )
        if not approved or structural_hit:
            return self._reject(
                current=current,
                proposed=proposed,
                review=reviewed,
                code="skeptic_structural_hit",
                reason=reason,
            )

        try:
            next_topic = self._learner.build_knowledge_candidate(
                candidate_base, update=dict(candidate)
            )
        except (TypeError, ValueError) as exc:
            return self._reject(
                current=current,
                proposed=proposed,
                review=reviewed,
                code="invalid_candidate",
                reason=str(exc),
            )

        published = self._record(
            topic_id=topic_id,
            candidate_id=candidate_id,
            state=PublicationState.PUBLISHED,
            base_version=base_version,
            delta=proposed.delta,
            integration=proposed.integration,
            review=reviewed.review,
            published_version=next_topic.version,
        )
        try:
            saved, terminal = self._store.commit_lifecycle(
                topic_id,
                candidate_id=candidate_id,
                records=[proposed, reviewed, published],
                published_topic=next_topic,
            )
        except VersionConflictError as exc:
            return self._reject(
                current=self._store.load(topic_id),
                proposed=proposed,
                review=reviewed,
                code="version_conflict",
                reason=str(exc),
            )
        return self._outcome(saved, terminal)

    def retire(
        self,
        *,
        topic_id: str,
        base_version: int,
        claim_ids: list[str],
        candidate_id: str,
    ) -> PublicationOutcome:
        """Retire claims through the same immutable writer and audit journal."""
        current = self._store.load(topic_id)
        candidate = {
            "delta": {
                "new_claim_ids": [],
                "revised_claim_ids": [],
                "retired_claim_ids": list(claim_ids),
                "new_evidence_ids": [],
                "resolved_gap_ids": [],
                "new_gap_ids": [],
                "counterexample_hits": [],
            },
            "claims": [],
            "evidence": [],
            "gaps": [],
            "counterexamples": [],
            "cycle": (
                current.convergence_history[-1].cycle + 1
                if current.convergence_history
                else 1
            ),
            "phase": "post_baseline",
            "gain_level": "medium",
            "skeptic_structural_hit": False,
        }
        try:
            next_topic = self._learner.build_knowledge_candidate(
                current, update=candidate
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid retirement candidate: {exc}") from exc
        retired = self._record(
            topic_id=topic_id,
            candidate_id=candidate_id,
            state=PublicationState.RETIRED,
            base_version=base_version,
            delta=candidate["delta"],
            integration={"retired_claim_ids": list(claim_ids)},
            published_version=next_topic.version,
        )
        saved, terminal = self._store.commit_lifecycle(
            topic_id,
            candidate_id=candidate_id,
            records=[retired],
            published_topic=next_topic,
        )
        return self._outcome(saved, terminal)

    def _reject(
        self,
        *,
        current: TopicKnowledge,
        proposed: PublicationRecord,
        review: PublicationRecord | None,
        code: str,
        reason: str,
    ) -> PublicationOutcome:
        rejected = self._record(
            topic_id=proposed.topic_id,
            candidate_id=proposed.candidate_id,
            state=PublicationState.REJECTED,
            base_version=proposed.base_version,
            delta=proposed.delta,
            integration=proposed.integration,
            review=None if review is None else review.review,
            rejection={"code": code, "reason": self._safe_reason(reason)},
        )
        records = [proposed]
        if review is not None:
            records.append(review)
        records.append(rejected)
        saved, terminal = self._store.commit_lifecycle(
            proposed.topic_id,
            candidate_id=proposed.candidate_id,
            records=records,
        )
        return self._outcome(saved, terminal)

    @staticmethod
    def _record(
        *,
        topic_id: str,
        candidate_id: str,
        state: PublicationState,
        base_version: int,
        delta: dict[str, Any],
        integration: dict[str, Any],
        review: dict[str, Any] | None = None,
        rejection: dict[str, str] | None = None,
        published_version: int | None = None,
    ) -> PublicationRecord:
        return PublicationRecord(
            schema_version=1,
            record_id="pending",
            candidate_id=candidate_id,
            topic_id=topic_id,
            state=state.value,
            base_version=base_version,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            delta=delta,
            integration=integration,
            review=review,
            rejection=rejection,
            published_version=published_version,
        )

    @staticmethod
    def _candidate_delta(candidate: dict[str, object]) -> dict[str, Any]:
        delta = candidate.get("delta", {})
        return dict(delta) if isinstance(delta, dict) else {}

    @staticmethod
    def _integration(candidate: dict[str, object]) -> dict[str, Any]:
        return {
            str(key): value
            for key, value in candidate.items()
            if key not in {"delta", "claims", "evidence", "gaps", "counterexamples"}
        }

    @staticmethod
    def _review_decision(review: dict[str, object]) -> tuple[bool, bool, str]:
        approved = review.get("approved")
        structural_hit = review.get("structural_hit")
        reason = review.get("reason")
        if not isinstance(approved, bool) or not isinstance(structural_hit, bool):
            raise ValueError("review approval and structural_hit must be boolean")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("review reason must be a non-empty string")
        return approved, structural_hit, reason

    @staticmethod
    def _safe_reason(reason: str) -> str:
        return " ".join(reason.split())[:240] or "publication rejected"

    @staticmethod
    def _outcome(
        topic: TopicKnowledge, terminal: PublicationRecord
    ) -> PublicationOutcome:
        return PublicationOutcome(
            state=terminal.state,
            record=terminal,
            topic=(
                topic
                if terminal.state
                in {
                    PublicationState.PUBLISHED.value,
                    PublicationState.RETIRED.value,
                }
                else None
            ),
            rejection_code=(
                terminal.rejection["code"]
                if terminal.rejection is not None
                else None
            ),
        )
