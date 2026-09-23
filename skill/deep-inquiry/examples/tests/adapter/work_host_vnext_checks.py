#!/usr/bin/env python3
"""End-to-end checks for the vNext Work-host process contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT / "examples"))

from tests.fixtures.knowledge_first_cases import complete_topic  # noqa: E402

CLI = SKILL_ROOT / "scripts" / "cli.py"
SKILL_MD = SKILL_ROOT / "SKILL.md"


def _run(
    cli: Path,
    cwd: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    return subprocess.run(
        [sys.executable, str(cli), *arguments],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _assert_host_fields(
    payload: dict,
    *,
    knowledge_root: Path,
    topic_id: str,
) -> None:
    required = {
        "status",
        "next_action",
        "knowledge_root",
        "topic_id",
        "request_path",
        "request_paths",
    }
    assert required <= payload.keys(), sorted(required - payload.keys())
    assert payload["knowledge_root"] == str(knowledge_root.resolve())
    assert payload["topic_id"] == topic_id
    assert set(payload["request_paths"]) == {
        "state",
        "pending",
        "request",
        "judgment",
    }


def _initialization_response() -> dict:
    topic = complete_topic()
    topic["coverage_dimensions"] = [
        "optical-mechanism",
        "observer-geometry",
    ]
    return {
        key: topic[key]
        for key in (
            "title",
            "proposition",
            "coverage_dimensions",
            "claims",
            "evidence",
            "gaps",
            "counterexamples",
        )
    }


def main() -> None:
    topic_id = "work-host-topic"
    with tempfile.TemporaryDirectory(prefix="mentor-work-host-") as tmp:
        root = Path(tmp)
        caller = root / "caller"
        caller.mkdir()
        knowledge_root = root / "knowledge"
        state_path = caller / ".mentor-state" / "session.json"

        pending_run = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(state_path),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "init",
            "A durable Work-host contract distinguishes control flow from errors.",
        )
        assert pending_run.returncode == 0, pending_run.stderr
        pending = json.loads(pending_run.stdout)
        _assert_host_fields(
            pending,
            knowledge_root=knowledge_root,
            topic_id=topic_id,
        )
        assert pending["status"] == "pending"
        assert pending["next_action"] == "write_judgment_and_step"
        assert pending["request_path"] == pending["request_paths"]["request"]
        assert Path(pending["request_path"]).is_file()
        print("[1/5] JSON pending uses exit code zero and explicit control flow")

        request = json.loads(Path(pending["request_path"]).read_text())
        assert request["judgment"] == "initialize_topic"
        judgment_path = Path(pending["request_paths"]["judgment"])
        judgment_path.write_text(
            json.dumps(
                {
                    "judgment": request["judgment"],
                    "response": {"title": "missing required seed fields"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        invalid_seed = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(state_path),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "step",
        )
        assert invalid_seed.returncode != 0
        invalid_payload = json.loads(invalid_seed.stdout)
        assert invalid_payload["status"] == "error"
        assert Path(pending["request_path"]).is_file()
        judgment_path.write_text(
            json.dumps(
                {
                    "judgment": request["judgment"],
                    "response": _initialization_response(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        done_run = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(state_path),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "step",
        )
        assert done_run.returncode == 0, done_run.stderr
        done = json.loads(done_run.stdout)
        _assert_host_fields(
            done,
            knowledge_root=knowledge_root,
            topic_id=topic_id,
        )
        assert done["status"] == "done"
        assert done["next_action"] == "read_result"
        assert done["result"]["knowledge_version"] == 1

        learn_run = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(state_path),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "learn",
        )
        assert learn_run.returncode == 0, learn_run.stderr
        learning_pending = json.loads(learn_run.stdout)
        assert learning_pending["status"] == "pending"
        learning_request = json.loads(
            Path(learning_pending["request_path"]).read_text()
        )
        assert learning_request["judgment"] == "map_knowledge"
        judgment_path.write_text(
            json.dumps(
                {
                    "judgment": "map_knowledge",
                    "response": {"accepted": True},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        learning_step = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(state_path),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "step",
        )
        assert learning_step.returncode == 0, learning_step.stderr
        learning_next = json.loads(learning_step.stdout)
        assert learning_next["status"] == "pending"
        assert learning_next["request"]["judgment"] == "plan_investigation"

        state_run = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(state_path),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "state",
        )
        assert state_run.returncode == 0, state_run.stderr
        state_result = json.loads(state_run.stdout)
        _assert_host_fields(
            state_result,
            knowledge_root=knowledge_root,
            topic_id=topic_id,
        )
        assert state_result["status"] == "state"
        assert state_result["state"]["runtime_kind"] == "vnext_host_run"
        assert state_result["state"]["topic_id"] == topic_id
        assert state_result["state"]["knowledge_root"] == str(
            knowledge_root.resolve()
        )
        assert state_result["state"]["canonical_version"] == 1
        assert "decision" not in state_result["state"]

        cancel_run = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(state_path),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "cancel",
        )
        assert cancel_run.returncode == 0, cancel_run.stderr
        cancel_result = json.loads(cancel_run.stdout)
        _assert_host_fields(
            cancel_result,
            knowledge_root=knowledge_root,
            topic_id=topic_id,
        )
        assert cancel_result["status"] == "cancelled"

        invalid_run = _run(
            CLI,
            caller,
            "--json",
            "--state",
            str(root / "missing" / "session.json"),
            "--knowledge-root",
            str(knowledge_root),
            "--topic-id",
            topic_id,
            "step",
        )
        assert invalid_run.returncode != 0
        error = json.loads(invalid_run.stdout)
        _assert_host_fields(
            error,
            knowledge_root=knowledge_root,
            topic_id=topic_id,
        )
        assert error["status"] == "error"
        assert error["next_action"] == "correct_error"
        print("[2/5] real state and usage errors retain non-zero exit codes")

        query_root = root / "query-knowledge"
        query_topic = query_root / "topics" / topic_id
        query_topic.mkdir(parents=True)
        shutil.copyfile(
            SKILL_ROOT
            / "examples"
            / "fixtures"
            / "complete_topic.json",
            query_topic / "knowledge.json",
        ) if (
            SKILL_ROOT / "examples" / "fixtures" / "complete_topic.json"
        ).is_file() else None

        skill_copy = root / "readonly-skill"
        shutil.copytree(SKILL_ROOT, skill_copy)
        copied_cli = skill_copy / "scripts" / "cli.py"
        help_run = _run(copied_cli, caller, "--help")
        assert help_run.returncode == 0, help_run.stderr
        assert not list(skill_copy.rglob("__pycache__"))
        print("[3/5] CLI suppresses bytecode without relying on host environment")

        source = CLI.read_text(encoding="utf-8")
        bytecode_pos = source.find("sys.dont_write_bytecode = True")
        local_import_pos = source.find("from scripts.")
        assert 0 <= bytecode_pos < local_import_pos
        print("[4/5] bytecode suppression precedes local package imports")

        skill_text = SKILL_MD.read_text(encoding="utf-8")
        first_action = skill_text.find("first non-Skill tool call")
        init_command = skill_text.find(
            'python3 "$SKILL_DIR/scripts/cli.py" --json --knowledge-root'
        )
        research_gate = skill_text.find("plan_investigation")
        research_permission = skill_text.find("research tool", research_gate)
        assert -1 not in {
            first_action,
            init_command,
            research_gate,
            research_permission,
        }
        assert first_action < init_command < research_gate < research_permission
        print("[5/5] Skill starts the protocol before gated research tools")

    print("\nvNext Work-host contract checks passed.")


if __name__ == "__main__":
    main()
