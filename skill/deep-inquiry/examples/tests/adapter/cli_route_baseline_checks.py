#!/usr/bin/env python3
"""M0 route-baseline checks for the public CLI."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
CLI = SKILL_ROOT / "scripts" / "cli.py"
FIXTURE = (
    SKILL_ROOT.parent.parent
    / "docs"
    / "aegis"
    / "specs"
    / "2026-09-18-m0-cli-route-golden.json"
)


def _run(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"missing function: {name}")


def _calls(function: ast.FunctionDef) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def _attribute_calls(function: ast.FunctionDef) -> set[str]:
    return {
        f"{node.func.value.id}.{node.func.attr}"
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
    }


def main() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["fixture_kind"] == "m0_cli_route_baseline"
    commands = fixture["commands"]
    assert set(commands) == {
        "ask",
        "cancel",
        "demo",
        "init",
        "learn",
        "query",
        "state",
        "step",
    }

    tree = ast.parse(CLI.read_text(encoding="utf-8"))
    main_calls = _calls(_function(tree, "main"))
    host_calls = _attribute_calls(_function(tree, "_run_vnext_host"))
    cli_source = CLI.read_text(encoding="utf-8")

    assert {"query_knowledge", "_run_vnext_host", "_run_demo"} <= main_calls
    assert "KnowledgeStore" in main_calls
    assert {
        "host.initialize",
        "host.learn",
        "host.step",
        "host.cancel",
        "host.state",
    } <= host_calls
    assert "MentorLoop" not in cli_source
    assert "_bind_runtime_reference" not in cli_source
    assert commands["init"]["owner"] == "scripts.vnext_host.VNextHost.initialize"
    assert commands["learn"]["owner"] == "scripts.vnext_host.VNextHost.learn"
    assert commands["step"]["owner"] == "scripts.vnext_host.VNextHost.step"
    assert commands["cancel"]["owner"] == "scripts.vnext_host.VNextHost.cancel"
    assert commands["state"]["owner"] == "scripts.vnext_host.VNextHost.state"
    assert commands["demo"]["owner"] == "examples.smoke_run.main"
    assert commands["query"]["owner"] == "scripts.query.query_knowledge"
    assert commands["ask"]["owner"] == commands["query"]["owner"]
    print("[1/4] AST matches the fixture's vNext public and smoke owners")

    with tempfile.TemporaryDirectory(prefix="mentor-m0-route-") as tmp:
        caller = Path(tmp)
        help_run = _run(caller, "--help")
        assert help_run.returncode == 0, help_run.stderr
        for command in commands:
            assert command in help_run.stdout, command
        print("[2/4] help exposes the eight public baseline commands")

        demo_run = _run(caller, "demo")
        assert demo_run.returncode == 0, demo_run.stderr
        assert "vNext smoke passed" in demo_run.stdout
        print("[3/4] demo reaches its fixture-owned vNext smoke")

        missing_query = _run(
            caller,
            "--json",
            "--knowledge-root",
            str(caller / "knowledge"),
            "--topic-id",
            "missing-topic",
            "query",
            "baseline question",
        )
        missing_ask = _run(
            caller,
            "--json",
            "--knowledge-root",
            str(caller / "knowledge"),
            "--topic-id",
            "missing-topic",
            "ask",
            "baseline question",
        )
        assert missing_query.returncode == missing_ask.returncode == 1
        assert json.loads(missing_query.stdout) == json.loads(missing_ask.stdout)
        assert not (caller / ".mentor-state").exists()
        print("[4/4] query and ask retain identical stateless error behavior")

    print("\nM0 CLI route baseline checks passed.")


if __name__ == "__main__":
    main()
