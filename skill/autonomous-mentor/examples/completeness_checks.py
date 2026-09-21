#!/usr/bin/env python3
"""P1-1 回归：怀疑者「领域完备性」第四问。

结构三问（最可能错在哪 / 更强替代 / 教学露馅）追不出领域标准实践的必答项，
简审因此增加固定第四问：本解释是否漏掉内行必问项。这仍是认识论判断，
内核不内置知识清单，只保证：四问固定、上下文带完备性提示、命中即回流。

不经过文件协议，直接驱动 Skeptic 与 loop 分发，覆盖：
1. 简审必须回答固定四问（旧三问形状被拒）
2. 预埋缺口 A（软基负摩阻力）经第四问击中 → 回流 LEARN、缺口登记为怀疑来源
3. 预埋缺口 B（风荷载/波浪荷载混为一谈）同样击中
4. 明确回答「无遗漏」→ 不回流，不登记缺口
5. completeness_hint 由状态确定性生成：列出阶段维度、已覆盖/未覆盖维度
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SKILL_ROOT)

from scripts.judgments import BRIEF_QUESTIONS  # noqa: E402
from scripts.loop import MentorLoop, TurnTrace  # noqa: E402
from scripts.schema import QuestionStatus, SchemaError, Stage, TriggerSource  # noqa: E402
from scripts.store import StateStore  # noqa: E402

D1, D2, D3 = "结构选型", "地基基础", "经济性"

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


def _session(loop, store):
    state = store.new_session()
    loop.learner.anchor(state, ANCHOR_OK)
    loop.learner.build_tree(state, TREE_OK)
    for q in state.question_tree.sub_questions:
        q.status = QuestionStatus.STABLE.value
    return state


def _findings(three_pass: list[dict] | None = None, fourth: dict | None = None):
    base = three_pass or [
        {"answer": "无明显错误", "structural_hit": False},
        {"answer": "没有更强替代", "structural_hit": False},
        {"answer": "教学时不会露馅", "structural_hit": False},
    ]
    fourth = fourth or {"answer": "无遗漏", "structural_hit": False}
    return base + [fourth]


def _dispatch_brief(loop, state, response):
    pending = {
        "stage": Stage.BRIEF.value,
        "attempt": 0,
        "stage_explanation": "一版阶段解释",
        "brief_passed": False,
    }
    trace = TurnTrace("自主学习循环", "完备性测试")
    return loop._dispatch_learning(
        state, pending, Stage.BRIEF.value, response, trace
    ), pending


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="mentor-complete-")
    try:
        store = StateStore(os.path.join(tmp, ".mentor-state", "session.json"))
        loop = MentorLoop(store)

        # ---- 1. 固定四问：三问旧形状拒绝；第四问必须是完备性之问 ----
        assert len(BRIEF_QUESTIONS) == 4, f"简审固定问题应为四问，实际 {len(BRIEF_QUESTIONS)}"
        assert "标准实践" in BRIEF_QUESTIONS[3] and "必答" in BRIEF_QUESTIONS[3], (
            BRIEF_QUESTIONS[3]
        )
        state = _session(loop, store)
        try:
            loop.skeptic.parse_brief(state, "解释", 0, {"findings": _findings()[:3]})
            raise AssertionError("三问旧形状必须被拒绝")
        except SchemaError:
            pass
        review = loop.skeptic.parse_brief(
            state, "解释", 0, {"findings": _findings()}
        )
        assert len(review.findings) == 4
        print("[1/5] 简审固定四问，旧三问形状被拒；第四问为领域完备性之问 ✓")

        # ---- 2. 预埋缺口 A：负摩阻力（软基填土/固结导致的下拉荷载）----
        state = _session(loop, store)
        gap_a = {
            "gap_type": "证据缺口",
            "gap_statement": "完全没提软基固结下沉对基桩产生的负摩阻力（下拉荷载），"
                             "这是任何内行做海滩桩基都会追问的必答项",
            "why_priority": "不考虑负摩阻力会低估桩身轴力，导致断桩",
        }
        resp_a = {"findings": _findings(fourth={
            "answer": "存在必答项：负摩阻力未提及",
            "structural_hit": True,
            "loop_gap": gap_a,
        })}
        (kind, _judgment, nxt), pending = _dispatch_brief(loop, state, resp_a)
        assert kind == "request" and nxt == Stage.LEARN.value, (kind, nxt)
        assert state.gap.is_open(), "完备性击中必须登记主认知缺口"
        assert state.gap.trigger_source == TriggerSource.SKEPTIC.value
        assert "负摩阻力" in state.gap.gap_statement
        assert pending["brief_passed"] is False and pending["attempt"] == 1
        print("[2/5] 预埋缺口 A（负摩阻力）经第四问击中 → 回流重学、登记怀疑缺口 ✓")

        # ---- 3. 预埋缺口 B：风荷载与波浪荷载混为一谈 ----
        state = _session(loop, store)
        gap_b = {
            "gap_type": "结构缺口",
            "gap_statement": "把风荷载和波浪荷载合成一个水平力讲，"
                             "内行必问两者的荷载组合方向、周期与工况组合",
            "why_priority": "荷载工况错配直接影响桩身内力计算",
        }
        resp_b = {"findings": _findings(fourth={
            "answer": "存在必答项：风/波浪荷载工况未分开",
            "structural_hit": True,
            "loop_gap": gap_b,
        })}
        (kind, _j, nxt), _p = _dispatch_brief(loop, state, resp_b)
        assert (kind, nxt) == ("request", Stage.LEARN.value), (kind, nxt)
        assert "风荷载" in state.gap.gap_statement
        print("[3/5] 预埋缺口 B（风/波浪荷载工况）经第四问击中 → 回流重学 ✓（命中率 2/2）")

        # ---- 4. 显式回答「无」：四问全未击中 → 不登记缺口、不回 LEARN ----
        state = _session(loop, store)
        # 两维度均已有规则，简审放行后可一路到压缩，排除深度闸门的干扰
        loop.learner.learn_round(
            state, "obj", 0,
            {"stage_explanation": "解释", "understanding_change": "补齐结构",
             "driver": "测试", "proposition_link": "回连命题",
             "dimension_rules": [
                 {"dimension": D1, "rule": "规则甲：风浪大时选桩基础"},
                 {"dimension": D2, "rule": "规则乙：软基先打砂井固结"},
             ]},
        )
        (kind, judgment, nxt), pending = _dispatch_brief(
            loop, state, {"findings": _findings()}
        )
        assert nxt != Stage.LEARN.value, "完备性无遗漏时不得回流"
        assert judgment == "compress_explanation", f"简审放行后应直达压缩，实际 {judgment}"
        assert not state.gap.is_open(), "未击中不得登记缺口"
        assert pending["brief_passed"] is True
        print("[4/5] 第四问明确无遗漏且未击中 → 不回流、不登记缺口，简审放行 ✓")

        # ---- 5. completeness_hint：确定性生成覆盖现状 ----
        state = _session(loop, store)
        hint = loop.build_completeness_hint(state)
        assert D1 in hint["phase_dimensions"] and D2 in hint["phase_dimensions"]
        assert D3 not in hint["phase_dimensions"], "横切/未声明维度不得混入阶段列表"
        # 两个维度都没有规则：全部标为未覆盖
        assert set(hint["dimensions_with_rule"]) == set()
        assert set(hint["uncovered_dimensions"]) == {D1, D2}, hint
        loop.learner.learn_round(
            state, "obj", 0,
            {"stage_explanation": "解释", "understanding_change": "补齐结构",
             "driver": "测试", "proposition_link": "回连命题",
             "dimension_rules": [{"dimension": D1, "rule": "规则：风浪大时选桩基础"}]},
        )
        hint2 = loop.build_completeness_hint(state)
        assert hint2["dimensions_with_rule"] == [D1]
        assert hint2["uncovered_dimensions"] == [D2]
        print("[5/5] completeness_hint：阶段维度+已覆盖/未覆盖维度确定性生成 ✓")

        print("\n怀疑者领域完备性第四问全部断言通过（预埋缺口命中率 2/2）。")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
