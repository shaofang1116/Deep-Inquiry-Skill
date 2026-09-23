"""最小状态对象定义（严格对应主循环规范 v3.1「最小状态对象」）。

持久化边界（见 MVP 实现边界文档）：
- 本文件中的五类状态对象属于**持久化状态**，由 store.py 写入 JSON。
- 某轮临时推理、简审/深审草稿、一次性分支判断、消息级临时选择属于
  **运行时状态**，定义在 loop.RunContext，不进入持久层。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SchemaError(ValueError):
    """状态对象未通过最小一致性校验。"""


# P1-3：经验启发式规则对外展示时强制附带的溯源声明（无统一出处，不得伪装成定论）
HEURISTIC_NOTE = "（经验启发式，须以当地规划/现行规范为准）"


class GapType(str, Enum):
    CONCEPT = "概念缺口"
    STRUCTURE = "结构缺口"
    EVIDENCE = "证据缺口"
    COUNTEREXAMPLE = "反例冲突"
    TEACHING = "教学缺口"
    MIGRATION = "迁移缺口"


class TriggerSource(str, Enum):
    LEARNING = "学习"
    SKEPTIC = "怀疑"
    TEACHING = "教学"
    MIGRATION = "迁移练习"


class DialogGoal(str, Enum):
    LITERACY = "扫盲"
    FRAMEWORK = "搭框架"
    CLARIFY = "解惑"
    CORRECT = "纠偏"
    JUDGMENT = "提升判断力"
    TRANSFER = "促进迁移"


class TeachingAction(str, Enum):
    QUESTION = "先提问"
    DEFINE = "先定义"
    FRAME = "先搭框架"
    CORRECT = "先纠偏"
    EXAMPLE = "先举例"
    COUNTEREXAMPLE = "先给反例"
    TRANSFER = "先做迁移"


class ActiveLoop(str, Enum):
    LEARNING = "自主学习循环"
    TEACHING = "教学响应循环"


class Stage(str, Enum):
    """v3.1 八阶段。IDLE 表示当前无进行中的轮次。"""

    IDLE = "空闲"
    ANCHOR = "阶段1-命题锚定"
    TREE = "阶段2-问题树展开"
    GAP = "阶段3-认知缺口识别"
    LEARN = "阶段4-主动学习推进"
    BRIEF = "阶段5-怀疑者简审"
    DEEP = "阶段6-怀疑者深审"
    COMPRESS = "阶段7-阶段压缩"
    TRANSLATE = "阶段8-导师转译"


class QuestionStatus(str, Enum):
    OPEN = "open"
    STABLE = "stable"


def _enum_value(value: Any, enum_cls: type[Enum], field_name: str) -> str:
    """接受枚举成员或其 value 字符串，返回合法 value，否则报错。"""
    if isinstance(value, enum_cls):
        return value.value
    values = {m.value for m in enum_cls}  # type: ignore[attr-defined]
    if isinstance(value, str) and value in values:
        return value
    raise SchemaError(f"字段 {field_name} 的值 {value!r} 不在 {enum_cls.__name__} 合法范围内")


@dataclass
class SubQuestion:
    id: str
    text: str
    depends_on: list[str] = field(default_factory=list)
    status: str = QuestionStatus.OPEN.value
    dimension: str = ""
    # P0-2：二级树支撑。parent_id 为空表示挂在根下的一级节点；
    # 非空必须指向某个一级节点（树深最多 2，不允许三级）。
    parent_id: str = ""

    def validate(self) -> None:
        if not self.id or not self.text:
            raise SchemaError("子问题 id 与 text 不能为空")
        if self.status not in {s.value for s in QuestionStatus}:
            raise SchemaError(f"子问题状态非法: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "depends_on": list(self.depends_on),
            "status": self.status,
            "dimension": self.dimension,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubQuestion":
        return cls(
            id=data["id"],
            text=data["text"],
            depends_on=list(data.get("depends_on", [])),
            status=data.get("status", QuestionStatus.OPEN.value),
            dimension=data.get("dimension", ""),
            parent_id=str(data.get("parent_id", "") or ""),
        )


@dataclass
class Evidence:
    """支撑某个版本解释的一条证据。

    证据簿是 v2 轻量扩展件：只记录「这版解释由什么推动」，不做重型知识图谱。
    evidence_type 取值：来源观察 / 反例击穿 / 教学断链 / 逻辑推导。
    """

    version: int
    evidence_type: str
    content: str
    source: str = ""
    citation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "evidence_type": self.evidence_type,
            "content": self.content,
            "source": self.source,
            "citation": self.citation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        return cls(
            version=int(data.get("version", 0)),
            evidence_type=data.get("evidence_type", ""),
            content=data.get("content", ""),
            source=data.get("source", ""),
            citation=data.get("citation", ""),
        )


@dataclass
class Counterexample:
    """击穿过某版解释的反例，沉淀为可复用的检查项。

    反例库是 v2 轻量扩展件：只记录反例本身与击穿上下文，供后续审查参考，
    内核不做自动模式匹配（重型逻辑留作后续）。
    """

    content: str
    pierced_version: int = 0
    review_stage: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "pierced_version": self.pierced_version,
            "review_stage": self.review_stage,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Counterexample":
        return cls(
            content=data.get("content", ""),
            pierced_version=int(data.get("pierced_version", 0)),
            review_stage=data.get("review_stage", ""),
        )


@dataclass
class DimensionDepth:
    """单个主干维度的「最低深度」记录（P0-1 双条件闸门）。

    维度满足最低深度只有两种互斥方式：
    - rules 非空：该维度已沉淀至少一条可执行规则/取值/判定式/if-then 分支；
    - no_increment=True：怀疑者显式裁决「本命题下该维度与通用做法相同，
      无专项增量」，并给出理由、绑定裁决时的命题版本。
    两者皆无的维度即使子问题全部 stable，也不允许压缩（防止维度占位符过闸）。
    """

    dimension: str
    rules: list[str] = field(default_factory=list)
    # P1-3：规则溯源 meta，键为 rules 中的规则原文：
    # {"basis": 规范编号级出处, "heuristic": 是否经验启发式（无统一出处）}
    rule_meta: dict[str, dict[str, Any]] = field(default_factory=dict)
    no_increment: bool = False
    no_increment_reason: str = ""
    decided_version: int = 0

    @property
    def depth_satisfied(self) -> bool:
        return bool(self.rules) or self.no_increment

    def render_rule(self, rule: str) -> str:
        """对外展示规则文本：启发式规则强制附加可溯源声明，防止伪装成定论。"""
        meta = self.rule_meta.get(rule, {})
        if meta.get("heuristic"):
            return f"{rule}{HEURISTIC_NOTE}"
        return rule

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "rules": list(self.rules),
            "rule_meta": {k: dict(v) for k, v in self.rule_meta.items()},
            "no_increment": self.no_increment,
            "no_increment_reason": self.no_increment_reason,
            "decided_version": self.decided_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DimensionDepth":
        raw_meta = data.get("rule_meta") or {}
        meta = {
            str(k): {
                "basis": str(v.get("basis", "")),
                "heuristic": bool(v.get("heuristic", False)),
            }
            for k, v in raw_meta.items()
            if isinstance(v, dict)
        } if isinstance(raw_meta, dict) else {}
        return cls(
            dimension=data.get("dimension", ""),
            rules=[str(r) for r in data.get("rules", []) if str(r).strip()],
            rule_meta=meta,
            no_increment=bool(data.get("no_increment", False)),
            no_increment_reason=data.get("no_increment_reason", ""),
            decided_version=int(data.get("decided_version", 0)),
        )


# P0-3：主干维度来源类型
DIM_SOURCE_PHASE = "phase"                # 阶段维度：由某个命题限定词直接推出
DIM_SOURCE_CROSS_CUTTING = "cross_cutting"  # 横切面：跨阶段的属性（如成本/合规）
DIM_SOURCE_STANDALONE = "standalone"      # 其他：非限定词推出，锚定必须说明理由
DIM_SOURCE_LEGACY = "legacy"              # 旧会话迁移：来源缺失，仅加载兼容用
DIM_SOURCE_KINDS = {
    DIM_SOURCE_PHASE, DIM_SOURCE_CROSS_CUTTING,
    DIM_SOURCE_STANDALONE, DIM_SOURCE_LEGACY,
}
# 新锚定只允许前三种（legacy 只能来自旧状态迁移）
DIM_SOURCE_ANCHOR_KINDS = {
    DIM_SOURCE_PHASE, DIM_SOURCE_CROSS_CUTTING, DIM_SOURCE_STANDALONE,
}


@dataclass
class DimensionSource:
    """单个主干维度的推导链记录（P0-3：限定词→维度可审计）。

    - phase：阶段维度，source_qualifier 必须回指 scope_qualifiers 中的原文；
    - cross_cutting：横切维度（如成本/合规），必须给 reason，并可在
      related_phases 中声明它横切哪些阶段维度（默认全部阶段），
      建树时该维度的一级节点必须依赖这些阶段维度的一级节点；
    - standalone：非限定词推出的其他维度，必须给 reason；
    - legacy：旧会话迁移占位，不允许在新锚定中出现。
    """

    dimension: str
    kind: str
    source_qualifier: str = ""
    reason: str = ""
    related_phases: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if not self.dimension:
            raise SchemaError("维度来源记录缺少 dimension")
        if self.kind not in DIM_SOURCE_KINDS:
            raise SchemaError(f"维度 {self.dimension} 的来源类型非法: {self.kind}")
        if self.kind == DIM_SOURCE_LEGACY:
            return
        if self.kind == DIM_SOURCE_PHASE and not self.source_qualifier:
            raise SchemaError(
                f"阶段维度 {self.dimension} 必须用 source_qualifier 回指标定词原文"
            )
        if self.kind in (DIM_SOURCE_CROSS_CUTTING, DIM_SOURCE_STANDALONE) \
                and not self.reason:
            raise SchemaError(
                f"维度 {self.dimension} 来源为 {self.kind}，必须给出 reason"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "kind": self.kind,
            "source_qualifier": self.source_qualifier,
            "reason": self.reason,
            "related_phases": list(self.related_phases),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DimensionSource":
        return cls(
            dimension=data.get("dimension", ""),
            kind=data.get("kind", DIM_SOURCE_LEGACY),
            source_qualifier=data.get("source_qualifier", ""),
            reason=data.get("reason", ""),
            related_phases=list(data.get("related_phases", [])),
        )


@dataclass
class PropositionState:
    """1. 命题状态。"""

    proposition_text: str = ""
    proposition_version: int = 0
    current_explanation: str = ""
    open_boundaries: list[str] = field(default_factory=list)
    proposition_scope: str = ""
    adjacent_topics: list[str] = field(default_factory=list)
    # 先宽后深：锚定阶段拆出的命题限定词，以及必须被问题树覆盖的主干维度
    scope_qualifiers: list[str] = field(default_factory=list)
    coverage_dimensions: list[str] = field(default_factory=list)
    evidence_book: list[Evidence] = field(default_factory=list)
    counterexample_library: list[Counterexample] = field(default_factory=list)
    # P0-1：每个主干维度的最低深度记录（可执行规则或「无专项增量」裁决）
    dimension_depth: list[DimensionDepth] = field(default_factory=list)
    # P0-3：每个主干维度的推导链（由哪个限定词推出，或横切面/其他，可审计）
    dimension_sources: list[DimensionSource] = field(default_factory=list)

    def validate(self) -> None:
        if not isinstance(self.proposition_version, int) or self.proposition_version < 0:
            raise SchemaError("proposition_version 必须为非负整数")
        if not isinstance(self.open_boundaries, list) or not isinstance(
            self.adjacent_topics, list
        ):
            raise SchemaError("开放边界与邻接议题必须为列表")
        if not isinstance(self.scope_qualifiers, list) or not isinstance(
            self.coverage_dimensions, list
        ):
            raise SchemaError("命题限定词与覆盖维度必须为列表")
        if not isinstance(self.dimension_depth, list):
            raise SchemaError("维度深度记录必须为列表")
        for d in self.dimension_depth:
            if not d.dimension:
                raise SchemaError("维度深度记录缺少 dimension")
            if not d.rules and not d.no_increment:
                raise SchemaError(
                    f"维度 {d.dimension} 的深度记录既无可执行规则也无无增量裁决"
                )
            if d.no_increment and not d.no_increment_reason:
                raise SchemaError(
                    f"维度 {d.dimension} 裁决为无专项增量时必须给出理由"
                )
        if not isinstance(self.dimension_sources, list):
            raise SchemaError("维度来源记录必须为列表")
        sourced = {s.dimension for s in self.dimension_sources if s.dimension}
        declared = set(self.coverage_dimensions)
        if sourced != declared:
            missing = sorted(declared - sourced)
            extra = sorted(sourced - declared)
            raise SchemaError(
                "维度来源记录与 coverage_dimensions 不一致："
                f"缺来源 {missing}，来源多出 {extra}"
            )
        for s in self.dimension_sources:
            s.validate()
            if s.kind == DIM_SOURCE_CROSS_CUTTING:
                unknown = [d for d in s.related_phases if d not in declared]
                if unknown:
                    raise SchemaError(
                        f"横切维度 {s.dimension} 的 related_phases 含未声明维度: {unknown}"
                    )

    def get_dimension_depth(self, dimension: str) -> DimensionDepth | None:
        return next(
            (d for d in self.dimension_depth if d.dimension == dimension), None
        )

    def get_dimension_source(self, dimension: str) -> DimensionSource | None:
        return next(
            (s for s in self.dimension_sources if s.dimension == dimension), None
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposition_text": self.proposition_text,
            "proposition_version": self.proposition_version,
            "current_explanation": self.current_explanation,
            "open_boundaries": list(self.open_boundaries),
            "proposition_scope": self.proposition_scope,
            "adjacent_topics": list(self.adjacent_topics),
            "scope_qualifiers": list(self.scope_qualifiers),
            "coverage_dimensions": list(self.coverage_dimensions),
            "evidence_book": [e.to_dict() for e in self.evidence_book],
            "counterexample_library": [
                c.to_dict() for c in self.counterexample_library
            ],
            "dimension_depth": [d.to_dict() for d in self.dimension_depth],
            "dimension_sources": [s.to_dict() for s in self.dimension_sources],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PropositionState":
        dimensions = list(data.get("coverage_dimensions", []))
        raw_sources = data.get("dimension_sources")
        if raw_sources is None:
            # 旧会话：有维度名无来源记录，迁移为 legacy 占位以保证可加载，
            # 新锚定不允许产出 legacy（由 Learner.anchor 强制）。
            sources = [
                DimensionSource(dimension=d, kind=DIM_SOURCE_LEGACY)
                for d in dimensions
            ]
        else:
            sources = [DimensionSource.from_dict(s) for s in raw_sources]
        return cls(
            proposition_text=data.get("proposition_text", ""),
            proposition_version=data.get("proposition_version", 0),
            current_explanation=data.get("current_explanation", ""),
            open_boundaries=list(data.get("open_boundaries", [])),
            proposition_scope=data.get("proposition_scope", ""),
            adjacent_topics=list(data.get("adjacent_topics", [])),
            scope_qualifiers=list(data.get("scope_qualifiers", [])),
            coverage_dimensions=list(dimensions),
            evidence_book=[Evidence.from_dict(e) for e in data.get("evidence_book", [])],
            counterexample_library=[
                Counterexample.from_dict(c)
                for c in data.get("counterexample_library", [])
            ],
            dimension_depth=[
                DimensionDepth.from_dict(d) for d in data.get("dimension_depth", [])
            ],
            dimension_sources=sources,
        )


@dataclass
class QuestionTreeState:
    """2. 问题树状态。"""

    root_question: str = ""
    sub_questions: list[SubQuestion] = field(default_factory=list)
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    priority_id: str = ""

    @property
    def stable_questions(self) -> list[str]:
        return [q.text for q in self.sub_questions if q.status == QuestionStatus.STABLE.value]

    @property
    def open_questions(self) -> list[str]:
        return [q.text for q in self.sub_questions if q.status == QuestionStatus.OPEN.value]

    def validate(self) -> None:
        for q in self.sub_questions:
            q.validate()
        by_id = {q.id: q for q in self.sub_questions}
        if len(by_id) != len(self.sub_questions):
            raise SchemaError("问题树存在重复的子问题 id")
        for q in self.sub_questions:
            unknown = [d for d in q.depends_on if d not in by_id]
            if unknown:
                raise SchemaError(f"子问题 {q.id} 依赖了不存在的问题: {unknown}")
            # P0-2：二级树结构不变量——parent 必须存在且本身是一级节点（禁止三级），
            # 二级节点必须与父节点同维度（深挖是在维度内部生长，不跨维度挂载）。
            if q.parent_id:
                parent = by_id.get(q.parent_id)
                if parent is None:
                    raise SchemaError(
                        f"子问题 {q.id} 的 parent_id {q.parent_id} 不在问题树中"
                    )
                if parent.parent_id:
                    raise SchemaError(
                        f"子问题 {q.id} 挂在二级节点 {q.parent_id} 下，"
                        "问题树最多两级，不允许三级节点"
                    )
                if q.dimension and parent.dimension and q.dimension != parent.dimension:
                    raise SchemaError(
                        f"二级子问题 {q.id}（维度 {q.dimension}）与父节点 "
                        f"{q.parent_id}（维度 {parent.dimension}）维度不一致，"
                        "二级深挖只能在同一维度内生长"
                    )
        if self.priority_id and self.priority_id not in by_id:
            raise SchemaError(f"优先问题 {self.priority_id} 不在问题树中")

    def level1(self) -> list[SubQuestion]:
        """挂在根下的一级子问题。"""
        return [q for q in self.sub_questions if not q.parent_id]

    def children_of(self, qid: str) -> list[SubQuestion]:
        """某一级节点下的二级子问题。"""
        return [q for q in self.sub_questions if q.parent_id == qid]

    def get(self, qid: str) -> SubQuestion | None:
        return next((q for q in self.sub_questions if q.id == qid), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_question": self.root_question,
            "sub_questions": [q.to_dict() for q in self.sub_questions],
            "dependencies": {k: list(v) for k, v in self.dependencies.items()},
            "stable_questions": self.stable_questions,
            "open_questions": self.open_questions,
            "priority_id": self.priority_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuestionTreeState":
        subs = [SubQuestion.from_dict(q) for q in data.get("sub_questions", [])]
        deps = data.get("dependencies") or {q.id: list(q.depends_on) for q in subs}
        return cls(
            root_question=data.get("root_question", ""),
            sub_questions=subs,
            dependencies={k: list(v) for k, v in deps.items()},
            priority_id=data.get("priority_id", ""),
        )


@dataclass
class GapState:
    """3. 认知缺口状态（MVP 只维护一个主缺口）。"""

    gap_type: str = ""
    gap_statement: str = ""
    why_priority: str = ""
    secondary_gaps: list[str] = field(default_factory=list)
    trigger_source: str = ""
    resolved: bool = False

    def validate(self) -> None:
        if self.gap_statement and not self.gap_type:
            raise SchemaError("存在主缺口描述但缺少缺口类型")
        if self.gap_type:
            _enum_value(self.gap_type, GapType, "gap.gap_type")
        if self.trigger_source:
            _enum_value(self.trigger_source, TriggerSource, "gap.trigger_source")

    def is_open(self) -> bool:
        return bool(self.gap_statement) and not self.resolved

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_type": self.gap_type,
            "gap_statement": self.gap_statement,
            "why_priority": self.why_priority,
            "secondary_gaps": list(self.secondary_gaps),
            "trigger_source": self.trigger_source,
            "resolved": self.resolved,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GapState":
        return cls(
            gap_type=data.get("gap_type", ""),
            gap_statement=data.get("gap_statement", ""),
            why_priority=data.get("why_priority", ""),
            secondary_gaps=list(data.get("secondary_gaps", [])),
            trigger_source=data.get("trigger_source", ""),
            resolved=data.get("resolved", False),
        )


@dataclass
class LearnerHypothesis:
    """用户当前理解假设：可被单轮对话修正，不是长期画像。"""

    level: str = ""
    block_type: str = ""
    preferred_style: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "block_type": self.block_type,
            "preferred_style": self.preferred_style,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnerHypothesis":
        data = data or {}
        return cls(
            level=data.get("level", ""),
            block_type=data.get("block_type", ""),
            preferred_style=data.get("preferred_style", ""),
            note=data.get("note", ""),
        )


@dataclass
class TeachingAsset:
    """一条教学经验：某动作对某类用户是否有效。

    教学资产库是 v2 轻量扩展件：记录 block_type × action × goal × effective
    四元组，供后续选动作时参考；内核不做自动推荐。
    """

    block_type: str
    teaching_action: str
    dialog_goal: str
    effective: bool
    failure_kind: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_type": self.block_type,
            "teaching_action": self.teaching_action,
            "dialog_goal": self.dialog_goal,
            "effective": self.effective,
            "failure_kind": self.failure_kind,
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TeachingAsset":
        return cls(
            block_type=data.get("block_type", ""),
            teaching_action=data.get("teaching_action", ""),
            dialog_goal=data.get("dialog_goal", ""),
            effective=bool(data.get("effective", False)),
            failure_kind=data.get("failure_kind", ""),
            note=data.get("note", ""),
        )


@dataclass
class TeachingState:
    """4. 教学状态。"""

    learner_hypothesis: LearnerHypothesis = field(default_factory=LearnerHypothesis)
    dialog_goal: str = ""
    teaching_action: str = ""
    failed_actions: list[str] = field(default_factory=list)
    effective_actions: list[str] = field(default_factory=list)
    misconception_signal: str = ""
    asset_library: list[TeachingAsset] = field(default_factory=list)
    migration_task: str = ""
    migration_output: str = ""

    def validate(self) -> None:
        if self.dialog_goal:
            _enum_value(self.dialog_goal, DialogGoal, "teaching.dialog_goal")
        if self.teaching_action:
            _enum_value(self.teaching_action, TeachingAction, "teaching.teaching_action")

    def to_dict(self) -> dict[str, Any]:
        return {
            "learner_hypothesis": self.learner_hypothesis.to_dict(),
            "dialog_goal": self.dialog_goal,
            "teaching_action": self.teaching_action,
            "failed_actions": list(self.failed_actions),
            "effective_actions": list(self.effective_actions),
            "misconception_signal": self.misconception_signal,
            "asset_library": [a.to_dict() for a in self.asset_library],
            "migration_task": self.migration_task,
            "migration_output": self.migration_output,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TeachingState":
        return cls(
            learner_hypothesis=LearnerHypothesis.from_dict(
                data.get("learner_hypothesis", {})
            ),
            dialog_goal=data.get("dialog_goal", ""),
            teaching_action=data.get("teaching_action", ""),
            failed_actions=list(data.get("failed_actions", [])),
            effective_actions=list(data.get("effective_actions", [])),
            misconception_signal=data.get("misconception_signal", ""),
            asset_library=[
                TeachingAsset.from_dict(a) for a in data.get("asset_library", [])
            ],
            migration_task=data.get("migration_task", ""),
            migration_output=data.get("migration_output", ""),
        )


@dataclass
class DecisionState:
    """5. 循环决策状态（持久化其最近稳定结果）。"""

    active_loop: str = ActiveLoop.LEARNING.value
    active_stage: str = Stage.IDLE.value
    primary_objective: str = ""
    next_action: str = ""
    decision_reason: str = ""
    rejected_actions: list[dict[str, str]] = field(default_factory=list)
    loop_back_reason: str = ""
    teachable: bool = False
    # 怀疑者空转失败模式需要跨轮观察最近三次简审是否击中结构问题
    recent_review_hits: list[bool] = field(default_factory=list)

    def validate(self) -> None:
        _enum_value(self.active_loop, ActiveLoop, "decision.active_loop")
        _enum_value(self.active_stage, Stage, "decision.active_stage")

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_loop": self.active_loop,
            "active_stage": self.active_stage,
            "primary_objective": self.primary_objective,
            "next_action": self.next_action,
            "decision_reason": self.decision_reason,
            "rejected_actions": list(self.rejected_actions),
            "loop_back_reason": self.loop_back_reason,
            "teachable": self.teachable,
            "recent_review_hits": list(self.recent_review_hits),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DecisionState":
        return cls(
            active_loop=data.get("active_loop", ActiveLoop.LEARNING.value),
            active_stage=data.get("active_stage", Stage.IDLE.value),
            primary_objective=data.get("primary_objective", ""),
            next_action=data.get("next_action", ""),
            decision_reason=data.get("decision_reason", ""),
            rejected_actions=list(data.get("rejected_actions", [])),
            loop_back_reason=data.get("loop_back_reason", ""),
            teachable=data.get("teachable", False),
            recent_review_hits=[bool(x) for x in data.get("recent_review_hits", [])],
        )


@dataclass
class ProgressEntry:
    """学习进展日志的一条里程碑事件。

    轻量学习进展日志是 v2 扩展件：只在关键节点（压缩达成、教学成败）记录，
    形成单命题内的宏观时间线，供后续轮次辅助决策；不做跨 session 聚合。
    """

    event: str
    proposition_version: int = 0
    summary: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event": self.event,
            "proposition_version": self.proposition_version,
            "summary": self.summary,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProgressEntry":
        return cls(
            event=data.get("event", ""),
            proposition_version=int(data.get("proposition_version", 0)),
            summary=data.get("summary", ""),
            timestamp=data.get("timestamp", ""),
        )


@dataclass
class SessionState:
    """一个中心命题对应一个会话，即一个持久化 JSON 文件。"""

    topic_id: str = ""
    knowledge_root: str = ""
    base_version: int = 0
    proposition: PropositionState = field(default_factory=PropositionState)
    question_tree: QuestionTreeState = field(default_factory=QuestionTreeState)
    gap: GapState = field(default_factory=GapState)
    teaching: TeachingState = field(default_factory=TeachingState)
    decision: DecisionState = field(default_factory=DecisionState)
    progress_log: list[ProgressEntry] = field(default_factory=list)
    round_count: int = 0
    turns_since_explanation_update: int = 0
    schema_version: int = 1
    created_at: str = ""
    updated_at: str = ""

    def validate(self) -> None:
        if bool(self.topic_id) != bool(self.knowledge_root):
            raise SchemaError("topic_id 与 knowledge_root 必须同时存在或同时为空")
        if isinstance(self.base_version, bool) or not isinstance(self.base_version, int):
            raise SchemaError("base_version 必须为非负整数")
        if self.base_version < 0:
            raise SchemaError("base_version 必须为非负整数")
        if self.topic_id and self.base_version < 1:
            raise SchemaError("vNext 会话引用必须使用正数 base_version")
        self.proposition.validate()
        self.question_tree.validate()
        self.gap.validate()
        self.teaching.validate()
        self.decision.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "topic_id": self.topic_id,
            "knowledge_root": self.knowledge_root,
            "base_version": self.base_version,
            "round_count": self.round_count,
            "turns_since_explanation_update": self.turns_since_explanation_update,
            "proposition": self.proposition.to_dict(),
            "question_tree": self.question_tree.to_dict(),
            "gap": self.gap.to_dict(),
            "teaching": self.teaching.to_dict(),
            "decision": self.decision.to_dict(),
            "progress_log": [p.to_dict() for p in self.progress_log],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        return cls(
            schema_version=data.get("schema_version", 1),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            topic_id=data.get("topic_id", ""),
            knowledge_root=data.get("knowledge_root", ""),
            base_version=data.get("base_version", 0),
            round_count=data.get("round_count", 0),
            turns_since_explanation_update=data.get(
                "turns_since_explanation_update", 0
            ),
            proposition=PropositionState.from_dict(data.get("proposition", {})),
            question_tree=QuestionTreeState.from_dict(data.get("question_tree", {})),
            gap=GapState.from_dict(data.get("gap", {})),
            teaching=TeachingState.from_dict(data.get("teaching", {})),
            decision=DecisionState.from_dict(data.get("decision", {})),
            progress_log=[
                ProgressEntry.from_dict(p) for p in data.get("progress_log", [])
            ],
        )
