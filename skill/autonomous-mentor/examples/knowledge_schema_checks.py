#!/usr/bin/env python3
"""Contract checks for vNext durable knowledge and runtime references."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from fixtures.knowledge_first_cases import complete_topic  # noqa: E402


def _expect_schema_error(error_type, data, expected_fragment: str) -> None:
    try:
        topic_type = _knowledge_schema().TopicKnowledge
        topic_type.from_dict(data)
        raise AssertionError(f"expected schema error containing {expected_fragment!r}")
    except error_type as exc:
        assert expected_fragment in str(exc), (
            f"expected {expected_fragment!r} in error, got {exc!r}"
        )


def _knowledge_schema():
    schema_path = SKILL_ROOT / "scripts" / "knowledge_schema.py"
    assert schema_path.is_file(), (
        "Task 2 RED: durable knowledge owner does not exist: "
        "scripts/knowledge_schema.py"
    )
    from scripts import knowledge_schema

    return knowledge_schema


def main() -> None:
    knowledge_schema = _knowledge_schema()
    TopicKnowledge = knowledge_schema.TopicKnowledge
    KnowledgeSchemaError = knowledge_schema.KnowledgeSchemaError

    source = complete_topic()
    topic = TopicKnowledge.from_dict(source)
    assert topic.to_dict() == source
    assert TopicKnowledge.from_dict(topic.to_dict()).to_dict() == source
    print("[1/7] complete topic round-trips without loss")

    origin = deepcopy(source)
    origin["origin_metadata"] = {"host_run_id": "origin-run"}
    originated = TopicKnowledge.from_dict(origin)
    assert originated.origin_metadata == {"host_run_id": "origin-run"}
    assert originated.to_dict() == origin
    assert topic.origin_metadata is None
    print("[2/7] optional origin metadata preserves legacy topic shape")

    invalid_enum = deepcopy(source)
    invalid_enum["claims"][0]["kind"] = "persuasive_story"
    _expect_schema_error(KnowledgeSchemaError, invalid_enum, "kind")
    print("[3/7] invalid enum is rejected")

    broken_reference = deepcopy(source)
    broken_reference["claims"][0]["evidence_ids"] = ["missing-evidence"]
    _expect_schema_error(
        KnowledgeSchemaError, broken_reference, "missing-evidence"
    )
    print("[4/7] broken evidence reference is rejected")

    duplicate_id = deepcopy(source)
    duplicate_id["claims"].append(deepcopy(duplicate_id["claims"][0]))
    _expect_schema_error(KnowledgeSchemaError, duplicate_id, "duplicate")
    print("[5/7] duplicate entity ID is rejected")

    missing_evidence = deepcopy(source)
    missing_evidence["claims"][0]["evidence_ids"] = []
    _expect_schema_error(
        KnowledgeSchemaError, missing_evidence, "high-confidence"
    )
    print("[6/7] high-confidence claim without evidence is rejected")

    from scripts.schema import SessionState

    runtime = SessionState(
        topic_id=source["topic_id"],
        knowledge_root="/tmp/mentor-knowledge",
        base_version=source["version"],
    )
    payload = runtime.to_dict()
    assert payload["topic_id"] == source["topic_id"]
    assert payload["knowledge_root"] == "/tmp/mentor-knowledge"
    assert payload["base_version"] == source["version"]
    restored = SessionState.from_dict(payload)
    assert restored.topic_id == runtime.topic_id
    assert restored.knowledge_root == runtime.knowledge_root
    assert restored.base_version == runtime.base_version
    print("[7/7] runtime session stores topic reference and optimistic version")

    print("\nDurable knowledge schema checks passed.")


if __name__ == "__main__":
    main()
