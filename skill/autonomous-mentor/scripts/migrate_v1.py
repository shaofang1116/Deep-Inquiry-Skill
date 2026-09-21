"""One-way import of legacy v1 sessions into durable vNext topics."""

from __future__ import annotations

from dataclasses import dataclass, is_dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, get_args, get_origin, get_type_hints

sys.dont_write_bytecode = True

from .knowledge_schema import (  # noqa: E402
    Claim,
    Counterexample,
    Evidence,
    KnowledgeGap,
    TopicKnowledge,
)
from .knowledge_store import KnowledgeStore  # noqa: E402
from .schema import (  # noqa: E402
    DialogGoal,
    QuestionTreeState,
    SchemaError,
    SessionState,
    TeachingAction,
)


V1_EVIDENCE_TYPES = {
    "来源观察",
    "反例击穿",
    "教学断链",
    "逻辑推导",
    "反例分析",
    "逻辑判定",
}


class V1MigrationError(ValueError):
    """A legacy session cannot be imported without violating the contract."""


@dataclass(frozen=True)
class MigrationResult:
    topic: TopicKnowledge
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic.to_dict(),
            "metadata": dict(self.metadata),
        }


def import_v1_session(
    source_path: str | Path,
    knowledge_root: str | Path,
    topic_id: str,
    *,
    create_new_version: bool = False,
) -> MigrationResult:
    """Read a v1 session and create one canonical vNext topic snapshot."""
    source = Path(source_path).expanduser().absolute()
    source_bytes = _read_source(source)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    payload = _decode_source(source_bytes, source)

    store = KnowledgeStore(knowledge_root)
    if create_new_version:
        current = store.load(topic_id)
        prior_import = current.migration_metadata
        if (
            prior_import.get("source_kind") != "autonomous-mentor-v1"
            or prior_import.get("target_version") != current.version
        ):
            raise V1MigrationError(
                "explicit re-import rejected because the topic has evolved "
                "beyond the last importer-owned version"
            )
        target_version = current.version + 1
        metadata = _migration_metadata(payload, source_hash, target_version)
        topic = _map_topic(
            payload,
            topic_id,
            target_version=target_version,
            created_at=current.created_at,
            migration_metadata=metadata,
        )
    else:
        target_version = 1
        metadata = _migration_metadata(payload, source_hash, target_version)
        topic = _map_topic(
            payload,
            topic_id,
            target_version=target_version,
            migration_metadata=metadata,
        )

    _assert_source_unchanged(source, source_bytes)
    if create_new_version:
        saved = store.save(topic, base_version=target_version - 1)
    else:
        saved = store.create(topic)
    return MigrationResult(
        topic=saved,
        metadata=dict(saved.migration_metadata),
    )


def _read_source(source: Path) -> bytes:
    try:
        return source.read_bytes()
    except OSError as exc:
        raise V1MigrationError(f"cannot read v1 session {source}: {exc}") from exc


def _decode_source(source_bytes: bytes, source: Path) -> dict[str, Any]:
    try:
        payload = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise V1MigrationError(f"invalid v1 session {source}: {exc}") from exc
    if not isinstance(payload, dict):
        raise V1MigrationError(
            f"invalid v1 session {source}: top level must be an object"
        )
    schema_version = payload.get("schema_version")
    if (
        isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != 1
    ):
        raise V1MigrationError(
            "invalid v1 session: schema_version must be exactly 1"
        )
    try:
        _validate_dataclass_shape(payload, SessionState, "session")
        SessionState.from_dict(payload).validate()
        _validate_legacy_enums(payload)
    except (SchemaError, TypeError, ValueError, KeyError) as exc:
        raise V1MigrationError(
            f"invalid v1 session {source}: {exc}"
        ) from exc
    _proposition(payload)
    return payload


def _proposition(payload: dict[str, Any]) -> dict[str, Any]:
    proposition = payload.get("proposition")
    if not isinstance(proposition, dict):
        raise V1MigrationError(
            "invalid v1 session: proposition must be an object"
        )
    text = proposition.get("proposition_text")
    if not isinstance(text, str) or not text.strip():
        raise V1MigrationError(
            "invalid v1 session: proposition_text must be non-empty"
        )
    version = proposition.get("proposition_version", 0)
    if isinstance(version, bool) or not isinstance(version, int) or version < 0:
        raise V1MigrationError(
            "invalid v1 session: proposition_version must be non-negative"
        )
    return proposition


def _map_topic(
    payload: dict[str, Any],
    topic_id: str,
    *,
    target_version: int,
    created_at: str | None = None,
    migration_metadata: dict[str, Any],
) -> TopicKnowledge:
    proposition = _proposition(payload)
    dimensions = _dimensions(proposition)
    primary_dimension = dimensions[0]
    evidence = _map_evidence(proposition.get("evidence_book", []))
    counterexamples = _map_counterexamples(
        proposition.get("counterexample_library", [])
    )
    central_claim_id = "claim-v1-proposition"
    central_statement = _optional_text(
        proposition.get("current_explanation"),
        "current_explanation",
    ) or proposition["proposition_text"].strip()
    claims = [
        Claim(
            id=central_claim_id,
            dimension=primary_dimension,
            kind="synthesis",
            statement=central_statement,
            confidence="medium" if evidence else "low",
            evidence_ids=[item.id for item in evidence],
            counterexample_ids=[item.id for item in counterexamples],
            introduced_version=target_version,
            updated_version=target_version,
        )
    ]
    for item in evidence:
        item.supports_claim_ids = [central_claim_id]
    for item in counterexamples:
        item.claim_ids = [central_claim_id]
    claims.extend(
        _map_rules(
            proposition.get("dimension_depth", []),
            dimensions,
            target_version=target_version,
        )
    )

    source_created_at = _timestamp(payload.get("created_at"))
    topic = TopicKnowledge(
        schema_version=1,
        topic_id=topic_id,
        title=_optional_text(
            proposition.get("proposition_scope"),
            "proposition_scope",
        )
        or proposition["proposition_text"].strip(),
        proposition=proposition["proposition_text"].strip(),
        version=target_version,
        coverage_dimensions=dimensions,
        claims=claims,
        evidence=evidence,
        gaps=_map_gaps(payload, proposition, primary_dimension),
        counterexamples=counterexamples,
        convergence_history=[],
        created_at=created_at or source_created_at,
        updated_at=_timestamp(
            payload.get("updated_at"),
            source_created_at,
            field_name="updated_at",
        ),
        migration_metadata=migration_metadata,
    )
    topic.validate()
    return topic


def _dimensions(proposition: dict[str, Any]) -> list[str]:
    dimensions: list[str] = []
    raw_dimensions = proposition.get("coverage_dimensions", [])
    if not isinstance(raw_dimensions, list):
        raise V1MigrationError(
            "invalid v1 session: coverage_dimensions must be a list"
        )
    for item in raw_dimensions:
        text = _nonempty_text(item)
        if not text:
            raise V1MigrationError(
                "invalid v1 session: coverage_dimensions items "
                "must be non-empty strings"
            )
        if text in dimensions:
            raise V1MigrationError(
                "invalid v1 session: coverage_dimensions contains duplicates"
            )
        if text not in dimensions:
            dimensions.append(text)
    raw_depth = proposition.get("dimension_depth", [])
    if not isinstance(raw_depth, list):
        raise V1MigrationError(
            "invalid v1 session: dimension_depth must be a list"
        )
    for depth in raw_depth:
        if not isinstance(depth, dict):
            raise V1MigrationError(
                "invalid v1 session: dimension_depth items must be objects"
            )
        text = _nonempty_text(depth.get("dimension"))
        if not text:
            raise V1MigrationError(
                "invalid v1 session: dimension_depth dimension "
                "must be non-empty"
            )
        if text and text not in dimensions:
            dimensions.append(text)
    return dimensions or ["legacy"]


def _map_rules(
    raw_depth: Any,
    dimensions: list[str],
    *,
    target_version: int,
) -> list[Claim]:
    if not isinstance(raw_depth, list):
        raise V1MigrationError(
            "invalid v1 session: dimension_depth must be a list"
        )
    claims: list[Claim] = []
    for depth in raw_depth:
        if not isinstance(depth, dict):
            raise V1MigrationError(
                "invalid v1 session: dimension_depth items must be objects"
            )
        dimension = _nonempty_text(depth.get("dimension"))
        if not dimension:
            raise V1MigrationError(
                "invalid v1 session: dimension_depth dimension "
                "must be non-empty"
            )
        _validate_depth_context(depth)
        raw_rules = depth.get("rules", [])
        if not isinstance(raw_rules, list):
            raise V1MigrationError(
                "invalid v1 session: dimension rules must be a list"
            )
        for raw_rule in raw_rules:
            rule = _nonempty_text(raw_rule)
            if not rule:
                raise V1MigrationError(
                    "invalid v1 session: rules must contain "
                    "non-empty strings"
                )
            claims.append(
                Claim(
                    id=f"claim-v1-rule-{len(claims) + 1:03d}",
                    dimension=dimension,
                    kind="rule",
                    statement=rule,
                    confidence="low",
                    introduced_version=target_version,
                    updated_version=target_version,
                )
            )
    return claims


def _map_evidence(raw_evidence: Any) -> list[Evidence]:
    if not isinstance(raw_evidence, list):
        raise V1MigrationError(
            "invalid v1 session: evidence_book must be a list"
        )
    result: list[Evidence] = []
    for item in raw_evidence:
        if not isinstance(item, dict):
            raise V1MigrationError(
                "invalid v1 session: evidence items must be objects"
            )
        version = _nonnegative_int(
            item.get("version", 0),
            "evidence version",
        )
        text_fields = (
            (
                "type",
                _optional_text(
                    item.get("evidence_type"),
                    "evidence_type",
                ),
            ),
            (
                "content",
                _optional_text(item.get("content"), "evidence content"),
            ),
            (
                "source",
                _optional_text(item.get("source"), "evidence source"),
            ),
            (
                "citation",
                _optional_text(item.get("citation"), "evidence citation"),
            ),
        )
        if not any(value for _, value in text_fields):
            raise V1MigrationError(
                "invalid v1 session: evidence items must contain provenance"
            )
        fields = (
            ("version", str(version)),
            *text_fields,
        )
        rendered = " | ".join(
            f"{label}: {text}"
            for label, value in fields
            if (text := _nonempty_text(value))
        )
        if not rendered:
            raise V1MigrationError(
                "invalid v1 session: evidence items must contain provenance"
            )
        result.append(
            Evidence(
                id=f"evidence-v1-{len(result) + 1:03d}",
                source=rendered,
            )
        )
    return result


def _map_counterexamples(raw_counterexamples: Any) -> list[Counterexample]:
    if not isinstance(raw_counterexamples, list):
        raise V1MigrationError(
            "invalid v1 session: counterexample_library must be a list"
        )
    result: list[Counterexample] = []
    for item in raw_counterexamples:
        if not isinstance(item, dict):
            raise V1MigrationError(
                "invalid v1 session: counterexample items must be objects"
            )
        _nonnegative_int(
            item.get("pierced_version", 0),
            "counterexample pierced_version",
        )
        _optional_text(
            item.get("review_stage"),
            "counterexample review_stage",
        )
        statement = _optional_text(
            item.get("content"),
            "counterexample content",
        )
        if not statement:
            raise V1MigrationError(
                "invalid v1 session: counterexample content must be non-empty"
            )
        result.append(
            Counterexample(
                id=f"counterexample-v1-{len(result) + 1:03d}",
                statement=statement,
            )
        )
    return result


def _map_gaps(
    payload: dict[str, Any],
    proposition: dict[str, Any],
    dimension: str,
) -> list[KnowledgeGap]:
    raw_boundaries = proposition.get("open_boundaries", [])
    if not isinstance(raw_boundaries, list):
        raise V1MigrationError(
            "invalid v1 session: open_boundaries must be a list"
        )
    questions: list[tuple[str, str]] = []
    for item in raw_boundaries:
        text = _optional_text(item, "open boundary")
        if not text:
            raise V1MigrationError(
                "invalid v1 session: open_boundaries must contain "
                "non-empty strings"
            )
        if text not in {question for question, _ in questions}:
            questions.append((text, "Imported from a v1 open boundary."))

    raw_gap = payload.get("gap", {})
    if raw_gap is not None and not isinstance(raw_gap, dict):
        raise V1MigrationError("invalid v1 session: gap must be an object")
    if isinstance(raw_gap, dict):
        resolved = raw_gap.get("resolved", False)
        if not isinstance(resolved, bool):
            raise V1MigrationError(
                "invalid v1 session: gap.resolved must be a boolean"
            )
    if isinstance(raw_gap, dict) and not resolved:
        statement = _optional_text(
            raw_gap.get("gap_statement"),
            "gap.gap_statement",
        )
        if statement and statement not in {
            question for question, _ in questions
        }:
            reason = _optional_text(
                raw_gap.get("why_priority"),
                "gap.why_priority",
            )
            questions.append(
                (statement, reason or "Imported from the active v1 gap.")
            )

    return [
        KnowledgeGap(
            id=f"gap-v1-{index:03d}",
            question=question,
            dimension=dimension,
            priority="low",
            expected_gain="low",
            reason=reason,
        )
        for index, (question, reason) in enumerate(questions, start=1)
    ]


def _timestamp(
    value: Any,
    fallback: str = "1970-01-01T00:00:00+00:00",
    *,
    field_name: str = "created_at",
) -> str:
    if value in (None, ""):
        timestamp = fallback
    elif not isinstance(value, str):
        raise V1MigrationError(
            f"invalid v1 session: {field_name} must be a timestamp string"
        )
    else:
        timestamp = value.strip()
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise V1MigrationError(
            f"invalid v1 session: invalid {field_name} {timestamp!r}"
        ) from exc
    return timestamp


def _nonempty_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _optional_text(value: Any, field_name: str) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise V1MigrationError(
            f"invalid v1 session: {field_name} must be a string"
        )
    return value.strip()


def _nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise V1MigrationError(
            f"invalid v1 session: {field_name} must be a non-negative integer"
        )
    return value


def _validate_depth_context(depth: dict[str, Any]) -> None:
    no_increment = depth.get("no_increment", False)
    if not isinstance(no_increment, bool):
        raise V1MigrationError(
            "invalid v1 session: dimension no_increment must be a boolean"
        )
    reason = _optional_text(
        depth.get("no_increment_reason"),
        "dimension no_increment_reason",
    )
    if no_increment and not reason:
        raise V1MigrationError(
            "invalid v1 session: no_increment requires a reason"
        )
    _nonnegative_int(
        depth.get("decided_version", 0),
        "dimension decided_version",
    )
    rule_meta = depth.get("rule_meta", {})
    if not isinstance(rule_meta, dict):
        raise V1MigrationError(
            "invalid v1 session: rule_meta must be an object"
        )
    for rule, metadata in rule_meta.items():
        if not _nonempty_text(rule) or not isinstance(metadata, dict):
            raise V1MigrationError(
                "invalid v1 session: rule_meta entries are malformed"
            )
        _optional_text(metadata.get("basis"), "rule_meta basis")
        heuristic = metadata.get("heuristic", False)
        if not isinstance(heuristic, bool):
            raise V1MigrationError(
                "invalid v1 session: rule_meta heuristic must be a boolean"
            )


def _assert_source_unchanged(source: Path, original: bytes) -> None:
    try:
        current = source.read_bytes()
    except OSError as exc:
        raise V1MigrationError(
            f"cannot verify unchanged v1 session {source}: {exc}"
        ) from exc
    if current != original:
        raise V1MigrationError(
            f"v1 session changed during one-way import: {source}"
        )


def _migration_metadata(
    payload: dict[str, Any],
    source_hash: str,
    target_version: int,
) -> dict[str, Any]:
    proposition = _proposition(payload)
    teaching = payload.get("teaching", {})
    return {
        "source_kind": "autonomous-mentor-v1",
        "source_sha256": source_hash,
        "source_schema_version": payload["schema_version"],
        "source_proposition_version": proposition.get(
            "proposition_version", 0
        ),
        "target_version": target_version,
        "unsupported_teaching_state": dict(teaching),
        "rule_context": _legacy_context_list(
            proposition.get("dimension_depth", []),
            "dimension_depth",
        ),
        "evidence_context": _legacy_context_list(
            proposition.get("evidence_book", []),
            "evidence_book",
        ),
        "counterexample_context": _legacy_context_list(
            proposition.get("counterexample_library", []),
            "counterexample_library",
        ),
    }


def _legacy_context_list(value: Any, field_name: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise V1MigrationError(
            f"invalid v1 session: {field_name} must be a list"
        )
    if any(not isinstance(item, dict) for item in value):
        raise V1MigrationError(
            f"invalid v1 session: {field_name} items must be objects"
        )
    return [dict(item) for item in value]


def _validate_legacy_enums(payload: dict[str, Any]) -> None:
    proposition = payload.get("proposition", {})
    for index, evidence in enumerate(proposition.get("evidence_book", [])):
        evidence_type = evidence.get("evidence_type")
        if evidence_type not in V1_EVIDENCE_TYPES:
            raise V1MigrationError(
                "invalid v1 session: "
                f"evidence_book[{index}].evidence_type is invalid"
            )

    teaching = payload.get("teaching", {})
    action_values = {item.value for item in TeachingAction}
    goal_values = {item.value for item in DialogGoal}
    for field_name in ("failed_actions", "effective_actions"):
        for index, action in enumerate(teaching.get(field_name, [])):
            if action not in action_values:
                raise V1MigrationError(
                    "invalid v1 session: "
                    f"teaching.{field_name}[{index}] is invalid"
                )
    for index, asset in enumerate(teaching.get("asset_library", [])):
        action = asset.get("teaching_action")
        goal = asset.get("dialog_goal")
        if action not in action_values:
            raise V1MigrationError(
                "invalid v1 session: "
                f"teaching.asset_library[{index}].teaching_action is invalid"
            )
        if goal not in goal_values:
            raise V1MigrationError(
                "invalid v1 session: "
                f"teaching.asset_library[{index}].dialog_goal is invalid"
            )


def _validate_dataclass_shape(
    value: Any,
    model: type,
    field_name: str,
) -> None:
    if not isinstance(value, dict):
        raise V1MigrationError(
            f"invalid v1 session: {field_name} must be an object"
        )
    annotations = get_type_hints(model)
    if model is QuestionTreeState:
        annotations = {
            **annotations,
            "stable_questions": list[str],
            "open_questions": list[str],
        }
    for key, item in value.items():
        annotation = annotations.get(key)
        if annotation is None:
            raise V1MigrationError(
                f"invalid v1 session: unknown field {field_name}.{key}"
            )
        _validate_typed_value(item, annotation, f"{field_name}.{key}")


def _validate_typed_value(
    value: Any,
    annotation: Any,
    field_name: str,
) -> None:
    if annotation is Any:
        return
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is list:
        if not isinstance(value, list):
            raise V1MigrationError(
                f"invalid v1 session: {field_name} must be a list"
            )
        item_type = arguments[0] if arguments else Any
        for index, item in enumerate(value):
            _validate_typed_value(
                item,
                item_type,
                f"{field_name}[{index}]",
            )
        return
    if origin is dict:
        if not isinstance(value, dict):
            raise V1MigrationError(
                f"invalid v1 session: {field_name} must be an object"
            )
        key_type, item_type = arguments if len(arguments) == 2 else (Any, Any)
        for key, item in value.items():
            _validate_typed_value(key, key_type, f"{field_name} key")
            _validate_typed_value(item, item_type, f"{field_name}.{key}")
        return
    if isinstance(annotation, type) and is_dataclass(annotation):
        _validate_dataclass_shape(value, annotation, field_name)
        return
    if annotation in (str, int, bool):
        if type(value) is not annotation:
            raise V1MigrationError(
                f"invalid v1 session: {field_name} must be "
                f"{annotation.__name__}"
            )
        return
    if isinstance(annotation, type) and not isinstance(value, annotation):
        raise V1MigrationError(
            f"invalid v1 session: {field_name} has invalid type"
        )
