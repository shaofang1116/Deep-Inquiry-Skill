#!/usr/bin/env python3
"""Behavior checks for the vNext atomic global knowledge library."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import stat
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from fixtures.knowledge_first_cases import complete_topic  # noqa: E402
from scripts.knowledge_schema import TopicKnowledge  # noqa: E402


def _knowledge_store():
    store_path = SKILL_ROOT / "scripts" / "knowledge_store.py"
    assert store_path.is_file(), (
        "Task 3 RED: durable knowledge store does not exist: "
        "scripts/knowledge_store.py"
    )
    from scripts import knowledge_store

    return knowledge_store


def _topic() -> TopicKnowledge:
    payload = deepcopy(complete_topic())
    payload["version"] = 1
    return TopicKnowledge.from_dict(payload)


def _updated_topic(topic: TopicKnowledge) -> TopicKnowledge:
    payload = topic.to_dict()
    payload["title"] = f"{payload['title']} revised"
    payload["updated_at"] = "2026-09-17T12:00:00+00:00"
    return TopicKnowledge.from_dict(payload)


def _expect_error(error_type, action, expected_fragment: str) -> None:
    try:
        action()
        raise AssertionError(f"expected {error_type.__name__}")
    except error_type as exc:
        assert expected_fragment in str(exc).lower(), (
            f"expected {expected_fragment!r} in error, got {exc!r}"
        )


def main() -> None:
    knowledge_store = _knowledge_store()
    KnowledgeStore = knowledge_store.KnowledgeStore
    KnowledgeStoreError = knowledge_store.KnowledgeStoreError
    VersionConflictError = knowledge_store.VersionConflictError
    IntegrityError = knowledge_store.IntegrityError
    TopicLockedError = knowledge_store.TopicLockedError

    with tempfile.TemporaryDirectory(prefix="mentor-knowledge-store-") as tmp:
        root = Path(tmp) / "global-library"
        store = KnowledgeStore(root)
        topic = _topic()

        created = store.create(topic)
        topic_dir = root / "topics" / topic.topic_id
        current_path = topic_dir / "knowledge.json"
        snapshot_v1 = topic_dir / "history" / "v000001.json"
        assert created.version == 1
        assert current_path.is_file()
        assert snapshot_v1.is_file()
        assert store.load(topic.topic_id).to_dict() == topic.to_dict()
        print("[1/9] create and load use the explicit global library")

        v1_bytes = snapshot_v1.read_bytes()
        updated = store.save(_updated_topic(created), base_version=1)
        snapshot_v2 = topic_dir / "history" / "v000002.json"
        assert updated.version == 2
        assert snapshot_v1.read_bytes() == v1_bytes
        assert snapshot_v2.is_file()
        assert not list(topic_dir.rglob(".tmp-*"))
        print("[2/9] save increments version and preserves immutable snapshots")

        current_path.write_text("{partial", encoding="utf-8")
        recovered = store.load(topic.topic_id)
        assert recovered.to_dict() == updated.to_dict()
        assert current_path.read_bytes() == snapshot_v2.read_bytes()
        print("[3/9] invalid current-state write recovers from latest snapshot")

        _expect_error(
            VersionConflictError,
            lambda: store.save(_updated_topic(recovered), base_version=1),
            "stale base version",
        )
        assert store.load(topic.topic_id).version == 2
        print("[4/9] stale optimistic base version is rejected")

        tampered_snapshot = updated.to_dict()
        tampered_snapshot["title"] = "tampered but schema-valid"
        snapshot_v2.write_bytes(
            knowledge_store.canonical_json_bytes(tampered_snapshot)
        )
        _expect_error(
            IntegrityError,
            lambda: store.load(topic.topic_id),
            "sha-256",
        )
        snapshot_v2.write_bytes(
            knowledge_store.canonical_json_bytes(updated.to_dict())
        )
        current_path.write_bytes(snapshot_v2.read_bytes())
        print("[5/9] snapshot SHA-256 verification detects tampering")

        lock_path = topic_dir / ".write-lock.json"
        lock_path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        _expect_error(
            TopicLockedError,
            lambda: store.save(_updated_topic(updated), base_version=2),
            "active writer",
        )
        print("[6/9] a second active writer is rejected")

        lock_path.write_text(
            json.dumps(
                {
                    "pid": 99999999,
                    "created_at": (
                        datetime.now(timezone.utc) - timedelta(days=1)
                    ).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        _expect_error(
            TopicLockedError,
            lambda: store.save(_updated_topic(updated), base_version=2),
            "stale lock",
        )
        lock_path.unlink()
        print("[7/9] stale locks produce explicit diagnostics")

    with tempfile.TemporaryDirectory(prefix="mentor-knowledge-denied-") as tmp:
        denied_root = Path(tmp) / "global-library"
        denied_root.mkdir()
        denied_root.chmod(stat.S_IRUSR | stat.S_IXUSR)
        try:
            denied_store = KnowledgeStore(denied_root)
            _expect_error(
                KnowledgeStoreError,
                lambda: denied_store.create(_topic()),
                "configured knowledge root",
            )
        finally:
            denied_root.chmod(
                stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
            )
        print("[8/9] permission failure is surfaced at the configured root")

    with tempfile.TemporaryDirectory(prefix="mentor-project-") as project_tmp:
        project = Path(project_tmp)
        configured_root = project / "unavailable-root"
        configured_root.write_text("not a directory", encoding="utf-8")
        old_cwd = Path.cwd()
        os.chdir(project)
        try:
            unavailable_store = KnowledgeStore(configured_root)
            _expect_error(
                KnowledgeStoreError,
                lambda: unavailable_store.create(_topic()),
                "configured knowledge root",
            )
            assert not (project / "topics").exists()
            assert not (project / ".mentor-state" / "topics").exists()
        finally:
            os.chdir(old_cwd)
        print("[9/9] unavailable global storage never falls back locally")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nAtomic global knowledge-store checks passed.")


if __name__ == "__main__":
    main()
