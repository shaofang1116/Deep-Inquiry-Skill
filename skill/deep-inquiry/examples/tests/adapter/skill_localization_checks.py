#!/usr/bin/env python3
"""Release contract for canonical English and Chinese companion protocols."""

from __future__ import annotations

from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[3]
CANONICAL = SKILL_ROOT / "SKILL.md"
CHINESE_COMPANION = SKILL_ROOT / "SKILL.zh-CN.md"
COMMAND_LITERALS = (
    ".mentor-state/sessions/<proposition-slug>/session.json",
    'status: "pending"',
    "plan_investigation",
    "request_paths.judgment",
)
CANONICAL_ONLY_LITERALS = (
    'init "<central proposition>"',
    'ask "<user question>"',
    "brief review: four questions",
    "Queries never write user profile, teaching action, feedback state, or durable knowledge.",
)
CHINESE_ONLY_LITERALS = (
    'init "<中心命题>"',
    'ask "<用户问题>"',
    "简审四问",
    "查询不得写入用户画像、教学动作、反馈状态或任何 durable knowledge 字段。",
)
CHINESE_LEGACY_DRIFT = (
    "用户卡在哪",
    "该用哪个教学动作",
    "共 12 个",
    "Task 10",
)


def main() -> None:
    canonical = CANONICAL.read_text(encoding="utf-8")
    chinese = CHINESE_COMPANION.read_text(encoding="utf-8")

    frontmatter = canonical.split("---", 2)[1]
    assert 'name: "deep-inquiry"' in frontmatter
    assert 'description: "Use when ' in frontmatter
    assert "# Deep Inquiry" in canonical
    assert "## Mandatory Execution Gate After Triggering" in canonical
    assert "## When to Use" in canonical
    assert "## Execution Protocol" in canonical
    assert "canonical English protocol" in chinese
    assert "# Deep Inquiry（深度探究）" in chinese
    assert "## 触发后的强制执行闸门" in chinese
    assert "## 执行协议" in chinese

    for literal in COMMAND_LITERALS:
        assert literal in canonical, f"canonical protocol lost: {literal}"
        assert literal in chinese, f"Chinese companion lost: {literal}"
    for literal in CANONICAL_ONLY_LITERALS:
        assert literal in canonical, f"canonical protocol lost: {literal}"
    for literal in CHINESE_ONLY_LITERALS:
        assert literal in chinese, f"Chinese companion lost: {literal}"
    for phrase in CHINESE_LEGACY_DRIFT:
        assert phrase not in chinese, f"Chinese companion retains legacy v1 behavior: {phrase}"

    print("Skill localization checks passed.")


if __name__ == "__main__":
    main()
