"""状态读写：只负责持久化状态的 JSON 存取与最小一致性校验。

两类文件，边界严格分开（MVP 实现边界「哪些状态持久化、哪些只在运行时存在」）：

- ``session.json`` —— 五类持久化状态对象，决定多轮连续性，原子写入。
- ``pending.json`` / ``request.json`` / ``judgment.json`` —— 仅运行时存在：
  单轮执行信封、判断请求、agent 刚填好的判断响应。随时可删，不承载知识。
  step 消费 judgment.json 后立即删除，防止旧判断被误复用。

本模块不生成任何解释或判断内容。
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from .schema import SessionState, SchemaError

SESSION_FILE = "session.json"
PENDING_FILE = "pending.json"
REQUEST_FILE = "request.json"
JUDGMENT_FILE = "judgment.json"


class StoreError(RuntimeError):
    pass


class StateStore:
    """一个会话对应状态目录中的一个 session.json，原子写入避免半写损坏。"""

    def __init__(self, path: str):
        self.path = path
        self.state_dir = os.path.dirname(os.path.abspath(path))

    # ---- 持久化状态 ----

    def exists(self) -> bool:
        return os.path.isfile(self.path)

    def new_session(self) -> SessionState:
        state = SessionState()
        now = _now()
        state.created_at = now
        state.updated_at = now
        return state

    def load(self) -> SessionState:
        if not self.exists():
            raise StoreError(f"状态文件不存在: {self.path}，请先接收新命题")
        data = _read_json(self.path)
        try:
            state = SessionState.from_dict(data)
            state.validate()
        except SchemaError as exc:
            raise StoreError(f"状态一致性校验失败: {exc}") from exc
        return state

    def save(self, state: SessionState) -> None:
        state.validate()
        state.updated_at = _now()
        _atomic_write_json(self.path, state.to_dict())

    # ---- 运行时文件（pending / request / judgment）----

    def _runtime_path(self, filename: str) -> str:
        return os.path.join(self.state_dir, filename)

    def has_pending(self) -> bool:
        return os.path.isfile(self._runtime_path(PENDING_FILE))

    def save_pending(self, pending: dict[str, Any]) -> None:
        _atomic_write_json(self._runtime_path(PENDING_FILE), pending)

    def load_pending(self) -> dict[str, Any]:
        path = self._runtime_path(PENDING_FILE)
        if not os.path.isfile(path):
            raise StoreError("没有进行中的轮次（pending.json 不存在），请先 init/learn/ask")
        return _read_json(path)

    def clear_pending(self) -> None:
        for name in (PENDING_FILE, REQUEST_FILE, JUDGMENT_FILE):
            path = self._runtime_path(name)
            if os.path.isfile(path):
                os.unlink(path)

    def write_request(self, request: dict[str, Any]) -> str:
        path = self._runtime_path(REQUEST_FILE)
        _atomic_write_json(path, request)
        return path

    def read_judgment(self) -> tuple[str, dict[str, Any]]:
        """读取 judgment.json 但不删除：校验失败时保留现场，便于修改后重跑 step。"""
        path = self._runtime_path(JUDGMENT_FILE)
        if not os.path.isfile(path):
            raise StoreError(
                f"未找到判断响应 {JUDGMENT_FILE}：请按 {REQUEST_FILE} 的模板填写后再 step"
            )
        data = _read_json(path)
        if not isinstance(data, dict) or "judgment" not in data or "response" not in data:
            raise StoreError(
                f"{JUDGMENT_FILE} 格式必须为 {{\"judgment\": <名称>, \"response\": {{...}}}}"
            )
        return str(data["judgment"]), data["response"]

    def discard_judgment(self) -> None:
        """判断被成功消费后删除，保证不会被重复使用。"""
        path = self._runtime_path(JUDGMENT_FILE)
        if os.path.isfile(path):
            os.unlink(path)

    def write_judgment(self, envelope: dict[str, Any]) -> str:
        path = self._runtime_path(JUDGMENT_FILE)
        _atomic_write_json(path, envelope)
        return path

    def runtime_path(self, filename: str) -> str:
        return self._runtime_path(filename)


def _read_json(path: str) -> dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise StoreError(f"JSON 无法解析 {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise StoreError(f"{path} 顶层必须是 JSON 对象")
    return data


def _atomic_write_json(path: str, data: dict[str, Any]) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
