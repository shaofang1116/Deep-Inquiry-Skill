#!/usr/bin/env python3
"""RED-first checks for M0.5 vNext host runtime contracts."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import uuid

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "examples"))

from fixtures.knowledge_first_cases import complete_topic  # noqa: E402
from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore, KnowledgeStoreError  # noqa: E402


def _expect_error(error_type, callback, fragment: str) -> None:
    try:
        callback()
        raise AssertionError(f"expected runtime error containing {fragment!r}")
    except error_type as exc:
        assert fragment in str(exc), str(exc)


def _initialization_response() -> dict:
    topic = complete_topic()
    topic["title"] = "  Rainbow formation  "
    topic["proposition"] = (
        "  A rainbow is an observer-dependent optical phenomenon.  "
    )
    topic["coverage_dimensions"] = [
        "optical-mechanism",
        "observer-geometry",
    ]
    return {
        key: topic[key]
        for key in (
            "title",
            "proposition",
            "coverage_dimensions",
            "claims",
            "evidence",
            "gaps",
            "counterexamples",
        )
    }


def _topic_with_gap(topic_id: str) -> TopicKnowledge:
    payload = complete_topic()
    payload.update(
        {
            "topic_id": topic_id,
            "version": 1,
            "gaps": [
                {
                    "id": "gap-recovery",
                    "question": "Which durable recovery condition remains?",
                    "dimension": "optical-mechanism",
                    "priority": "high",
                    "expected_gain": "high",
                    "reason": "Recovery must preserve the next judgment.",
                    "status": "open",
                    "resolution_claim_ids": [],
                    "defer_reason": "",
                }
            ],
            "convergence_history": [],
        }
    )
    return TopicKnowledge.from_dict(payload)


def _integration_response(gap: dict) -> dict:
    return {
        "delta": {
            "new_claim_ids": [],
            "revised_claim_ids": [],
            "retired_claim_ids": [],
            "new_evidence_ids": [],
            "new_gap_ids": [],
            "resolved_gap_ids": [gap["id"]],
            "counterexample_hits": [],
        },
        "claims": [],
        "evidence": [],
        "gaps": [
            {
                **gap,
                "status": "resolved",
                "resolution_claim_ids": ["claim-1"],
            }
        ],
        "counterexamples": [],
        "phase": "post_baseline",
        "gain_level": "low",
    }


def main() -> None:
    try:
        from scripts.autonomous_runtime import (
            HostRun,
            HostRuntimeCoordinator,
            PendingCursor,
            RuntimeContractError,
        )
    except ModuleNotFoundError as exc:
        raise AssertionError(
            "M0.5 RED: missing scripts.autonomous_runtime host runtime contract"
        ) from exc

    run = HostRun.new(
        topic_id="three-cycle-topic",
        knowledge_root=str((Path("/tmp") / "mentor-knowledge").resolve()),
    )
    assert str(uuid.UUID(run.run_id)) == run.run_id
    assert run.base_version == 0
    assert HostRun.from_dict(run.to_dict()).to_dict() == run.to_dict()

    source = complete_topic()
    source["origin_metadata"] = {"host_run_id": run.run_id}
    topic = TopicKnowledge.from_dict(source)
    assert topic.to_dict()["origin_metadata"] == {
        "host_run_id": run.run_id
    }

    legacy_topic = TopicKnowledge.from_dict(complete_topic())
    assert legacy_topic.origin_metadata is None

    cursor = PendingCursor.initialize_topic(
        run,
        proposition="A durable host run persists only a topic reference.",
    )
    assert cursor.run_id == run.run_id
    assert cursor.stage == "initialize_topic"
    assert cursor.payload == {
        "proposition": "A durable host run persists only a topic reference."
    }

    copied_topic = deepcopy(cursor.to_dict())
    copied_topic["payload"]["topic"] = source
    _expect_error(
        RuntimeContractError,
        lambda: PendingCursor.from_dict(copied_topic),
        "full topic graph",
    )
    relative_root = run.to_dict()
    relative_root["knowledge_root"] = "relative/knowledge"
    _expect_error(RuntimeContractError, lambda: HostRun.from_dict(relative_root), "absolute")
    _expect_error(
        RuntimeContractError,
        lambda: HostRun.new(
            topic_id="three-cycle-topic",
            knowledge_root="relative/knowledge",
        ),
        "absolute",
    )
    malformed_run = run.to_dict()
    malformed_run["run_id"] = "not-a-uuid"
    _expect_error(RuntimeContractError, lambda: HostRun.from_dict(malformed_run), "UUID")
    unknown_stage = cursor.to_dict()
    unknown_stage["stage"] = "legacy_learning"
    _expect_error(RuntimeContractError, lambda: PendingCursor.from_dict(unknown_stage), "unknown")

    with tempfile.TemporaryDirectory(prefix="mentor-m05-init-") as directory:
        root = str(Path(directory).resolve())
        store = KnowledgeStore(root)
        host = HostRuntimeCoordinator(store)
        init_run = HostRun.new(
            topic_id="rainbow-host-topic",
            knowledge_root=root,
        )
        pending = host.begin_initialization(
            init_run,
            proposition="A rainbow depends on droplet optics and observer geometry.",
        )
        request = host.initialization_request(pending)
        assert request.name == "initialize_topic"
        assert request.context["topic_id"] == init_run.topic_id
        assert request.context["proposition"] == pending.payload["proposition"]
        assert set(request.response_template) == {
            "title",
            "proposition",
            "coverage_dimensions",
            "claims",
            "evidence",
            "gaps",
            "counterexamples",
        }

        invalid = _initialization_response()
        invalid["claims"][0]["evidence_ids"] = ["missing-evidence"]
        _expect_error(
            RuntimeContractError,
            lambda: host.initialize_topic(pending, invalid),
            "initialization response",
        )
        _expect_error(
            KnowledgeStoreError,
            lambda: store.load(init_run.topic_id),
            "cannot read current topic state",
        )

        created = host.initialize_topic(pending, _initialization_response())
        assert created.version == 1
        assert created.title == "Rainbow formation"
        assert created.proposition == (
            "A rainbow is an observer-dependent optical phenomenon."
        )
        assert created.origin_metadata == {"host_run_id": init_run.run_id}
        assert store.load(init_run.topic_id).to_dict() == created.to_dict()
        assert host.initialize_topic(
            pending, _initialization_response()
        ).to_dict() == created.to_dict()

        unrelated = HostRun.new(
            topic_id=init_run.topic_id,
            knowledge_root=root,
        )
        _expect_error(
            RuntimeContractError,
            lambda: host.initialize_topic(
                host.begin_initialization(
                    unrelated,
                    proposition="A different topic must not overwrite state.",
                ),
                _initialization_response(),
            ),
            "unrelated existing topic",
        )

    with tempfile.TemporaryDirectory(prefix="mentor-m05-recovery-") as directory:
        root = str(Path(directory).resolve())
        store = KnowledgeStore(root)
        run = HostRun.new(
            topic_id="recovery-topic",
            knowledge_root=root,
            base_version=1,
        )
        store.create(_topic_with_gap(run.topic_id))
        host = HostRuntimeCoordinator(store)

        pending = host.begin_learning(run)
        assert pending.stage == "map_knowledge"
        pending = PendingCursor.from_dict(pending.to_dict())
        request = HostRuntimeCoordinator(store).learning_request(pending)
        assert request.name == "map_knowledge"
        pending = host.advance_learning(pending, {"accepted": True})
        assert pending.stage == "plan_investigation"
        pending = PendingCursor.from_dict(pending.to_dict())
        assert HostRuntimeCoordinator(store).learning_request(
            pending
        ).name == "plan_investigation"
        selected_gap = pending.payload["selected_gap"]

        pending = host.advance_learning(
            pending,
            {"plan": "Investigate the durable recovery boundary."},
        )
        assert pending.stage == "integrate_learning"
        pending = PendingCursor.from_dict(pending.to_dict())
        assert HostRuntimeCoordinator(store).learning_request(
            pending
        ).name == "integrate_learning"
        pending = host.advance_learning(
            pending,
            _integration_response(selected_gap),
        )
        assert pending.stage == "skeptic_review"
        pending = PendingCursor.from_dict(pending.to_dict())
        assert HostRuntimeCoordinator(store).learning_request(
            pending
        ).name == "skeptic_review"
        pending = host.advance_learning(pending, {"structural_hit": False})
        assert pending.stage == "commit_learning"
        assert pending.commit_marker
        marker_payload = json.dumps(
            pending.payload, ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        assert pending.commit_marker == hashlib.sha256(marker_payload).hexdigest()

        reconstructed = PendingCursor.from_dict(pending.to_dict())
        after_commit = HostRuntimeCoordinator(store).commit_learning(reconstructed)
        assert store.load(run.topic_id).version == 2
        assert after_commit.stage == "assess_convergence"
        assert after_commit.expected_version == 2
        after_commit = PendingCursor.from_dict(after_commit.to_dict())
        assert HostRuntimeCoordinator(store).learning_request(
            after_commit
        ).name == "assess_convergence"

        after_retry = HostRuntimeCoordinator(store).commit_learning(reconstructed)
        assert after_retry.to_dict() == after_commit.to_dict()
        assert store.load(run.topic_id).version == 2

    print("[1/12] origin metadata is optional durable provenance")
    print("[2/12] host run validates UUID identity and canonical root")
    print("[3/12] initialization cursor keeps only stage-local input")
    print("[4/12] copied durable knowledge is rejected from runtime payload")
    print("[5/12] malformed runtime identities and stages are rejected")
    print("[6/12] initialization emits a full durable-topic request")
    print("[7/12] invalid cross-references leave no durable topic behind")
    print("[8/12] valid initialization creates a normalized version-1 topic")
    print("[9/12] only same-run initialization retries are idempotent")
    print("[10/12] every agent stage can stop at a durable pending cursor")
    print("[11/12] a reconstructed coordinator resumes the commit boundary")
    print("[12/12] post-save retry recognizes the commit marker without replay")


if __name__ == "__main__":
    main()
