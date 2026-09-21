#!/usr/bin/env python3
"""Behavior checks for the one-way v1 session importer."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore, KnowledgeStoreError  # noqa: E402


def _migrator():
    module_path = SKILL_ROOT / "scripts" / "migrate_v1.py"
    assert module_path.is_file(), (
        "Task 10 RED: one-way v1 importer does not exist: "
        "scripts/migrate_v1.py"
    )
    from scripts import migrate_v1

    return migrate_v1


def _valid_session() -> dict:
    return {
        "schema_version": 1,
        "created_at": "2026-09-10T08:00:00+00:00",
        "updated_at": "2026-09-10T09:00:00+00:00",
        "proposition": {
            "proposition_text": "Caching changes latency and freshness tradeoffs.",
            "proposition_version": 4,
            "current_explanation": (
                "Cache placement and invalidation policy jointly determine "
                "latency and freshness."
            ),
            "open_boundaries": [
                "The optimal invalidation policy under bursty writes is unresolved."
            ],
            "proposition_scope": "Distributed cache behavior",
            "coverage_dimensions": ["placement", "invalidation", "consistency"],
            "dimension_depth": [
                {
                    "dimension": "placement",
                    "rules": ["Place shared caches near the dominant readers."],
                    "rule_meta": {
                        "Place shared caches near the dominant readers.": {
                            "basis": "bench-17",
                            "heuristic": True,
                        }
                    },
                    "no_increment": False,
                    "no_increment_reason": "",
                    "decided_version": 3,
                },
                {
                    "dimension": "invalidation",
                    "rules": ["Invalidate before serving known-stale values."],
                    "rule_meta": {},
                    "no_increment": False,
                    "no_increment_reason": "",
                    "decided_version": 4,
                },
                {
                    "dimension": "consistency",
                    "rules": [],
                    "rule_meta": {},
                    "no_increment": True,
                    "no_increment_reason": "No cache-specific increment was found.",
                    "decided_version": 4,
                },
            ],
            "evidence_book": [
                {
                    "version": 3,
                    "evidence_type": "来源观察",
                    "content": "Regional cache hits reduced median read latency.",
                    "source": "benchmark",
                    "citation": "bench-17",
                }
            ],
            "counterexample_library": [
                {
                    "content": "A hot key made the nearest cache the bottleneck.",
                    "pierced_version": 2,
                    "review_stage": "skeptic",
                }
            ],
        },
        "gap": {
            "gap_type": "结构缺口",
            "gap_statement": "How should invalidation behave during partitions?",
            "why_priority": "Incorrect freshness assumptions can corrupt decisions.",
            "secondary_gaps": [],
            "trigger_source": "怀疑",
            "resolved": False,
        },
        "teaching": {
            "learner_hypothesis": {
                "level": "intermediate",
                "block_type": "transfer",
                "preferred_style": "example",
                "note": "Legacy-only learner state.",
            },
            "dialog_goal": "促进迁移",
            "teaching_action": "先做迁移",
            "failed_actions": ["先定义"],
            "effective_actions": ["先给反例"],
            "misconception_signal": "Caching always improves latency.",
            "asset_library": [],
            "migration_task": "Apply the rule to CDN invalidation.",
            "migration_output": "Use versioned keys.",
        },
        "decision": {"teachable": True},
    }


def _partial_session() -> dict:
    return {
        "schema_version": 1,
        "proposition": {
            "proposition_text": "A partial legacy session remains importable."
        },
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expect_error(error_type, action, expected_fragment: str) -> None:
    try:
        action()
        raise AssertionError(f"expected {error_type.__name__}")
    except error_type as exc:
        assert expected_fragment in str(exc).lower(), (
            f"expected {expected_fragment!r} in error, got {exc!r}"
        )


def main() -> None:
    migrate_v1 = _migrator()

    with tempfile.TemporaryDirectory(prefix="mentor-v1-import-") as tmp:
        temp_root = Path(tmp)
        source = temp_root / "valid-v1-session.json"
        knowledge_root = temp_root / "knowledge"
        _write_json(source, _valid_session())
        source_hash = _sha256(source)

        result = migrate_v1.import_v1_session(
            source,
            knowledge_root,
            "cache-behavior",
        )
        topic = KnowledgeStore(knowledge_root).load("cache-behavior")
        assert result.topic.to_dict() == topic.to_dict()
        assert topic.version == 1
        assert topic.proposition == _valid_session()["proposition"]["proposition_text"]
        assert topic.coverage_dimensions == [
            "placement",
            "invalidation",
            "consistency",
        ]
        assert {
            (claim.kind, claim.dimension, claim.statement)
            for claim in topic.claims
        } >= {
            (
                "synthesis",
                "placement",
                _valid_session()["proposition"]["current_explanation"],
            ),
            ("rule", "placement", "Place shared caches near the dominant readers."),
            ("rule", "invalidation", "Invalidate before serving known-stale values."),
        }
        assert len(topic.evidence) == 1
        assert "Regional cache hits" in topic.evidence[0].source
        assert len(topic.counterexamples) == 1
        assert "hot key" in topic.counterexamples[0].statement
        assert {
            gap.question for gap in topic.gaps
        } == {
            "The optimal invalidation policy under bursty writes is unresolved.",
            "How should invalidation behave during partitions?",
        }
        assert all(gap.priority == "low" for gap in topic.gaps)
        assert all(gap.expected_gain == "low" for gap in topic.gaps)
        assert result.metadata["source_sha256"] == source_hash
        assert (
            result.metadata["unsupported_teaching_state"]
            == _valid_session()["teaching"]
        )
        assert topic.migration_metadata == result.metadata
        assert result.metadata["rule_context"][0]["rule_meta"]
        assert result.metadata["rule_context"][2]["no_increment"] is True
        assert result.metadata["evidence_context"][0]["version"] == 3
        assert result.metadata["counterexample_context"][0][
            "pierced_version"
        ] == 2
        assert "teaching" not in topic.to_dict()
        assert not list((knowledge_root / "topics" / "cache-behavior").glob(
            "*migration*"
        ))
        assert _sha256(source) == source_hash
        print("[1/8] valid v1 knowledge maps through the canonical store only")

        _expect_error(
            KnowledgeStoreError,
            lambda: migrate_v1.import_v1_session(
                source,
                knowledge_root,
                "cache-behavior",
            ),
            "already exists",
        )
        assert KnowledgeStore(knowledge_root).load("cache-behavior").version == 1
        print("[2/8] repeat import is rejected by default")

        repeated = migrate_v1.import_v1_session(
            source,
            knowledge_root,
            "cache-behavior",
            create_new_version=True,
        )
        assert repeated.topic.version == 2
        assert repeated.metadata["target_version"] == 2
        assert (
            knowledge_root
            / "topics"
            / "cache-behavior"
            / "history"
            / "v000002.json"
        ).is_file()
        assert _sha256(source) == source_hash
        print("[3/8] explicit repeat import creates a new immutable topic version")

        evolved_payload = repeated.topic.to_dict()
        evolved_payload["title"] = "vNext-enriched cache behavior"
        evolved = KnowledgeStore(knowledge_root).save(
            TopicKnowledge.from_dict(evolved_payload),
            base_version=2,
        )
        _expect_error(
            migrate_v1.V1MigrationError,
            lambda: migrate_v1.import_v1_session(
                source,
                knowledge_root,
                "cache-behavior",
                create_new_version=True,
            ),
            "evolved",
        )
        assert KnowledgeStore(knowledge_root).load("cache-behavior").to_dict() == (
            evolved.to_dict()
        )
        print("[4/8] explicit re-import cannot overwrite vNext evolution")

        partial_source = temp_root / "partial-v1-session.json"
        _write_json(partial_source, _partial_session())
        partial_result = migrate_v1.import_v1_session(
            partial_source,
            knowledge_root,
            "partial-session",
        )
        assert partial_result.topic.coverage_dimensions == ["legacy"]
        assert partial_result.topic.proposition == (
            "A partial legacy session remains importable."
        )
        assert partial_result.topic.claims[0].statement == (
            "A partial legacy session remains importable."
        )
        assert partial_result.metadata["unsupported_teaching_state"] == {}
        print("[5/8] partial v1 sessions receive a deterministic legacy dimension")

        corrupt_source = temp_root / "corrupt-v1-session.json"
        corrupt_source.write_text('{"proposition":', encoding="utf-8")
        corrupt_hash = _sha256(corrupt_source)
        _expect_error(
            migrate_v1.V1MigrationError,
            lambda: migrate_v1.import_v1_session(
                corrupt_source,
                knowledge_root,
                "corrupt-session",
            ),
            "invalid v1 session",
        )
        assert _sha256(corrupt_source) == corrupt_hash
        assert not (knowledge_root / "topics" / "corrupt-session").exists()
        print("[6/8] malformed JSON is rejected before durable topic creation")

        wrong_schema = deepcopy(_valid_session())
        wrong_schema["schema_version"] = 999
        wrong_schema_source = temp_root / "wrong-schema-session.json"
        _write_json(wrong_schema_source, wrong_schema)
        malformed_shape = deepcopy(_valid_session())
        malformed_shape["proposition"]["coverage_dimensions"] = "placement"
        malformed_shape_source = temp_root / "malformed-shape-session.json"
        _write_json(malformed_shape_source, malformed_shape)
        invalid_timestamp = deepcopy(_valid_session())
        invalid_timestamp["created_at"] = 17
        invalid_timestamp_source = temp_root / "invalid-timestamp-session.json"
        _write_json(invalid_timestamp_source, invalid_timestamp)
        invalid_evidence = deepcopy(_valid_session())
        invalid_evidence["proposition"]["evidence_book"][0]["version"] = "three"
        invalid_evidence_source = temp_root / "invalid-evidence-session.json"
        _write_json(invalid_evidence_source, invalid_evidence)
        malformed_nested_cases = {
            "invalid-gap-type": ("gap", "gap_type", 7),
            "invalid-secondary-gaps": ("gap", "secondary_gaps", "not-a-list"),
            "invalid-teaching-goal": ("teaching", "dialog_goal", 7),
            "invalid-decision": (None, "decision", []),
            "invalid-adjacent-topics": (
                "proposition",
                "adjacent_topics",
                "not-a-list",
            ),
            "invalid-scope-qualifiers": (
                "proposition",
                "scope_qualifiers",
                "not-a-list",
            ),
            "invalid-dimension-sources": (
                "proposition",
                "dimension_sources",
                "not-a-list",
            ),
            "invalid-evidence-type": (
                "proposition",
                "evidence_book",
                [
                    {
                        "version": 1,
                        "evidence_type": "fabricated",
                        "content": "Invalid enum.",
                        "source": "",
                        "citation": "",
                    }
                ],
            ),
            "invalid-failed-action": (
                "teaching",
                "failed_actions",
                ["invalid-action"],
            ),
            "invalid-teaching-asset": (
                "teaching",
                "asset_library",
                [
                    {
                        "block_type": "transfer",
                        "teaching_action": "invalid-action",
                        "dialog_goal": "促进迁移",
                        "effective": False,
                        "failure_kind": "",
                        "note": "",
                    }
                ],
            ),
        }
        malformed_nested_sources = {}
        for topic_name, (parent, field, value) in malformed_nested_cases.items():
            malformed = deepcopy(_valid_session())
            if parent is None:
                malformed[field] = value
            else:
                malformed[parent][field] = value
            malformed_path = temp_root / f"{topic_name}.json"
            _write_json(malformed_path, malformed)
            malformed_nested_sources[topic_name] = malformed_path
        empty_evidence = deepcopy(_valid_session())
        empty_evidence["proposition"]["evidence_book"] = [{}]
        empty_evidence_source = temp_root / "empty-evidence-session.json"
        _write_json(empty_evidence_source, empty_evidence)
        _expect_error(
            migrate_v1.V1MigrationError,
            lambda: migrate_v1.import_v1_session(
                wrong_schema_source,
                knowledge_root,
                "wrong-schema",
            ),
            "schema_version",
        )
        _expect_error(
            migrate_v1.V1MigrationError,
            lambda: migrate_v1.import_v1_session(
                malformed_shape_source,
                knowledge_root,
                "malformed-shape",
            ),
            "coverage_dimensions",
        )
        _expect_error(
            migrate_v1.V1MigrationError,
            lambda: migrate_v1.import_v1_session(
                invalid_timestamp_source,
                knowledge_root,
                "invalid-timestamp",
            ),
            "created_at",
        )
        _expect_error(
            migrate_v1.V1MigrationError,
            lambda: migrate_v1.import_v1_session(
                invalid_evidence_source,
                knowledge_root,
                "invalid-evidence",
            ),
            "evidence_book[0].version",
        )
        for topic_name, malformed_path in malformed_nested_sources.items():
            _expect_error(
                migrate_v1.V1MigrationError,
                lambda path=malformed_path, name=topic_name: (
                    migrate_v1.import_v1_session(
                        path,
                        knowledge_root,
                        name,
                    )
                ),
                "invalid v1 session",
            )
        _expect_error(
            migrate_v1.V1MigrationError,
            lambda: migrate_v1.import_v1_session(
                empty_evidence_source,
                knowledge_root,
                "empty-evidence",
            ),
            "evidence",
        )
        for rejected_topic in (
            "wrong-schema",
            "malformed-shape",
            "invalid-timestamp",
            "invalid-evidence",
            *malformed_nested_sources,
            "empty-evidence",
        ):
            assert not (knowledge_root / "topics" / rejected_topic).exists()
        print("[7/8] non-v1 and malformed typed fields are rejected")

        changing_source = temp_root / "changing-source-session.json"
        _write_json(changing_source, _valid_session())
        original_check = migrate_v1._assert_source_unchanged

        def mutate_before_check(path, original):
            path.write_bytes(original + b" ")
            original_check(path, original)

        migrate_v1._assert_source_unchanged = mutate_before_check
        try:
            _expect_error(
                migrate_v1.V1MigrationError,
                lambda: migrate_v1.import_v1_session(
                    changing_source,
                    knowledge_root,
                    "changed-before-commit",
                ),
                "changed during",
            )
        finally:
            migrate_v1._assert_source_unchanged = original_check
        assert not (
            knowledge_root / "topics" / "changed-before-commit"
        ).exists()

        post_commit_source = temp_root / "post-commit-source-session.json"
        _write_json(post_commit_source, _valid_session())
        original_store = migrate_v1.KnowledgeStore

        class SourceChangingStore:
            def __init__(self, root):
                self.inner = original_store(root)

            def create(self, topic):
                saved = self.inner.create(topic)
                post_commit_source.write_bytes(
                    post_commit_source.read_bytes() + b" "
                )
                return saved

        migrate_v1.KnowledgeStore = SourceChangingStore
        try:
            committed = migrate_v1.import_v1_session(
                post_commit_source,
                knowledge_root,
                "changed-after-commit",
            )
        finally:
            migrate_v1.KnowledgeStore = original_store
        assert committed.topic.version == 1
        assert KnowledgeStore(knowledge_root).load(
            "changed-after-commit"
        ).version == 1

        unavailable_root = temp_root / "unavailable-root"
        unavailable_root.write_text("not a directory", encoding="utf-8")
        _expect_error(
            KnowledgeStoreError,
            lambda: migrate_v1.import_v1_session(
                source,
                unavailable_root,
                "store-error",
            ),
            "configured knowledge root",
        )
        sentinel = KnowledgeStoreError("sentinel store failure")

        class FailingStore:
            def __init__(self, root):
                self.root = root

            def create(self, topic):
                raise sentinel

        migrate_v1.KnowledgeStore = FailingStore
        try:
            try:
                migrate_v1.import_v1_session(
                    source,
                    knowledge_root,
                    "sentinel-store-error",
                )
                raise AssertionError("expected sentinel KnowledgeStoreError")
            except KnowledgeStoreError as exc:
                assert exc is sentinel
        finally:
            migrate_v1.KnowledgeStore = original_store
        print("[8/8] source races and store failures have unambiguous outcomes")

    assert not list(SKILL_ROOT.rglob("__pycache__"))
    print("\nOne-way v1 migration checks passed.")


if __name__ == "__main__":
    main()
