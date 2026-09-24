"""File-host adapter for resumable vNext public learning commands."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from .autonomous_runtime import (
    HostRun,
    HostRuntimeCoordinator,
    PendingCursor,
    RuntimeContractError,
)
from .compressor import project_durable_learning_result
from .convergence import ConvergenceDecision
from .judgments import JudgmentRequest
from .knowledge_store import KnowledgeStore, KnowledgeStoreError
from .reader_document import reader_document_ready
from .renderer import render_knowledge_report
from .store import StateStore, StoreError, _atomic_write_json, _read_json


class VNextHostError(RuntimeError):
    """The public vNext file-host operation cannot proceed."""


@dataclass
class HostOutcome:
    status: str
    request: JudgmentRequest | None = None
    request_path: str | None = None
    result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        if self.status == "pending" and self.request is not None:
            return {
                "status": "pending",
                "request_path": self.request_path,
                "request": self.request.to_dict(),
            }
        if self.status == "done":
            return {"status": "done", "result": dict(self.result or {})}
        if self.status == "cancelled":
            return {"status": "cancelled"}
        raise VNextHostError(f"unsupported host outcome {self.status!r}")


class VNextHost:
    """Bridge the host runtime files and the canonical runtime coordinator."""

    def __init__(self, *, state_path: str, knowledge_root: str):
        self.runtime = StateStore(state_path)
        self.knowledge = KnowledgeStore(knowledge_root)
        self.coordinator = HostRuntimeCoordinator(self.knowledge)

    def initialize(self, *, topic_id: str, proposition: str) -> HostOutcome:
        try:
            if self.runtime.exists():
                run = self._load_run()
                if (
                    run.status == "active"
                    and run.topic_id == topic_id
                    and run.knowledge_root == str(self.knowledge.root.resolve())
                    and self.runtime.has_pending()
                ):
                    return self._resume(run)
                raise VNextHostError(
                    "a vNext host run already exists at this state path"
                )
            run = HostRun.new(
                topic_id=topic_id,
                knowledge_root=str(self.knowledge.root.resolve()),
            )
            self._save_run(run)
            cursor = self.coordinator.begin_initialization(
                run,
                proposition=proposition,
            )
            return self._persist_agent_cursor(cursor)
        except RuntimeContractError as exc:
            raise VNextHostError(str(exc)) from exc

    def learn(self, *, topic_id: str) -> HostOutcome:
        try:
            run = self._load_run()
            self._require_topic(run, topic_id)
            if run.status != "active":
                raise VNextHostError(
                    f"cannot learn from a host run with status {run.status!r}"
                )
            if self.runtime.has_pending():
                return self._resume(run)

            topic = self.knowledge.load(topic_id)
            run = self._updated_run(run, base_version=topic.version)
            self._save_run(run)
            cursor = self.coordinator.begin_learning(run)
            return self._persist_agent_cursor(cursor)
        except RuntimeContractError as exc:
            raise VNextHostError(str(exc)) from exc

    def step(self) -> HostOutcome:
        try:
            run = self._load_run()
            if not self.runtime.has_pending():
                raise VNextHostError("no vNext pending cursor to step")
            cursor = self._load_cursor()
            judgment, response = self.runtime.read_judgment()
            request = self._request_for(cursor)
            if judgment != request.name:
                raise VNextHostError(
                    f"judgment {judgment!r} does not match pending stage "
                    f"{request.name!r}"
                )

            if cursor.stage == "initialize_topic":
                topic = self.coordinator.initialize_topic(cursor, response)
                self._save_run(self._updated_run(run, base_version=topic.version))
                self.runtime.clear_pending()
                return HostOutcome(
                    status="done",
                    result={
                        "topic_id": topic.topic_id,
                        "knowledge_version": topic.version,
                    },
                )

            cursor = self.coordinator.advance_learning(cursor, response)
            return self._advance_internal(cursor, run, discard_judgment=True)
        except RuntimeContractError as exc:
            raise VNextHostError(str(exc)) from exc

    def cancel(self, *, topic_id: str) -> HostOutcome:
        run = self._load_run()
        self._require_topic(run, topic_id)
        self._save_run(self._updated_run(run, status="cancelled"))
        self.runtime.clear_pending()
        return HostOutcome(status="cancelled")

    def state(self, *, topic_id: str) -> dict[str, Any]:
        run = self._load_run()
        self._require_topic(run, topic_id)
        state = run.to_dict()
        try:
            state["canonical_version"] = self.knowledge.load(topic_id).version
        except Exception as exc:
            raise VNextHostError(
                f"cannot load canonical topic for vNext host state: {exc}"
            ) from exc
        return state

    def _resume(self, run: HostRun) -> HostOutcome:
        cursor = self._load_cursor()
        if cursor.run_id != run.run_id:
            raise VNextHostError("pending cursor does not belong to host run")
        return self._advance_internal(cursor, run, discard_judgment=False)

    def _advance_internal(
        self,
        cursor: PendingCursor,
        run: HostRun,
        *,
        discard_judgment: bool,
    ) -> HostOutcome:
        while True:
            if cursor.stage == "commit_learning":
                self.runtime.save_pending(cursor.to_dict())
                if discard_judgment:
                    self.runtime.discard_judgment()
                    discard_judgment = False
                cursor = self.coordinator.commit_learning(cursor)
                continue
            if cursor.stage == "checkpoint_or_complete":
                self.runtime.save_pending(cursor.to_dict())
                if discard_judgment:
                    self.runtime.discard_judgment()
                    discard_judgment = False
                next_cursor = self.coordinator.checkpoint_or_continue(cursor)
                if next_cursor is None:
                    result = self._result(cursor)
                    self._save_run(self._updated_run(run, status="complete"))
                    self.runtime.clear_pending()
                    return HostOutcome(status="done", result=result)
                cursor = next_cursor
                continue
            return self._persist_agent_cursor(
                cursor,
                discard_judgment=discard_judgment,
            )

    def _persist_agent_cursor(
        self,
        cursor: PendingCursor,
        *,
        discard_judgment: bool = False,
    ) -> HostOutcome:
        request = self._request_for(cursor)
        self.runtime.save_pending(cursor.to_dict())
        request_path = self.runtime.write_request(request.to_dict())
        if discard_judgment:
            self.runtime.discard_judgment()
        return HostOutcome(
            status="pending",
            request=request,
            request_path=request_path,
        )

    def _request_for(self, cursor: PendingCursor) -> JudgmentRequest:
        if cursor.stage == "initialize_topic":
            return self.coordinator.initialization_request(cursor)
        return self.coordinator.learning_request(cursor)

    def _load_run(self) -> HostRun:
        try:
            return HostRun.from_dict(_read_json(self.runtime.path))
        except (OSError, StoreError, RuntimeContractError) as exc:
            raise VNextHostError(f"cannot load vNext host run: {exc}") from exc

    def _load_cursor(self) -> PendingCursor:
        try:
            return PendingCursor.from_dict(self.runtime.load_pending())
        except (StoreError, RuntimeContractError) as exc:
            raise VNextHostError(
                f"cannot load vNext pending cursor: {exc}"
            ) from exc

    def _save_run(self, run: HostRun) -> None:
        _atomic_write_json(self.runtime.path, run.to_dict())

    @staticmethod
    def _require_topic(run: HostRun, topic_id: str) -> None:
        if run.topic_id != topic_id:
            raise VNextHostError("topic_id does not match vNext host run")

    @staticmethod
    def _updated_run(
        run: HostRun,
        *,
        base_version: int | None = None,
        status: str | None = None,
    ) -> HostRun:
        return replace(
            run,
            base_version=run.base_version if base_version is None else base_version,
            status=run.status if status is None else status,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def _result(self, cursor: PendingCursor) -> dict[str, Any]:
        decision = ConvergenceDecision(**cursor.payload["convergence"])
        topic = self.knowledge.load(cursor.topic_id)
        if topic.version != cursor.expected_version:
            raise VNextHostError(
                "completion cursor expected_version does not match "
                "canonical topic version"
            )
        result = project_durable_learning_result(topic, decision)
        if decision.converged:
            if topic.schema_version != 2 or not reader_document_ready(topic):
                raise VNextHostError(
                    "cannot complete a converged report without a ready "
                    "schema-v2 reader document"
                )
            try:
                report_path = self.knowledge.write_markdown_report(
                    topic,
                    render_knowledge_report(topic),
                )
            except (KnowledgeStoreError, ValueError) as exc:
                raise VNextHostError(
                    f"cannot write completion Markdown report: {exc}"
                ) from exc
            result["report_path"] = str(report_path)
        return result
