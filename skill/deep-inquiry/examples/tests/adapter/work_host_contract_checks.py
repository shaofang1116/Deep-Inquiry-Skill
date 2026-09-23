#!/usr/bin/env python3
"""Regression check for the host CLI-first execution contract."""

from __future__ import annotations

from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[3]
SKILL_MD = SKILL_ROOT / "SKILL.md"


def main() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]

    assert 'description: "Use when ' in frontmatter, (
        "description must describe triggering rather than replace the workflow"
    )

    gate_heading = "## Mandatory Execution Gate After Triggering"
    gate_pos = text.find(gate_heading)
    usage_pos = text.find("## When to Use")
    assert gate_pos >= 0, "missing mandatory host execution gate"
    assert gate_pos < usage_pos, "mandatory execution gate must precede usage"

    required_fragments = [
        "first non-Skill tool call",
        "--knowledge-root",
        "--topic-id",
        'init "<central proposition>"',
        "learn",
        'ask "<user question>"',
        ".mentor-state/sessions/<proposition-slug>/session.json",
        "do not use `mkdir`",
        "do not answer directly",
        "Do not silently degrade",
        'status: "pending"',
        "next_action",
        "plan_investigation",
        "research tool",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in text]
    assert not missing, f"execution contract is missing: {missing}"

    print("Host execution contract passed: CLI-first, loop, isolation, and no degradation.")


if __name__ == "__main__":
    main()
