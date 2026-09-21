#!/usr/bin/env python3
"""Checks for stateless durable-knowledge queries and CLI compatibility."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from fixtures.knowledge_first_cases import complete_topic  # noqa: E402
from scripts.knowledge_schema import TopicKnowledge  # noqa: E402
from scripts.knowledge_store import KnowledgeStore  # noqa: E402
from scripts.query import query_knowledge  # noqa: E402


FORBIDDEN_STATEFUL_FIELDS = {
    "assess_user",
    "feedback",
    "learner_profile",
    "plan_teaching",
    "teach",
    "teach_reply",
    "teaching_action",
}


def _topic() -> TopicKnowledge:
    payload = complete_topic()
    payload["version"] = 1
    return TopicKnowledge.from_dict(payload)


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        return [
            *(str(key) for key in value),
            *(
                item
                for child in value.values()
                for item in _flatten_strings(child)
            ),
        ]
    if isinstance(value, (list, tuple, set)):
        return [item for child in value for item in _flatten_strings(child)]
    return [value] if isinstance(value, str) else []


def _run_cli(
    cwd: Path,
    knowledge_root: Path,
    command: str,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts" / "cli.py"),
            "--json",
            command,
            "What determines the visible rainbow?",
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            "mechanism-of-rainbows",
        ],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mentor-query-") as tmp:
        root = Path(tmp)
        knowledge_root = root / "knowledge"
        caller = root / "caller"
        caller.mkdir()
        store = KnowledgeStore(knowledge_root)
        topic = store.create(_topic())
        canonical_path = (
            knowledge_root / "topics" / topic.topic_id / "knowledge.json"
        )
        before = canonical_path.read_bytes()

        result = query_knowledge(
            store,
            topic.topic_id,
            "What determines the visible rainbow?",
        )
        after = canonical_path.read_bytes()

        assert result["topic_id"] == topic.topic_id
        assert result["knowledge_version"] == topic.version
        assert result["question"] == "What determines the visible rainbow?"
        assert len(result["claims"]) == 4
        assert before == after
        print("[1/5] query reads the current version without mutating it")

        tokens = {token.lower() for token in _flatten_strings(result)}
        assert not (FORBIDDEN_STATEFUL_FIELDS & tokens)
        assert "user_profile" not in result
        print("[2/5] query result contains no learner profile or teaching action")

        import_probe = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "import sys;"
                    f"sys.path.insert(0, {str(SKILL_ROOT)!r});"
                    "from scripts import cli;"
                    "raise SystemExit(1 if 'scripts.mentor' in sys.modules else 0)"
                ),
            ],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        assert import_probe.returncode == 0, import_probe.stderr

        query_run = _run_cli(caller, knowledge_root, "query")
        assert query_run.returncode == 0, query_run.stderr
        query_result = json.loads(query_run.stdout)
        assert not (caller / ".mentor-state").exists()
        print("[3/5] query CLI is stateless in the caller workspace")

        ask_run = _run_cli(caller, knowledge_root, "ask")
        assert ask_run.returncode == 0, ask_run.stderr
        assert json.loads(ask_run.stdout) == query_result
        print("[4/5] ask is an exact compatibility alias of query")

        feedback_run = subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "cli.py"),
                "--json",
                "feedback",
                "still confused",
            ],
            cwd=caller,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            capture_output=True,
            check=False,
        )
        assert feedback_run.returncode == 2
        assert "invalid choice" in feedback_run.stderr
        print("[5/5] feedback is absent from the default CLI graph")

    print("\nStateless query checks passed.")


if __name__ == "__main__":
    main()
