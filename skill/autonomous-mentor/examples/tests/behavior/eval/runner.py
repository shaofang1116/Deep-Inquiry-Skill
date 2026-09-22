"""eval 闭环驱动器与确定性断言画像。

对每个 CasePack：
1. 走完整文件协议：锚定 → 学习闭环（缺口/简审/深审/双条件闸门/压缩定稿）；
2. 对定稿状态做画像断言（规则密度、溯源、悬置节点处置、开放边界）；
3. 三个画像用户各走一遍教学进入点（其中迁移用户必须走完整迁移判分闭环）；
4. 新会话仅有锚定、无可教版本时教学请求必须被 need_learn 拦截。

真实模型宿主验证时只替换 ScriptedHost（同一 request/pending 协议），
断言画像与阈值不变——这就是阶段三固化的「同一把尺子」。

画像函数 profile_* 对脚本宿主与真实宿主（人工/模型逐判断作答）共用：
真实宿主跑完后把 artifacts（judgment 信封序列）与定稿 state 交给
realhost_profile.py 即可，断言路径完全相同。
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field

from scripts.judgments import (
    BRIEF_QUESTIONS,
    BRIEF_REVIEW,
    COMPRESS,
    DEEP_REVIEW,
    LEARN,
)
from scripts.learner import _NUMERIC_RULE_RE
from scripts.loop import DoneOutcome, MentorLoop, PendingOutcome
from scripts.schema import QuestionStatus
from scripts.store import StateStore

from tests.behavior.eval.base import CasePack, ScriptedHost

MAX_JUDGMENTS = 80


@dataclass
class CaseReport:
    case_id: str
    label: str
    passed: bool
    checks: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    counters: dict[str, int] = field(default_factory=dict)

    def check(self, ok: bool, desc: str) -> bool:
        if ok:
            self.checks.append(desc)
        else:
            self.failures.append(desc)
        return ok

    def line(self) -> str:
        head = f"[{ 'PASS' if self.passed else 'FAIL' }] {self.label}（{self.case_id}）"
        c = self.counters
        tail = (
            f"：简审击中 {c.get('brief_hits', 0)}（第四问 {c.get('completeness_hits', 0)}）、"
            f"深审击穿 {c.get('deep_pierces', 0)}、规则 {c.get('rule_total', 0)} 条/"
            f"{c.get('dim_total', 0)} 维、边界 {c.get('boundaries', 0)}、"
            f"悬置稳定 {c.get('stabilized', 0)} / 显式保留 {c.get('retained', 0)}、"
            f"教学动作 {c.get('teaching_actions', 0)} 种"
        )
        return head + tail


def new_report(case: CasePack) -> CaseReport:
    return CaseReport(case_id=case.id, label=case.label, passed=False)


def _drive(loop: MentorLoop, outcome: PendingOutcome | DoneOutcome,
           host: ScriptedHost, transcript: list[tuple[str, dict]]) -> DoneOutcome:
    for _ in range(MAX_JUDGMENTS):
        if isinstance(outcome, DoneOutcome):
            return outcome
        assert isinstance(outcome, PendingOutcome), outcome
        assert os.path.isfile(outcome.request_path), "request.json 未落盘"
        with open(outcome.request_path, encoding="utf-8") as f:
            request = json.load(f)
        assert request["judgment"] == outcome.request.name
        response = host.build_judgment(request)
        loop.store.write_judgment(
            {"judgment": request["judgment"], "response": response}
        )
        transcript.append((request["judgment"], response))
        outcome = loop.step()
    raise AssertionError(f"单轮判断次数超过上限 {MAX_JUDGMENTS}，疑似路由不收敛")


# ================= 画像断言（脚本宿主与真实宿主共用） =================

def profile_learning(
    case: CasePack,
    report: CaseReport,
    store: StateStore,
    result: dict,
    transcript: list[tuple[str, dict]],
    anchored: bool = True,
) -> None:
    """学习闭环定稿画像：结果、应答计数、定稿状态（规则/溯源/悬置/边界）。"""
    if anchored:
        report.check(result.get("status") in ("compressed",),
                     f"学习闭环压缩定稿（实际：{result.get('status')}）")
    report.check(result.get("proposition_version") == 1,
                 f"定稿版本为 v1（实际：v{result.get('proposition_version')}）")

    brief_hits = sum(
        1 for name, resp in transcript if name == BRIEF_REVIEW
        for f in resp.get("findings", []) if f.get("structural_hit")
    )
    completeness_hits = sum(
        1 for name, resp in transcript if name == BRIEF_REVIEW
        for f in resp.get("findings", [])
        if f.get("structural_hit") and f.get("question") == BRIEF_QUESTIONS[3]
    )
    deep_pierces = sum(
        1 for name, resp in transcript if name == DEEP_REVIEW
        if resp.get("counterexample_pierces")
    )
    deep_count = sum(1 for name, _ in transcript if name == 'deep_review')
    compress_count = sum(1 for name, _ in transcript if name == COMPRESS)
    competing_seen = any(
        name == LEARN and resp.get("competing_explanations")
        for name, resp in transcript
    )

    exp = case.expect
    # 路径形状类断言：真实模型可能发现比脚本宿主更多的合理击中，
    # 因此断言"至少达到预埋缺口数"而非"恰好等于"——预埋缺口必须被命中，
    # 但不限制真实模型额外发现的高质量击中。
    report.check(brief_hits >= exp.brief_hits,
                 f"简审结构击中 {brief_hits} 次（≥期望 {exp.brief_hits}）")
    report.check(completeness_hits >= exp.completeness_hits,
                 f"第四问（完备性）击中 {completeness_hits} 次（≥期望 {exp.completeness_hits}）")
    report.check(deep_pierces >= exp.deep_pierces,
                 f"深审反例击穿 {deep_pierces} 次（≥期望 {exp.deep_pierces}）")
    report.check(deep_count >= 1 + exp.deep_pierces,
                 f"深审触发 {deep_count} 次（≥期望 {1 + exp.deep_pierces}）")
    report.check(compress_count == 1,
                 f"压缩请求仅 {compress_count} 次（闸门零拦截）")
    if exp.competing:
        report.check(competing_seen, "重学轮显式登记竞争解释共存")

    state = store.load()
    boundaries = result.get("open_boundaries") or list(state.proposition.open_boundaries)
    report.check(len(boundaries) >= exp.boundaries_min,
                 f"开放边界 {len(boundaries)} 条（≥{exp.boundaries_min}）")

    depths = {d.dimension: d for d in state.proposition.dimension_depth}
    for dim in state.proposition.coverage_dimensions:
        d = depths.get(dim)
        report.check(d is not None and d.depth_satisfied,
                     f"维度「{dim}」满足最低深度（规则或无增量裁决）")

    rule_total = 0
    bare_numeric = []
    for d in state.proposition.dimension_depth:
        for rule in d.rules:
            rule_total += 1
            meta = d.rule_meta.get(rule, {})
            if _NUMERIC_RULE_RE.search(rule) and not meta.get("basis") and not meta.get("heuristic"):
                bare_numeric.append(rule)
    report.check(not bare_numeric,
                 f"裸数值规则零逃逸（{rule_total} 条规则全部有溯源/启发式标记）"
                 + ("" if not bare_numeric else f"；逃逸：{bare_numeric}"))

    nodes = {q.id: q for q in state.question_tree.sub_questions}
    open_ids = {qid for qid, q in nodes.items() if q.status == QuestionStatus.OPEN.value}
    stabilized = [
        qid for qid, q in nodes.items() if q.status == QuestionStatus.STABLE.value
    ]
    report.check(open_ids == set(exp.retain_open),
                 f"定稿 open 集合 {sorted(open_ids)} == 显式保留 {sorted(exp.retain_open)}")
    for qid, reason_fragment in exp.retain_open.items():
        marker = f"未闭合子问题（{qid}）"
        report.check(any(marker in b for b in boundaries),
                     f"保留节点 {qid} 已并入开放边界（{marker}…）")
        report.check(any(reason_fragment[:12] in b for b in boundaries),
                     f"保留节点 {qid} 的保留理由进入边界文本")

    report.counters.update({
        "brief_hits": brief_hits,
        "completeness_hits": completeness_hits,
        "deep_pierces": deep_pierces,
        "rule_total": rule_total,
        "dim_total": len(state.proposition.coverage_dimensions),
        "boundaries": len(boundaries),
        "stabilized": len(stabilized),
        "retained": len(open_ids),
    })


def profile_teaching(
    case: CasePack,
    report: CaseReport,
    teaching_results: list[dict],
) -> None:
    """教学画像：三个画像用户按序得到三种互异进入点，迁移用户闭环 migration_passed。"""
    report.check(len(teaching_results) == len(case.users),
                 f"教学闭环 {len(teaching_results)} 个（期望 {len(case.users)}）")
    actions_seen: set[str] = set()
    for user, tr in zip(case.users, teaching_results):
        # 伪造检测：真实 step --json done 整包必带交付内容字段；
        # 只含 status/teaching_action/dialog_goal 三字段几乎必是手写 result（真实宿主形状回补）。
        forged = (
            "reply" not in tr and "structure_applied" not in tr
        ) or tr.get("status") not in ("teaching", "migration_passed")
        if forged:
            report.check(False,
                         f"用户「{user.name}」result 信封疑似手写/截断"
                         f"（status={tr.get('status')!r}，"
                         f"字段={sorted(tr.keys())}）；result_*.json 必须由 step --json done 整包重定向生成，禁止手写")
            continue
        report.check(tr.get("teaching_action") == user.expected_action,
                     f"用户「{user.name}」→ {user.expected_action}（实际：{tr.get('teaching_action')}）")
        actions_seen.add(tr.get("teaching_action", ""))
        if user.expected_action == "先做迁移":
            report.check(tr.get("status") == "migration_passed",
                         f"迁移用户闭环至 migration_passed（实际：{tr.get('status')}）")
        else:
            report.check(tr.get("status") == "teaching",
                         f"用户「{user.name}」教学轮正常交付（实际：{tr.get('status')}）")
    report.check(len(actions_seen) == 3,
                 f"三类用户走出三条互异进入点（实际 {len(actions_seen)} 种：{sorted(actions_seen)}）")
    report.counters["teaching_actions"] = len(actions_seen)


def profile_need_learn(
    report: CaseReport,
    fresh_store: StateStore,
    result_status: str | None = None,
) -> None:
    """无可教版本拦截画像：仅锚定的新会话教学请求必须被 need_learn 拦截。"""
    state = fresh_store.load()
    ok = (
        state.decision.teachable is False
        and state.proposition.proposition_version == 0
        and (result_status in (None, "need_learn"))
    )
    report.check(ok,
                 "无可教版本时教学请求被 need_learn 拦截（不得硬教）"
                 + ("" if ok else f"；teachable={state.decision.teachable}，"
                    f"v{state.proposition.proposition_version}，result={result_status}"))


def finalize(report: CaseReport) -> CaseReport:
    report.passed = not report.failures
    return report


# ================= 脚本宿主端到端入口 =================

def run_case(case: CasePack) -> CaseReport:
    report = new_report(case)
    tmp = tempfile.mkdtemp(prefix=f"mentor-eval-{case.id}-")
    try:
        store = StateStore(os.path.join(tmp, ".mentor-state", "session.json"))
        loop = MentorLoop(store)
        host = ScriptedHost(case)
        transcript: list[tuple[str, dict]] = []

        # ---- 锚定 ----
        done = _drive(loop, loop.begin_init(case.proposition), host, transcript)
        report.check(done.trace.result["status"] == "anchored", "锚定完成")

        # ---- 学习闭环 → 压缩定稿 ----
        done = _drive(loop, loop.begin_learning(), host, transcript)
        learning_transcript = transcript
        profile_learning(case, report, store, done.trace.result, learning_transcript)

        # ---- 三个画像用户：三种进入点；迁移用户走完整迁移闭环 ----
        teaching_results: list[dict] = []
        for user in case.users:
            d = _drive(
                loop,
                loop.begin_teaching(user.message, reset_teaching=True),
                host, transcript,
            )
            teaching_results.append(d.trace.result)
        profile_teaching(case, report, teaching_results)

        # ---- need_learn 闸门：仅锚定的新会话不得硬教 ----
        fresh = tempfile.mkdtemp(prefix=f"mentor-eval-{case.id}-fresh-")
        try:
            fresh_store = StateStore(os.path.join(fresh, ".mentor-state", "session.json"))
            fresh_loop = MentorLoop(fresh_store)
            _drive(fresh_loop, fresh_loop.begin_init(case.proposition), host, transcript)
            blocked = fresh_loop.begin_teaching("我有个问题想直接问")
            status = blocked.trace.result["status"] if isinstance(blocked, DoneOutcome) else None
            profile_need_learn(report, fresh_store, status)
        finally:
            import shutil
            shutil.rmtree(fresh, ignore_errors=True)

        return finalize(report)
    except Exception as exc:  # noqa: BLE001
        report.failures.append(f"用例执行异常：{type(exc).__name__}: {exc}")
        report.passed = False
        report.counters = {}
        return report
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
