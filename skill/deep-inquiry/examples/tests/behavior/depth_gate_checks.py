#!/usr/bin/env python3
"""P0-1 回归：覆盖度闸门升级为「覆盖 + 最低深度」双条件。

不经过文件协议，直接驱动角色对象与闸门函数，覆盖六组断言：
1. 零参数维度（全 stable 但无任何可执行规则/裁决）→ 拦截，回缺口识别，带 depth_hint
2. 怀疑者显式「本命题下无专项增量」裁决 → 放行压缩
3. 维度有 ≥1 条可执行规则 → 放行压缩
4. learn_round 合并 dimension_rules：未知维度拒绝、空规则拒绝、重复规则去重
5. 无增量裁决形状校验：未知维度拒绝、空理由拒绝、与已有规则矛盾拒绝
6. 安全阀 forced_compress 可越过深度闸门；旧会话（无 coverage_dimensions）不启用闸门
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, SKILL_ROOT)

from scripts.loop import MentorLoop, TurnTrace  # noqa: E402
from scripts.schema import QuestionStatus, SchemaError  # noqa: E402
from scripts.store import StateStore  # noqa: E402

D1, D2 = "维度甲", "维度乙"

ANCHOR_OK = {
    "proposition_text": "测试命题",
    "proposition_scope": "测试范围",
    "adjacent_topics": ["邻接a", "邻接b"],
    "scope_qualifiers": ["限定词甲", "限定词乙"],
    "coverage_dimensions": [D1, D2],
    "dimension_sources": [
        {"dimension": D1, "kind": "phase", "source_qualifier": "限定词甲",
         "reason": "", "related_phases": []},
        {"dimension": D2, "kind": "phase", "source_qualifier": "限定词乙",
         "reason": "", "related_phases": []},
    ],
}
TREE_OK = {
    "root_question": "主问题",
    "priority_id": "q1",
    "sub_questions": [
        {"id": "q1", "text": "维度甲问题", "dimension": D1, "depends_on": []},
        {"id": "q2", "text": "维度乙问题", "dimension": D2, "depends_on": ["q1"]},
    ],
}
LEARN_OK = {
    "stage_explanation": "阶段性解释",
    "understanding_change": "补齐了结构",
    "driver": "测试",
    "proposition_link": "直接回连命题",
}


def _ready_session(loop: MentorLoop, store: StateStore, stable: bool = True):
    state = store.new_session()
    loop.learner.anchor(state, ANCHOR_OK)
    loop.learner.build_tree(state, TREE_OK)
    if stable:
        for q in state.question_tree.sub_questions:
            q.status = QuestionStatus.STABLE.value
    return state


def _gate(loop: MentorLoop, state, pending: dict | None = None):
    if pending is None:  # 注意不能用 `pending or {}`：空 dict 为假会导致写回丢失
        pending = {}
    return loop._coverage_gate_or_compress(
        state, pending, TurnTrace("自主学习循环", "双条件闸门测试")
    )


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="mentor-depth-")
    try:
        store = StateStore(os.path.join(tmp, ".mentor-state", "session.json"))
        loop = MentorLoop(store)

        # ---- 1. 零参数维度：全覆盖且全 stable，但没有任何规则/裁决 → 拦截 ----
        state = _ready_session(loop, store)
        pending: dict = {}
        kind, name, stage = _gate(loop, state, pending)
        assert name == "identify_gap", f"零参数维度必须被拦回缺口识别，实际 {name}"
        hint = pending.get("depth_hint")
        assert hint and hint["reason"] == "coverage_gate_zero_depth", hint
        assert set(hint["shallow_dimensions"]) == {D1, D2}, hint
        assert pending["brief_passed"] is False, "拦截后必须重置审查运行时态"
        print("[1/6] 零参数维度（无规则无裁决）→ 拦截压缩、回缺口识别、带 depth_hint ✓")

        # ---- 2. 显式无增量裁决：乙维度无规则，但怀疑者裁决无专项增量 → 放行 ----
        state = _ready_session(loop, store)
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_OK, "dimension_rules": [{"dimension": D1, "rule": "若 A 则 B（参数化规则）"}]},
        )
        loop.skeptic.apply_no_increment_verdicts(
            state,
            {"no_increment_verdicts": [
                {"dimension": D2, "reason": "本命题为纯概念辨析，乙维度与通用做法完全相同，无专项增量"}
            ]},
        )
        kind, name, stage = _gate(loop, state, {})
        assert name == "compress_explanation", f"无增量裁决应放行，实际 {name}"
        rec = next(d for d in state.proposition.dimension_depth if d.dimension == D2)
        assert rec.no_increment and rec.no_increment_reason
        print("[2/6] 怀疑者显式「无专项增量」裁决（带理由）→ 该维度深度条件满足、放行压缩 ✓")

        # ---- 3. 两个维度都有可执行规则 → 放行 ----
        state = _ready_session(loop, store)
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_OK, "dimension_rules": [
                {"dimension": D1, "rule": "规则1：x>10 时取方案A"},
                {"dimension": D2, "rule": "规则2：保护层厚度≥50mm",
                 "basis": "GB 50010-2010 表8.2.1"},
            ]},
        )
        kind, name, stage = _gate(loop, state, {})
        assert name == "compress_explanation", name
        print("[3/6] 每个维度 ≥1 条参数化规则 → 放行压缩 ✓")

        # ---- 4. learn_round 对 dimension_rules 的形状/语义校验 ----
        state = _ready_session(loop, store)
        try:
            loop.learner.learn_round(
                state, "obj", 0,
                {**LEARN_OK, "dimension_rules": [{"dimension": "不存在的维度", "rule": "r"}]},
            )
            raise AssertionError("未知维度的规则必须被拒绝")
        except SchemaError:
            pass
        try:
            loop.learner.learn_round(
                state, "obj", 0,
                {**LEARN_OK, "dimension_rules": [{"dimension": D1, "rule": "   "}]},
            )
            raise AssertionError("空规则必须被拒绝（防止空话过闸）")
        except SchemaError:
            pass
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_OK, "dimension_rules": [
                {"dimension": D1, "rule": "同一规则"},
                {"dimension": D1, "rule": "同一规则"},
                {"dimension": D1, "rule": "另一条规则"},
            ]},
        )
        rec = next(d for d in state.proposition.dimension_depth if d.dimension == D1)
        assert rec.rules == ["同一规则", "另一条规则"], rec.rules
        print("[4/6] dimension_rules：未知维度拒绝、空规则拒绝、同维度重复规则去重 ✓")

        # ---- 5. 无增量裁决的三类非法形状 ----
        state = _ready_session(loop, store)
        for bad in (
            {"no_increment_verdicts": [{"dimension": "幽灵维度", "reason": "x"}]},
            {"no_increment_verdicts": [{"dimension": D1, "reason": "  "}]},
        ):
            try:
                loop.skeptic.apply_no_increment_verdicts(state, bad)
                raise AssertionError(f"非法裁决必须被拒绝: {bad}")
            except SchemaError:
                pass
        # 该维度已有规则时，禁止再裁决为无增量（自相矛盾）
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_OK, "dimension_rules": [{"dimension": D1, "rule": "已有规则"}]},
        )
        try:
            loop.skeptic.apply_no_increment_verdicts(
                state, {"no_increment_verdicts": [{"dimension": D1, "reason": "又说没有增量"}]}
            )
            raise AssertionError("已有可执行规则的维度不能裁决为无增量")
        except SchemaError:
            pass
        print("[5/6] 无增量裁决：未知维度/空理由拒绝，与已有规则矛盾拒绝 ✓")

        # ---- 6. 安全阀与向后兼容 ----
        state = _ready_session(loop, store)  # 零深度
        kind, name, stage = _gate(loop, state, {"forced_compress": True})
        assert name == "compress_explanation", "无限扩张安全阀必须能越过深度闸门"
        # 旧会话：没有 coverage_dimensions，闸门整体不启用
        state.proposition.coverage_dimensions = []
        state.proposition.dimension_sources = []
        kind, name, stage = _gate(loop, state, {})
        assert name == "compress_explanation", "旧会话必须保持向后兼容"
        print("[6/6] forced_compress 安全阀越过深度闸门；旧会话无覆盖维度时不启用 ✓")

        print("\n双条件覆盖度闸门全部断言通过。")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
