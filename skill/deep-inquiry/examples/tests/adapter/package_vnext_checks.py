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

SKILL_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = SKILL_ROOT.parents[1]
GIT_COMMON_DIR = Path(
    subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=WORKSPACE_ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
)
PROJECT_ROOT = GIT_COMMON_DIR.parent
SANDBOX_ROOT = PROJECT_ROOT / ".sandbox" / "deep-inquiry-vnext"
SANDBOX_SKILL = SANDBOX_ROOT / "skills" / "deep-inquiry"
SANDBOX_WORKSPACE = SANDBOX_ROOT / "workspace"
SANDBOX_KNOWLEDGE = SANDBOX_ROOT / "knowledge"
FROZEN_SKILL = PROJECT_ROOT / ".trae" / "skills" / "deep-inquiry"
USER_SKILL = Path.home() / ".trae-cn" / "skills" / "deep-inquiry"
VALIDATION_RECORD = (
    PROJECT_ROOT / ".sandbox" / "deep-inquiry-rename-validation.json"
)
CHECKS = (
    "examples/tests/core_contract/knowledge_schema_checks.py",
    "examples/tests/core_contract/knowledge_store_checks.py",
    "examples/tests/core_contract/index_rebuild_checks.py",
    "examples/tests/core_contract/learning_delta_checks.py",
    "examples/tests/core_contract/convergence_checks.py",
    "examples/tests/core_contract/markdown_report_checks.py",
    "examples/tests/behavior/autonomous_loop_checks.py",
    "examples/tests/behavior/knowledge_first_acceptance_checks.py",
    "examples/tests/adapter/skill_identity_checks.py",
    "examples/tests/adapter/skill_localization_checks.py",
    "examples/tests/adapter/query_checks.py",
    "examples/tests/adapter/work_host_vnext_checks.py",
    "examples/tests/adapter/work_host_contract_checks.py",
    "examples/tests/adapter/markdown_report_host_checks.py",
    "examples/tests/migration/migration_v1_checks.py",
    "examples/tests/behavior/eval_vnext_suite.py",
    "examples/tests/adapter/smoke_run.py",
    "examples/tests/behavior/eval_suite.py",
)
EXCLUDED_PACKAGE_PARTS = {
    ".mentor-state",
    "__pycache__",
    ".DS_Store",
}
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

from tests.behavior.eval_vnext.cases import build_initial_topic, ProfileAgent
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


def _verify_installed_copies() -> tuple[str, str]:
    development_hash = _tree_hash(SKILL_ROOT)
    frozen_hash = _tree_hash(FROZEN_SKILL)
    user_hash = _tree_hash(USER_SKILL)
    assert frozen_hash == development_hash, (
        "workspace discovery copy differs from the verified development package"
    )
    assert user_hash == development_hash, (
        "user-level installation differs from the verified development package"
    )
    assert not USER_SKILL.is_symlink(), (
        "user-level installation must be a copied directory, not a symlink"
    )
    assert USER_SKILL.resolve() != SKILL_ROOT.resolve(), (
        "user-level installation must be an independent copy"
    )
    retired_user_skill = (
        Path.home() / ".trae-cn" / "skills" / "autonomous-mentor"
    )
    assert not retired_user_skill.exists() and not retired_user_skill.is_symlink(), (
        "retired user-level Skill installation still exists"
    )
    for label, root in (("frozen", FROZEN_SKILL), ("user", USER_SKILL)):
        result = _run(
            sys.executable,
            "examples/tests/adapter/skill_identity_checks.py",
            cwd=root,
        )
        assert result.returncode == 0, (
            f"{label} installation identity check failed:\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return frozen_hash, user_hash


def _write_validation_record(
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
    VALIDATION_RECORD.parent.mkdir(parents=True, exist_ok=True)
    temporary = VALIDATION_RECORD.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, VALIDATION_RECORD)


def main() -> None:
    assert FROZEN_SKILL.is_dir(), FROZEN_SKILL
    assert USER_SKILL.is_dir(), USER_SKILL
    frozen_hash, user_hash = _verify_installed_copies()

    _rebuild_sandbox()
    _run_sandbox_checks()
    _exercise_sandbox_learning()
    _assert_package_contents()

    _rebuild_sandbox()
    _assert_package_contents()
    assert _tree_hash(FROZEN_SKILL) == frozen_hash
    assert _tree_hash(USER_SKILL) == user_hash
    _write_validation_record(frozen_hash, user_hash)
    assert VALIDATION_RECORD.is_file()
    print("[4/5] installed copies match the package and remain unchanged")
    print("[5/5] ephemeral validation record created; ZIP remains approval-gated")
    print("\nTask 12 sandbox recovery and release gate passed.")


if __name__ == "__main__":
    main()
