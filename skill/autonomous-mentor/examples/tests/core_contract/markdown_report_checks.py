#!/usr/bin/env python3
"""Checks for deterministic, immutable completion Markdown reports."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "examples"))

from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import (  # noqa: E402
    IntegrityError,
    KnowledgeStore,
    KnowledgeStoreError,
)
from scripts import renderer  # noqa: E402
from tests.fixtures.knowledge_first_cases import complete_topic  # noqa: E402


def _topic() -> TopicKnowledge:
    payload = deepcopy(complete_topic())
    payload["topic_id"] = "markdown-report-topic"
    payload["version"] = 1
    payload["title"] = "Durable # Knowledge"
    payload["proposition"] = "1. promoted\n`tick`"
    payload["claims"][0]["statement"] = "---\nClaim with *literal* Markdown."
    payload["claims"][0]["related_claim_refs"] = [
        "other-topic#claim`tick"
    ]
    return TopicKnowledge.from_dict(payload)


def _expect_error(error_type, action, fragment: str) -> None:
    try:
        action()
        raise AssertionError(f"expected {error_type.__name__}")
    except error_type as exc:
        assert fragment in str(exc), str(exc)


def main() -> None:
    assert hasattr(renderer, "render_knowledge_report"), (
        "RED: renderer.render_knowledge_report is missing"
    )
    topic = _topic()
    first = renderer.render_knowledge_report(topic)
    second = renderer.render_knowledge_report(topic)
    assert isinstance(first, bytes)
    assert first == second
    text = first.decode("utf-8")
    assert text.startswith("# Durable \\# Knowledge\n")
    assert "1\\. promoted \\`tick\\`" in text
    assert "## Knowledge by Dimension" in text
    assert "### optical-mechanism" in text
    assert "\\--- Claim with \\*literal\\* Markdown." in text
    assert "``other-topic#claim`tick``" in text
    assert "## Evidence" in text
    assert "## Counterexamples" in text
    assert "## Knowledge Gaps" in text
    assert "## Convergence History" in text
    print("[1/5] renderer produces deterministic escaped UTF-8 Markdown")

    with tempfile.TemporaryDirectory(prefix="mentor-markdown-report-") as tmp:
        store = KnowledgeStore(Path(tmp) / "knowledge")
        created = store.create(topic)
        assert hasattr(store, "write_markdown_report"), (
            "RED: KnowledgeStore.write_markdown_report is missing"
        )
        _expect_error(
            KnowledgeStoreError,
            lambda: store.write_markdown_report(created, b""),
            "non-empty bytes",
        )
        _expect_error(
            KnowledgeStoreError,
            lambda: store.write_markdown_report(created, b"\xff"),
            "valid UTF-8",
        )
        report_path = store.write_markdown_report(created, first)
        expected = (
            Path(tmp)
            / "knowledge"
            / "topics"
            / topic.topic_id
            / "reports"
            / "v000001.md"
        )
        assert report_path == expected.absolute()
        assert report_path.read_bytes() == first
        assert not list(report_path.parent.glob(".tmp-*"))
        print("[2/5] store atomically writes the versioned report path")

        repeated = store.write_markdown_report(created, first)
        assert repeated == report_path
        assert repeated.read_bytes() == first
        print("[3/5] identical completion retries reuse immutable bytes")

        report_path.write_text("tampered\n", encoding="utf-8")
        _expect_error(
            IntegrityError,
            lambda: store.write_markdown_report(created, first),
            "different SHA-256",
        )
        stale = TopicKnowledge.from_dict(
            {**created.to_dict(), "version": created.version + 1}
        )
        _expect_error(
            IntegrityError,
            lambda: store.write_markdown_report(stale, first),
            "canonical topic",
        )
        print("[4/5] mismatched bytes and non-canonical versions fail closed")

    with tempfile.TemporaryDirectory(prefix="mentor-report-symlink-") as tmp:
        root = Path(tmp)
        store = KnowledgeStore(root / "knowledge")
        created = store.create(topic)
        topic_dir = (
            root / "knowledge" / "topics" / topic.topic_id
        )
        escaped = root / "outside-reports"
        escaped.mkdir()
        (topic_dir / "reports").symlink_to(
            escaped, target_is_directory=True
        )
        _expect_error(
            KnowledgeStoreError,
            lambda: store.write_markdown_report(created, first),
            "symbolic link",
        )
        assert not list(escaped.iterdir())

        external_store = KnowledgeStore(root / "external-knowledge")
        external_topic = external_store.create(
            TopicKnowledge.from_dict(
                {**topic.to_dict(), "topic_id": "linked-topic"}
            )
        )
        linked_root = root / "linked-knowledge"
        (linked_root / "topics").mkdir(parents=True)
        (linked_root / "topics" / external_topic.topic_id).symlink_to(
            root
            / "external-knowledge"
            / "topics"
            / external_topic.topic_id,
            target_is_directory=True,
        )
        linked_store = KnowledgeStore(linked_root)
        _expect_error(
            KnowledgeStoreError,
            lambda: linked_store.write_markdown_report(
                external_topic,
                renderer.render_knowledge_report(external_topic),
            ),
            "symbolic link",
        )

        ancestor_root = root / "ancestor-linked-knowledge"
        ancestor_root.mkdir()
        escaped_topics = root / "outside-topics"
        escaped_topics.mkdir()
        (ancestor_root / "topics").symlink_to(
            escaped_topics, target_is_directory=True
        )
        ancestor_store = KnowledgeStore(ancestor_root)
        ancestor_topic = TopicKnowledge.from_dict(
            {**topic.to_dict(), "topic_id": "ancestor-linked-topic"}
        )
        ancestor_store.create(ancestor_topic)
        _expect_error(
            KnowledgeStoreError,
            lambda: ancestor_store.write_markdown_report(
                ancestor_topic,
                renderer.render_knowledge_report(ancestor_topic),
            ),
            "symbolic link",
        )
        assert not (
            escaped_topics
            / ancestor_topic.topic_id
            / "reports"
        ).exists()
        print("[5/5] report paths reject symbolic-link escapes")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nCompletion Markdown report checks passed.")


if __name__ == "__main__":
    main()
