"""学习者逻辑：向前推进。

本模块不调用任何模型。认识论判断由执行 Skill 的 agent 经 judgment JSON 提供，
本模块只负责把判断应用到状态，并做规则校验（回连命题、问题树结构、缺口消解）。

读写状态：命题、问题树、认知缺口。
阶段性解释在通过审查与压缩之前只存在于运行时信封，不直接写入命题状态。
"""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from . import failures
from .knowledge_schema import (
    Claim,
    ClaimStatus,
    ConvergenceRecord,
    Counterexample,
    Evidence,
    GainLevel,
    KnowledgeGap,
    LearningDelta,
    Priority,
    TopicKnowledge,
)
from .knowledge_store import KnowledgeStore
from .schema import (
    DIM_SOURCE_ANCHOR_KINDS,
    DIM_SOURCE_CROSS_CUTTING,
    DIM_SOURCE_PHASE,
    DimensionDepth,
    DimensionSource,
    GapState,
    QuestionStatus,
    SchemaError,
    SubQuestion,
    TriggerSource,
)

# 疑问词按长在前匹配，避免「为什么」被拆成两个词
_QUESTION_STEMS = (
    "为什么", "为何", "如何", "怎么", "怎样", "什么", "哪些",
    "哪里", "哪儿", "是否", "能否", "该不该", "要不要", "多少",
)
_STEM_RE = re.compile("|".join(_QUESTION_STEMS))
# P1-3：带计量单位的数值取值（如 65mm、200米、3.5m、30%）。命中即要求
# 规则给出 basis（规范编号级出处）或显式标 heuristic=true，防止经验值伪装定论。
_NUMERIC_RULE_RE = re.compile(
    r"\d+(?:\.\d+)?\s*"
    r"(?:mm|cm|kPa|MPa|kN|m|%|‰|°|倍|毫米|厘米|米|度|级)"
    r"(?![a-zA-Z])"
)
# 根问题一旦预写答案形态，问题树就会退化为目录树（海滩命题复审结论）
_ROOT_ANSWER_MARKERS = (
    "完整决策框架", "决策框架", "全过程", "完整流程", "完整方案",
    "知识体系", "全景图", "总体框架", "方法论框架", "完整框架",
)


class Learner:
    # ---- 阶段 1 ----
    def anchor(self, state: Any, judgment: dict[str, Any]) -> dict[str, Any]:
        if not judgment.get("proposition_text"):
            raise SchemaError("命题锚定失败：缺少一句话中心命题")
        if len(judgment.get("adjacent_topics", [])) < 2:
            raise SchemaError("命题锚定失败：至少要显式说明两个不属于命题的邻接议题")
        dimensions = [
            str(d).strip() for d in judgment.get("coverage_dimensions", [])
            if str(d).strip()
        ]
        if len(set(dimensions)) < 2:
            raise SchemaError(
                "命题锚定失败：coverage_dimensions 至少要给出两个不同的主干覆盖维度，"
                "否则问题树无法保证先宽后深"
            )
        dimensions = list(dict.fromkeys(dimensions))
        qualifiers = [
            str(q).strip() for q in judgment.get("scope_qualifiers", []) if str(q).strip()
        ]
        sources = self._parse_dimension_sources(
            judgment.get("dimension_sources"), dimensions, qualifiers
        )
        state.proposition.proposition_text = judgment["proposition_text"]
        state.proposition.proposition_scope = judgment.get("proposition_scope", "")
        state.proposition.adjacent_topics = list(judgment["adjacent_topics"])
        state.proposition.scope_qualifiers = qualifiers
        state.proposition.coverage_dimensions = dimensions
        state.proposition.dimension_sources = sources
        return judgment

    @staticmethod
    def _parse_dimension_sources(
        raw: Any, dimensions: list[str], qualifiers: list[str]
    ) -> list[DimensionSource]:
        """P0-3：把锚定判断里的 dimension_sources 审计为来源记录。

        每个 coverage_dimension 必须恰好有一条来源；phase 必须回指存在的限定词；
        cross_cutting/standalone 必须给理由；横切面的 related_phases 只能引用
        阶段维度。legacy 只允许来自旧状态迁移，新锚定一律拒绝。
        """
        if not isinstance(raw, list) or not raw:
            raise SchemaError(
                "命题锚定失败：必须提供 dimension_sources，逐个说明每个主干维度"
                "由哪个限定词推出（phase），或显式标注横切面/其他并给理由"
            )
        records: list[DimensionSource] = []
        seen: set[str] = set()
        kind_by_dim: dict[str, str] = {}
        for item in raw:
            if not isinstance(item, dict):
                raise SchemaError("dimension_sources 每项必须是对象")
            dim = str(item.get("dimension", "")).strip()
            kind = str(item.get("kind", "")).strip()
            if dim not in dimensions:
                raise SchemaError(
                    f"dimension_sources 出现未在 coverage_dimensions 声明的维度 {dim!r}；"
                    "先改维度声明，再谈来源"
                )
            if dim in seen:
                raise SchemaError(f"维度 {dim} 的来源记录重复，每个维度恰好一条")
            if kind not in DIM_SOURCE_ANCHOR_KINDS:
                raise SchemaError(
                    f"维度 {dim} 的 kind={kind!r} 非法，"
                    f"新锚定只允许 {sorted(DIM_SOURCE_ANCHOR_KINDS)}"
                )
            record = DimensionSource(
                dimension=dim,
                kind=kind,
                source_qualifier=str(item.get("source_qualifier", "")).strip(),
                reason=str(item.get("reason", "")).strip(),
                related_phases=[
                    str(p).strip() for p in item.get("related_phases", [])
                    if str(p).strip()
                ],
            )
            record.validate()
            if kind == DIM_SOURCE_PHASE and record.source_qualifier not in qualifiers:
                raise SchemaError(
                    f"阶段维度 {dim} 标注由限定词 {record.source_qualifier!r} 推出，"
                    f"但 scope_qualifiers 中没有该原文：{qualifiers}；"
                    "来源必须可审计，不能引用未声明的限定词"
                )
            records.append(record)
            seen.add(dim)
            kind_by_dim[dim] = kind
        missing = [d for d in dimensions if d not in seen]
        if missing:
            raise SchemaError(
                f"主干维度 {missing} 缺少 dimension_sources 来源记录，"
                "维度不允许脱离限定词/横切面标注凭空添加"
            )
        phase_dims = {d for d, k in kind_by_dim.items() if k == DIM_SOURCE_PHASE}
        for record in records:
            if record.kind == DIM_SOURCE_CROSS_CUTTING:
                unknown = [p for p in record.related_phases if p not in dimensions]
                if unknown:
                    raise SchemaError(
                        f"横切维度 {record.dimension} 的 related_phases 含未声明维度 {unknown}"
                    )
                bad = [
                    p for p in record.related_phases
                    if kind_by_dim.get(p) != DIM_SOURCE_PHASE
                ]
                if bad:
                    raise SchemaError(
                        f"横切维度 {record.dimension} 的 related_phases 只能引用阶段维度，"
                        f"这些不是：{bad}"
                    )
        if not phase_dims:
            raise SchemaError(
                "dimension_sources 中至少要有一个由限定词推出的 phase 阶段维度，"
                "不能全是横切面"
            )
        return records

    # ---- 阶段 2 ----
    def build_tree(self, state: Any, judgment: dict[str, Any]) -> dict[str, Any]:
        raws = judgment.get("sub_questions", [])
        if not judgment.get("root_question") or len(raws) < 2:
            raise SchemaError("问题树展开失败：需要至少一个主问题与两个关键子问题")
        root = str(judgment["root_question"])
        marker = self._root_presupposes_answer(root)
        if marker:
            raise SchemaError(
                f"根问题预写了答案形态（命中 {marker!r}）：{root}；"
                "根问题必须中性提问（如何成立/如何起作用/在什么条件下失效），"
                "不能把「全过程框架/体系」这类答案目录写进问题，否则树会退化为目录"
            )

        # 每个子问题必须带主干维度标签、只问一件事
        for raw in raws:
            if not isinstance(raw, dict) or not raw.get("id") or not raw.get("text"):
                raise SchemaError("问题树展开失败：每个子问题需要 id 与 text")
            if not str(raw.get("dimension", "")).strip():
                raise SchemaError(
                    f"问题树展开失败：子问题 {raw.get('id')} 缺少 dimension 主干维度标签"
                )
            if self._is_compound_question(str(raw["text"])):
                raise SchemaError(
                    f"问题树展开失败：子问题 {raw.get('id')} 是复合问法——"
                    f"「{raw['text']}」同时问了多件事；一个节点只问一件可独立回答的事，"
                    "请拆成多个节点（深挖用二级子问题 parent_id 挂载）"
                )

        # 幂等合并（覆盖度闸门可能要求回到问题树补枝）：
        # 以 id 为键更新，保留已存在问题的稳定状态，新增缺失维度的问题，不丢已学进度。
        existing = {q.id: q for q in state.question_tree.sub_questions}
        subs: list[SubQuestion] = []
        seen_ids: set[str] = set()
        for raw in raws:
            qid = raw["id"]
            dim = str(raw.get("dimension", "")).strip()
            parent_id = str(raw.get("parent_id", "") or "").strip()
            if qid in existing:
                q = existing[qid]
                q.text = raw["text"]
                q.depends_on = list(raw.get("depends_on", []))
                q.dimension = dim
                q.parent_id = parent_id
                subs.append(q)
            else:
                subs.append(
                    SubQuestion(
                        id=qid,
                        text=raw["text"],
                        depends_on=list(raw.get("depends_on", [])),
                        dimension=dim,
                        parent_id=parent_id,
                    )
                )
            seen_ids.add(qid)
        # 保留本次未重报但此前已存在的分支（通常是已稳定的问题）
        for qid, q in existing.items():
            if qid not in seen_ids:
                subs.append(q)

        # 先宽后深的确定性闸门：锚定声明的每个主干维度都必须在树中有子问题
        required = [
            d for d in state.proposition.coverage_dimensions if d
        ]
        present = {q.dimension for q in subs if q.dimension}
        missing = [d for d in required if d not in present]
        if missing:
            raise SchemaError(
                "问题树展开失败：问题树未覆盖锚定声明的主干维度 "
                f"{missing}；请先为这些维度各补至少一个子问题（先宽后深）"
            )

        priority_id = judgment.get("priority_id", "")
        if priority_id and not any(q.id == priority_id for q in subs):
            raise SchemaError("问题树展开失败：优先问题不在子问题列表中")
        state.question_tree.root_question = root
        state.question_tree.sub_questions = subs
        state.question_tree.dependencies = {q.id: list(q.depends_on) for q in subs}
        state.question_tree.priority_id = priority_id
        # 结构不变量（层级/依赖/容量）+ 横切维度依赖边一致性
        state.question_tree.validate()
        self._validate_tree_limits_and_crosscuts(state)
        return judgment

    @staticmethod
    def _is_compound_question(text: str) -> bool:
        """确定性复合问法检测（模型判断之外的硬性下限）。

        命中任一即判复合：出现 ≥2 个问号；出现 ≥2 个疑问词。
        计数前先剥掉「」/《》内的命题复述（节点常引用命题原文，其中的
        疑问词不是本节点在问的事）。这是保守下限，拦不住全部隐式复合，
        但能挡住「一问塞两事」的直白形态，模型侧仍须按指令做语义拆分。
        """
        t = str(text or "")
        t = re.sub(r"[「《][^」》]*[」》]", "", t)
        if t.count("？") + t.count("?") >= 2:
            return True
        return len(_STEM_RE.findall(t)) >= 2

    @staticmethod
    def _root_presupposes_answer(text: str) -> str:
        """根问题预写答案形态时返回命中的标记词，否则返回空串。"""
        t = str(text or "")
        return next((m for m in _ROOT_ANSWER_MARKERS if m in t), "")

    @staticmethod
    def _validate_tree_limits_and_crosscuts(state: Any) -> None:
        """分层容量上限 + P0-3 横切维度依赖边校验。前置：tree.validate() 已过。"""
        tree = state.question_tree
        l1 = tree.level1()
        if len(l1) > failures.LEVEL1_HARD_CAP:
            raise SchemaError(
                f"一级子问题 {len(l1)} 个超过上限 {failures.LEVEL1_HARD_CAP}："
                "宽骨架先合并同类维度，深挖请挂二级节点而不是继续铺一级"
            )
        for parent in l1:
            n = len(tree.children_of(parent.id))
            if n > failures.LEVEL2_PER_PARENT_CAP:
                raise SchemaError(
                    f"一级节点 {parent.id} 下二级子问题 {n} 个，"
                    f"超过单父上限 {failures.LEVEL2_PER_PARENT_CAP}："
                    "深挖也要收敛，合并同类追问"
                )
        if len(tree.sub_questions) > failures.TREE_TOTAL_CAP:
            raise SchemaError(
                f"问题树总节点 {len(tree.sub_questions)} 个超过上限 {failures.TREE_TOTAL_CAP}"
            )
        # 横切维度（成本/合规等）的一级节点必须依赖其横切的全部阶段维度
        by_id = {q.id: q for q in tree.sub_questions}
        proposition = state.proposition
        for node in l1:
            source = proposition.get_dimension_source(node.dimension)
            if source is None or source.kind != DIM_SOURCE_CROSS_CUTTING:
                continue
            if source.related_phases:
                required_phases = set(source.related_phases)
            else:
                required_phases = {
                    s.dimension for s in proposition.dimension_sources
                    if s.kind == DIM_SOURCE_PHASE
                }
            dep_dims = {
                by_id[d].dimension for d in node.depends_on
                if d in by_id and not by_id[d].parent_id
            }
            lacking = sorted(required_phases - dep_dims)
            if lacking:
                raise SchemaError(
                    f"横切维度节点 {node.id}（{node.dimension}）必须用 depends_on 依赖"
                    f"其横切的全部阶段维度节点，缺少：{lacking}；"
                    "横切面在依赖图上后置于阶段，不能悬空平行放置"
                )

    # ---- 阶段 3 ----
    def identify_gap(
        self, state: Any, judgment: dict[str, Any], source: str = ""
    ) -> GapState:
        statement = judgment.get("gap_statement", "")
        if not statement:
            # 判断结论是当前没有可识别主缺口：显式置空，由调度决定待命
            state.gap = GapState()
            return state.gap
        gap = GapState(
            gap_type=judgment["gap_type"],
            gap_statement=statement,
            why_priority=judgment.get("why_priority", ""),
            secondary_gaps=list(judgment.get("secondary_gaps", [])),
            trigger_source=source or TriggerSource.LEARNING.value,
        )
        state.gap = gap
        return gap

    # ---- 阶段 4 ----
    def learn_round(
        self, state: Any, objective: str, attempt: int,
        judgment: dict[str, Any],
    ) -> dict[str, Any]:
        explanation = judgment.get("stage_explanation", "")
        if not explanation:
            raise SchemaError("主动学习推进失败：未产出可被审查的阶段性解释")
        if not judgment.get("proposition_link"):
            raise SchemaError(
                "主动学习推进失败：新增学习未能回连中心命题，按低价值扩张处理"
            )

        # 应用问题树更新
        for qid in judgment.get("stable_question_ids", []):
            question = state.question_tree.get(qid)
            if question is not None:
                question.status = QuestionStatus.STABLE.value
        new_nodes = judgment.get("new_sub_questions", [])
        for raw in new_nodes:
            if not isinstance(raw, dict) or not raw.get("id") or not raw.get("text"):
                raise SchemaError("new_sub_questions 每项需要 id 与 text")
            if self._is_compound_question(str(raw["text"])):
                raise SchemaError(
                    f"新子问题 {raw.get('id')} 是复合问法——「{raw['text']}」"
                    "同时问了多件事；一个节点只问一件事，深挖请拆成节点并用 parent_id 挂载"
                )
        for raw in new_nodes:
            if state.question_tree.get(raw["id"]) is None:
                state.question_tree.sub_questions.append(
                    SubQuestion(
                        id=raw["id"],
                        text=raw["text"],
                        depends_on=list(raw.get("depends_on", [])),
                        dimension=str(raw.get("dimension", "")).strip(),
                        parent_id=str(raw.get("parent_id", "") or "").strip(),
                    )
                )
        if new_nodes:
            # 新增节点后全树仍须满足层级/容量/横切依赖不变量
            state.question_tree.dependencies = {
                q.id: list(q.depends_on) for q in state.question_tree.sub_questions
            }
            state.question_tree.validate()
            self._validate_tree_limits_and_crosscuts(state)
        next_priority = judgment.get("next_priority_id")
        if next_priority and state.question_tree.get(next_priority):
            state.question_tree.priority_id = next_priority

        # P0-1：沉淀本轮各维度的可执行规则（最低深度的证据）
        self._merge_dimension_rules(state, judgment.get("dimension_rules", []) or [])

        # 应用缺口更新（仅在判断确认消解时）
        if judgment.get("resolved_gap"):
            state.gap.resolved = True

        return judgment

    def build_knowledge_candidate(
        self,
        current: TopicKnowledge,
        *,
        update: dict[str, Any],
    ) -> TopicKnowledge:
        """Construct one validated next projection without durable I/O."""
        next_version = current.version + 1
        delta = LearningDelta.from_dict(update.get("delta", {}))
        _validate_disjoint_claim_actions(delta)

        claim_payloads = _payloads_by_id(update.get("claims", []), "claim")
        evidence_payloads = _payloads_by_id(
            update.get("evidence", []), "evidence"
        )
        gap_payloads = _payloads_by_id(update.get("gaps", []), "gap")
        counterexample_payloads = _payloads_by_id(
            update.get("counterexamples", []), "counterexample"
        )
        _require_exact_payloads(
            claim_payloads,
            set(delta.new_claim_ids) | set(delta.revised_claim_ids),
            "claim",
        )
        _require_exact_payloads(
            evidence_payloads, set(delta.new_evidence_ids), "evidence"
        )
        _require_exact_payloads(
            gap_payloads,
            set(delta.new_gap_ids) | set(delta.resolved_gap_ids),
            "gap",
        )
        undeclared_counterexamples = (
            set(counterexample_payloads) - set(delta.counterexample_hits)
        )
        if undeclared_counterexamples:
            raise ValueError(
                "counterexample payloads are not declared in "
                f"counterexample_hits: {sorted(undeclared_counterexamples)}"
            )

        claims = {item.id: item for item in current.claims}
        evidence = {item.id: item for item in current.evidence}
        gaps = {item.id: item for item in current.gaps}
        counterexamples = {
            item.id: item for item in current.counterexamples
        }

        for claim_id in delta.new_claim_ids:
            if claim_id in claims:
                raise ValueError(f"new claim {claim_id!r} already exists")
            payload = dict(claim_payloads[claim_id])
            payload["introduced_version"] = next_version
            payload["updated_version"] = next_version
            claims[claim_id] = Claim.from_dict(payload)

        for claim_id in delta.revised_claim_ids:
            if claim_id not in claims:
                raise ValueError(f"revised claim {claim_id!r} does not exist")
            payload = dict(claim_payloads[claim_id])
            payload["introduced_version"] = claims[
                claim_id
            ].introduced_version
            payload["updated_version"] = next_version
            claims[claim_id] = Claim.from_dict(payload)

        for claim_id in delta.retired_claim_ids:
            if claim_id not in claims:
                raise ValueError(f"retired claim {claim_id!r} does not exist")
            payload = claims[claim_id].to_dict()
            payload["status"] = ClaimStatus.RETIRED.value
            payload["updated_version"] = next_version
            claims[claim_id] = Claim.from_dict(payload)

        for evidence_id in delta.new_evidence_ids:
            if evidence_id in evidence:
                raise ValueError(
                    f"new evidence {evidence_id!r} already exists"
                )
            evidence[evidence_id] = Evidence.from_dict(
                evidence_payloads[evidence_id]
            )

        for gap_id in delta.new_gap_ids:
            if gap_id in gaps:
                raise ValueError(f"new gap {gap_id!r} already exists")
            gaps[gap_id] = KnowledgeGap.from_dict(gap_payloads[gap_id])

        for gap_id in delta.resolved_gap_ids:
            if gap_id not in gaps:
                raise ValueError(f"resolved gap {gap_id!r} does not exist")
            resolved = KnowledgeGap.from_dict(gap_payloads[gap_id])
            if resolved.status != "resolved":
                raise ValueError(
                    f"resolved gap {gap_id!r} must have status 'resolved'"
                )
            gaps[gap_id] = resolved

        for counterexample_id, payload in counterexample_payloads.items():
            if counterexample_id in counterexamples:
                raise ValueError(
                    f"counterexample {counterexample_id!r} already exists"
                )
            counterexamples[counterexample_id] = Counterexample.from_dict(
                payload
            )

        _validate_gain_level(
            delta,
            gain_level=update.get("gain_level", ""),
            gaps=gaps,
        )
        record = ConvergenceRecord.from_dict(
            {
                "cycle": update.get("cycle", 0),
                "phase": update.get("phase", ""),
                "delta": delta.to_dict(),
                "gain_level": update.get("gain_level", ""),
                "skeptic_structural_hit": update.get(
                    "skeptic_structural_hit", False
                ),
            }
        )
        candidate_payload = current.to_dict()
        candidate_payload.update(
            {
                "version": next_version,
                "claims": [item.to_dict() for item in claims.values()],
                "evidence": [item.to_dict() for item in evidence.values()],
                "gaps": [item.to_dict() for item in gaps.values()],
                "counterexamples": [
                    item.to_dict() for item in counterexamples.values()
                ],
                "convergence_history": [
                    *candidate_payload["convergence_history"],
                    record.to_dict(),
                ],
                "updated_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
            }
        )
        candidate = TopicKnowledge.from_dict(candidate_payload)
        return candidate

    def apply_knowledge_delta(
        self,
        store: KnowledgeStore,
        topic_id: str,
        *,
        base_version: int,
        update: dict[str, Any],
    ) -> TopicKnowledge:
        """Validate and atomically apply one auditable durable delta."""
        current = store.load(topic_id)
        if current.topic_id != topic_id:
            raise ValueError(
                f"loaded topic {current.topic_id!r} does not match {topic_id!r}"
            )
        candidate = self.build_knowledge_candidate(current, update=update)
        return store.save(candidate, base_version=base_version)

    @staticmethod
    def _merge_dimension_rules(state: Any, raw_rules: list[dict[str, Any]]) -> None:
        """把 learn_round 给出的 dimension_rules 合并进命题状态。

        规则：维度必须是锚定声明的 coverage_dimensions；规则文本不能为空；
        同维度内按文本去重保序；已有「无专项增量」裁决的维度不允许再补规则
        （裁决与规则互斥，矛盾说明裁决被推翻，应先显式处理而不是静默混合）。

        P1-3 溯源：规则可带 basis（规范编号级出处）与 heuristic（经验启发式）；
        带计量单位的数值规则两者必须至少给一个，防止无出处经验值伪装成确定规则。
        """
        valid = set(state.proposition.coverage_dimensions)
        for item in raw_rules:
            if not isinstance(item, dict):
                raise SchemaError("dimension_rules 每项必须是 {dimension, rule} 对象")
            dim = str(item.get("dimension", "")).strip()
            rule = str(item.get("rule", "")).strip()
            if dim not in valid:
                raise SchemaError(
                    f"dimension_rules 的维度 {dim!r} 不在锚定声明的主干维度中："
                    f"{sorted(valid)}；规则不能挂到未声明的维度上"
                )
            if not rule:
                raise SchemaError(
                    f"维度 {dim} 的可执行规则为空；「应注意/需考虑」类空话不能计入最低深度"
                )
            basis_raw = item.get("basis", "")
            if not isinstance(basis_raw, str):
                raise SchemaError(
                    f"维度 {dim} 规则 {rule!r} 的 basis 必须是字符串（规范编号级出处）"
                )
            basis = basis_raw.strip()
            heuristic = item.get("heuristic", False)
            if not isinstance(heuristic, bool):
                raise SchemaError(
                    f"维度 {dim} 规则 {rule!r} 的 heuristic 必须是布尔值"
                )
            if _NUMERIC_RULE_RE.search(rule) and not basis and not heuristic:
                raise SchemaError(
                    f"维度 {dim} 的数值规则 {rule!r} 缺少溯源：带计量单位的取值要么给出 "
                    "basis（规范编号/条文出处），要么显式标 heuristic=true"
                    "（经验启发式，对外展示将强制附带「须以当地规划/现行规范为准」）；"
                    "无统一出处的经验值不得写成确定规则"
                )
            record = state.proposition.get_dimension_depth(dim)
            if record is None:
                record = DimensionDepth(dimension=dim)
                state.proposition.dimension_depth.append(record)
            if record.no_increment:
                raise SchemaError(
                    f"维度 {dim} 已被怀疑者裁决为「本命题下无专项增量」，"
                    "不能再向其追加可执行规则；若裁决已被推翻请先显式撤销裁决"
                )
            meta = {"basis": basis, "heuristic": heuristic}
            if rule not in record.rules:
                record.rules.append(rule)
                record.rule_meta[rule] = meta
            elif basis or heuristic:
                # 重复提交时允许补登溯源信息，不允许把已有出处规则改成空话 meta
                old = record.rule_meta.setdefault(rule, {"basis": "", "heuristic": False})
                if basis and not old.get("basis"):
                    old["basis"] = basis
                if heuristic:
                    old["heuristic"] = True


def _payloads_by_id(raw: Any, entity_name: str) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, list):
        raise ValueError(f"{entity_name} payloads must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError(f"{entity_name} payload must be an object")
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"{entity_name} payload requires a non-empty ID")
        if identifier in result:
            raise ValueError(
                f"duplicate {entity_name} payload ID {identifier!r}"
            )
        result[identifier] = item
    return result


def _require_exact_payloads(
    payloads: dict[str, dict[str, Any]],
    declared_ids: set[str],
    entity_name: str,
) -> None:
    actual_ids = set(payloads)
    if actual_ids != declared_ids:
        raise ValueError(
            f"{entity_name} payload IDs must exactly match delta declarations; "
            f"missing={sorted(declared_ids - actual_ids)}, "
            f"undeclared={sorted(actual_ids - declared_ids)}"
        )


def _validate_disjoint_claim_actions(delta: LearningDelta) -> None:
    action_sets = [
        set(delta.new_claim_ids),
        set(delta.revised_claim_ids),
        set(delta.retired_claim_ids),
    ]
    for index, left in enumerate(action_sets):
        for right in action_sets[index + 1 :]:
            overlap = left & right
            if overlap:
                raise ValueError(
                    f"claim IDs cannot have multiple delta actions: "
                    f"{sorted(overlap)}"
                )


def _validate_gain_level(
    delta: LearningDelta,
    *,
    gain_level: Any,
    gaps: dict[str, KnowledgeGap],
) -> None:
    """Reject a low-gain label when the same delta records a major change."""
    if gain_level != GainLevel.LOW.value:
        return
    has_high_value_gap = any(
        gaps[gap_id].priority == Priority.HIGH.value
        or gaps[gap_id].expected_gain == GainLevel.HIGH.value
        for gap_id in delta.new_gap_ids
    )
    if (
        delta.revised_claim_ids
        or delta.retired_claim_ids
        or delta.counterexample_hits
        or has_high_value_gap
    ):
        raise ValueError(
            "low-gain delta cannot contain a major revision, retirement, "
            "counterexample, or high-value gap"
        )
