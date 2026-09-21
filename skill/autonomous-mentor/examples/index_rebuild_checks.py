#!/usr/bin/env python3
"""Checks for deterministic, rebuildable knowledge-library projections."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore, sha256_bytes  # noqa: E402


def _projection_modules():
    indexer_path = SKILL_ROOT / "scripts" / "indexer.py"
    renderer_path = SKILL_ROOT / "scripts" / "renderer.py"
    assert indexer_path.is_file() and renderer_path.is_file(), (
        "Task 4 RED: projection owners do not exist: "
        "scripts/indexer.py and scripts/renderer.py"
    )
    from scripts import indexer, renderer

    return indexer, renderer


def _topic(
    topic_id: str,
    title: str,
    claim_id: str,
    related_claim_refs: list[str],
) -> TopicKnowledge:
    payload = {
        "schema_version": 1,
        "topic_id": topic_id,
        "title": title,
        "proposition": f"Understand {title}",
        "version": 1,
        "coverage_dimensions": ["mechanism"],
        "claims": [
            {
                "id": claim_id,
                "dimension": "mechanism",
                "kind": "mechanism",
                "statement": f"{title} mechanism",
                "confidence": "medium",
                "evidence_ids": [],
                "counterexample_ids": [],
                "related_claim_refs": related_claim_refs,
                "status": "active",
                "introduced_version": 1,
                "updated_version": 1,
            }
        ],
        "evidence": [],
        "gaps": [],
        "counterexamples": [],
        "convergence_history": [],
        "created_at": "2026-09-17T10:00:00+00:00",
        "updated_at": "2026-09-17T10:00:00+00:00",
    }
    return TopicKnowledge.from_dict(payload)


def main() -> None:
    topic_a = _topic(
        "topic-a",
        "Alpha",
        "claim-a",
        ["topic-b#claim-b"],
    )
    assert topic_a.to_dict()["claims"][0].get("related_claim_refs") == [
        "topic-b#claim-b"
    ], "Task 4 RED: cross-topic claim refs are not durable schema fields"

    indexer, renderer = _projection_modules()

    with tempfile.TemporaryDirectory(prefix="mentor-index-rebuild-") as tmp:
        root = Path(tmp) / "knowledge"
        store = KnowledgeStore(root)
        topic_b = _topic(
            "topic-b",
            "Beta",
            "claim-b",
            ["topic-a#claim-a"],
        )
        store.create(topic_a)
        store.create(topic_b)

        canonical_before = {
            topic_id: (root / "topics" / topic_id / "knowledge.json").read_bytes()
            for topic_id in ("topic-a", "topic-b")
        }
        first_index = indexer.rebuild_library(root)
        index_path = root / "index.json"
        summary_paths = {
            topic_id: root / "topics" / topic_id / "summary.md"
            for topic_id in ("topic-a", "topic-b")
        }
        assert index_path.is_file()
        assert all(path.is_file() for path in summary_paths.values())
        assert [item["topic_id"] for item in first_index["topics"]] == [
            "topic-a",
            "topic-b",
        ]
        print("[1/6] deterministic scan builds two topic projections")

        source_hashes = {
            topic_id: sha256_bytes(canonical_before[topic_id])
            for topic_id in canonical_before
        }
        indexed_hashes = {
            item["topic_id"]: item["source_sha256"]
            for item in first_index["topics"]
        }
        assert indexed_hashes == source_hashes
        assert first_index["claim_links"] == [
            {
                "source_topic_id": "topic-a",
                "source_claim_id": "claim-a",
                "target_topic_id": "topic-b",
                "target_claim_id": "claim-b",
            },
            {
                "source_topic_id": "topic-b",
                "source_claim_id": "claim-b",
                "target_topic_id": "topic-a",
                "target_claim_id": "claim-a",
            },
        ]
        print("[2/6] index preserves source hashes and cross-topic claim links")

        alpha_summary = summary_paths["topic-a"].read_text(encoding="utf-8")
        assert "# Alpha" in alpha_summary
        assert source_hashes["topic-a"] in alpha_summary
        assert "`topic-b#claim-b`" in alpha_summary
        assert alpha_summary == renderer.render_topic_summary(
            store.load("topic-a"), source_hashes["topic-a"]
        )
        print("[3/6] Markdown is a human-readable canonical-state projection")

        first_index_bytes = index_path.read_bytes()
        first_summary_bytes = {
            topic_id: path.read_bytes()
            for topic_id, path in summary_paths.items()
        }
        index_path.unlink()
        for path in summary_paths.values():
            path.unlink()
        rebuilt_index = indexer.rebuild_library(root)
        assert rebuilt_index == first_index
        assert index_path.read_bytes() == first_index_bytes
        assert {
            topic_id: path.read_bytes()
            for topic_id, path in summary_paths.items()
        } == first_summary_bytes
        print("[4/6] deleted projections rebuild byte-for-byte")

        index_path.write_text('{"corrupt": true}\n', encoding="utf-8")
        summary_paths["topic-a"].write_text("corrupt\n", encoding="utf-8")
        repaired_index = indexer.rebuild_library(root)
        assert repaired_index == first_index
        assert index_path.read_bytes() == first_index_bytes
        assert summary_paths["topic-a"].read_bytes() == first_summary_bytes["topic-a"]
        print("[5/6] corrupted projections are repaired from canonical JSON")

        canonical_after = {
            topic_id: (root / "topics" / topic_id / "knowledge.json").read_bytes()
            for topic_id in ("topic-a", "topic-b")
        }
        assert canonical_after == canonical_before
        assert json.loads(index_path.read_text(encoding="utf-8")) == first_index
        assert not list(root.rglob("__pycache__"))
        print("[6/6] rebuild never mutates canonical topic state")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nRebuildable index and Markdown projection checks passed.")


if __name__ == "__main__":
    main()
