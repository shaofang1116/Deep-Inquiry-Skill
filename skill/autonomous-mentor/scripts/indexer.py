"""Rebuild deterministic library projections from canonical topic JSON."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Any

from .knowledge_schema import TopicKnowledge
from .knowledge_store import (
    KnowledgeStore,
    KnowledgeStoreError,
    canonical_json_bytes,
    sha256_bytes,
)
from .renderer import render_topic_summary


class IndexRebuildError(RuntimeError):
    """Canonical topic data cannot produce a consistent library index."""


def rebuild_library(
    knowledge_root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Recreate every derived projection from canonical topic files."""
    root = Path(knowledge_root).expanduser().absolute()
    topics_root = root / "topics"
    store = KnowledgeStore(root)
    topics: list[tuple[TopicKnowledge, str]] = []

    if topics_root.exists() and not topics_root.is_dir():
        raise IndexRebuildError(f"topics path is not a directory: {topics_root}")

    topic_dirs = []
    if topics_root.is_dir():
        topic_dirs = sorted(
            (path for path in topics_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        )

    for topic_dir in topic_dirs:
        try:
            topic = store.load(topic_dir.name)
            source_bytes = (topic_dir / "knowledge.json").read_bytes()
        except (OSError, KnowledgeStoreError) as exc:
            raise IndexRebuildError(
                f"cannot index canonical topic {topic_dir.name!r}: {exc}"
            ) from exc
        topics.append((topic, sha256_bytes(source_bytes)))

    claim_locations = {
        (topic.topic_id, claim.id)
        for topic, _ in topics
        for claim in topic.claims
    }
    claim_links = _collect_claim_links(topics, claim_locations)

    topic_entries: list[dict[str, Any]] = []
    for topic, source_hash in topics:
        topic_dir = topics_root / topic.topic_id
        summary_path = topic_dir / "summary.md"
        summary = render_topic_summary(topic, source_hash).encode("utf-8")
        _atomic_write(summary_path, summary)
        topic_entries.append(
            {
                "topic_id": topic.topic_id,
                "title": topic.title,
                "proposition": topic.proposition,
                "version": topic.version,
                "claim_count": len(topic.claims),
                "evidence_count": len(topic.evidence),
                "open_gap_count": sum(
                    gap.status == "open" for gap in topic.gaps
                ),
                "source_sha256": source_hash,
                "summary_path": (
                    f"topics/{topic.topic_id}/summary.md"
                ),
            }
        )

    index = {
        "schema_version": 1,
        "projection_version": 1,
        "topics": topic_entries,
        "claim_links": claim_links,
    }
    _atomic_write(root / "index.json", canonical_json_bytes(index))
    return index


def _collect_claim_links(
    topics: list[tuple[TopicKnowledge, str]],
    claim_locations: set[tuple[str, str]],
) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for topic, _ in topics:
        for claim in topic.claims:
            for reference in claim.related_claim_refs:
                target_topic_id, target_claim_id = reference.split("#", 1)
                if (target_topic_id, target_claim_id) not in claim_locations:
                    raise IndexRebuildError(
                        f"claim {topic.topic_id}#{claim.id} references "
                        f"missing claim {reference}"
                    )
                links.append(
                    {
                        "source_topic_id": topic.topic_id,
                        "source_claim_id": claim.id,
                        "target_topic_id": target_topic_id,
                        "target_claim_id": target_claim_id,
                    }
                )
    return sorted(
        links,
        key=lambda item: (
            item["source_topic_id"],
            item["source_claim_id"],
            item["target_topic_id"],
            item["target_claim_id"],
        ),
    )


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=".tmp-projection-",
        dir=path.parent,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise
