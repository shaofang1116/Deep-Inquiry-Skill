#!/usr/bin/env python3
"""Adapter checks for publisher-owned host commits and recovery."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "examples"))

from fixtures.knowledge_first_cases import complete_topic  # noqa: E402
from scripts.autonomous_runtime import HostRun, HostRuntimeCoordinator  # noqa: E402
from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore  # noqa: E402


def _topic(topic_id: str) -> TopicKnowledge:
    payload = deepcopy(complete_topic())
    payload.update(
        {
            "topic_id": topic_id,
            "version": 1,
            "gaps": [
                {
                    "id": "gap-host-publication",
                    "question": "Which host publication boundary remains?",
                    "dimension": "optical-mechanism",
                    "priority": "high",
                    "expected_gain": "high",
                    "reason": "Host recovery needs a durable boundary.",
                    "status": "open",
                    "resolution_claim_ids": [],
                    "defer_reason": "",
                }
            ],
            "convergence_history": [],
        }
    )
    return TopicKnowledge.from_dict(payload)


def _commit_cursor(
    host: HostRuntimeCoordinator,
    run: HostRun,
    *,
    structural_hit: bool,
):
    cursor = host.begin_learning(run)
    cursor = host.advance_learning(cursor, {"accepted": True})
    gap = cursor.payload["selected_gap"]
    cursor = host.advance_learning(
        cursor, {"plan": "Investigate host publication recovery."}
    )
    cursor = host.advance_learning(
        cursor,
        {
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
        },
    )
    return host.advance_learning(cursor, {"structural_hit": structural_hit})


def _candidate_records(root: Path, topic_id: str, candidate_id: str) -> list[dict]:
    audit_dir = root / "topics" / topic_id / "audit"
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(audit_dir.glob("*.json"))
        if candidate_id in path.name
    ]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mentor-publication-host-") as tmp:
        root = Path(tmp) / "knowledge"
        store = KnowledgeStore(root)

        published_run = HostRun.new(
            topic_id="host-published",
            knowledge_root=str(root.resolve()),
            base_version=1,
        )
        store.create(_topic(published_run.topic_id))
        published_host = HostRuntimeCoordinator(store)
        published_cursor = _commit_cursor(
            published_host, published_run, structural_hit=False
        )
        resumed = HostRuntimeCoordinator(store).commit_learning(published_cursor)
        assert resumed.stage == "assess_convergence"
        assert resumed.expected_version == 2
        records = _candidate_records(
            root, published_run.topic_id, published_cursor.commit_marker
        )
        assert [record["state"] for record in records] == [
            "proposed",
            "reviewed",
            "published",
        ]
        assert records[-1]["published_version"] == 2
        retry = HostRuntimeCoordinator(store).commit_learning(published_cursor)
        assert retry.to_dict() == resumed.to_dict()
        assert len(
            _candidate_records(
                root, published_run.topic_id, published_cursor.commit_marker
            )
        ) == 3
        print("[1/3] recovered commit publishes one audit chain exactly once")

        rejected_run = HostRun.new(
            topic_id="host-rejected",
            knowledge_root=str(root.resolve()),
            base_version=1,
        )
        store.create(_topic(rejected_run.topic_id))
        rejected_host = HostRuntimeCoordinator(store)
        rejected_cursor = _commit_cursor(
            rejected_host, rejected_run, structural_hit=True
        )
        retry_candidate = HostRuntimeCoordinator(store).commit_learning(
            rejected_cursor
        )
        assert retry_candidate.stage == "integrate_learning"
        assert retry_candidate.expected_version == 1
        assert store.load(rejected_run.topic_id).version == 1
        records = _candidate_records(
            root, rejected_run.topic_id, rejected_cursor.commit_marker
        )
        assert [record["state"] for record in records] == [
            "proposed",
            "reviewed",
            "rejected",
        ]
        assert records[-1]["rejection"]["code"] == "skeptic_structural_hit"
        assert "assess_convergence" not in retry_candidate.to_dict()["stage"]
        print("[2/3] skeptic rejection returns a new integration cursor")

        repeated_rejection = HostRuntimeCoordinator(store).commit_learning(
            rejected_cursor
        )
        assert repeated_rejection.to_dict() == retry_candidate.to_dict()
        assert len(
            _candidate_records(
                root, rejected_run.topic_id, rejected_cursor.commit_marker
            )
        ) == 3
        assert store.load(rejected_run.topic_id).version == 1
        print("[3/3] rejected commit retry does not add audit records or versions")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nPublisher-owned host recovery checks passed.")


if __name__ == "__main__":
    main()
