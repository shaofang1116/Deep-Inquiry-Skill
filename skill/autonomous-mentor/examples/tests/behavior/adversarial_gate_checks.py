#!/usr/bin/env python3
"""对抗性宿主端到端压测：恶意/偷懒作答必须被硬闸门拦截。

与 depth_gate_checks（直接驱动角色对象的单元测试）不同，本文件完全经文件协议
（request.json / judgment.json / pending.json → loop.step()）驱动，模拟一个真实
但偷懒、甚至作弊的宿主 agent，验证拦截发生在完整链路里而不只是单元边界。

攻击场景：
A. 伪精确数值：learn_round 提交带计量单位的规则，但无 basis 也不标 heuristic
   → 内核必须拒绝，且该规则不得落库；原地补上 basis 后必须能通过（协议可自愈）。
B. 空话规则：rule 为空串 → 内核必须拒绝（「应注意/需考虑」不得计入深度）。
C. 零深度冲压缩：全部节点标 stable、一条规则不给、简审/深审都放行
   → 压缩前最低深度闸门必须拦回缺口识别。
D. 缺枝维度：问题树故意只建一个主干维度 → 覆盖闸门必须拦回问题树补枝。
E. 占位不学透：两维节点都在但一个都不标 stable、零规则 → 必须拦回缺口补学。
F. 简审固定问法被篡改（真实宿主形状回补）：宿主概括/截断四问 question 文本
   → 内核必须拒绝（逐字校验），逐字照抄 BRIEF_QUESTIONS 后必须放行。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "examples"))

from scripts.judgments import BRIEF_QUESTIONS, EXPAND_TREE  # noqa: E402
from scripts.loop import DoneOutcome, MentorLoop, PendingOutcome  # noqa: E402
from scripts.schema import GapType  # noqa: E402
from scripts.store import StateStore  # noqa: E402
import tests.behavior.scripted_judge as scripted_judge  # noqa: E402
from tests.behavior.eval.cases.mechanism import MechanismCase  # noqa: E402
from tests.behavior.samples import PROPOSITIONS  # noqa: E402

PROP = PROPOSITIONS["mechanism"]["text"]
DIMS = ["概念定义", "作用机制"]

# 合法内容单一事实来源在 eval 机制型用例；对抗场景只替换被攻击判断点
_CASE = MechanismCase()


# ---------- 对抗响应构造 ----------

def _brief_all_clear():
    """简审固定四问，每问都放行（含完备性第四问）。"""
    return {
        "findings": [
            {"question": BRIEF_QUESTIONS[0], "answer": "未发现结构脆弱点",
             "structural_hit": False, "loop_gap": None},
            {"question": BRIEF_QUESTIONS[1], "answer": "无成立的替代解释",
             "structural_hit": False, "loop_gap": None},
            {"question": BRIEF_QUESTIONS[2], "answer": "教学暴露点本轮不攻击",
             "structural_hit": False, "loop_gap": None},
            {"question": BRIEF_QUESTIONS[3],
             "answer": "对照完备性提示无遗漏：本命题讨论怀疑机制本身",
             "structural_hit": False, "loop_gap": None},
        ]
    }


def _gap():
    return {
        "gap_type": GapType.STRUCTURE.value,
        "gap_statement": "机制链条存在待补环节",
        "why_priority": "压缩前必须补齐",
        "secondary_gaps": [],
    }


def _anchor_three_dims():
    """攻击 D 专用锚定：声明三个主干维度（建树时故意只覆盖前两个）。"""
    return {
        "proposition_text": PROP,
        "proposition_scope": f"围绕「{PROP}」本身如何成立、如何起作用展开，不延伸到周边主题",
        "adjacent_topics": ["资料搜集与工具评测", "一般学习理论与流派比较"],
        "scope_qualifiers": ["怀疑机制", "避免伪理解", "边界条件"],
        "coverage_dimensions": ["概念定义", "作用机制", "边界条件"],
        "dimension_sources": [
            {"dimension": "概念定义", "kind": "phase",
             "source_qualifier": "怀疑机制", "reason": "", "related_phases": []},
            {"dimension": "作用机制", "kind": "phase",
             "source_qualifier": "避免伪理解", "reason": "", "related_phases": []},
            {"dimension": "边界条件", "kind": "phase",
             "source_qualifier": "边界条件",
             "reason": "机制在什么条件下失效是命题主张的限定部分", "related_phases": []},
        ],
    }


def _learn(stable_ids, rules):
    return {
        "stage_explanation": "偷懒宿主的阶段性解释：机制已经清楚，细节略。",
        "understanding_change": "无实质变化",
        "driver": "按主缺口推进",
        "proposition_link": f"回连命题「{PROP}」",
        "resolved_gap": True,
        "stable_question_ids": stable_ids,
        "new_sub_questions": [],
        "next_priority_id": None,
        "competing_explanations": False,
        "dimension_rules": rules,
    }


def adversarial_response(request, scenario):
    """按场景返回对抗响应；锚定与深审复用合法夹具。"""
    name = request["judgment"]
    if name == "anchor_proposition":
        return _CASE.anchor(request.get("context", {}))
    if name == "expand_tree":
        # 各场景在建树判断点直接提交响应，不经此分发；走到这里说明脚本有误
        raise AssertionError("expand_tree 响应应在场景内直接构造")
    if name == "identify_gap":
        return _gap()
    if name == "learn_round":
        if scenario == "A":
            return _learn(["q1"], [
                {"dimension": "概念定义",
                 "rule": "保护层厚度必须不小于55mm，否则返工"},
            ])
        if scenario == "B":
            return _learn(["q1"], [{"dimension": "概念定义", "rule": "   "}])
        if scenario == "C":
            return _learn(["q1", "q2", "q3"], [])  # 全 stable、零规则
        if scenario == "E":
            return _learn([], [])  # 节点全 open、零规则
        return _learn(["q1"], [])
    if name == "brief_review":
        return _brief_all_clear()
    if name == "deep_review":
        return _CASE.deep({}, {})
    raise AssertionError(f"攻击不应到达的判断点：{name}")


# ---------- 驱动辅助 ----------

def fresh_loop(tmp):
    path = os.path.join(tmp, ".mentor-state", "session.json")
    return MentorLoop(StateStore(path)), path


def submit(loop, outcome, response):
    """经真实文件协议提交判断并 step 一次。"""
    loop.store.write_judgment(
        {"judgment": outcome.request.name, "response": response}
    )
    return loop.step()


def scripted_reply(outcome):
    """读盘上 request.json，用合法夹具给出该判断点的响应。"""
    import json
    with open(outcome.request_path, encoding="utf-8") as f:
        return scripted_judge.build_judgment(json.load(f))


def tree_full(outcome):
    import json
    with open(outcome.request_path, encoding="utf-8") as f:
        snap = json.load(f)["state_snapshot"]
    return _CASE.tree(snap, {})


def anchor(loop):
    outcome = loop.begin_init(PROP)
    done = submit(loop, outcome, scripted_reply(outcome))
    assert isinstance(done, DoneOutcome)
    return done


def begin_learn(loop):
    return loop.begin_learning()


def gate_events_text(loop):
    """从盘上 pending.json 读累计 trace（宿主可在 request 上下文看到同一拦截原因）。"""
    pending = loop.store.load_pending()
    return " | ".join(e.get("summary", "") for e in pending["trace"]["events"])


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="mentor-adv-")
    try:
        # ---- A. 伪精确数值：无 basis/heuristic 必须被拒，且不得落库 ----
        loop, path = fresh_loop(tmp + "/A")
        anchor(loop)
        outcome = begin_learn(loop)
        # expand_tree → identify_gap → learn_round
        outcome = submit(loop, outcome, tree_full(outcome))
        outcome = submit(loop, outcome, _gap())
        assert outcome.request.name == "learn_round", outcome.request.name
        try:
            submit(loop, outcome, adversarial_response(
                {"judgment": "learn_round"}, "A"))
            raise AssertionError("A 失败：无出处的数值规则竟被内核接受")
        except Exception as exc:  # noqa: BLE001
            assert "溯源" in str(exc) or "heuristic" in str(exc), str(exc)
        state = StateStore(path).load()
        n_rules = sum(len(d.rules) for d in state.proposition.dimension_depth)
        assert n_rules == 0, f"A 失败：被拒规则疑似已落库（{n_rules} 条）"
        # 协议可自愈：同一判断点原地补上 basis 后必须通过
        ok_resp = _learn(["q1"], [
            {"dimension": "概念定义",
             "rule": "保护层厚度必须不小于55mm，否则返工",
             "basis": "GB 50010-2010 表8.2.1", "heuristic": False},
        ])
        outcome = submit(loop, outcome, ok_resp)
        assert outcome.request.name == "brief_review", outcome.request.name
        print("[A/6] 伪精确数值（55mm 无出处）被拒且未落库；补 basis 后原地放行 ✓")

        # ---- B. 空话规则：空文本必须被拒 ----
        loop, path = fresh_loop(tmp + "/B")
        anchor(loop)
        outcome = begin_learn(loop)
        outcome = submit(loop, outcome, tree_full(outcome))
        outcome = submit(loop, outcome, _gap())
        try:
            submit(loop, outcome, adversarial_response(
                {"judgment": "learn_round"}, "B"))
            raise AssertionError("B 失败：空规则竟被接受")
        except Exception as exc:  # noqa: BLE001
            assert any(k in str(exc) for k in ("为空", "空话", "缺少非空")), str(exc)
        print("[B/6] 空话/空文本规则被拒（不得计入最低深度） ✓")

        # ---- C. 零深度冲压缩：全 stable + 零规则 + 审查全放行 → 拦回 GAP ----
        loop, path = fresh_loop(tmp + "/C")
        anchor(loop)
        outcome = begin_learn(loop)
        outcome = submit(loop, outcome, tree_full(outcome))
        outcome = submit(loop, outcome, _gap())
        outcome = submit(loop, outcome, adversarial_response(
            {"judgment": "learn_round"}, "C"))
        assert outcome.request.name == "brief_review"
        outcome = submit(loop, outcome, _brief_all_clear())
        # 首轮 about_to_stabilize=True 触发深审；深审也放行
        if outcome.request.name == "deep_review":
            outcome = submit(loop, outcome, _CASE.deep({}, {}))
        assert outcome.request.name == "identify_gap", (
            f"C 失败：零维度深度竟放往 {outcome.request.name}"
        )
        assert "最低深度闸门" in gate_events_text(loop), gate_events_text(loop)
        state = StateStore(path).load()
        assert state.proposition.proposition_version == 0, "被拦截时不得产出新版本"
        print("[C/6] 全 stable 零规则冲压缩：最低深度闸门拦回缺口识别，不产版本 ✓")

        # ---- D. 缺枝维度：锚定 3 维、建树只覆盖 2 维 → 建树阶段拒绝，补枝后自愈 ----
        loop, path = fresh_loop(tmp + "/D")
        outcome = loop.begin_init(PROP)
        assert isinstance(submit(loop, outcome, _anchor_three_dims()), DoneOutcome)
        outcome = begin_learn(loop)
        assert outcome.request.name == EXPAND_TREE
        try:
            submit(loop, outcome, tree_full(outcome))  # 夹具树只覆盖前两维
            raise AssertionError("D 失败：树未覆盖全部锚定维度竟被接受")
        except Exception as exc:  # noqa: BLE001
            assert "未覆盖锚定声明的主干维度" in str(exc) and "边界条件" in str(exc), str(exc)
        # 判断未被消费：原地补齐第三维后必须通过
        tree_3dim = {
            "root_question": f"如何理解「{PROP}」？",
            "sub_questions": [
                {"id": "q1", "text": f"「{PROP}」中的核心概念分别指什么？",
                 "dimension": "概念定义", "depends_on": [], "parent_id": ""},
                {"id": "q2", "text": "这些概念之间按什么关系形成机制？",
                 "dimension": "作用机制", "depends_on": ["q1"], "parent_id": ""},
                {"id": "q3", "text": "这套机制在什么条件下失效？",
                 "dimension": "边界条件", "depends_on": ["q2"], "parent_id": ""},
            ],
            "priority_id": "q1",
        }
        outcome = submit(loop, outcome, tree_3dim)
        assert outcome.request.name == "identify_gap", outcome.request.name
        print("[D/6] 锚定 3 维、建树偷漏 1 维：build_tree 拒绝并保留判断点，补枝后通过 ✓")

        # ---- E. 占位不学透：节点全 open + 零规则 → 拦回缺口补学 ----
        loop, path = fresh_loop(tmp + "/E")
        anchor(loop)
        outcome = begin_learn(loop)
        outcome = submit(loop, outcome, tree_full(outcome))
        outcome = submit(loop, outcome, _gap())
        outcome = submit(loop, outcome, adversarial_response(
            {"judgment": "learn_round"}, "E"))
        outcome = submit(loop, outcome, _brief_all_clear())
        if outcome.request.name == "deep_review":
            outcome = submit(loop, outcome, _CASE.deep({}, {}))
        assert outcome.request.name == "identify_gap", (
            f"E 失败：占位维度竟放往 {outcome.request.name}"
        )
        assert "尚未学透" in gate_events_text(loop), gate_events_text(loop)
        print("[E/6] 维度占位但零 stable：覆盖闸门拦回缺口补学 ✓")

        # ---- F. 简审固定问法被篡改（真实宿主形状回补）：截断第四问 question 必须被拒 ----
        loop, path = fresh_loop(tmp + "/F")
        anchor(loop)
        outcome = begin_learn(loop)
        outcome = submit(loop, outcome, tree_full(outcome))
        outcome = submit(loop, outcome, _gap())
        # 合法 learn：q1 stable + 1 条规则，确保流程推到 brief_review
        outcome = submit(loop, outcome, _learn(["q1"], [
            {"dimension": "概念定义", "rule": "伪理解判定式：复述流畅但追问前提即断裂即记为伪理解"},
        ]))
        assert outcome.request.name == "brief_review", outcome.request.name
        # 篡改第四问：保留前三问原文，第四问 question 截断为概括版
        tampered = _brief_all_clear()
        tampered["findings"][3] = {
            "question": "在该领域的标准实践中，是否存在必答项？",
            "answer": "无",
            "structural_hit": False, "loop_gap": None,
        }
        try:
            submit(loop, outcome, tampered)
            raise AssertionError("F 失败：篡改第四问问法竟被内核接受")
        except Exception as exc:  # noqa: BLE001
            assert "必须固定为" in str(exc), str(exc)
        # 判断未被消费：原地逐字照抄 BRIEF_QUESTIONS 后必须通过
        outcome = submit(loop, outcome, _brief_all_clear())
        assert outcome.request.name in ("deep_review", "identify_gap"), outcome.request.name
        print("[F/6] 简审第四问问法被截断/概括：逐字校验拒绝，照抄后放行（真实宿主形状回补） ✓")

        print("\n对抗性压测 6/6 通过：硬闸门在端到端链路中真实拦截。")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
