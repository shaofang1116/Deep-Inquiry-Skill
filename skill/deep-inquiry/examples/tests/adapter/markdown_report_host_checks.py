#!/usr/bin/env python3
"""Adapter checks for completion-time Markdown report generation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "examples"))

from scripts.autonomous_runtime import (  # noqa: E402
    HostRun,
    PendingCursor,
    PENDING_CURSOR_KIND,
    RUNTIME_SCHEMA_VERSION,
)
from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStoreError  # noqa: E402
from scripts.vnext_host import VNextHost, VNextHostError  # noqa: E402
from tests.fixtures.knowledge_first_cases import complete_topic  # noqa: E402


def _topic(topic_id: str) -> TopicKnowledge:
    payload = deepcopy(complete_topic())
    payload.update({"topic_id": topic_id, "version": 1})
    return TopicKnowledge.from_dict(payload)


def _host(
    directory: Path,
    topic_id: str,
) -> tuple[VNextHost, HostRun]:
    knowledge_root = (directory / "knowledge").resolve()
    state_path = directory / "state" / "session.json"
    host = VNextHost(
        state_path=str(state_path),
        knowledge_root=str(knowledge_root),
    )
    host.knowledge.create(_topic(topic_id))
    run = HostRun.new(
        topic_id=topic_id,
        knowledge_root=str(knowledge_root),
        base_version=1,
    )
    host._save_run(run)
    return host, run


def _cursor(run: HostRun, *, converged: bool) -> PendingCursor:
    return PendingCursor(
        schema_version=RUNTIME_SCHEMA_VERSION,
        runtime_kind=PENDING_CURSOR_KIND,
        run_id=run.run_id,
        topic_id=run.topic_id,
        knowledge_root=run.knowledge_root,
        stage="checkpoint_or_complete",
        expected_version=1,
        commit_marker=None,
        payload={
            "cycle": 1,
            "convergence": {
                "converged": converged,
                "reason_code": (
                    "converged" if converged else "safety_checkpoint"
                ),
                "reason": (
                    "Knowledge has converged."
                    if converged
                    else "A safety checkpoint stopped this run."
                ),
                "checkpoint_required": not converged,
                "blocking_ids": [],
            },
        },
    )


def _expect_error(action, fragment: str) -> None:
    try:
        action()
        raise AssertionError("expected VNextHostError")
    except VNextHostError as exc:
        assert fragment in str(exc), str(exc)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mentor-report-host-") as tmp:
        root = Path(tmp)

        converged_host, converged_run = _host(root / "converged", "converged")
        outcome = converged_host._advance_internal(
            _cursor(converged_run, converged=True),
            converged_run,
            discard_judgment=False,
        )
        report_path = Path(outcome.result["report_path"])
        assert outcome.status == "done"
        assert report_path.is_file()
        assert report_path.name == "v000001.md"
        assert "# Rainbow formation" in report_path.read_text(encoding="utf-8")
        assert converged_host._load_run().status == "complete"
        assert not converged_host.runtime.has_pending()
        print("[1/4] true convergence returns a durable Markdown report")

        checkpoint_host, checkpoint_run = _host(
            root / "checkpoint", "checkpoint"
        )
        checkpoint = checkpoint_host._advance_internal(
            _cursor(checkpoint_run, converged=False),
            checkpoint_run,
            discard_judgment=False,
        )
        assert checkpoint.status == "done"
        assert "report_path" not in checkpoint.result
        assert not (
            Path(checkpoint_run.knowledge_root)
            / "topics"
            / checkpoint_run.topic_id
            / "reports"
        ).exists()
        print("[2/4] checkpoint termination does not claim a completed report")

        retry_host, retry_run = _host(root / "retry", "retry")
        cursor = _cursor(retry_run, converged=True)
        original_write = retry_host.knowledge.write_markdown_report

        def fail_write(topic, payload):
            raise KnowledgeStoreError("simulated report write failure")

        retry_host.knowledge.write_markdown_report = fail_write
        _expect_error(
            lambda: retry_host._advance_internal(
                cursor,
                retry_run,
                discard_judgment=False,
            ),
            "Markdown report",
        )
        assert retry_host._load_run().status == "active"
        assert retry_host.runtime.has_pending()

        retry_host.knowledge.write_markdown_report = original_write
        recovered = retry_host._resume(retry_host._load_run())
        assert recovered.status == "done"
        assert Path(recovered.result["report_path"]).is_file()
        assert retry_host._load_run().status == "complete"
        assert not retry_host.runtime.has_pending()
        print("[3/4] report write failure preserves a retryable completion cursor")

        stale_host, stale_run = _host(root / "stale", "stale")
        stale_cursor = _cursor(stale_run, converged=True)
        current = stale_host.knowledge.load(stale_run.topic_id)
        updated = current.to_dict()
        updated["title"] = "Newer unassessed knowledge"
        updated["updated_at"] = "2026-09-23T00:00:00+00:00"
        stale_host.knowledge.save(
            TopicKnowledge.from_dict(updated),
            base_version=current.version,
        )
        _expect_error(
            lambda: stale_host._advance_internal(
                stale_cursor,
                stale_run,
                discard_judgment=False,
            ),
            "version",
        )
        assert stale_host._load_run().status == "active"
        assert stale_host.runtime.has_pending()
        assert not (
            Path(stale_run.knowledge_root)
            / "topics"
            / stale_run.topic_id
            / "reports"
            / "v000002.md"
        ).exists()
        print("[4/4] stale convergence cannot certify a newer topic version")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nCompletion Markdown host checks passed.")


if __name__ == "__main__":
    main()
