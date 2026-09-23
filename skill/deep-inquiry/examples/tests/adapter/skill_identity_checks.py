#!/usr/bin/env python3
"""Release contract for the Deep Inquiry public Skill identity."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parents[3]
SKILL_MD = SKILL_ROOT / "SKILL.md"
CLI = SKILL_ROOT / "scripts" / "cli.py"
PACKAGE_CHECK = SKILL_ROOT / "examples" / "tests" / "adapter" / "package_vnext_checks.py"
LEGACY_PROVENANCE = "autonomous-mentor-v1"
RETIRED_SKILL_ID = "autonomous-mentor"


def _assert_workspace_discovery() -> None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=SKILL_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return
    workspace = Path(result.stdout.strip())
    canonical = workspace / "skill" / "deep-inquiry"
    retired_package = workspace / "skill" / RETIRED_SKILL_ID
    discovery = workspace / ".trae" / "skills" / "deep-inquiry"
    retired_discovery = workspace / ".trae" / "skills" / RETIRED_SKILL_ID

    assert canonical.is_dir() and not canonical.is_symlink(), canonical
    assert not retired_package.exists() and not retired_package.is_symlink()
    assert discovery.is_symlink(), discovery
    assert discovery.resolve() == canonical.resolve()
    assert not retired_discovery.exists() and not retired_discovery.is_symlink()
    for skill_md in (workspace / ".trae" / "skills").glob("*/SKILL.md"):
        frontmatter = skill_md.read_text(encoding="utf-8").split("---", 2)[1]
        assert f'name: "{RETIRED_SKILL_ID}"' not in frontmatter, skill_md


def main() -> None:
    assert SKILL_ROOT.name == "deep-inquiry", SKILL_ROOT

    text = SKILL_MD.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    assert 'name: "deep-inquiry"' in frontmatter
    assert "# Deep Inquiry" in text
    assert "`deep-inquiry/`" in text

    help_result = subprocess.run(
        [sys.executable, str(CLI), "--help"],
        cwd=SKILL_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0, help_result.stderr
    assert help_result.stdout.startswith("usage: deep-inquiry ")
    assert "Deep Inquiry" in help_result.stdout

    package_text = PACKAGE_CHECK.read_text(encoding="utf-8")
    assert '".sandbox" / "deep-inquiry-vnext"' in package_text
    assert '"skills" / "deep-inquiry"' in package_text
    assert 'Path.home() / ".trae-cn" / "skills" / "deep-inquiry"' in package_text

    unexpected = []
    for path in SKILL_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py", ".json"}:
            continue
        if path == Path(__file__):
            continue
        content = path.read_text(encoding="utf-8")
        if RETIRED_SKILL_ID not in content:
            continue
        if path == SKILL_ROOT / "scripts" / "migrate_v1.py":
            assert LEGACY_PROVENANCE in content
            continue
        if path == PACKAGE_CHECK:
            assert "retired_user_skill" in content
            assert "not retired_user_skill.exists()" in content
            continue
        unexpected.append(path.relative_to(SKILL_ROOT).as_posix())
    assert not unexpected, f"active package retains retired identity: {unexpected}"

    mentor_text = (SKILL_ROOT / "scripts" / "mentor.py").read_text(encoding="utf-8")
    loop_text = (SKILL_ROOT / "scripts" / "loop.py").read_text(encoding="utf-8")
    assert "class Mentor:" in mentor_text
    assert "class MentorLoop:" in loop_text
    _assert_workspace_discovery()
    print("Deep Inquiry identity checks passed.")


if __name__ == "__main__":
    main()
