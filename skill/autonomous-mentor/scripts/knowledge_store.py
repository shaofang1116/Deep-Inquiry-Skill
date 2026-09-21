"""Atomic, versioned storage for durable topic knowledge."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator

from .knowledge_schema import KnowledgeSchemaError, TopicKnowledge


class KnowledgeStoreError(RuntimeError):
    """The configured durable knowledge library cannot satisfy an operation."""


class VersionConflictError(KnowledgeStoreError):
    """A writer used an optimistic base version that is no longer current."""


class IntegrityError(KnowledgeStoreError):
    """Canonical state and its immutable snapshot do not agree."""


class TopicLockedError(KnowledgeStoreError):
    """Another writer owns the topic lock, or a stale lock needs attention."""


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    """Return deterministic UTF-8 JSON bytes used for snapshots and hashes."""
    text = json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        separators=(",", ": "),
    )
    return f"{text}\n".encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class KnowledgeStore:
    """Persist topics under one explicit user-selected knowledge root."""

    def __init__(
        self,
        knowledge_root: str | os.PathLike[str],
        *,
        stale_lock_seconds: int = 300,
    ):
        if not str(knowledge_root).strip():
            raise KnowledgeStoreError("configured knowledge root is required")
        if stale_lock_seconds < 1:
            raise ValueError("stale_lock_seconds must be positive")
        self.root = Path(knowledge_root).expanduser().absolute()
        self.stale_lock_seconds = stale_lock_seconds

    def create(self, topic: TopicKnowledge) -> TopicKnowledge:
        topic.validate()
        if topic.version != 1:
            raise KnowledgeStoreError("new topics must start at version 1")
        topic_dir = self._prepare_topic_dir(topic.topic_id)
        try:
            with self._topic_lock(topic_dir):
                current_path = topic_dir / "knowledge.json"
                if current_path.exists():
                    raise KnowledgeStoreError(
                        f"topic {topic.topic_id!r} already exists"
                    )
                payload = canonical_json_bytes(topic.to_dict())
                self._write_snapshot(topic_dir, topic.version, payload)
                self._atomic_write(current_path, payload)
        except KnowledgeStoreError:
            raise
        except OSError as exc:
            raise self._root_error(exc) from exc
        return TopicKnowledge.from_dict(topic.to_dict())

    def load(self, topic_id: str) -> TopicKnowledge:
        topic_dir = self._topic_dir(topic_id)
        try:
            return self._load_unlocked(topic_dir, recover_current=False)
        except IntegrityError:
            if not topic_dir.is_dir():
                raise
        with self._topic_lock(topic_dir):
            return self._load_unlocked(topic_dir, recover_current=True)

    def save(
        self,
        topic: TopicKnowledge,
        *,
        base_version: int,
    ) -> TopicKnowledge:
        topic.validate()
        topic_dir = self._prepare_topic_dir(topic.topic_id)
        try:
            with self._topic_lock(topic_dir):
                current = self._load_unlocked(
                    topic_dir, recover_current=True
                )
                if base_version != current.version:
                    raise VersionConflictError(
                        f"stale base version {base_version}; "
                        f"current version is {current.version}"
                    )
                if topic.created_at != current.created_at:
                    raise KnowledgeStoreError(
                        "topic created_at cannot change during save"
                    )

                payload = topic.to_dict()
                payload["version"] = current.version + 1
                saved = TopicKnowledge.from_dict(payload)
                encoded = canonical_json_bytes(saved.to_dict())
                self._write_snapshot(topic_dir, saved.version, encoded)
                self._atomic_write(topic_dir / "knowledge.json", encoded)
        except KnowledgeStoreError:
            raise
        except OSError as exc:
            raise self._root_error(exc) from exc
        return saved

    def _load_unlocked(
        self,
        topic_dir: Path,
        *,
        recover_current: bool,
    ) -> TopicKnowledge:
        current_path = topic_dir / "knowledge.json"
        try:
            current_bytes = current_path.read_bytes()
            current = self._decode_topic(current_bytes, current_path)
        except (OSError, IntegrityError) as exc:
            if not recover_current:
                raise IntegrityError(
                    f"cannot read current topic state {current_path}: {exc}"
                ) from exc
            recovered = self._latest_valid_snapshot(topic_dir)
            if recovered is None:
                raise IntegrityError(
                    f"no valid snapshot can recover {current_path}: {exc}"
                ) from exc
            current, current_bytes = recovered
            self._atomic_write(current_path, current_bytes)

        snapshot_path = self._snapshot_path(topic_dir, current.version)
        try:
            snapshot_bytes = snapshot_path.read_bytes()
        except OSError as exc:
            raise IntegrityError(
                f"snapshot missing for topic {current.topic_id!r} "
                f"version {current.version}: {snapshot_path}"
            ) from exc

        current_hash = sha256_bytes(current_bytes)
        snapshot_hash = sha256_bytes(snapshot_bytes)
        if current_hash != snapshot_hash:
            raise IntegrityError(
                f"SHA-256 mismatch between current topic and snapshot "
                f"{snapshot_path.name}: {current_hash} != {snapshot_hash}"
            )
        snapshot = self._decode_topic(snapshot_bytes, snapshot_path)
        if snapshot.version != current.version:
            raise IntegrityError(
                f"snapshot {snapshot_path} contains version "
                f"{snapshot.version}, expected {current.version}"
            )
        return current

    def _latest_valid_snapshot(
        self, topic_dir: Path
    ) -> tuple[TopicKnowledge, bytes] | None:
        history_dir = topic_dir / "history"
        if not history_dir.is_dir():
            return None
        for path in sorted(history_dir.glob("v*.json"), reverse=True):
            try:
                raw = path.read_bytes()
                topic = self._decode_topic(raw, path)
            except (OSError, IntegrityError):
                continue
            if path.name == f"v{topic.version:06d}.json":
                return topic, raw
        return None

    def _write_snapshot(
        self, topic_dir: Path, version: int, payload: bytes
    ) -> None:
        snapshot_path = self._snapshot_path(topic_dir, version)
        if snapshot_path.exists():
            existing = snapshot_path.read_bytes()
            if sha256_bytes(existing) != sha256_bytes(payload):
                raise IntegrityError(
                    f"immutable snapshot already exists with different "
                    f"SHA-256: {snapshot_path}"
                )
            return
        self._atomic_write(snapshot_path, payload, exclusive=True)

    def _prepare_topic_dir(self, topic_id: str) -> Path:
        topic_dir = self._topic_dir(topic_id)
        try:
            self._ensure_root_writable()
            (topic_dir / "history").mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise self._root_error(exc) from exc
        return topic_dir

    def _root_error(self, exc: OSError) -> KnowledgeStoreError:
        return KnowledgeStoreError(
            f"configured knowledge root is unavailable: {self.root}: {exc}"
        )

    def _ensure_root_writable(self) -> None:
        if self.root.exists() and not self.root.is_dir():
            raise NotADirectoryError(str(self.root))
        self.root.mkdir(parents=True, exist_ok=True)
        if not os.access(self.root, os.W_OK | os.X_OK):
            raise PermissionError(f"not writable: {self.root}")

    def _topic_dir(self, topic_id: str) -> Path:
        if (
            not topic_id
            or topic_id in {".", ".."}
            or Path(topic_id).name != topic_id
            or "/" in topic_id
            or "\\" in topic_id
        ):
            raise KnowledgeStoreError(f"invalid topic ID {topic_id!r}")
        return self.root / "topics" / topic_id

    @staticmethod
    def _snapshot_path(topic_dir: Path, version: int) -> Path:
        return topic_dir / "history" / f"v{version:06d}.json"

    @contextmanager
    def _topic_lock(self, topic_dir: Path) -> Iterator[None]:
        lock_path = topic_dir / ".write-lock.json"
        metadata = {
            "pid": os.getpid(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            fd = os.open(
                lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError as exc:
            raise self._lock_error(lock_path) from exc
        except OSError as exc:
            raise KnowledgeStoreError(
                f"configured knowledge root cannot create topic lock "
                f"{lock_path}: {exc}"
            ) from exc

        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(canonical_json_bytes(metadata))
                handle.flush()
                os.fsync(handle.fileno())
            yield
        finally:
            try:
                lock_path.unlink()
            except FileNotFoundError:
                pass

    def _lock_error(self, lock_path: Path) -> TopicLockedError:
        try:
            metadata = json.loads(lock_path.read_text(encoding="utf-8"))
            pid = int(metadata["pid"])
            created = datetime.fromisoformat(metadata["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - created).total_seconds()
            stale = age > self.stale_lock_seconds or not _pid_is_running(pid)
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            return TopicLockedError(
                f"stale lock has invalid metadata and requires manual "
                f"inspection: {lock_path}"
            )
        if stale:
            return TopicLockedError(
                f"stale lock requires manual inspection: {lock_path} "
                f"(pid={pid}, age_seconds={int(age)})"
            )
        return TopicLockedError(
            f"active writer holds topic lock: {lock_path} (pid={pid})"
        )

    @staticmethod
    def _decode_topic(raw: bytes, path: Path) -> TopicKnowledge:
        try:
            data = json.loads(raw.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("top level must be an object")
            return TopicKnowledge.from_dict(data)
        except (
            UnicodeDecodeError,
            json.JSONDecodeError,
            ValueError,
            KnowledgeSchemaError,
        ) as exc:
            raise IntegrityError(f"invalid topic snapshot {path}: {exc}") from exc

    @staticmethod
    def _atomic_write(
        path: Path,
        payload: bytes,
        *,
        exclusive: bool = False,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=".tmp-",
            suffix=".json",
            dir=path.parent,
        )
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            if exclusive:
                os.link(temp_path, path)
                temp_path.unlink()
            else:
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


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
