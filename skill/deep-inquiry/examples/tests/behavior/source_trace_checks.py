#!/usr/bin/env python3
"""P1-3 回归：证据溯源与伪精确标记。

可执行规则/取值默认要可溯源：
- 带计量单位的数值规则，要么给 basis（规范编号级出处），要么显式标
  heuristic=true（经验启发式，无统一出处）；两者皆无即「伪精确」，拒绝；
- heuristic 规则渲染时必须强制附带「经验启发式，须以当地规划为准」；
- 逻辑推导型无数值规则不需要出处；
- 证据条目支持 citation（规范编号级出处）并随状态持久化；
- heuristic 规则照常计入最低深度（它仍是可执行规则，只是不能伪装成定论）。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, SKILL_ROOT)

from scripts.loop import MentorLoop, TurnTrace  # noqa: E402
from scripts.schema import HEURISTIC_NOTE, QuestionStatus, SchemaError  # noqa: E402
from scripts.store import StateStore  # noqa: E402

D1, D2 = "结构选型", "地基基础"

ANCHOR_OK = {
    "proposition_text": "海滩架空建筑建造测试命题",
    "proposition_scope": "软基海滩架空建筑",
    "adjacent_topics": ["海岸动力学", "滨海生态保护"],
    "scope_qualifiers": ["结构如何选型", "地基怎么处理"],
    "coverage_dimensions": [D1, D2],
    "dimension_sources": [
        {"dimension": D1, "kind": "phase", "source_qualifier": "结构如何选型",
         "reason": "", "related_phases": []},
        {"dimension": D2, "kind": "phase", "source_qualifier": "地基怎么处理",
         "reason": "", "related_phases": []},
    ],
}
TREE_OK = {
    "root_question": "海滩架空建筑如何站稳？",
    "priority_id": "q1",
    "sub_questions": [
        {"id": "q1", "text": "结构选型的决定因素有哪些？", "dimension": D1, "depends_on": []},
        {"id": "q2", "text": "软基上桩基如何布置？", "dimension": D2, "depends_on": ["q1"]},
    ],
}
LEARN_BASE = {
    "stage_explanation": "阶段性解释",
    "understanding_change": "补齐了结构",
    "driver": "测试",
    "proposition_link": "直接回连命题",
}


def _session(loop, store):
    state = store.new_session()
    loop.learner.anchor(state, ANCHOR_OK)
    loop.learner.build_tree(state, TREE_OK)
    for q in state.question_tree.sub_questions:
        q.status = QuestionStatus.STABLE.value
    return state


def _depth(state, dim=D1):
    return next(d for d in state.proposition.dimension_depth if d.dimension == dim)


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="mentor-src-")
    try:
        store = StateStore(os.path.join(tmp, ".mentor-state", "session.json"))
        loop = MentorLoop(store)

        # ---- 1. 伪精确防线：数值规则无出处且未标启发式 → 拒绝 ----
        state = _session(loop, store)
        for bad_rule in (
            "退让距离按 30/50/100/200米取值",  # 老 v5 被订正的那条经验值
            "保护层厚度不小于 50mm",
            "桩径取 600mm",
        ):
            try:
                loop.learner.learn_round(
                    state, "obj", 0,
                    {**LEARN_BASE, "dimension_rules": [{"dimension": D1, "rule": bad_rule}]},
                )
                raise AssertionError(f"无出处的数值规则必须拒绝（伪精确）: {bad_rule}")
            except SchemaError:
                pass
        print("[1/6] 带单位的数值规则：无 basis 且未标 heuristic → 拒绝（防伪精确）✓")

        # ---- 2. 数值规则 + 规范编号出处 → 接受，出处随规则持久化 ----
        state = _session(loop, store)
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_BASE, "dimension_rules": [{
                "dimension": D1,
                "rule": "浪溅区钢筋保护层厚度不小于 65mm",
                "basis": "JTS 151-2011《水运工程混凝土结构设计规范》表 4.4.2",
            }]},
        )
        rec = _depth(state)
        assert rec.rule_meta["浪溅区钢筋保护层厚度不小于 65mm"]["basis"].startswith("JTS 151")
        assert rec.render_rule("浪溅区钢筋保护层厚度不小于 65mm").endswith("65mm"), (
            "有出处的确定规则不得追加启发式免责声明"
        )
        print("[2/6] 数值规则带规范编号 basis → 接受、meta 持久化、不附加免责标记 ✓")

        # ---- 3. 数值规则 + heuristic=true → 接受，渲染强制带免责语 ----
        state = _session(loop, store)
        rule = "退让距离无明值时按 200米估算"
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_BASE, "dimension_rules": [{
                "dimension": D2, "rule": rule, "heuristic": True,
                "basis": "地方项目经验区间 30/50/100/200",
            }]},
        )
        rec = _depth(state, D2)
        assert rec.rule_meta[rule]["heuristic"] is True
        rendered = rec.render_rule(rule)
        assert rendered.endswith(HEURISTIC_NOTE) and "经验启发式" in rendered
        # 持久化往返
        store.save(state)
        state2 = store.load()
        rec2 = next(d for d in state2.proposition.dimension_depth if d.dimension == D2)
        assert rec2.rule_meta[rule]["heuristic"] is True
        print("[3/6] 经验值显式标 heuristic → 接受、渲染强制带「须以当地规划为准」、往返持久化 ✓")

        # ---- 4. 逻辑推导型无数值规则无需 basis/heuristic ----
        state = _session(loop, store)
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_BASE, "dimension_rules": [
                {"dimension": D1, "rule": "稳定解释必须自带至少一个教学检验位"},
                {"dimension": D1, "rule": "若两种荷载工况方向不同则不得合并为一个水平力"},
            ]},
        )
        rec = _depth(state)
        assert all(not m.get("heuristic") for m in rec.rule_meta.values())
        print("[4/6] 无数值的逻辑推导规则无需出处，正常计入深度 ✓")

        # ---- 5. 形状校验：basis 必须字符串、heuristic 必须布尔 ----
        state = _session(loop, store)
        for bad in (
            {"dimension": D1, "rule": "桩距 3m", "basis": 123},
            {"dimension": D1, "rule": "桩距 3m", "heuristic": "true"},
        ):
            try:
                loop.learner.learn_round(
                    state, "obj", 0, {**LEARN_BASE, "dimension_rules": [bad]}
                )
                raise AssertionError(f"非法 meta 形状必须拒绝: {bad}")
            except SchemaError:
                pass
        print("[5/6] basis/heuristic 非法类型被拒 ✓")

        # ---- 6. heuristic 规则计入最低深度；证据 citation 随压缩持久化 ----
        state = _session(loop, store)
        loop.learner.learn_round(
            state, "obj", 0,
            {**LEARN_BASE, "dimension_rules": [
                {"dimension": D1, "rule": "经验桩距约 3m", "heuristic": True},
                {"dimension": D2, "rule": "经验桩距约 3.5m", "heuristic": True},
            ],
             "evidence": [{
                 "evidence_type": "来源观察",
                 "content": "地方滨海项目常用桩距经验区间",
                 "source": "地区惯例汇编",
                 "citation": "无统一规范条文，见地方规划技术指引",
             }]},
        )
        proposal = loop.compressor.propose(state, "阶段解释", {
            "explanation": "一版解释",
            "open_boundaries": ["极端风暴潮工况未覆盖"],
            "reason": "双维度均已有可执行规则",
        })
        applied = loop.compressor.apply(state, proposal, [
            {"evidence_type": "来源观察", "content": "地方滨海项目常用桩距经验区间",
             "source": "地区惯例汇编", "citation": "无统一规范条文，见地方规划技术指引"},
        ])
        assert applied["new_version"] == 1
        ev = state.proposition.evidence_book[-1]
        assert ev.citation == "无统一规范条文，见地方规划技术指引"
        # 闸门：heuristic 规则同样满足最低深度
        gate = loop._coverage_gate_or_compress(
            state, {}, TurnTrace("自主学习循环", "溯源测试")
        )
        assert gate[1] == "compress_explanation", f"启发式规则应计入深度，实际闸门 {gate[1]}"
        store.save(state)
        state3 = store.load()
        assert state3.proposition.evidence_book[-1].citation.startswith("无统一规范条文")
        print("[6/6] heuristic 规则计入最低深度；证据 citation 随压缩落库并持久化 ✓")

        print("\n证据溯源与伪精确标记全部断言通过。")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
