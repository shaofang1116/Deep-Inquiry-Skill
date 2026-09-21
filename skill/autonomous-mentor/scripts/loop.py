"""主循环调度：双循环 + 八阶段，模型无关的文件协议状态机。

运行协议（执行 Skill 的 agent 与内核之间）：
1. agent 运行 begin（init/learn/ask/feedback）：内核做确定性路由，
   把「判断请求」写入 request.json，把轮次信封写入 pending.json；
2. agent 阅读请求，按 response_template 自行完成认识论判断，
   将 {"judgment": <名称>, "response": {...}} 写入 judgment.json；
3. agent 运行 step：内核校验判断、执行规则与状态迁移。若还需要下一个判断，
   回到第 2 步；若本轮完成，落库 session.json 并清除 pending。

内核本身不调用任何模型，因此同一份 Skill 可由任意模型执行。

铁律仍由规则保证：一轮一个主推进目标；阶段性解释必过简审；深审按四条件触发；
无开放边界不得压缩；教学结构缺口必须回流。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from . import failures, judgments
from .autonomous_runtime import HostRun, HostRuntimeCoordinator
from .compressor import Compressor, project_durable_learning_result
from .convergence import ConvergenceDecision, evaluate_convergence
from .judgments import (
    ANCHOR,
    ASSESS_USER,
    BRIEF_REVIEW,
    COMPRESS,
    DEEP_REVIEW,
    EXPAND_TREE,
    IDENTIFY_GAP,
    LEARN,
    ASSESS_MIGRATION_OUTPUT,
    PLAN_TEACHING,
    READ_FEEDBACK,
    REWRITE_FOCUS,
    TEACH,
    JudgmentRequest,
)
from .learner import Learner
from .knowledge_schema import (
    ConvergenceAssessment,
    GainLevel,
    GapStatus,
    Priority,
    TopicKnowledge,
)
from .knowledge_store import KnowledgeStore
from .mentor import Mentor
from .schema import (
    ActiveLoop,
    Counterexample,
    GapState,
    GapType,
    ProgressEntry,
    QuestionStatus,
    SchemaError,
    Stage,
    TeachingAsset,
    TriggerSource,
)
from .skeptic import Skeptic
from .store import StateStore, StoreError

# 教学子阶段（运行时阶段名，不进入持久化状态的 Stage 枚举）
T_ASSESS = "T_ASSESS"
T_PLAN = "T_PLAN"
T_TEACH = "T_TEACH"
T_MIGRATION_ASSESS = "T_MIGRATION_ASSESS"
F_FEEDBACK = "F_FEEDBACK"
REWRITE = "REWRITE_FOCUS"


class LoopError(RuntimeError):
    pass


@dataclass
class TraceEvent:
    stage: str
    kind: str  # action / gate / failure / result
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {"stage": self.stage, "kind": self.kind, "summary": self.summary}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TraceEvent":
        return cls(stage=d["stage"], kind=d["kind"], summary=d["summary"])


@dataclass
class TurnTrace:
    """一次轮次的运行记录。属于运行时态，随 pending.json 临时存在，不落 session。"""

    loop: str
    primary_objective: str
    events: list[TraceEvent] = field(default_factory=list)
    effective_updates: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)

    def event(self, stage: str, kind: str, summary: str) -> None:
        self.events.append(TraceEvent(stage, kind, summary))

    def to_dict(self) -> dict[str, Any]:
        return {
            "loop": self.loop,
            "primary_objective": self.primary_objective,
            "events": [e.to_dict() for e in self.events],
            "effective_updates": list(self.effective_updates),
            "result": dict(self.result),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TurnTrace":
        return cls(
            loop=d["loop"],
            primary_objective=d["primary_objective"],
            events=[TraceEvent.from_dict(e) for e in d.get("events", [])],
            effective_updates=list(d.get("effective_updates", [])),
            result=dict(d.get("result", {})),
        )


@dataclass
class PendingOutcome:
    """本轮尚未完成：内核在等待 agent 填一个判断。"""

    request: JudgmentRequest
    request_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "pending",
            "request_path": self.request_path,
            "request": self.request.to_dict(),
        }


@dataclass
class DoneOutcome:
    """本轮完成。"""

    trace: TurnTrace

    def to_dict(self) -> dict[str, Any]:
        return {"status": "done", "trace": self.trace.to_dict()}


class MentorLoop:
    def __init__(self, store: StateStore):
        self.store = store
        self.learner = Learner()
        self.skeptic = Skeptic()
        self.compressor = Compressor()
        self.mentor = Mentor()

    # ================= 输入 1：新命题 =================

    def begin_init(self, raw_text: str) -> PendingOutcome:
        if self.store.exists():
            raise LoopError("状态文件已存在；新命题请使用新的状态路径")
        if self.store.has_pending():
            raise LoopError("已有进行中的轮次，请先 step 完成或 cancel")
        text = (raw_text or "").strip()
        if not text:
            raise LoopError("命题文本不能为空")
        state = self.store.new_session()
        state.decision.active_loop = ActiveLoop.LEARNING.value
        state.decision.active_stage = Stage.ANCHOR.value
        objective = "锚定中心命题"
        state.decision.primary_objective = objective
        trace = TurnTrace(ActiveLoop.LEARNING.value, objective)
        pending = self._new_pending(
            kind="init",
            state=state,
            stage=Stage.ANCHOR.value,
            trace=trace,
            judgment=ANCHOR,
            extra={"proposition": text},
        )
        return self._emit(pending, context={"raw_proposition": text})

    # ================= 自主学习循环 =================

    def begin_learning(self, objective: str | None = None) -> PendingOutcome:
        state = self.store.load()
        if not state.proposition.proposition_text:
            raise LoopError("尚未接收中心命题，无法开始学习循环")
        if self.store.has_pending():
            raise LoopError("已有进行中的轮次，请先 step 完成或 cancel")

        drift = failures.check_proposition_drift(state)
        if drift.detected:
            raise LoopError(f"命中失败模式「{drift.mode}」：{drift.correction}")

        state.turns_since_explanation_update += 1
        forced_compress = failures.check_infinite_expansion(state).detected

        if forced_compress and not state.proposition.current_explanation:
            # 无限扩张的截断分支：连当前版本都输出不了，低价值扩张直接中止
            self.store.save(state)
            raise LoopError(
                "命中失败模式「无限扩张」：无法输出任何当前解释版本，本轮扩张判定为低价值并截断"
            )

        if objective:
            obj = objective
        elif state.gap.is_open():
            obj = f"修复主缺口并重构解释：{state.gap.gap_statement}"
        else:
            obj = f"形成「{state.proposition.proposition_text}」的第一个可教学阶段版本"

        decision = state.decision
        decision.active_loop = ActiveLoop.LEARNING.value
        decision.primary_objective = obj
        decision.loop_back_reason = ""
        trace = TurnTrace(ActiveLoop.LEARNING.value, obj)

        if forced_compress:
            stage = Stage.COMPRESS.value
            stage_explanation = state.proposition.current_explanation
            trace.event(
                Stage.COMPRESS.value, "failure",
                "命中失败模式「无限扩张」：跳过推进，强制输出当前解释版本",
            )
        elif not self._tree_ready(state):
            stage = Stage.TREE.value
            stage_explanation = ""
        elif state.gap.is_open():
            stage = Stage.LEARN.value  # 怀疑/教学已登记缺口：直接修正
            stage_explanation = ""
        else:
            stage = Stage.GAP.value
            stage_explanation = ""

        judgment = self._judgment_for_stage(stage)
        pending = self._new_pending(
            kind="learning",
            state=state,
            stage=stage,
            trace=trace,
            judgment=judgment,
            extra={
                "objective": obj,
                "stage_explanation": stage_explanation,
                "attempt": 0,
                "brief_passed": forced_compress,  # 已压缩版本此前必已过审
                "deep_required": False,
                "deep_passed": False,
                "competing": False,
                "forced_compress": forced_compress,
                "about_to_stabilize": state.proposition.proposition_version == 0,
                "force_reassess": False,
            },
        )
        self.store.save(state)  # 轮次计数等先落库
        return self._emit(pending)

    # ================= 教学响应循环 =================

    def begin_teaching(
        self, user_message: str, reset_teaching: bool = False
    ) -> DoneOutcome | PendingOutcome:
        state = self.store.load()
        if self.store.has_pending():
            raise LoopError("已有进行中的轮次，请先 step 完成或 cancel")
        decision = state.decision

        if not decision.teachable:
            # v3.1 决策二：没有可教版本时不得硬教
            decision.active_loop = ActiveLoop.LEARNING.value
            decision.next_action = "先完成一轮自主学习（补关键缺口）"
            decision.decision_reason = "当前解释一教就会露馅，优先先学"
            self.store.save(state)
            trace = TurnTrace(
                ActiveLoop.TEACHING.value,
                primary_objective=f"判断教学请求是否可响应：{user_message}",
            )
            trace.event(
                Stage.TRANSLATE.value, "failure", "尚无可教版本，退回学习循环"
            )
            trace.result = {"status": "need_learn"}
            return DoneOutcome(trace)

        if reset_teaching:
            self.mentor.reset_for_new_user(state)
            self.store.save(state)

        obj = f"导师式回应：{user_message}"
        decision.active_loop = ActiveLoop.TEACHING.value
        decision.active_stage = Stage.TRANSLATE.value
        decision.primary_objective = obj
        trace = TurnTrace(ActiveLoop.TEACHING.value, obj)
        pending = self._new_pending(
            kind="teaching",
            state=state,
            stage=T_ASSESS,
            trace=trace,
            judgment=ASSESS_USER,
            extra={
                "user_message": user_message,
                "reset_teaching": reset_teaching,
                "force_reassess": False,
            },
        )
        return self._emit(pending)

    def begin_feedback(
        self, user_message: str, feedback_text: str
    ) -> PendingOutcome:
        state = self.store.load()
        if state.decision.active_loop != ActiveLoop.TEACHING.value:
            raise LoopError("当前不在教学响应循环中，没有等待反馈的教学轮")
        if self.store.has_pending():
            raise LoopError("已有进行中的轮次，请先 step 完成或 cancel")
        obj = "读取教学反馈并决定修正或回流"
        trace = TurnTrace(ActiveLoop.TEACHING.value, obj)
        pending = self._new_pending(
            kind="feedback",
            state=state,
            stage=F_FEEDBACK,
            trace=trace,
            judgment=READ_FEEDBACK,
            extra={
                "user_message": user_message,
                "feedback_text": feedback_text,
            },
        )
        return self._emit(pending)

    # ================= step：消费一个判断并尽量推进 =================

    def step(self, message: str = "") -> PendingOutcome | DoneOutcome:
        pending = self.store.load_pending()

        # 迁移练习等场景：用户产出通过 message 传入 pending
        if message:
            pending["user_message"] = message

        # 读取判断（成功消费前不删除，失败时 pending 与 request 保持不变）
        name, response = self.store.read_judgment()
        if name != pending.get("judgment"):
            raise LoopError(
                f"判断名称不匹配：当前请求需要 {pending.get('judgment')}，收到 {name}"
            )
        judgments.validate(name, response)

        from .schema import SessionState

        state = SessionState.from_dict(pending["state"])
        trace = TurnTrace.from_dict(pending["trace"])

        done = self._dispatch(state, pending, name, response, trace)
        # _dispatch 要么抛错（判断未被消费），要么返回 ("request", next_name) / ("done", result)

        if done[0] == "done":
            self.store.discard_judgment()
            self._finalize(state, pending, trace, done[1])
            return DoneOutcome(trace)

        # 需要下一个判断
        next_name = done[1]
        pending["stage"] = done[2]
        pending["judgment"] = next_name
        # 跨循环回流时切换 kind（如教学失败回流学习循环）
        learning_judgments = {
            ANCHOR, EXPAND_TREE, IDENTIFY_GAP, LEARN,
            BRIEF_REVIEW, REWRITE_FOCUS, DEEP_REVIEW, COMPRESS,
        }
        if next_name in learning_judgments:
            pending["kind"] = "learning"
            if next_name == LEARN and "attempt" not in pending:
                pending["attempt"] = 0
        else:
            pending["kind"] = "teaching"
        pending["state"] = state.to_dict()
        pending["trace"] = trace.to_dict()
        outcome = self._emit(pending)
        self.store.discard_judgment()
        return outcome

    def cancel(self) -> None:
        self.store.clear_pending()

    # ================= 分发与路由 =================

    def _dispatch(
        self, state: Any, pending: dict[str, Any], name: str,
        response: dict[str, Any], trace: TurnTrace,
    ) -> tuple[str, Any, str]:
        kind = pending["kind"]
        stage = pending["stage"]

        if kind == "init":
            return self._handle_anchor(state, pending, response, trace)
        if kind == "feedback":
            return self._handle_feedback(state, pending, response, trace)
        if kind == "teaching":
            return self._dispatch_teaching(state, pending, stage, response, trace)
        return self._dispatch_learning(state, pending, stage, response, trace)

    # ---- 自主学习循环 ----

    def _handle_anchor(
        self, state: Any, pending: dict[str, Any],
        response: dict[str, Any], trace: TurnTrace,
    ) -> tuple[str, Any, str]:
        self.learner.anchor(state, response)
        trace.effective_updates.append("命题状态：中心命题、命题边界、两个邻接议题")
        trace.event(
            Stage.ANCHOR.value, "gate",
            f"一句话命题已确立；邻接议题 {len(response['adjacent_topics'])} 个，锚定通过",
        )
        state.decision.active_stage = Stage.TREE.value
        state.decision.next_action = "问题树展开"
        state.decision.decision_reason = "命题已锚定，下一步需要围绕命题建立最小问题树"
        trace.result = {
            "status": "anchored",
            "proposition": state.proposition.proposition_text,
            "next_action": state.decision.next_action,
        }
        return ("done", None, "")

    def _dispatch_learning(
        self, state: Any, pending: dict[str, Any], stage: str,
        response: dict[str, Any], trace: TurnTrace,
    ) -> tuple[str, Any, str]:
        # 先应用当前判断对应的阶段
        if stage == Stage.TREE.value:
            self.learner.build_tree(state, response)
            trace.effective_updates.append(
                "问题树状态：主问题、子问题、依赖与优先问题"
            )
            bloat = failures.check_tree_bloat(state)
            if bloat.detected:
                removed = failures.prune_tree(state)
                trace.event(
                    stage, "failure",
                    f"命中「问题树膨胀」，裁剪低关联分支 {removed}",
                )
            trace.event(
                stage, "gate",
                f"问题树含 {len(state.question_tree.level1())} 个一级、"
                f"{sum(1 for q in state.question_tree.sub_questions if q.parent_id)} 个二级子问题，"
                f"优先问题={state.question_tree.priority_id}",
            )

        elif stage == Stage.GAP.value:
            source = state.gap.trigger_source if state.gap.is_open() else ""
            gap = self.learner.identify_gap(state, response, source=source)
            if not gap.gap_statement:
                state.decision.next_action = "等待用户提问或邻接扩张指令"
                state.decision.active_stage = Stage.IDLE.value
                trace.event(stage, "result", "当前无可识别主缺口，学习循环待命")
                trace.result = {"status": "idle_no_gap"}
                return ("done", None, "")
            trace.effective_updates.append(
                f"认知缺口状态：{state.gap.gap_type} / 来源={state.gap.trigger_source}"
            )
            trace.event(
                stage, "gate",
                f"主缺口：[{state.gap.gap_type}] {state.gap.gap_statement}",
            )

        elif stage == Stage.LEARN.value:
            result = self.learner.learn_round(
                state, pending["primary_objective"], pending["attempt"], response
            )
            pending["stage_explanation"] = result["stage_explanation"]
            pending["competing"] = bool(result.get("competing_explanations"))
            pending["evidence"] = result.get("evidence") or []
            trace.effective_updates.append(
                f"阶段性解释（attempt={pending['attempt']}）："
                f"{result['understanding_change']}"
            )
            trace.event(
                stage, "action",
                f"推动来源：{result['driver']}；回连命题：{result['proposition_link']}",
            )

        elif stage == Stage.BRIEF.value:
            review = self.skeptic.parse_brief(
                state, pending["stage_explanation"], pending["attempt"], response
            )
            for f in review.findings:
                trace.event(
                    stage, "action",
                    f"简审四问｜{f.question} "
                    f"{'【击中】' if f.structural_hit else '未击中'}：{f.answer}",
                )
            failures.record_review_hit(state, review.structural_hit)
            if review.structural_hit:
                gap_data = review.first_hit_gap()
                if gap_data:
                    self.skeptic.install_loop_gap(state, gap_data)
                # 反例库：把击中的反例沉淀下来
                for f in review.findings:
                    if f.structural_hit and f.counterexample:
                        # 同一轮多个问题可能给出相同反例，按内容+版本去重
                        already = any(
                            c.content == f.counterexample
                            and c.pierced_version == state.proposition.proposition_version
                            and c.review_stage == "简审"
                            for c in state.proposition.counterexample_library
                        )
                        if not already:
                            state.proposition.counterexample_library.append(
                                Counterexample(
                                    content=f.counterexample,
                                    pierced_version=state.proposition.proposition_version,
                                    review_stage="简审",
                                )
                            )
                state.decision.loop_back_reason = "简审击中核心脆弱点，回流重写解释"
                trace.event(stage, "failure", state.decision.loop_back_reason)
                pending["attempt"] += 1
                pending["brief_passed"] = False
                pending["stage_explanation"] = ""
                pending["evidence"] = []
                return ("request", LEARN, Stage.LEARN.value)

            idle = failures.check_skeptic_idle(state)
            if idle.detected:
                trace.event(
                    stage, "failure",
                    "命中「怀疑者空转」，需要重写异议焦点后再审",
                )
                return ("request", REWRITE_FOCUS, REWRITE)

            pending["brief_passed"] = True
            # P0-1：简审通过时，登记怀疑者的「无专项增量」裁决
            verdicts = self.skeptic.apply_no_increment_verdicts(state, response)
            if verdicts:
                trace.event(
                    stage, "gate",
                    f"怀疑者裁决 {verdicts} 个维度在本命题下无专项增量（最低深度以裁决满足）",
                )
            trace.event(stage, "gate", "简审四问均未击中关键结构问题（含领域完备性）")

        elif stage == REWRITE:
            new_focus = response.get("new_focus", "")
            if not new_focus:
                raise SchemaError("重写异议焦点失败：new_focus 为空")
            failures.clear_idle_window(state)
            trace.event(stage, "failure", f"异议焦点已重写：{new_focus}")

        elif stage == Stage.DEEP.value:
            deep = self.skeptic.parse_deep(state, response)
            pending["deep_passed"] = deep.passed
            trace.event(
                stage, "action",
                f"深审：显式前提 {len(deep.premises)} 个；边界清={deep.boundary_clear}；"
                f"反例击穿={deep.counterexample_pierces}；"
                f"只适用于高认知用户={deep.only_high_cognition}",
            )
            if not deep.passed:
                if deep.loop_gap:
                    self.skeptic.install_loop_gap(state, deep.loop_gap)
                # 反例库：深审击穿时沉淀反例（按内容+版本去重）
                if deep.counterexample:
                    already = any(
                        c.content == deep.counterexample
                        and c.pierced_version == state.proposition.proposition_version
                        and c.review_stage == "深审"
                        for c in state.proposition.counterexample_library
                    )
                    if not already:
                        state.proposition.counterexample_library.append(
                            Counterexample(
                                content=deep.counterexample,
                                pierced_version=state.proposition.proposition_version,
                                review_stage="深审",
                            )
                        )
                state.decision.loop_back_reason = (
                    f"深审未通过：{deep.critical_issue or '关键前提或边界不成立'}，回流"
                )
                trace.event(stage, "failure", state.decision.loop_back_reason)
                pending["attempt"] += 1
                pending["brief_passed"] = False
                pending["stage_explanation"] = ""
                pending["evidence"] = []
                return ("request", LEARN, Stage.LEARN.value)
            pending["deep_required"] = True
            # P0-1：深审通过时同样可登记「无专项增量」裁决
            verdicts = self.skeptic.apply_no_increment_verdicts(state, response)
            if verdicts:
                trace.event(
                    stage, "gate",
                    f"怀疑者裁决 {verdicts} 个维度在本命题下无专项增量（最低深度以裁决满足）",
                )
            trace.event(stage, "gate", "深审四项退出判据成立")

        elif stage == Stage.COMPRESS.value:
            proposal = self.compressor.propose(
                state, pending["stage_explanation"], response,
                enforce_open_disposition=not pending.get("forced_compress", False),
            )
            conv = failures.check_premature_convergence(
                state,
                brief_passed=bool(pending.get("brief_passed")),
                deep_required=bool(pending.get("deep_required")),
                deep_passed=bool(pending.get("deep_passed")),
                explanation=proposal.explanation,
                open_boundaries=proposal.open_boundaries,
            )
            if conv.detected:
                trace.event(
                    stage, "failure", f"命中「过早收敛」：{conv.correction}"
                )
                return ("request", IDENTIFY_GAP, Stage.GAP.value)

            applied = self.compressor.apply(
                state, proposal, evidence=pending.get("evidence")
            )
            state.round_count += 1
            state.turns_since_explanation_update = 0
            state.gap.resolved = True
            # 学习进展日志：记录压缩达成新版本
            state.progress_log.append(
                ProgressEntry(
                    event="compress",
                    proposition_version=applied["new_version"],
                    summary=(
                        f"压缩为 v{applied['new_version']}，"
                        f"保留 {len(applied['open_boundaries'])} 个开放边界"
                    ),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
            trace.effective_updates.append(
                f"命题状态：当前解释升级为 v{applied['new_version']}，"
                f"开放边界 {len(applied['open_boundaries'])} 个"
            )
            trace.event(
                stage, "result",
                f"阶段压缩完成（v{applied['new_version']}）：{applied['reason']}",
            )
            state.decision.teachable = True
            state.decision.active_stage = Stage.IDLE.value
            state.decision.next_action = "等待用户提问（进入教学响应循环）"
            state.decision.decision_reason = "已有可教版本解释；按决策二优先先教"
            trace.result = {
                "status": "compressed",
                "proposition_version": applied["new_version"],
                "explanation": applied["explanation"],
                "open_boundaries": applied["open_boundaries"],
            }
            return ("done", None, "")

        else:
            raise LoopError(f"学习循环中出现未知阶段: {stage}")

        # ---- 确定性路由：决定下一阶段是否需要判断 ----
        return self._route_learning(state, pending, trace)

    def _route_learning(
        self, state: Any, pending: dict[str, Any], trace: TurnTrace
    ) -> tuple[str, Any, str]:
        """当前阶段处理完后，沿无判断阶段前进，直到遇到下一个判断点或完成。"""
        stage = pending["stage"]
        for _ in range(failures.MAX_TURN_ITERS):
            nxt = self._next_learning_stage(state, pending, stage)
            if nxt == Stage.LEARN.value:
                return ("request", LEARN, nxt)
            if nxt == Stage.GAP.value:
                return ("request", IDENTIFY_GAP, nxt)
            if nxt == Stage.BRIEF.value:
                return ("request", BRIEF_REVIEW, nxt)
            if nxt == Stage.COMPRESS.value:
                return self._coverage_gate_or_compress(state, pending, trace)
            if nxt == Stage.DEEP.value:
                # 深审是否需要由规则裁决；不需要则在同一轮直接放行到压缩
                counterexample = state.gap.gap_type == GapType.COUNTEREXAMPLE.value
                required = self.skeptic.needs_deep_review(
                    state,
                    about_to_stabilize=bool(pending.get("about_to_stabilize")),
                    as_teaching_backbone=False,
                    counterexample_conflict=counterexample,
                    competing_explanations=bool(pending.get("competing")),
                )
                if not required:
                    state.decision.rejected_actions = [
                        {"action": "怀疑者深审",
                         "reason": "四个深审触发条件均未满足，默认只做简审"}
                    ]
                    trace.event(
                        nxt, "gate", "未触发深审条件，直接进入压缩判断"
                    )
                    pending["deep_required"] = False
                    return self._coverage_gate_or_compress(state, pending, trace)
                return ("request", DEEP_REVIEW, nxt)
            raise LoopError(f"路由出现不可达阶段: {nxt}")
        raise LoopError("单轮迭代超过安全上限，怀疑回流未收敛，请检查失败模式处理")

    def _coverage_gate_or_compress(
        self, state: Any, pending: dict[str, Any], trace: TurnTrace
    ) -> tuple[str, Any, str]:
        """压缩前确定性双条件闸门（先宽后深 + 最低深度）。

        锚定声明的每个主干覆盖维度，在允许压缩前必须同时满足：
          1. 覆盖：问题树中存在该维度的子问题，且至少一个已 stable；
          2. 最低深度：该维度沉淀了 ≥1 条可执行规则/取值/判定式，
             或怀疑者显式裁决「本命题下该维度无专项增量」（附理由）。
        未覆盖按缺失类型打回：
          - 树里根本没有该维度的问题 → 回问题树补枝（EXPAND_TREE）；
          - 有问题但尚未学稳定        → 回缺口识别补学（IDENTIFY_GAP）；
          - 已学稳但零深度（占位符）  → 回缺口识别，要求补可执行规则，
            或在随后审查中由怀疑者给出无增量裁决（IDENTIFY_GAP）。
        旧会话没有 coverage_dimensions 时不启用闸门；forced_compress 安全阀
        可越过本闸门（无限扩张截断优先保证能输出版本）。
        """
        required = [
            d for d in state.proposition.coverage_dimensions if d
        ]
        if not required or pending.get("forced_compress"):
            pending.pop("depth_hint", None)
            pending.pop("stale_open_nodes", None)
            return ("request", COMPRESS, Stage.COMPRESS.value)

        tree = state.question_tree
        present = {q.dimension for q in tree.sub_questions if q.dimension}
        stable = {
            q.dimension for q in tree.sub_questions
            if q.dimension and q.status == QuestionStatus.STABLE.value
        }
        missing_branch = [d for d in required if d not in present]
        unlearned = [d for d in required if d in present and d not in stable]

        if missing_branch:
            # 重置审查/解释运行时态，使补枝后重新走完整学习-审查
            pending["brief_passed"] = False
            pending["deep_passed"] = False
            pending["deep_required"] = False
            pending["stage_explanation"] = ""
            pending["evidence"] = []
            pending["coverage_hint"] = {
                "reason": "coverage_gate_missing_branch",
                "missing_dimensions": missing_branch,
                "unlearned_dimensions": unlearned,
                "instruction": "问题树缺少这些主干维度的子问题，请保留已有 id 与内容，为每个缺失维度补至少一个子问题",
            }
            trace.event(
                Stage.TREE.value, "failure",
                f"覆盖度闸门拦截压缩：问题树缺主干维度 {missing_branch}，回问题树补枝",
            )
            return ("request", EXPAND_TREE, Stage.TREE.value)

        if unlearned:
            pending["brief_passed"] = False
            pending["deep_passed"] = False
            pending["deep_required"] = False
            pending["stage_explanation"] = ""
            pending["evidence"] = []
            pending["coverage_hint"] = {
                "reason": "coverage_gate_unlearned",
                "missing_dimensions": [],
                "unlearned_dimensions": unlearned,
                "instruction": "这些主干维度在问题树里只有占位、尚未学稳定，请把主缺口指向其中最该先补的一个并完成学习",
            }
            trace.event(
                Stage.GAP.value, "failure",
                f"覆盖度闸门拦截压缩：主干维度尚未学透 {unlearned}，回缺口识别补学",
            )
            return ("request", IDENTIFY_GAP, Stage.GAP.value)

        # 条件二：最低深度。规则数与无增量裁决都是确定性计数，不靠模型自觉。
        shallow = [
            d for d in required
            if not (
                (rec := state.proposition.get_dimension_depth(d)) is not None
                and rec.depth_satisfied
            )
        ]
        if shallow:
            pending["brief_passed"] = False
            pending["deep_passed"] = False
            pending["deep_required"] = False
            pending["stage_explanation"] = ""
            pending["evidence"] = []
            pending.pop("stale_open_nodes", None)
            pending["depth_hint"] = {
                "reason": "coverage_gate_zero_depth",
                "shallow_dimensions": shallow,
                "instruction": (
                    "这些主干维度的子问题虽已稳定，但没有沉淀任何可执行规则/取值/判定式，"
                    "属于「维度占位符」。请把主缺口指向其中最该先补的一个并补学，"
                    "在 learn_round 的 dimension_rules 中给出具体规则；"
                    "若某一维在本命题下确实与通用做法完全相同、没有专项增量，"
                    "不要硬造规则，在随后的简审/深审 no_increment_verdicts 中附理由裁决。"
                ),
            }
            trace.event(
                Stage.GAP.value, "failure",
                f"最低深度闸门拦截压缩：维度 {shallow} 零规则零裁决，回缺口识别补深度",
            )
            return ("request", IDENTIFY_GAP, Stage.GAP.value)

        # 双条件全部满足：提示用后即弃，放行压缩
        pending.pop("depth_hint", None)
        # P1-4：放行前清点悬置 open 节点（规则已沉淀但状态未回补），
        # 注入压缩判断上下文，定稿时必须逐个 stabilize/retain 处置
        stale_open = [
            {"id": q.id, "text": q.text, "dimension": q.dimension}
            for q in tree.sub_questions
            if q.status == QuestionStatus.OPEN.value
        ]
        if stale_open:
            pending["stale_open_nodes"] = stale_open
            trace.event(
                Stage.COMPRESS.value, "gate",
                f"双条件闸门通过，但有 {len(stale_open)} 个悬置 open 节点"
                f"（{[q['id'] for q in stale_open]}），压缩定稿必须逐个处置："
                "stabilize 回补或 retain 附理由并入开放边界",
            )
        else:
            pending.pop("stale_open_nodes", None)
        rule_count = sum(
            len(state.proposition.get_dimension_depth(d).rules)
            for d in required
            if state.proposition.get_dimension_depth(d) is not None
        )
        verdict_count = sum(
            1 for d in required
            if (rec := state.proposition.get_dimension_depth(d)) is not None
            and rec.no_increment
        )
        trace.event(
            Stage.COMPRESS.value, "gate",
            f"双条件闸门通过：{len(required)} 个维度均已稳定，"
            f"可执行规则 {rule_count} 条、无增量裁决 {verdict_count} 个",
        )
        return ("request", COMPRESS, Stage.COMPRESS.value)

    def _next_learning_stage(
        self, state: Any, pending: dict[str, Any], stage: str
    ) -> str:
        if stage == Stage.TREE.value:
            return Stage.GAP.value if not state.gap.is_open() else Stage.LEARN.value
        if stage == Stage.GAP.value:
            return Stage.LEARN.value
        if stage == Stage.LEARN.value:
            return Stage.BRIEF.value
        if stage == Stage.BRIEF.value:
            return Stage.DEEP.value
        if stage == REWRITE:
            # 重写异议焦点后必须用新焦点重新简审（见 REWRITE_FOCUS 指令：
            # 「使下一次简审指向真正的结构/教学脆弱点」）。不能跳到深审，
            # 否则深审触发条件不满足时会被旁路到压缩，令空转拦截形同虚设。
            return Stage.BRIEF.value
        if stage == Stage.DEEP.value:
            return Stage.COMPRESS.value
        raise LoopError(f"阶段 {stage} 没有后继路由")

    # ---- 教学响应循环 ----

    def _dispatch_teaching(
        self, state: Any, pending: dict[str, Any], stage: str,
        response: dict[str, Any], trace: TurnTrace,
    ) -> tuple[str, Any, str]:
        user_message = pending.get("user_message", "")

        if stage == T_ASSESS:
            hypothesis = self.mentor.assess(state, user_message, response)
            if pending.get("force_reassess"):
                trace.event(
                    Stage.TRANSLATE.value, "failure",
                    f"已强制重判用户假设：水平={hypothesis.level}；卡点={hypothesis.block_type}",
                )
                pending["force_reassess"] = False
            else:
                trace.event(
                    Stage.TRANSLATE.value, "action",
                    f"用户假设：水平={hypothesis.level}；卡点={hypothesis.block_type}；"
                    f"适宜方式={hypothesis.preferred_style}",
                )
            return ("request", PLAN_TEACHING, T_PLAN)

        if stage == T_PLAN:
            plan = self.mentor.plan(state, user_message, response)
            pseudo = failures.check_pseudo_adaptation(
                state, plan["teaching_action"]
            )
            if pseudo.detected:
                trace.event(
                    Stage.TRANSLATE.value, "failure", pseudo.correction
                )
                pending["force_reassess"] = True
                return ("request", ASSESS_USER, T_ASSESS)
            state.decision.next_action = "读取用户反馈"
            state.decision.decision_reason = plan["reason"]
            trace.event(
                Stage.TRANSLATE.value, "gate",
                f"本轮目标={plan['dialog_goal']}；唯一主动作={plan['teaching_action']}",
            )
            return ("request", TEACH, T_TEACH)

        if stage == T_TEACH:
            output = self.mentor.build_reply(state, response)
            trace.effective_updates.append(
                f"教学状态：假设 / 目标={state.teaching.dialog_goal} / "
                f"动作={state.teaching.teaching_action}"
            )
            # 迁移练习闭环：先做迁移时，teach 产出练习任务，进入判分子阶段
            if state.teaching.teaching_action == "先做迁移":
                state.teaching.migration_task = output["reply"]
                trace.event(
                    Stage.TRANSLATE.value, "action",
                    "已生成迁移练习任务，等待用户提交产出后判分",
                )
                trace.result = {
                    "status": "migration_task",
                    "teaching_action": state.teaching.teaching_action,
                    "reply": output["reply"],
                    "path_note": output["path_note"],
                }
                # 文件协议跨进程：题面是持久化教学状态，返回 pending 前必须落库，
                # 否则下一个 step 进程读到的 migration_task 为空
                self.store.save(state)
                return ("request", ASSESS_MIGRATION_OUTPUT, T_MIGRATION_ASSESS)
            # 非迁移动作：清空迁移相关字段，走原有教学回应流程
            state.teaching.migration_task = ""
            state.teaching.migration_output = ""
            trace.result = {
                "status": "teaching",
                "dialog_goal": state.teaching.dialog_goal,
                "teaching_action": state.teaching.teaching_action,
                "reply": output["reply"],
                "path_note": output["path_note"],
            }
            return ("done", None, "")

        if stage == T_MIGRATION_ASSESS:
            assessment = self.skeptic.parse_migration_assessment(response)
            state.teaching.migration_output = pending.get("user_message", "")
            action = state.teaching.teaching_action
            block_type = state.teaching.learner_hypothesis.block_type
            if assessment["passed"]:
                # 迁移通过：记录教学资产 + 进展日志
                if action not in state.teaching.effective_actions:
                    state.teaching.effective_actions.append(action)
                state.teaching.misconception_signal = ""
                state.decision.active_loop = ActiveLoop.LEARNING.value
                state.decision.active_stage = Stage.IDLE.value
                state.decision.next_action = "继续自主学习或等待新问题"
                trace.effective_updates.append(
                    f"教学状态：迁移练习通过，动作 {action} 记入有效动作"
                )
                state.teaching.asset_library.append(
                    TeachingAsset(
                        block_type=block_type,
                        teaching_action=action,
                        dialog_goal=state.teaching.dialog_goal,
                        effective=True,
                        note=assessment["note"],
                    )
                )
                state.progress_log.append(
                    ProgressEntry(
                        event="teaching_success",
                        proposition_version=state.proposition.proposition_version,
                        summary=f"迁移练习通过：{assessment['structure_applied']}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                trace.result = {
                    "status": "migration_passed",
                    "teaching_action": action,
                    "structure_applied": assessment["structure_applied"],
                    "note": assessment["note"],
                }
                return ("done", None, "")
            else:
                # 迁移失败：暴露结构缺口，回流学习循环
                state.gap = GapState(
                    gap_type=GapType.MIGRATION.value,
                    gap_statement=assessment["gap_if_failed"],
                    why_priority="迁移练习暴露结构缺口，必须回到学习循环修正解释",
                    trigger_source=TriggerSource.MIGRATION.value,
                )
                state.decision.active_loop = ActiveLoop.LEARNING.value
                state.decision.active_stage = Stage.GAP.value
                state.decision.next_action = "修复迁移练习暴露的结构缺口"
                state.decision.loop_back_reason = "迁移练习失败回流"
                trace.effective_updates.append(
                    f"认知缺口状态：迁移缺口 / 来源=迁移练习"
                )
                state.progress_log.append(
                    ProgressEntry(
                        event="teaching_failure_loop_back",
                        proposition_version=state.proposition.proposition_version,
                        summary=f"迁移练习失败，回流学习：{assessment['gap_if_failed']}",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                )
                trace.result = {
                    "status": "migration_failed",
                    "gap_if_failed": assessment["gap_if_failed"],
                    "note": assessment["note"],
                }
                return ("request", LEARN, Stage.LEARN.value)

        raise LoopError(f"教学循环中出现未知阶段: {stage}")

    def _handle_feedback(
        self, state: Any, pending: dict[str, Any],
        response: dict[str, Any], trace: TurnTrace,
    ) -> tuple[str, Any, str]:
        fb = self.mentor.receive_feedback(
            state,
            pending.get("user_message", ""),
            pending.get("feedback_text", ""),
            response,
        )
        decision = state.decision
        action = state.teaching.teaching_action
        block_type = state.teaching.learner_hypothesis.block_type
        if fb["understood"]:
            decision.active_loop = ActiveLoop.LEARNING.value
            decision.active_stage = Stage.IDLE.value
            decision.next_action = "继续自主学习或等待新问题"
            decision.loop_back_reason = ""
            trace.event(Stage.TRANSLATE.value, "result", fb["note"])
            trace.effective_updates.append(
                f"教学状态：动作 {action} 记入有效动作"
            )
            # 学习进展日志：教学成功
            state.progress_log.append(
                ProgressEntry(
                    event="teaching_success",
                    proposition_version=state.proposition.proposition_version,
                    summary=f"动作 {action} 对 {block_type} 用户有效",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        elif fb.get("loop_back"):
            decision.active_loop = ActiveLoop.LEARNING.value
            decision.active_stage = Stage.GAP.value
            decision.next_action = "修复教学暴露的主缺口"
            decision.loop_back_reason = f"教学回流：{fb['failure_kind']}"
            trace.event(
                Stage.TRANSLATE.value, "failure",
                f"{decision.loop_back_reason}；{fb['note']}（不默认归因于用户水平）",
            )
            trace.effective_updates.append(
                f"认知缺口状态：教学缺口 / 来源=教学 / {fb['failure_kind']}"
            )
            # 学习进展日志：教学失败回流
            state.progress_log.append(
                ProgressEntry(
                    event="teaching_failure_loop_back",
                    proposition_version=state.proposition.proposition_version,
                    summary=f"动作 {action} 失败（{fb['failure_kind']}），回流学习",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        else:
            decision.next_action = "重判用户假设并重选主导师动作"
            decision.loop_back_reason = f"教学内修正：{fb['failure_kind']}"
            trace.event(
                Stage.TRANSLATE.value, "failure",
                f"命中「教学伪适配」风险（{fb['failure_kind']}），下轮强制重判",
            )
            trace.effective_updates.append(
                f"教学状态：动作 {state.teaching.teaching_action} 记入失败动作"
            )
        trace.result = {
            "status": "understood" if fb["understood"] else "stuck",
            **fb,
        }
        return ("done", None, "")

    # ================= 收尾与工具 =================

    def _finalize(
        self, state: Any, pending: dict[str, Any],
        trace: TurnTrace, _done_marker: Any,
    ) -> None:
        """合格循环最小标准（v3.1）+ 落库 + 清除运行时信封。"""
        if not state.proposition.proposition_text:
            raise LoopError("合格循环校验失败：命题丢失")
        if not trace.effective_updates and trace.result.get("status") != "need_learn":
            raise LoopError("合格循环校验失败：没有任何状态对象发生有效更新")
        if not trace.primary_objective:
            raise LoopError("合格循环校验失败：缺少唯一主推进目标")
        self.store.save(state)
        self.store.clear_pending()

    def _judgment_for_stage(self, stage: str) -> str:
        mapping = {
            Stage.ANCHOR.value: ANCHOR,
            Stage.TREE.value: EXPAND_TREE,
            Stage.GAP.value: IDENTIFY_GAP,
            Stage.LEARN.value: LEARN,
            Stage.BRIEF.value: BRIEF_REVIEW,
            Stage.DEEP.value: DEEP_REVIEW,
            Stage.COMPRESS.value: COMPRESS,
        }
        if stage not in mapping:
            raise LoopError(f"阶段 {stage} 不对应判断点")
        return mapping[stage]

    @staticmethod
    def _tree_ready(state: Any) -> bool:
        tree = state.question_tree
        return bool(
            tree.root_question and len(tree.sub_questions) >= 2 and tree.priority_id
        )

    def _new_pending(
        self,
        *,
        kind: str,
        state: Any,
        stage: str,
        trace: TurnTrace,
        judgment: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        pending: dict[str, Any] = {
            "kind": kind,
            "loop": trace.loop,
            "primary_objective": trace.primary_objective,
            "state": state.to_dict(),
            "stage": stage,
            "judgment": judgment,
            "trace": trace.to_dict(),
        }
        if extra:
            pending.update(extra)
        return pending

    @staticmethod
    def build_completeness_hint(state: Any) -> dict[str, Any]:
        """简审第四问（领域完备性）的确定性上下文（P1-1）。

        内核不内置任何领域知识清单，只把「当前覆盖现状」摆给判断者：
        阶段维度、已沉淀规则的维度、尚无规则的维度，让其对照相邻标准工况
        自行发现内行必问项。接受 PropositionState 对象或其 dict 快照。
        """
        if isinstance(state, dict):
            prop = state.get("proposition", {})
            declared = list(prop.get("coverage_dimensions", []))
            sources = prop.get("dimension_sources", [])
            depths = prop.get("dimension_depth", [])
            phase = [
                s.get("dimension", "")
                for s in sources
                if s.get("kind") == "phase"
            ]
            with_rule = [
                d.get("dimension", "")
                for d in depths if d.get("rules")
            ]
        else:
            prop = state.proposition
            declared = list(prop.coverage_dimensions)
            phase = [
                s.dimension for s in prop.dimension_sources if s.kind == "phase"
            ]
            with_rule = [
                d.dimension for d in prop.dimension_depth if d.rules
            ]
        covered = set(with_rule)
        return {
            "phase_dimensions": [d for d in phase if d],
            "all_dimensions": declared,
            "dimensions_with_rule": [d for d in declared if d in covered],
            "uncovered_dimensions": [d for d in declared if d not in covered],
            "instruction": (
                "重点核对 uncovered_dimensions 中尚无规则沉淀的阶段维度，"
                "并主动联想相邻标准工况（遗漏的荷载工况、失效模式、"
                "规范强制验算、构造要求等）"
            ),
        }

    def _emit(
        self, pending: dict[str, Any], context: dict[str, Any] | None = None
    ) -> PendingOutcome:
        state_snapshot = pending["state"]
        ctx = {
            "primary_objective": pending["primary_objective"],
            "loop": pending["loop"],
        }
        # 仅携带该判断需要的运行时上下文，避免模板膨胀
        for key in (
            "attempt", "user_message", "feedback_text", "raw_proposition",
            "force_reassess", "forced_compress", "stage_explanation",
            "about_to_stabilize", "competing",
        ):
            if key in pending:
                ctx[key] = pending[key]
        # 覆盖度闸门提示只对紧邻的下一个判断生效，用后即弃，不跨判断持久化
        if pending.get("coverage_hint"):
            ctx["coverage_hint"] = pending["coverage_hint"]
            pending.pop("coverage_hint", None)
        # 最低深度提示需跨「缺口识别→学习→简审/深审」多个判断持续可见，
        # 由双条件闸门在通过或安全阀触发时清除（不用后即弃）
        if pending.get("depth_hint"):
            ctx["depth_hint"] = pending["depth_hint"]
        # 领域完备性提示：简审第四问/深审时摆清当前覆盖现状（P1-1），不持久化
        if pending.get("judgment") in (BRIEF_REVIEW, DEEP_REVIEW):
            ctx["completeness_hint"] = self.build_completeness_hint(state_snapshot)
        # 悬置 open 节点清单：仅压缩定稿判断可见，用后即弃（P1-4）；
        # 判断被拒重答时宿主依据已落盘的 request.json 重试，处置校验按状态现算
        if pending.get("judgment") == COMPRESS and pending.get("stale_open_nodes"):
            ctx["stale_open_nodes"] = pending["stale_open_nodes"]
            pending.pop("stale_open_nodes", None)
        if context:
            ctx.update(context)
        request = judgments.build_request(
            pending["judgment"], state_snapshot, ctx
        )
        self.store.save_pending(pending)
        path = self.store.write_request(request.to_dict())
        return PendingOutcome(request=request, request_path=path)


AutonomousAgent = Callable[[str, dict[str, Any]], dict[str, Any]]


def build_learning_result(
    topic: TopicKnowledge,
    convergence: ConvergenceDecision,
) -> dict[str, Any]:
    """Return the durable learning projection without teaching actions."""
    return project_durable_learning_result(topic, convergence)


class AutonomousLearningLoop:
    """Thin scripted adapter over the resumable vNext runtime."""

    def __init__(self, store: KnowledgeStore, agent: AutonomousAgent):
        self.store = store
        self.agent = agent

    def run(self, topic_id: str) -> dict[str, Any]:
        topic = self.store.load(topic_id)
        trace: list[dict[str, Any]] = []
        self._call_agent(judgments.AUTONOMOUS_ANCHOR, topic)
        self._trace(trace, judgments.AUTONOMOUS_ANCHOR)
        runtime = HostRuntimeCoordinator(self.store)
        run = HostRun.new(
            topic_id=topic_id,
            knowledge_root=str(self.store.root.resolve()),
            base_version=topic.version,
        )
        pending = runtime.begin_learning(run)
        while True:
            if pending.stage == "commit_learning":
                pending = runtime.commit_learning(pending)
                continue
            if pending.stage == "checkpoint_or_complete":
                decision_payload = pending.payload["convergence"]
                status = (
                    "complete"
                    if decision_payload["converged"]
                    else (
                        "checkpoint"
                        if decision_payload["checkpoint_required"]
                        else "continue"
                    )
                )
                self._trace(
                    trace,
                    judgments.CHECKPOINT_OR_COMPLETE,
                    cycle=pending.payload["cycle"],
                    status=status,
                )
                next_pending = runtime.checkpoint_or_continue(pending)
                if next_pending is None:
                    decision = ConvergenceDecision(**decision_payload)
                    result = build_learning_result(
                        self.store.load(topic_id), decision
                    )
                    result["trace"] = trace
                    return result
                pending = next_pending
                self._trace(
                    trace,
                    judgments.SELECT_GAP,
                    cycle=pending.payload["cycle"],
                    selected_gap_id=(
                        pending.payload["selected_gap"]["id"]
                        if pending.payload["selected_gap"] is not None
                        else None
                    ),
                )
                continue

            request = runtime.learning_request(pending)
            response = self.agent(
                pending.stage,
                {
                    "topic": request.state_snapshot,
                    "instruction": request.instruction,
                    **request.context,
                },
            )
            previous_stage = pending.stage
            pending = runtime.advance_learning(pending, response)
            cycle = pending.payload["cycle"]
            if previous_stage == judgments.MAP_KNOWLEDGE:
                self._trace(trace, judgments.MAP_KNOWLEDGE)
                self._trace(
                    trace,
                    judgments.SELECT_GAP,
                    cycle=cycle,
                    selected_gap_id=(
                        pending.payload["selected_gap"]["id"]
                        if pending.payload["selected_gap"] is not None
                        else None
                    ),
                )
            elif previous_stage == judgments.PLAN_INVESTIGATION:
                self._trace(
                    trace,
                    judgments.PLAN_INVESTIGATION,
                    cycle=cycle,
                    plan=pending.payload["plan"],
                )
            elif previous_stage == judgments.INTEGRATE_LEARNING:
                self._trace(trace, judgments.INTEGRATE_LEARNING, cycle=cycle)
            elif previous_stage == judgments.SKEPTIC_REVIEW:
                self._trace(
                    trace,
                    judgments.SKEPTIC_REVIEW,
                    cycle=cycle,
                    structural_hit=pending.payload["structural_hit"],
                )
            elif previous_stage == judgments.ASSESS_CONVERGENCE:
                self._trace(
                    trace,
                    judgments.ASSESS_CONVERGENCE,
                    cycle=cycle,
                    reason_code=pending.payload["convergence"]["reason_code"],
                )

    def _call_agent(
        self,
        stage: str,
        topic: TopicKnowledge,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request = judgments.build_autonomous_request(stage, topic, context)
        agent_context = {
            "topic": request.state_snapshot,
            "instruction": request.instruction,
            **request.context,
        }
        response = self.agent(stage, agent_context)
        return judgments.validate_autonomous_response(stage, response)

    @staticmethod
    def _trace(
        trace: list[dict[str, Any]],
        stage: str,
        **details: Any,
    ) -> None:
        trace.append({"stage": stage, **details})
