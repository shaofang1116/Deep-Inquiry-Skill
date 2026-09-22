#!/usr/bin/env python3
"""P1-4 回归：压缩定稿时悬置 open 节点必须显式处置。

v1 海滩重跑暴露的瑕疵：二级节点 q1b/q1c 的规则已沉淀、审查已放行，
但宿主忘了在 stable_question_ids 回补，闸门只按维度计数（同维有一个
stable 即过），两个节点永久滞留 open。修复原则：版本定稿时，内核按状态
现算全部 open 节点，宿主必须逐个二选一处置——
  stabilize_question_ids：规则已答，定稿即回补 stable；
  retain_open_questions：确属未决，必须带理由，理由并入开放边界。
不漏、不伪、不可无理由遗忘。

断言：
1-4 负向：未处置 / 漏处置 / retain 无理由 / id 不存在 → propose 拒绝
5.  全 stabilize → apply 后节点 stable，边界不被节点理由污染
6.  全 retain 带理由 → 节点保持 open，理由进入开放边界
7.  无 open 节点时旧形状 judgment（不带新字段）正常（向后兼容）
8.  端到端：COMPRESS 请求上下文带 stale_open_nodes；不处置 step 拒绝；
    处置后压缩完成且节点落定
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "examples"))

from scripts.compressor import Compressor  # noqa: E402
from scripts.judgments import BRIEF_QUESTIONS  # noqa: E402
from scripts.loop import DoneOutcome, MentorLoop  # noqa: E402
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
        {"id": "q3", "text": "维度乙的深挖追问", "dimension": D2,
         "depends_on": ["q2"], "parent_id": "q2"},
    ],
}


def _state_with_open(loop, store, open_ids=("q3",)):
    """两维都已 stable+有规则，但 q3 悬置 open（v1 瑕疵的最小复现）。"""
    state = store.new_session()
    loop.learner.anchor(state, ANCHOR_OK)
    loop.learner.build_tree(state, TREE_OK)
    for q in state.question_tree.sub_questions:
        if q.id not in open_ids:
            q.status = QuestionStatus.STABLE.value
    state.proposition.get_dimension_depth(D1)  # 仅占位避免误读
    rec = state.proposition.dimension_depth
    from scripts.schema import DimensionDepth
    rec.append(DimensionDepth(dimension=D1, rules=["甲维判定式：条件A触发措施甲"]))
    rec.append(DimensionDepth(dimension=D2, rules=["乙维判定式：条件B触发措施乙"]))
    return state


def _compress_judgment(**kw):
    base = {
        "explanation": "当前版本最稳解释",
        "open_boundaries": ["一个尚未解决的边界"],
        "reason": "结构稳定、边界清楚，可以阶段收敛",
    }
    base.update(kw)
    return base


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="mentor-open-")
    try:
        store = StateStore(os.path.join(tmp, ".mentor-state", "session.json"))
        loop = MentorLoop(store)
        comp = Compressor()

        # ---- 1. 悬置 open 未处置 → 拒绝 ----
        state = _state_with_open(loop, store)
        try:
            comp.propose(state, "阶段解释", _compress_judgment())
            raise AssertionError("1 失败：悬置 open 节点未处置竟允许压缩")
        except SchemaError as exc:
            assert "q3" in str(exc) and ("处置" in str(exc) or "open" in str(exc)), str(exc)
        print("[1/8] 悬置 open 节点无处置：压缩被拒 ✓")

        # ---- 2. 处置并集不全（漏掉 q3）→ 拒绝 ----
        state = _state_with_open(loop, store)
        try:
            comp.propose(state, "阶段解释",
                         _compress_judgment(stabilize_question_ids=["q1"]))
            raise AssertionError("2 失败：漏处置 q3 竟允许压缩")
        except SchemaError as exc:
            assert "q3" in str(exc), str(exc)
        print("[2/8] stabilize/retain 未覆盖全部悬置节点：压缩被拒 ✓")

        # ---- 3. retain 缺理由 → 拒绝 ----
        state = _state_with_open(loop, store)
        try:
            comp.propose(state, "阶段解释", _compress_judgment(
                retain_open_questions=[{"id": "q3", "reason": "  "}]))
            raise AssertionError("3 失败：retain 无理由竟允许压缩")
        except SchemaError as exc:
            assert "理由" in str(exc), str(exc)
        print("[3/8] retain_open_questions 缺非空理由：压缩被拒 ✓")

        # ---- 4. 处置含不存在 id → 拒绝 ----
        state = _state_with_open(loop, store)
        try:
            comp.propose(state, "阶段解释", _compress_judgment(
                stabilize_question_ids=["q3", "q99"]))
            raise AssertionError("4 失败：伪造节点 id 竟允许压缩")
        except SchemaError as exc:
            assert "q99" in str(exc), str(exc)
        print("[4/8] 处置含树中不存在的节点 id：压缩被拒 ✓")

        # ---- 5. 全 stabilize → apply 回补 stable，边界不污染 ----
        state = _state_with_open(loop, store)
        proposal = comp.propose(state, "阶段解释", _compress_judgment(
            stabilize_question_ids=["q3"]))
        applied = comp.apply(state, proposal)
        assert applied["new_version"] == 1
        assert state.question_tree.get("q3").status == QuestionStatus.STABLE.value
        assert not any("q3" in b or "未闭合子问题" in b for b in state.proposition.open_boundaries)
        print("[5/8] 全 stabilize：定稿即回补 stable，版本升级，开放边界不污染 ✓")

        # ---- 6. 全 retain 带理由 → 仍 open，理由进开放边界 ----
        state = _state_with_open(loop, store)
        proposal = comp.propose(state, "阶段解释", _compress_judgment(
            open_boundaries=["一个尚未解决的边界"],
            retain_open_questions=[{"id": "q3", "reason": "该追问依赖下阶段专项资料，本版无法闭合"}]))
        comp.apply(state, proposal)
        assert state.question_tree.get("q3").status == QuestionStatus.OPEN.value
        assert any("未闭合子问题" in b and "q3" in b and "专项资料" in b
                   for b in state.proposition.open_boundaries), state.proposition.open_boundaries
        print("[6/8] 全 retain 带理由：节点保持 open，理由并入开放边界 ✓")

        # ---- 7. 无 open 节点：旧形状 judgment 兼容 ----
        state = _state_with_open(loop, store, open_ids=())
        proposal = comp.propose(state, "阶段解释", _compress_judgment())
        comp.apply(state, proposal)
        assert state.proposition.proposition_version == 1
        print("[7/8] 全部节点已 stable：旧形状压缩判断（无新字段）照常工作 ✓")

        # ---- 8. 端到端：请求注入清单 → 不处置被拒 → 处置后压缩完成 ----
        etmp = tempfile.mkdtemp(prefix="mentor-open-e2e-")
        try:
            epath = os.path.join(etmp, ".mentor-state", "session.json")
            eloop = MentorLoop(StateStore(epath))
            out = eloop.begin_init("测试命题：悬置节点端到端")
            eloop.store.write_judgment({"judgment": out.request.name, "response": ANCHOR_OK})
            assert isinstance(eloop.step(), DoneOutcome)

            out = eloop.begin_learning()
            # expand_tree
            eloop.store.write_judgment({"judgment": out.request.name, "response": TREE_OK})
            out = eloop.step()
            # identify_gap
            gap = {"gap_type": "结构缺口", "gap_statement": "主链条待补",
                   "why_priority": "压缩前补齐", "secondary_gaps": []}
            eloop.store.write_judgment({"judgment": out.request.name, "response": gap})
            out = eloop.step()
            # learn_round：q1/q2 回补 stable、两维各一条规则，q3 故意不回补
            learn = {
                "stage_explanation": "阶段性解释：两维机制已清，q3 追问的规则也已沉淀",
                "understanding_change": "补齐结构",
                "driver": "主缺口推动",
                "proposition_link": "直接回连命题",
                "resolved_gap": True,
                "stable_question_ids": ["q1", "q2"],
                "new_sub_questions": [],
                "next_priority_id": None,
                "competing_explanations": False,
                "dimension_rules": [
                    {"dimension": D1, "rule": "甲维判定式：条件A触发措施甲"},
                    {"dimension": D2, "rule": "乙维判定式：条件B触发措施乙"},
                ],
            }
            eloop.store.write_judgment({"judgment": out.request.name, "response": learn})
            out = eloop.step()
            # brief：四问全放行
            brief = {"findings": [
                {"question": BRIEF_QUESTIONS[i], "answer": "未击中",
                 "structural_hit": False, "loop_gap": None} for i in range(4)]}
            eloop.store.write_judgment({"judgment": out.request.name, "response": brief})
            out = eloop.step()
            # deep（首轮 about_to_stabilize 触发）
            if out.request.name == "deep_review":
                deep = {"premises": ["前提一"], "boundary_clear": True,
                        "counterexample_pierces": False, "only_high_cognition": False,
                        "passed": True, "critical_issue": "", "loop_gap": None}
                eloop.store.write_judgment({"judgment": out.request.name, "response": deep})
                out = eloop.step()
            # 闸门双条件通过，但 q3 悬置 → 仍放压缩，请求必须带处置清单
            assert out.request.name == "compress_explanation", out.request.name
            with open(out.request_path, encoding="utf-8") as f:
                req = json.load(f)
            stale = req["context"].get("stale_open_nodes")
            assert stale and stale[0]["id"] == "q3", stale
            # 不处置 → step 拒绝（判断不被消费）
            eloop.store.write_judgment({"judgment": "compress_explanation",
                                        "response": _compress_judgment()})
            try:
                eloop.step()
                raise AssertionError("8 失败：端到端悬置节点未处置竟压缩成功")
            except SchemaError:
                pass
            # 处置后压缩完成，q3 落定 stable
            eloop.store.write_judgment({"judgment": "compress_explanation",
                                        "response": _compress_judgment(
                                            stabilize_question_ids=["q3"])})
            done = eloop.step()
            assert isinstance(done, DoneOutcome)
            assert done.trace.result["status"] == "compressed"
            estate = StateStore(epath).load()
            assert estate.question_tree.get("q3").status == QuestionStatus.STABLE.value
            print("[8/8] 端到端：请求带 stale_open_nodes，不处置拒绝，处置后 v1 定稿 ✓")
        finally:
            shutil.rmtree(etmp, ignore_errors=True)

        print("\n悬置 open 节点处置机制 8/8 通过。")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
