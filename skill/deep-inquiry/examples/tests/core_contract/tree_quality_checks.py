#!/usr/bin/env python3
"""P0-2 / P0-3 回归：问题树质量约束 + 维度推导链可审计。

不经文件协议，直接驱动 Learner 与 schema，共八组断言：

P0-2 复合节点拆分 + 二级树 + 根问题中性化
1. 复合问法节点（一问塞两事、两个疑问词/问号）被确定性拒；单一问法放行
2. 根问题预写答案形态（「完整决策框架」等）被拒；中性根问题放行
3. 二级子问题（parent_id 挂一级节点、同维度）合法，树深恰为 2
4. 三级节点、跨维度二级节点、未知 parent 被拒
5. 分层容量上限：一级 >7、单父二级 >3 被拒

P0-3 限定词→维度推导链
6. 锚定必须给 dimension_sources；phase 维度必须回指标定词原文；
   cross_cutting/standalone 无理由被拒；合法来源持久化并可往返
7. 横切维度节点必须依赖全部相关阶段维度（默认全部阶段），缺边被拒；
   声明 related_phases 后按声明集合校验
8. 旧会话（有维度名无来源记录）加载为 legacy，不阻断加载
"""

from __future__ import annotations

import os
import sys
import tempfile

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, SKILL_ROOT)

from scripts.learner import Learner  # noqa: E402
from scripts.schema import (  # noqa: E402
    PropositionState,
    SchemaError,
)
from scripts.store import StateStore  # noqa: E402

QA, QB = "限定词甲", "限定词乙"
DA, DB, DC = "阶段维度甲", "阶段维度乙", "横切维度丙"


def _source(dimension: str, kind: str, **kw) -> dict:
    item = {"dimension": dimension, "kind": kind}
    item.update(kw)
    return item


def _anchor_judgment(
    dimensions: list[str],
    sources: list[dict],
    qualifiers: list[str] | None = None,
) -> dict:
    return {
        "proposition_text": "测试命题",
        "proposition_scope": "测试范围",
        "adjacent_topics": ["邻接a", "邻接b"],
        "scope_qualifiers": list(qualifiers or [QA, QB]),
        "coverage_dimensions": dimensions,
        "dimension_sources": sources,
    }


PHASE_SOURCES = [
    _source(DA, "phase", source_qualifier=QA),
    _source(DB, "phase", source_qualifier=QB),
]


def _new_state() -> StateStore:
    store = StateStore(os.path.join(tempfile.mkdtemp(), ".mentor-state", "session.json"))
    return store.new_session()


def _anchor(state, sources=None, dimensions=None, qualifiers=None):
    sources = PHASE_SOURCES if sources is None else sources
    dimensions = [DA, DB] if dimensions is None else dimensions
    return Learner().anchor(
        state, _anchor_judgment(dimensions, sources, qualifiers=qualifiers)
    )


def _tree(subs: list[dict], root: str = "如何理解测试命题？", priority: str = "q1") -> dict:
    return {"root_question": root, "sub_questions": subs, "priority_id": priority}


def _node(qid: str, text: str, dim: str, **kw) -> dict:
    item = {"id": qid, "text": text, "dimension": dim, "depends_on": []}
    item.update(kw)
    return item


def main() -> None:
    learner = Learner()

    # ---- 1. 复合问法 ----
    assert learner._is_compound_question("桩长如何取值？冲刷线以下埋深怎么定？")
    assert learner._is_compound_question("地基如何选型，以及造价如何匡算？")
    assert not learner._is_compound_question("软土厚度超过 10m 时地基如何选型？")
    assert not learner._is_compound_question("核心概念分别指什么？")
    # 「」/《》内的命题复述里的疑问词不计（节点引用命题原文是常态）
    assert not learner._is_compound_question(
        "「怀疑机制如何避免伪理解」中的核心概念分别指什么？"
    )
    state = _new_state()
    _anchor(state)
    bad = _tree([
        _node("q1", "阶段甲的关键参数如何取值？", DA),
        _node("q2", "阶段乙怎么判定，以及失效后如何补救？", DB, depends_on=["q1"]),
    ])
    try:
        learner.build_tree(state, bad)
        raise AssertionError("复合节点（两个疑问词）必须被拒")
    except SchemaError:
        pass
    print("[1/8] 复合问法节点被确定性拦截，单一问法放行 ✓")

    # ---- 2. 根问题预写答案形态 ----
    assert learner._root_presupposes_answer("如何建立海边建房的完整决策框架？")
    assert learner._root_presupposes_answer("商用楼建设的全过程流程是什么？")
    assert not learner._root_presupposes_answer("海边商用楼建设如何成立？")
    state = _new_state()
    _anchor(state)
    try:
        learner.build_tree(
            state,
            _tree(
                [
                    _node("q1", "阶段甲的关键参数如何取值？", DA),
                    _node("q2", "阶段乙如何验收？", DB, depends_on=["q1"]),
                ],
                root="如何建立一套完整决策框架？",
            ),
        )
        raise AssertionError("预写答案形态的根问题必须被拒")
    except SchemaError:
        pass
    print("[2/8] 根问题禁止预写答案形态（框架/全过程/体系），中性问法放行 ✓")

    # ---- 3. 二级子问题合法 ----
    state = _new_state()
    _anchor(state)
    learner.build_tree(
        state,
        _tree([
            _node("q1", "阶段甲的关键参数如何取值？", DA),
            _node("q2", "阶段乙如何组织？", DB, depends_on=["q1"]),
            _node("q3", "参数超过阈值时如何分支处理？", DB, parent_id="q2", depends_on=["q2"]),
        ]),
    )
    q1, q2, q3 = state.question_tree.sub_questions
    assert q1.parent_id == "" and q2.parent_id == ""
    assert q3.parent_id == "q2" and q3.dimension == DB
    state.question_tree.validate()
    l1 = [q for q in state.question_tree.sub_questions if not q.parent_id]
    l2 = [q for q in state.question_tree.sub_questions if q.parent_id]
    assert len(l1) == 2 and len(l2) == 1
    print("[3/8] 二级子问题（parent_id + 同维度）合法，树深恰为 2 ✓")

    # ---- 4. 三级/跨维度/未知 parent ----
    def _expect_reject(subs, label):
        st = _new_state()
        _anchor(st)
        try:
            learner.build_tree(st, _tree(subs))
            raise AssertionError(label)
        except SchemaError:
            pass

    base = [
        _node("q1", "阶段甲的关键参数如何取值？", DA),
        _node("q2", "阶段乙如何组织？", DB, depends_on=["q1"]),
        _node("q3", "参数超过阈值时如何分支？", DB, parent_id="q2", depends_on=["q2"]),
    ]
    _expect_reject(base + [
        _node("q4", "再往下如何细化？", DB, parent_id="q3", depends_on=["q3"]),
    ], "三级节点必须被拒")
    _expect_reject([
        _node("q1", "阶段甲的关键参数如何取值？", DA),
        _node("q2", "阶段乙如何组织？", DB, depends_on=["q1"]),
        _node("q3", "甲维度细节如何展开？", DA, parent_id="q2", depends_on=["q2"]),
    ], "二级节点跨维度（与父节点维度不一致）必须被拒")
    _expect_reject([
        _node("q1", "阶段甲的关键参数如何取值？", DA),
        _node("q2", "阶段乙如何组织？", DB, depends_on=["q1"]),
        _node("q3", "挂到不存在的父节点如何处理？", DB, parent_id="qX", depends_on=["qX"]),
    ], "未知 parent 必须被拒")
    print("[4/8] 三级节点、跨维度二级节点、未知 parent 均被拒 ✓")

    # ---- 5. 分层容量 ----
    st = _new_state()
    _anchor(st)
    eight_l1 = [
        _node(f"q{i}", f"第 {i} 个一级问题如何回答？", DA if i % 2 else DB)
        for i in range(1, 9)
    ]
    try:
        learner.build_tree(st, _tree(eight_l1, priority="q1"))
        raise AssertionError("一级节点超过 7 个必须被拒")
    except SchemaError:
        pass
    st = _new_state()
    _anchor(st)
    four_l2 = [
        _node("q1", "阶段甲的关键参数如何取值？", DA),
        _node("q2", "阶段乙如何组织？", DB, depends_on=["q1"]),
    ] + [
        _node(f"c{i}", f"乙维度第 {i} 个细节如何定？", DB, parent_id="q2", depends_on=["q2"])
        for i in range(1, 5)
    ]
    try:
        learner.build_tree(st, _tree(four_l2, priority="q1"))
        raise AssertionError("单个一级节点下二级超过 3 个必须被拒")
    except SchemaError:
        pass
    print("[5/8] 分层容量：一级 ≤7、单父二级 ≤3，越界被拒 ✓")

    # ---- 6. 锚定来源审计 ----
    st = _new_state()
    try:
        learner.anchor(st, {
            "proposition_text": "p", "proposition_scope": "s",
            "adjacent_topics": ["a", "b"],
            "scope_qualifiers": [QA, QB],
            "coverage_dimensions": [DA, DB],
            # 故意缺 dimension_sources
        })
        raise AssertionError("无 dimension_sources 的锚定必须被拒")
    except SchemaError:
        pass
    st = _new_state()
    try:
        learner.anchor(
            st,
            _anchor_judgment(
                [DA, DB],
                [_source(DA, "phase", source_qualifier="不在限定词列表里的词"),
                 _source(DB, "phase", source_qualifier=QB)],
            ),
        )
        raise AssertionError("phase 维度必须回指 scope_qualifiers 中存在的原文")
    except SchemaError:
        pass
    st = _new_state()
    try:
        learner.anchor(
            st,
            _anchor_judgment(
                [DA, DC],
                [_source(DA, "phase", source_qualifier=QA),
                 _source(DC, "cross_cutting")],  # 缺 reason
            ),
        )
        raise AssertionError("cross_cutting 无理由必须被拒")
    except SchemaError:
        pass
    st = _new_state()
    sources = [
        _source(DA, "phase", source_qualifier=QA),
        _source(DB, "phase", source_qualifier=QB),
        _source(DC, "cross_cutting", reason="成本横切各阶段，非命题限定词推出"),
    ]
    learner.anchor(
        st,
        _anchor_judgment([DA, DB, DC], sources),
    )
    rec = st.proposition.get_dimension_source(DC)
    assert rec and rec.kind == "cross_cutting" and rec.reason
    again = PropositionState.from_dict(st.proposition.to_dict())
    assert again.get_dimension_source(DA).source_qualifier == QA
    print("[6/8] 维度来源审计：缺失/错引限定词/横切无理由被拒，合法记录可持久化往返 ✓")

    # ---- 7. 横切维度依赖全部相关阶段 ----
    st = _new_state()
    learner.anchor(
        st,
        _anchor_judgment(
            [DA, DB, DC],
            [
                _source(DA, "phase", source_qualifier=QA),
                _source(DB, "phase", source_qualifier=QB),
                _source(DC, "cross_cutting", reason="成本横切全部阶段"),
            ],
        ),
    )
    try:
        learner.build_tree(
            st,
            _tree([
                _node("q1", "阶段甲如何展开？", DA),
                _node("q2", "阶段乙如何展开？", DB, depends_on=["q1"]),
                _node("q3", "成本如何匡算？", DC, depends_on=["q1"]),  # 漏了 q2/DB
            ]),
        )
        raise AssertionError("横切维度节点必须依赖全部相关阶段维度，缺边被拒")
    except SchemaError:
        pass
    # 声明只与甲相关后，只依赖 q1 即合法
    st = _new_state()
    learner.anchor(
        st,
        _anchor_judgment(
            [DA, DB, DC],
            [
                _source(DA, "phase", source_qualifier=QA),
                _source(DB, "phase", source_qualifier=QB),
                _source(DC, "cross_cutting", reason="成本仅在甲阶段专项发生",
                         related_phases=[DA]),
            ],
        ),
    )
    learner.build_tree(
        st,
        _tree([
            _node("q1", "阶段甲如何展开？", DA),
            _node("q2", "阶段乙如何展开？", DB, depends_on=["q1"]),
            _node("q3", "甲阶段成本如何匡算？", DC, depends_on=["q1"]),
        ]),
    )
    print("[7/8] 横切维度依赖边一致性：默认依赖全部阶段，related_phases 可收窄 ✓")

    # ---- 8. 旧会话 legacy 兼容 ----
    old = PropositionState.from_dict({
        "proposition_text": "旧命题",
        "coverage_dimensions": ["旧维度"],
    })
    old.validate()
    rec = old.get_dimension_source("旧维度")
    assert rec is not None and rec.kind == "legacy"
    print("[8/8] 旧会话维度无来源记录时迁移为 legacy，加载不阻断 ✓")

    print("\nP0-2/P0-3 问题树质量与维度推导链全部断言通过。")


if __name__ == "__main__":
    main()
