"""Capture and replay vNext response artifacts against canonical storage."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any, Callable
from urllib.parse import urlparse

from scripts.knowledge_schema import TopicKnowledge
from scripts.knowledge_store import KnowledgeStore
from scripts.loop import AutonomousLearningLoop


AGENT_STAGES = {
    "anchor",
    "map_knowledge",
    "plan_investigation",
    "integrate_learning",
    "skeptic_review",
    "assess_convergence",
}
FORBIDDEN_STAGES = {
    "teach",
    "feedback",
    "assess_user",
    "plan_teaching",
    "teach_reply",
}


class ArtifactValidationError(ValueError):
    """A recorded response artifact cannot be trusted for deterministic replay."""


class RecordingAgent:
    def __init__(self, delegate: Callable[[str, dict[str, Any]], dict[str, Any]]):
        self.delegate = delegate
        self.events: list[dict[str, Any]] = []

    def __call__(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        response = self.delegate(stage, context)
        self.events.append({"stage": stage, "response": deepcopy(response)})
        return response


class ReplayAgent:
    def __init__(self, events: list[dict[str, Any]]):
        self.events = events
        self.index = 0

    def __call__(self, stage: str, context: dict[str, Any]) -> dict[str, Any]:
        if self.index >= len(self.events):
            raise ArtifactValidationError(
                f"recorded events exhausted before stage {stage!r}"
            )
        event = self.events[self.index]
        self.index += 1
        if event["stage"] != stage:
            raise ArtifactValidationError(
                f"event {self.index} records {event['stage']!r}, "
                f"but loop requested {stage!r}"
            )
        return deepcopy(event["response"])

    def require_exhausted(self) -> None:
        if self.index != len(self.events):
            raise ArtifactValidationError(
                f"{len(self.events) - self.index} recorded event(s) were unused"
            )


def capture_artifact(
    *,
    case_id: str,
    profile_id: str,
    initial_topic: dict[str, Any],
    agent: Callable[[str, dict[str, Any]], dict[str, Any]],
    source_receipts: list[dict[str, str]],
) -> dict[str, Any]:
    """Run a scripted profile once and capture the exact agent responses."""
    recorder = RecordingAgent(agent)
    with tempfile.TemporaryDirectory(prefix="mentor-vnext-capture-") as tmp:
        store = KnowledgeStore(Path(tmp) / "knowledge")
        store.create(TopicKnowledge.from_dict(deepcopy(initial_topic)))
        result = AutonomousLearningLoop(store, recorder).run(
            initial_topic["topic_id"]
        )
        final_topic = store.load(initial_topic["topic_id"]).to_dict()

    return {
        "schema_version": 1,
        "artifact_origin": "scripted_profile",
        "declared_provenance": {
            "host": "local-scripted-evaluator",
            "model": "deterministic-profile",
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "external_model_call_verified": False,
        "case_id": case_id,
        "profile_id": profile_id,
        "initial_topic": deepcopy(initial_topic),
        "events": recorder.events,
        "result": result,
        "final_topic": final_topic,
        "source_receipts": deepcopy(source_receipts),
    }


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_artifact(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactValidationError(f"cannot load artifact {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ArtifactValidationError("artifact root must be a JSON object")
    return payload


def finalize_external_capture(
    raw_capture: dict[str, Any],
) -> dict[str, Any]:
    """Build trusted replay outputs from externally supplied raw responses."""
    required = {
        "schema_version",
        "declared_provenance",
        "case_id",
        "profile_id",
        "initial_topic",
        "events",
        "source_receipts",
    }
    if set(raw_capture) != required:
        raise ArtifactValidationError(
            "raw capture fields must be exactly: "
            f"{sorted(required)}"
        )
    artifact = deepcopy(raw_capture)
    artifact.update(
        {
            "artifact_origin": "external_response_capture",
            "collection_protocol": "raw_events_v1",
            "external_model_call_verified": False,
            "result": {},
            "final_topic": deepcopy(raw_capture["initial_topic"]),
        }
    )
    _validate_envelope(artifact)
    initial = TopicKnowledge.from_dict(deepcopy(artifact["initial_topic"]))
    if initial.version != 1:
        raise ArtifactValidationError("initial_topic must have version 1")
    result, final_topic, consumed = _run_events(initial, artifact["events"])
    if consumed != len(artifact["events"]):
        raise ArtifactValidationError("raw capture contains unused events")
    artifact["result"] = result
    artifact["final_topic"] = final_topic
    validate_artifact(artifact)
    return artifact


def validate_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Replay an artifact and attach its prose-independent invariant profile."""
    from .invariants import build_invariant_profile

    replay = replay_artifact(artifact)
    replay["invariant_profile"] = build_invariant_profile(artifact, replay)
    replay["receipt_scope"] = (
        "hashes prove artifact-internal excerpt consistency only; "
        "they do not attest remote source authenticity"
    )
    return replay


def replay_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Validate one artifact and replay every response through the real loop."""
    _validate_envelope(artifact)
    initial = TopicKnowledge.from_dict(deepcopy(artifact["initial_topic"]))
    expected_final = TopicKnowledge.from_dict(
        deepcopy(artifact["final_topic"])
    ).to_dict()
    if initial.version != 1:
        raise ArtifactValidationError("initial_topic must have version 1")
    topic_ids = {
        initial.topic_id,
        expected_final["topic_id"],
        artifact["result"].get("topic_id"),
    }
    if len(topic_ids) != 1:
        raise ArtifactValidationError(
            "initial topic, final topic, and result must share one topic_id"
        )

    actual_result, actual_final, consumed = _run_events(
        initial,
        artifact["events"],
    )

    if actual_result != artifact["result"]:
        raise ArtifactValidationError(
            "replayed result does not match the recorded result"
        )
    if _stable_topic(actual_final) != _stable_topic(expected_final):
        raise ArtifactValidationError(
            "replayed canonical topic does not match recorded final_topic"
        )
    return {
        "status": "PASS",
        "validation_mode": "recorded_artifact_replay",
        "artifact_origin": artifact["artifact_origin"],
        "external_call_attestation": "not_verified",
        "case_id": artifact["case_id"],
        "profile_id": artifact["profile_id"],
        "events_consumed": consumed,
        "volatile_topic_fields_ignored": ["updated_at"],
        "result": actual_result,
        "final_topic": actual_final,
    }


def _run_events(
    initial: TopicKnowledge,
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], int]:
    replay_agent = ReplayAgent(deepcopy(events))
    with tempfile.TemporaryDirectory(prefix="mentor-vnext-replay-") as tmp:
        knowledge_root = Path(tmp) / "knowledge"
        store = KnowledgeStore(knowledge_root)
        store.create(initial)
        result = AutonomousLearningLoop(store, replay_agent).run(
            initial.topic_id
        )
        canonical_path = (
            knowledge_root / "topics" / initial.topic_id / "knowledge.json"
        )
        final_topic = json.loads(canonical_path.read_text(encoding="utf-8"))
        TopicKnowledge.from_dict(final_topic)
    replay_agent.require_exhausted()
    return result, final_topic, replay_agent.index


def _validate_envelope(artifact: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "artifact_origin",
        "declared_provenance",
        "external_model_call_verified",
        "case_id",
        "profile_id",
        "initial_topic",
        "events",
        "result",
        "final_topic",
        "source_receipts",
    }
    missing = sorted(required - artifact.keys())
    if missing:
        raise ArtifactValidationError(f"artifact missing fields: {missing}")
    if artifact["schema_version"] != 1:
        raise ArtifactValidationError("unsupported artifact schema_version")
    if not isinstance(artifact["artifact_origin"], str) or not artifact[
        "artifact_origin"
    ].strip():
        raise ArtifactValidationError("artifact_origin must be non-empty")
    provenance = artifact["declared_provenance"]
    if not isinstance(provenance, dict) or any(
        not isinstance(provenance.get(field), str)
        or not provenance[field].strip()
        for field in ("host", "model", "time")
    ):
        raise ArtifactValidationError(
            "declared_provenance requires non-empty host, model, and time"
        )
    if artifact["external_model_call_verified"] is not False:
        raise ArtifactValidationError(
            "artifact replay cannot attest an external model call"
        )
    if not isinstance(artifact["events"], list) or not artifact["events"]:
        raise ArtifactValidationError("events must be a non-empty list")
    for index, event in enumerate(artifact["events"], start=1):
        if not isinstance(event, dict):
            raise ArtifactValidationError(f"event {index} must be an object")
        stage = event.get("stage")
        if stage in FORBIDDEN_STAGES or stage not in AGENT_STAGES:
            raise ArtifactValidationError(
                f"event {index} has forbidden or unknown stage {stage!r}"
            )
        if not isinstance(event.get("response"), dict):
            raise ArtifactValidationError(
                f"event {index} response must be an object"
            )
    _validate_receipts(artifact)


def _validate_receipts(artifact: dict[str, Any]) -> None:
    sources = _new_evidence_sources(artifact["events"])
    if artifact["case_id"] == "unfamiliar_empirical":
        invalid_urls = sorted(source for source in sources if not _is_url(source))
        if invalid_urls:
            raise ArtifactValidationError(
                f"unfamiliar empirical evidence must use URLs: {invalid_urls}"
            )
    receipts = artifact["source_receipts"]
    if not isinstance(receipts, list):
        raise ArtifactValidationError("source_receipts must be a list")
    receipt_sources: set[str] = set()
    for receipt in receipts:
        if not isinstance(receipt, dict):
            raise ArtifactValidationError("each source receipt must be an object")
        source = receipt.get("source")
        retrieved_at = receipt.get("retrieved_at")
        excerpt = receipt.get("excerpt")
        digest = receipt.get("sha256")
        if not all(
            isinstance(value, str) and value.strip()
            for value in (source, retrieved_at, excerpt, digest)
        ):
            raise ArtifactValidationError(
                "receipt requires source, retrieved_at, excerpt, and sha256"
            )
        expected = hashlib.sha256(excerpt.encode("utf-8")).hexdigest()
        if digest != expected:
            raise ArtifactValidationError(
                f"receipt hash mismatch for source {source!r}"
            )
        if source in receipt_sources:
            raise ArtifactValidationError(f"duplicate receipt for {source!r}")
        receipt_sources.add(source)
    if receipt_sources != sources:
        raise ArtifactValidationError(
            "source receipts must exactly match new evidence sources: "
            f"evidence={sorted(sources)}, receipts={sorted(receipt_sources)}"
        )


def _new_evidence_sources(events: list[dict[str, Any]]) -> set[str]:
    sources: set[str] = set()
    for event in events:
        if event.get("stage") != "integrate_learning":
            continue
        response = event.get("response", {})
        new_ids = set(response.get("delta", {}).get("new_evidence_ids", []))
        for evidence in response.get("evidence", []):
            source = evidence.get("source")
            if evidence.get("id") in new_ids and isinstance(source, str):
                sources.add(source)
    return sources


def _is_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _stable_topic(topic: dict[str, Any]) -> dict[str, Any]:
    stable = deepcopy(topic)
    stable.pop("updated_at", None)
    return stable
