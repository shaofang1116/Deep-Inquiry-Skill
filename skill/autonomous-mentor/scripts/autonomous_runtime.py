"""Validated runtime references for resumable vNext host execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from typing import Any
import uuid

from .judgments import (
    JudgmentError,
    JudgmentRequest,
    build_autonomous_request,
    build_initialize_topic_request,
    validate_autonomous_response,
    validate_initialize_topic_response,
)
from .knowledge_schema import ConvergenceAssessment, KnowledgeSchemaError, TopicKnowledge
from .knowledge_store import KnowledgeStore, KnowledgeStoreError
from .learner import Learner
from .convergence import evaluate_convergence


HOST_RUN_KIND = "vnext_host_run"
PENDING_CURSOR_KIND = "vnext_host_pending"
RUNTIME_SCHEMA_VERSION = 1
RUN_STATUSES = {"active", "complete", "cancelled"}
PENDING_STAGES = {
    "initialize_topic",
    "map_knowledge",
    "plan_investigation",
    "integrate_learning",
    "skeptic_review",
    "commit_learning",
    "assess_convergence",
    "checkpoint_or_complete",
}
FORBIDDEN_PAYLOAD_KEYS = {
    "topic",
    "knowledge",
    "claims",
    "evidence",
    "gaps",
    "counterexamples",
    "convergence_history",
}


class RuntimeContractError(ValueError):
    """A host run or pending cursor violates the vNext runtime contract."""


def _required_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeContractError(f"{name} must be a non-empty string")
    return value


def _topic_id(value: Any) -> str:
    topic_id = _required_text(value, "topic_id")
    if (
        topic_id in {".", ".."}
        or os.path.basename(topic_id) != topic_id
        or "/" in topic_id
        or "\\" in topic_id
    ):
        raise RuntimeContractError(f"invalid topic_id {topic_id!r}")
    return topic_id


def _knowledge_root(value: Any) -> str:
    root = _required_text(value, "knowledge_root")
    if not os.path.isabs(root):
        raise RuntimeContractError("knowledge_root must be absolute")
    resolved = os.path.realpath(os.path.abspath(os.path.expanduser(root)))
    if root != resolved:
        raise RuntimeContractError(
            "knowledge_root must be canonical absolute path"
        )
    return resolved


def _run_id(value: Any) -> str:
    raw = _required_text(value, "run_id")
    try:
        parsed = uuid.UUID(raw)
    except (AttributeError, ValueError) as exc:
        raise RuntimeContractError("run_id must be a UUID") from exc
    if str(parsed) != raw:
        raise RuntimeContractError("run_id must use canonical UUID form")
    return raw


def _version(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeContractError(f"{name} must be a non-negative integer")
    return value


def _timestamp(value: Any, name: str) -> str:
    raw = _required_text(value, name)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RuntimeContractError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise RuntimeContractError(f"{name} must include a timezone")
    return raw


def _payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeContractError("payload must be an object")
    forbidden = FORBIDDEN_PAYLOAD_KEYS & set(value)
    if forbidden:
        raise RuntimeContractError(
            "payload must not contain a full topic graph: "
            f"{sorted(forbidden)}"
        )
    try:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise RuntimeContractError(
            "payload must contain JSON-compatible values"
        ) from exc
    return json.loads(encoded)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HostRun:
    schema_version: int
    runtime_kind: str
    run_id: str
    topic_id: str
    knowledge_root: str
    base_version: int
    status: str
    created_at: str
    updated_at: str

    @classmethod
    def new(
        cls,
        *,
        topic_id: str,
        knowledge_root: str,
        base_version: int = 0,
    ) -> "HostRun":
        now = _now()
        run = cls(
            schema_version=RUNTIME_SCHEMA_VERSION,
            runtime_kind=HOST_RUN_KIND,
            run_id=str(uuid.uuid4()),
            topic_id=topic_id,
            knowledge_root=knowledge_root,
            base_version=base_version,
            status="active",
            created_at=now,
            updated_at=now,
        )
        run.validate()
        return run

    def validate(self) -> None:
        if self.schema_version != RUNTIME_SCHEMA_VERSION:
            raise RuntimeContractError(
                f"unsupported runtime schema_version {self.schema_version!r}"
            )
        if self.runtime_kind != HOST_RUN_KIND:
            raise RuntimeContractError(
                f"runtime_kind must be {HOST_RUN_KIND!r}"
            )
        self.run_id = _run_id(self.run_id)
        self.topic_id = _topic_id(self.topic_id)
        self.knowledge_root = _knowledge_root(self.knowledge_root)
        self.base_version = _version(self.base_version, "base_version")
        if self.status not in RUN_STATUSES:
            raise RuntimeContractError(
                f"status must be one of {sorted(RUN_STATUSES)}"
            )
        self.created_at = _timestamp(self.created_at, "created_at")
        self.updated_at = _timestamp(self.updated_at, "updated_at")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "runtime_kind": self.runtime_kind,
            "run_id": self.run_id,
            "topic_id": self.topic_id,
            "knowledge_root": self.knowledge_root,
            "base_version": self.base_version,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HostRun":
        run = cls(
            schema_version=data.get("schema_version"),
            runtime_kind=data.get("runtime_kind"),
            run_id=data.get("run_id"),
            topic_id=data.get("topic_id"),
            knowledge_root=data.get("knowledge_root"),
            base_version=data.get("base_version"),
            status=data.get("status"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
        run.validate()
        return run


@dataclass
class PendingCursor:
    schema_version: int
    runtime_kind: str
    run_id: str
    topic_id: str
    knowledge_root: str
    stage: str
    expected_version: int
    commit_marker: str | None
    payload: dict[str, Any]

    @classmethod
    def initialize_topic(
        cls,
        run: HostRun,
        *,
        proposition: str,
    ) -> "PendingCursor":
        run.validate()
        cursor = cls(
            schema_version=RUNTIME_SCHEMA_VERSION,
            runtime_kind=PENDING_CURSOR_KIND,
            run_id=run.run_id,
            topic_id=run.topic_id,
            knowledge_root=run.knowledge_root,
            stage="initialize_topic",
            expected_version=run.base_version,
            commit_marker=None,
            payload={"proposition": proposition},
        )
        cursor.validate()
        return cursor

    def validate(self) -> None:
        if self.schema_version != RUNTIME_SCHEMA_VERSION:
            raise RuntimeContractError(
                f"unsupported cursor schema_version {self.schema_version!r}"
            )
        if self.runtime_kind != PENDING_CURSOR_KIND:
            raise RuntimeContractError(
                f"runtime_kind must be {PENDING_CURSOR_KIND!r}"
            )
        self.run_id = _run_id(self.run_id)
        self.topic_id = _topic_id(self.topic_id)
        self.knowledge_root = _knowledge_root(self.knowledge_root)
        if self.stage not in PENDING_STAGES:
            raise RuntimeContractError(
                f"unknown pending stage {self.stage!r}"
            )
        self.expected_version = _version(
            self.expected_version, "expected_version"
        )
        if self.commit_marker is not None:
            self.commit_marker = _required_text(
                self.commit_marker, "commit_marker"
            )
        self.payload = _payload(self.payload)
        if self.stage == "initialize_topic":
            proposition = self.payload.get("proposition")
            if not isinstance(proposition, str) or not proposition.strip():
                raise RuntimeContractError(
                    "initialize_topic payload requires proposition"
                )
            if set(self.payload) != {"proposition"}:
                raise RuntimeContractError(
                    "initialize_topic payload may contain only proposition"
                )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "runtime_kind": self.runtime_kind,
            "run_id": self.run_id,
            "topic_id": self.topic_id,
            "knowledge_root": self.knowledge_root,
            "stage": self.stage,
            "expected_version": self.expected_version,
            "commit_marker": self.commit_marker,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PendingCursor":
        cursor = cls(
            schema_version=data.get("schema_version"),
            runtime_kind=data.get("runtime_kind"),
            run_id=data.get("run_id"),
            topic_id=data.get("topic_id"),
            knowledge_root=data.get("knowledge_root"),
            stage=data.get("stage"),
            expected_version=data.get("expected_version"),
            commit_marker=data.get("commit_marker"),
            payload=data.get("payload"),
        )
        cursor.validate()
        return cursor


class HostRuntimeCoordinator:
    """Own resumable vNext stage transitions without becoming a durable writer."""

    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.learner = Learner()

    def begin_initialization(
        self,
        run: HostRun,
        *,
        proposition: str,
    ) -> PendingCursor:
        self._validate_store_root(run)
        return PendingCursor.initialize_topic(run, proposition=proposition)

    def initialization_request(self, cursor: PendingCursor) -> JudgmentRequest:
        cursor.validate()
        if cursor.stage != "initialize_topic":
            raise RuntimeContractError(
                "initialization request requires initialize_topic cursor"
            )
        return build_initialize_topic_request(
            topic_id=cursor.topic_id,
            proposition=cursor.payload["proposition"],
        )

    def initialize_topic(
        self,
        cursor: PendingCursor,
        response: Any,
    ) -> TopicKnowledge:
        cursor.validate()
        if cursor.stage != "initialize_topic":
            raise RuntimeContractError(
                "initialize_topic requires initialize_topic cursor"
            )
        self._validate_store_root_from_cursor(cursor)
        try:
            seed = validate_initialize_topic_response(response)
            now = _now()
            topic = TopicKnowledge.from_dict(
                {
                    "schema_version": 1,
                    "topic_id": cursor.topic_id,
                    "title": seed["title"],
                    "proposition": seed["proposition"],
                    "version": 1,
                    "coverage_dimensions": seed["coverage_dimensions"],
                    "claims": seed["claims"],
                    "evidence": seed["evidence"],
                    "gaps": seed["gaps"],
                    "counterexamples": seed["counterexamples"],
                    "convergence_history": [],
                    "created_at": now,
                    "updated_at": now,
                    "migration_metadata": {},
                    "origin_metadata": {"host_run_id": cursor.run_id},
                }
            )
        except (JudgmentError, KnowledgeSchemaError, TypeError, ValueError) as exc:
            raise RuntimeContractError(
                f"invalid initialization response: {exc}"
            ) from exc
        try:
            return self.store.create(topic)
        except KnowledgeStoreError as exc:
            try:
                existing = self.store.load(cursor.topic_id)
            except KnowledgeStoreError:
                raise exc
            if (
                existing.version == 1
                and existing.origin_metadata == {"host_run_id": cursor.run_id}
            ):
                return existing
            raise RuntimeContractError(
                "unrelated existing topic cannot be overwritten"
            ) from exc

    def begin_learning(self, run: HostRun) -> PendingCursor:
        """Project the first autonomous judgment from canonical topic state."""
        self._validate_store_root(run)
        topic = self.store.load(run.topic_id)
        if topic.version != run.base_version:
            raise RuntimeContractError(
                "host run base_version does not match canonical topic"
            )
        return self._cursor(
            run,
            stage="map_knowledge",
            expected_version=topic.version,
            payload={"cycle": self._next_cycle(topic)},
        )

    def learning_request(self, cursor: PendingCursor) -> JudgmentRequest:
        """Build exactly one host request from a durable pending cursor."""
        cursor.validate()
        if cursor.stage not in {
            "map_knowledge",
            "plan_investigation",
            "integrate_learning",
            "skeptic_review",
            "assess_convergence",
        }:
            raise RuntimeContractError(
                f"stage {cursor.stage!r} does not require an agent judgment"
            )
        self._validate_store_root_from_cursor(cursor)
        topic = self.store.load(cursor.topic_id)
        if topic.version != cursor.expected_version:
            raise RuntimeContractError(
                "pending cursor expected_version does not match canonical topic"
            )
        return build_autonomous_request(
            cursor.stage,
            topic,
            self._request_context(cursor.payload),
        )

    def advance_learning(
        self,
        cursor: PendingCursor,
        response: Any,
    ) -> PendingCursor:
        """Validate one response and write the next uncommitted stage cursor."""
        cursor.validate()
        if cursor.stage not in {
            "map_knowledge",
            "plan_investigation",
            "integrate_learning",
            "skeptic_review",
            "assess_convergence",
        }:
            raise RuntimeContractError(
                f"stage {cursor.stage!r} cannot consume an agent judgment"
            )
        self._validate_store_root_from_cursor(cursor)
        topic = self.store.load(cursor.topic_id)
        if topic.version != cursor.expected_version:
            raise RuntimeContractError(
                "pending cursor expected_version does not match canonical topic"
            )
        try:
            validated = validate_autonomous_response(cursor.stage, response)
        except JudgmentError as exc:
            raise RuntimeContractError(
                f"invalid {cursor.stage} response: {exc}"
            ) from exc

        payload = dict(cursor.payload)
        if cursor.stage == "map_knowledge":
            selected_gap = self._select_gap(topic)
            payload["selected_gap"] = (
                selected_gap.to_dict() if selected_gap is not None else None
            )
            return self._next_cursor(cursor, "plan_investigation", payload)
        if cursor.stage == "plan_investigation":
            payload["plan"] = validated["plan"]
            return self._next_cursor(cursor, "integrate_learning", payload)
        if cursor.stage == "integrate_learning":
            payload["integration"] = validated
            return self._next_cursor(cursor, "skeptic_review", payload)
        if cursor.stage == "skeptic_review":
            payload["structural_hit"] = validated["structural_hit"]
            marker = self._commit_marker(payload)
            return self._next_cursor(
                cursor,
                "commit_learning",
                payload,
                commit_marker=marker,
            )

        assessment = ConvergenceAssessment.from_dict(validated)
        decision = evaluate_convergence(topic, assessment)
        payload["convergence"] = {
            "converged": decision.converged,
            "reason_code": decision.reason_code,
            "reason": decision.reason,
            "checkpoint_required": decision.checkpoint_required,
            "blocking_ids": list(decision.blocking_ids),
        }
        return self._next_cursor(cursor, "checkpoint_or_complete", payload)

    def commit_learning(self, cursor: PendingCursor) -> PendingCursor:
        """Apply one durable delta exactly once, then project assessment."""
        cursor.validate()
        if cursor.stage != "commit_learning" or not cursor.commit_marker:
            raise RuntimeContractError("commit_learning requires a marked cursor")
        self._validate_store_root_from_cursor(cursor)
        if self._commit_marker(cursor.payload) != cursor.commit_marker:
            raise RuntimeContractError("commit marker does not match payload")

        current = self.store.load(cursor.topic_id)
        if current.version == cursor.expected_version:
            integration = dict(cursor.payload["integration"])
            integration["cycle"] = cursor.payload["cycle"]
            integration["skeptic_structural_hit"] = cursor.payload[
                "structural_hit"
            ]
            try:
                current = self.learner.apply_knowledge_delta(
                    self.store,
                    cursor.topic_id,
                    base_version=cursor.expected_version,
                    update=integration,
                )
            except (KnowledgeStoreError, ValueError, KeyError) as exc:
                raise RuntimeContractError(
                    f"durable learning commit failed: {exc}"
                ) from exc
        elif not self._commit_already_applied(current, cursor):
            raise RuntimeContractError(
                "canonical topic does not match pending commit marker"
            )

        payload = {
            "cycle": cursor.payload["cycle"],
            "commit_marker": cursor.commit_marker,
        }
        return self._cursor_from_cursor(
            cursor,
            stage="assess_convergence",
            expected_version=current.version,
            payload=payload,
        )

    def checkpoint_or_continue(
        self,
        cursor: PendingCursor,
    ) -> PendingCursor | None:
        """Finish a converged run or project the next deterministic cycle."""
        cursor.validate()
        if cursor.stage != "checkpoint_or_complete":
            raise RuntimeContractError(
                "checkpoint_or_continue requires checkpoint_or_complete cursor"
            )
        self._validate_store_root_from_cursor(cursor)
        decision = cursor.payload["convergence"]
        if decision["converged"] or decision["checkpoint_required"]:
            return None
        topic = self.store.load(cursor.topic_id)
        if topic.version != cursor.expected_version:
            raise RuntimeContractError(
                "pending cursor expected_version does not match canonical topic"
            )
        selected_gap = self._select_gap(topic)
        return self._cursor_from_cursor(
            cursor,
            stage="plan_investigation",
            expected_version=topic.version,
            payload={
                "cycle": self._next_cycle(topic),
                "selected_gap": (
                    selected_gap.to_dict() if selected_gap is not None else None
                ),
            },
        )

    @staticmethod
    def _request_context(payload: dict[str, Any]) -> dict[str, Any]:
        context = {"cycle": payload["cycle"]}
        if "selected_gap" in payload:
            context["selected_gap"] = payload["selected_gap"]
        if "plan" in payload:
            context["investigation_plan"] = payload["plan"]
        if "integration" in payload:
            context["integration_proposal"] = payload["integration"]
        return context

    @staticmethod
    def _next_cycle(topic: TopicKnowledge) -> int:
        return max(
            (record.cycle for record in topic.convergence_history),
            default=0,
        ) + 1

    @staticmethod
    def _select_gap(topic: TopicKnowledge):
        ranks = {"high": 0, "medium": 1, "low": 2}
        open_gaps = [gap for gap in topic.gaps if gap.status == "open"]
        return min(
            open_gaps,
            key=lambda gap: (
                ranks[gap.priority],
                ranks[gap.expected_gain],
                gap.id,
            ),
            default=None,
        )

    def _cursor(
        self,
        run: HostRun,
        *,
        stage: str,
        expected_version: int,
        payload: dict[str, Any],
        commit_marker: str | None = None,
    ) -> PendingCursor:
        return PendingCursor(
            schema_version=RUNTIME_SCHEMA_VERSION,
            runtime_kind=PENDING_CURSOR_KIND,
            run_id=run.run_id,
            topic_id=run.topic_id,
            knowledge_root=run.knowledge_root,
            stage=stage,
            expected_version=expected_version,
            commit_marker=commit_marker,
            payload=payload,
        )

    def _cursor_from_cursor(
        self,
        cursor: PendingCursor,
        *,
        stage: str,
        expected_version: int,
        payload: dict[str, Any],
        commit_marker: str | None = None,
    ) -> PendingCursor:
        return PendingCursor(
            schema_version=RUNTIME_SCHEMA_VERSION,
            runtime_kind=PENDING_CURSOR_KIND,
            run_id=cursor.run_id,
            topic_id=cursor.topic_id,
            knowledge_root=cursor.knowledge_root,
            stage=stage,
            expected_version=expected_version,
            commit_marker=commit_marker,
            payload=payload,
        )

    def _next_cursor(
        self,
        cursor: PendingCursor,
        stage: str,
        payload: dict[str, Any],
        *,
        commit_marker: str | None = None,
    ) -> PendingCursor:
        return self._cursor_from_cursor(
            cursor,
            stage=stage,
            expected_version=cursor.expected_version,
            payload=payload,
            commit_marker=commit_marker,
        )

    @staticmethod
    def _commit_marker(payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _commit_already_applied(
        topic: TopicKnowledge,
        cursor: PendingCursor,
    ) -> bool:
        if topic.version != cursor.expected_version + 1:
            return False
        if not topic.convergence_history:
            return False
        record = topic.convergence_history[-1]
        integration = cursor.payload["integration"]
        return (
            record.cycle == cursor.payload["cycle"]
            and record.delta.to_dict() == integration["delta"]
            and record.phase == integration["phase"]
            and record.gain_level == integration["gain_level"]
            and record.skeptic_structural_hit
            == cursor.payload["structural_hit"]
        )

    def _validate_store_root(self, run: HostRun) -> None:
        run.validate()
        if str(self.store.root.resolve()) != run.knowledge_root:
            raise RuntimeContractError(
                "host run knowledge_root does not match configured store"
            )

    def _validate_store_root_from_cursor(self, cursor: PendingCursor) -> None:
        if str(self.store.root.resolve()) != cursor.knowledge_root:
            raise RuntimeContractError(
                "pending cursor knowledge_root does not match configured store"
            )
