"""六类失败模式的最小检测 / 修正入口（主循环规范 v3.1）。

本模块只放**规则**：命中判据是可观察的结构信号，不依赖模型自评。
每个入口返回明确的修正动作（回流阶段 / 强制重判 / 截断），由 loop 执行。
模型判断类内容不在这里。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import QuestionStatus, Stage

# ---- 规则常量（MVP 固定值，不做配置系统）----
TREE_HARD_CAP = 7          # 兼容别名：一级子问题膨胀上限
LEVEL1_HARD_CAP = 7        # 一级（挂根）子问题上限：先宽后深的「宽」也不许铺开
LEVEL2_PER_PARENT_CAP = 3  # 单个一级节点下二级子问题上限：深挖可以长树但不能失控
TREE_TOTAL_CAP = 15        # 全树节点总上限（一级 + 二级）
TREE_KEEP = 5              # 膨胀修正时保留的关键一级分支上限
IDLE_REVIEW_WINDOW = 3     # 最近 N 次简审/深审均未击中 = 怀疑者空转
MAX_TURNS_WITHOUT_UPDATE = 3  # 连续 N 个学习轮无解释版本更新 = 无限扩张
MAX_TURN_ITERS = 12        # 单轮安全上限，防止回流死循环
MAX_AUTONOMOUS_CYCLES = 12  # vNext 到达上限只 checkpoint，不宣称知识已收敛


@dataclass
class FailureSignal:
    mode: str           # 失败模式名
    detected: bool
    correction: str     # 修正动作说明
    redirect_stage: str | None = None


# 1. 命题漂移 ----------------------------------------------------------------

def check_proposition_drift(state: Any) -> FailureSignal:
    p = state.proposition
    lost = (
        not p.proposition_text
        or (not p.current_explanation and state.round_count > 0)
        and state.question_tree.root_question == ""
    )
    return FailureSignal(
        mode="命题漂移",
        detected=bool(lost),
        correction="强制回到阶段1-命题锚定，重新用一句话确认中心命题与邻接边界",
        redirect_stage=Stage.ANCHOR.value if lost else None,
    )


# 2. 问题树膨胀 --------------------------------------------------------------

def check_tree_bloat(state: Any) -> FailureSignal:
    """分层膨胀检测（P0-2 二级树）：一级超限、单父二级超限或总数超限。

    与 build_tree 的硬性上限不同，这里只在「优先级不清」时才判膨胀——
    有清晰优先问题时多节点是深挖的正常形态，由建树上限兜底。
    """
    tree = state.question_tree
    l1 = tree.level1()
    per_parent = {
        q.id: len(tree.children_of(q.id)) for q in l1
    }
    over = (
        len(l1) > LEVEL1_HARD_CAP
        or len(tree.sub_questions) > TREE_TOTAL_CAP
        or any(n > LEVEL2_PER_PARENT_CAP for n in per_parent.values())
    )
    detected = over and not tree.priority_id
    return FailureSignal(
        mode="问题树膨胀",
        detected=detected,
        correction=(
            "分层超限：以优先问题及其依赖闭包为中心，"
            f"一级至多保留 {TREE_KEEP} 个分支，被删一级节点下的二级节点一并移除"
        ),
        redirect_stage=Stage.TREE.value if detected else None,
    )


def prune_tree(state: Any) -> list[str]:
    """执行膨胀修正，返回被删除的子问题 id。

    二级树语义：保留/删除一个一级节点时，其 parent_id 下的二级节点
    必须同进同退（结构字段单一真值，避免孤儿节点）。
    """
    tree = state.question_tree
    keep_ids: list[str] = []
    if tree.priority_id:
        keep_ids.append(tree.priority_id)
        # 保留优先问题的依赖闭包
        changed = True
        while changed:
            changed = False
            for q in tree.sub_questions:
                if q.id in keep_ids:
                    for dep in q.depends_on:
                        if dep not in keep_ids:
                            keep_ids.append(dep)
                            changed = True
    # 已稳定的问题总是保留
    keep_ids.extend(
        q.id for q in tree.sub_questions
        if q.status == QuestionStatus.STABLE.value and q.id not in keep_ids
    )
    # 二级随父节点：被保留的二级 → 父节点也保留
    by_id = {q.id: q for q in tree.sub_questions}
    for qid in list(keep_ids):
        node = by_id.get(qid)
        if node and node.parent_id and node.parent_id not in keep_ids:
            keep_ids.append(node.parent_id)
    # 一级分支上限：截断后父节点没留下的二级一律不保留（不制造孤儿）
    kept_l1 = [qid for qid in keep_ids if not by_id[qid].parent_id][:TREE_KEEP]
    keep_set = set(kept_l1)
    for q in tree.sub_questions:
        if q.parent_id and q.parent_id in keep_set and q.id in keep_ids:
            keep_set.add(q.id)
    removed = [q.id for q in tree.sub_questions if q.id not in keep_set]
    tree.sub_questions = [q for q in tree.sub_questions if q.id in keep_set]
    for q in tree.sub_questions:
        q.depends_on = [d for d in q.depends_on if d in keep_set]
    tree.dependencies = {q.id: list(q.depends_on) for q in tree.sub_questions}
    return removed


# 3. 怀疑者空转 --------------------------------------------------------------

def check_skeptic_idle(state: Any) -> FailureSignal:
    hits = state.decision.recent_review_hits[-IDLE_REVIEW_WINDOW:]
    detected = len(hits) == IDLE_REVIEW_WINDOW and not any(hits)
    return FailureSignal(
        mode="怀疑者空转",
        detected=detected,
        correction="回看最近三次审查均未击中结构问题，必须重写异议焦点后再审查",
        redirect_stage=Stage.BRIEF.value if detected else None,
    )


def record_review_hit(state: Any, structural_hit: bool) -> None:
    state.decision.recent_review_hits.append(bool(structural_hit))
    del state.decision.recent_review_hits[:-IDLE_REVIEW_WINDOW]


def clear_idle_window(state: Any) -> None:
    """重写异议焦点后清空观察窗，避免同一信号每轮重复触发。"""
    state.decision.recent_review_hits = []


# 4. 教学伪适配 --------------------------------------------------------------

def check_pseudo_adaptation(state: Any, action: str) -> FailureSignal:
    detected = action in state.teaching.failed_actions
    return FailureSignal(
        mode="教学伪适配",
        detected=detected,
        correction=(
            f"动作 {action} 在本命题下已验证无效；强制重判用户当前理解假设，"
            "重新选择主导师动作（必须换路径，不能只换语气）"
        ),
    )


# 5. 过早收敛 ----------------------------------------------------------------

def check_premature_convergence(
    state: Any,
    *,
    brief_passed: bool,
    deep_required: bool,
    deep_passed: bool,
    explanation: str,
    open_boundaries: list[str],
) -> FailureSignal:
    reasons = []
    if not brief_passed:
        reasons.append("阶段性解释尚未通过简审")
    if deep_required and not deep_passed:
        reasons.append("按触发条件应进深审且深审未通过")
    if not explanation:
        reasons.append("给不出当前最稳解释")
    if not open_boundaries:
        reasons.append("无法指出任何开放边界")
    detected = bool(reasons)
    return FailureSignal(
        mode="过早收敛",
        detected=detected,
        correction="强制回流怀疑者或缺口识别阶段：" + "；".join(reasons)
        if reasons
        else "允许阶段压缩",
        redirect_stage=Stage.GAP.value if detected else None,
    )


# 6. 无限扩张 ----------------------------------------------------------------

def check_infinite_expansion(state: Any) -> FailureSignal:
    n = state.turns_since_explanation_update
    detected = n >= MAX_TURNS_WITHOUT_UPDATE
    return FailureSignal(
        mode="无限扩张",
        detected=detected,
        correction=(
            f"已连续 {n} 个学习轮没有产生更稳解释版本；强制输出当前解释版本，"
            "若无法输出则判定扩张低价值并截断"
        ),
        redirect_stage=Stage.COMPRESS.value if detected else None,
    )
