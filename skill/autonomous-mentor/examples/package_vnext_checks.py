#!/usr/bin/env python3
"""Task 12 release-gate checks for the isolated vNext package."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = SKILL_ROOT.parents[1]
PROJECT_ROOT = WORKSPACE_ROOT.parents[1]
SANDBOX_ROOT = PROJECT_ROOT / ".sandbox" / "autonomous-mentor-vnext"
SANDBOX_SKILL = SANDBOX_ROOT / "skills" / "autonomous-mentor"
SANDBOX_WORKSPACE = SANDBOX_ROOT / "workspace"
SANDBOX_KNOWLEDGE = SANDBOX_ROOT / "knowledge"
FROZEN_SKILL = PROJECT_ROOT / ".trae" / "skills" / "autonomous-mentor"
USER_SKILL = Path.home() / ".trae-cn" / "skills" / "autonomous-mentor"
MANIFEST_PATH = (
    SKILL_ROOT
    / "sessions"
    / "knowledge-first-vnext"
    / "validation_manifest.json"
)
CHECKS = (
    "examples/knowledge_schema_checks.py",
    "examples/knowledge_store_checks.py",
    "examples/index_rebuild_checks.py",
    "examples/tests/core_contract/learning_delta_checks.py",
    "examples/convergence_checks.py",
    "examples/autonomous_loop_checks.py",
    "examples/knowledge_first_acceptance_checks.py",
    "examples/query_checks.py",
    "examples/work_host_vnext_checks.py",
    "examples/work_host_contract_checks.py",
    "examples/migration_v1_checks.py",
    "examples/eval_vnext_suite.py",
    "examples/smoke_run.py",
    "examples/eval_suite.py",
)
EXCLUDED_PACKAGE_PARTS = {
    ".mentor-state",
    "__pycache__",
    ".DS_Store",
}
MANIFEST_RELATIVE_PATH = Path(
    "sessions/knowledge-first-vnext/validation_manifest.json"
)


def _ignore_package_runtime(
    directory: str,
    names: list[str],
) -> set[str]:
    return {
        name
        for name in names
        if name in EXCLUDED_PACKAGE_PARTS or name.endswith(".pyc")
    }


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root)
        if (
            EXCLUDED_PACKAGE_PARTS & set(relative.parts)
            or path.name.endswith(".pyc")
            or relative == MANIFEST_RELATIVE_PATH
        ):
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _run(
    *command: str,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    run_env = dict(os.environ)
    run_env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        run_env.update(env)
    return subprocess.run(
        command,
        cwd=cwd,
        env=run_env,
        text=True,
        capture_output=True,
        check=False,
    )


def _rebuild_sandbox() -> None:
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT)
    SANDBOX_SKILL.parent.mkdir(parents=True)
    shutil.copytree(
        SKILL_ROOT,
        SANDBOX_SKILL,
        ignore=_ignore_package_runtime,
    )
    SANDBOX_WORKSPACE.mkdir(parents=True)
    SANDBOX_KNOWLEDGE.mkdir(parents=True)
    assert not list(SANDBOX_SKILL.rglob(".mentor-state"))
    assert not list(SANDBOX_SKILL.rglob("__pycache__"))
    assert not list(SANDBOX_SKILL.rglob("*.pyc"))


def _run_sandbox_checks() -> None:
    for check in CHECKS:
        result = _run(
            sys.executable,
            check,
            cwd=SANDBOX_SKILL,
        )
        assert result.returncode == 0, (
            f"{check} failed:\n{result.stdout}\n{result.stderr}"
        )
    print(f"[1/5] sandbox package passed {len(CHECKS)}/{len(CHECKS)} checks")


def _exercise_sandbox_learning() -> None:
    code = """
import hashlib
import json
import os
from pathlib import Path

from eval_vnext.cases import build_initial_topic, ProfileAgent
from scripts.indexer import rebuild_library
from scripts.knowledge_schema import TopicKnowledge
from scripts.knowledge_store import KnowledgeStore
from scripts.loop import AutonomousLearningLoop

root = Path(os.environ["TASK12_KNOWLEDGE_ROOT"])
store = KnowledgeStore(root)
topic = build_initial_topic("mechanism")
store.create(TopicKnowledge.from_dict(topic))
result = AutonomousLearningLoop(
    store,
    ProfileAgent("mechanism", "concise"),
).run(topic["topic_id"])
assert result["convergence_reason"]["code"] == "converged"
assert result["knowledge_version"] == 4

first = rebuild_library(root)
index_path = root / "index.json"
summary_paths = sorted(root.glob("topics/*/summary.md"))
before = {
    str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in [index_path, *summary_paths]
}
index_path.unlink()
for path in summary_paths:
    path.unlink()
second = rebuild_library(root)
after_paths = [root / "index.json", *sorted(root.glob("topics/*/summary.md"))]
after = {
    str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in after_paths
}
assert second == first
assert after == before
print(json.dumps({"topic_id": topic["topic_id"], "version": result["knowledge_version"]}))
"""
    result = _run(
        sys.executable,
        "-c",
        code,
        cwd=SANDBOX_WORKSPACE,
        env={
            "PYTHONPATH": os.pathsep.join(
                (str(SANDBOX_SKILL), str(SANDBOX_SKILL / "examples"))
            ),
            "TASK12_KNOWLEDGE_ROOT": str(SANDBOX_KNOWLEDGE),
        },
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert json.loads(result.stdout)["version"] == 4
    assert not list(SANDBOX_SKILL.rglob(".mentor-state"))
    print("[2/5] sandbox learning used explicit knowledge root and rebuilt projections")


def _assert_package_contents() -> None:
    forbidden_names = {
        ".mentor-state",
        "__pycache__",
        "knowledge",
    }
    found = [
        path.relative_to(SANDBOX_SKILL).as_posix()
        for path in SANDBOX_SKILL.rglob("*")
        if path.name in forbidden_names or path.suffix == ".pyc"
    ]
    assert not found, f"package contains runtime state or cache: {found}"
    absolute_paths = [
        path.relative_to(SANDBOX_SKILL).as_posix()
        for path in SANDBOX_SKILL.rglob("*")
        if path.is_file() and b"/" + b"Users/" in path.read_bytes()
    ]
    assert not absolute_paths, (
        f"package contains absolute user paths: {absolute_paths}"
    )
    assert _tree_hash(SKILL_ROOT) == _tree_hash(SANDBOX_SKILL)
    print("[3/5] package excludes runtime state, caches, and absolute user paths")


def _write_manifest(
    frozen_hash: str,
    user_hash: str,
) -> None:
    payload = {
        "schema_version": 1,
        "validation": "knowledge-first-vnext",
        "development_tree_sha256": _tree_hash(SKILL_ROOT),
        "sandbox_tree_sha256": _tree_hash(SANDBOX_SKILL),
        "frozen_skill_sha256": frozen_hash,
        "user_skill_sha256": user_hash,
        "sandbox_checks": list(CHECKS),
        "learning_topic_id": "eval-vnext-mechanism",
        "learning_final_version": 4,
        "projection_rebuild": "byte_equivalent",
        "package_excludes": sorted(EXCLUDED_PACKAGE_PARTS),
        "zip_generated": False,
        "zip_policy": "requires explicit user approval",
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    assert FROZEN_SKILL.is_dir(), FROZEN_SKILL
    assert USER_SKILL.is_dir(), USER_SKILL
    frozen_hash = _tree_hash(FROZEN_SKILL)
    user_hash = _tree_hash(USER_SKILL)

    _rebuild_sandbox()
    _run_sandbox_checks()
    _exercise_sandbox_learning()
    _assert_package_contents()
    _write_manifest(frozen_hash, user_hash)

    _rebuild_sandbox()
    _assert_package_contents()
    assert _tree_hash(FROZEN_SKILL) == frozen_hash
    assert _tree_hash(USER_SKILL) == user_hash
    assert MANIFEST_PATH.is_file()
    print("[4/5] frozen and user-level Skill hashes remain unchanged")
    print("[5/5] validation manifest created; ZIP remains approval-gated")
    print("\nTask 12 sandbox recovery and release gate passed.")


if __name__ == "__main__":
    main()
