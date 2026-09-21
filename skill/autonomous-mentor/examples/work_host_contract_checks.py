#!/usr/bin/env python3
"""回归检查：Work 类宿主加载 Skill 后必须先进入 CLI 文件协议。"""

from __future__ import annotations

from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_ROOT / "SKILL.md"


def main() -> None:
    text = SKILL_MD.read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]

    assert 'description: "Use when ' in frontmatter, (
        "description 必须只描述触发条件，避免模型把摘要当成完整工作流"
    )

    gate_heading = "## 触发后的强制执行闸门"
    gate_pos = text.find(gate_heading)
    usage_pos = text.find("## 何时使用")
    assert gate_pos >= 0, "缺少 Work 宿主强制执行闸门"
    assert gate_pos < usage_pos, "强制执行闸门必须位于一般说明之前"

    required_fragments = [
        "首个非 Skill 工具调用",
        "--knowledge-root",
        "--topic-id",
        'init "<中心命题>"',
        "learn",
        'ask "<用户问题>"',
        ".mentor-state/sessions/<proposition-slug>/session.json",
        "不得先用 mkdir",
        "不得直接回答",
        "不得静默降级",
        'status: "pending"',
        "next_action",
        "plan_investigation",
        "研究工具",
    ]
    missing = [fragment for fragment in required_fragments if fragment not in text]
    assert not missing, f"强制执行契约缺少：{missing}"

    print("Work 宿主执行契约检查通过：CLI 首动作、完整循环、多命题隔离、禁止降级均已声明。")


if __name__ == "__main__":
    main()
