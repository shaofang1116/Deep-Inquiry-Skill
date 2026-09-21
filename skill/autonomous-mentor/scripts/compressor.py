"""阶段压缩：把新增理解压成当前版本最稳解释。

压缩提案是 agent 的判断；本模块负责结构校验（解释/开放边界/收敛理由三件套）
与落库升版本。过早收敛门在 loop 中先于 apply 裁决。

P1-4：定稿前问题树中不得遗留「被遗忘的 open 节点」——其维度已学稳、规则已
沉淀，却没有任何机制再回收节点状态（v1 海滩重跑 q1b/q1c 滞留即此问题）。
压缩判断必须逐个显式处置：stabilize_question_ids（规则已答，回补 stable）
或 retain_open_questions（确属未决，带理由并入开放边界）。内核按状态现算
open 集合，宿主处置集合必须恰好覆盖，不漏不伪。
"""

from __future__ import annotations

from typing import Any

from .convergence import ConvergenceDecision
from .knowledge_schema import GapStatus, TopicKnowledge
from .schema import Evidence, QuestionStatus, SchemaError


class CompressionProposal:
    def __init__(
        self,
        explanation: str,
        open_boundaries: list[str],
        reason: str,
        stabilize_ids: list[str] | None = None,
        retain_open: dict[str, str] | None = None,
    ):
        self.explanation = explanation
        self.open_boundaries = open_boundaries
        self.reason = reason
        self.stabilize_ids = stabilize_ids or []
        # retain_open: {节点 id: 保留 open 的理由}
        self.retain_open = retain_open or {}


class Compressor:
    def propose(
        self, state: Any, stage_explanation: str, judgment: dict[str, Any],
        enforce_open_disposition: bool = True,
    ) -> CompressionProposal:
        proposal = CompressionProposal(
            explanation=judgment.get("explanation", ""),
            open_boundaries=list(judgment.get("open_boundaries", [])),
            reason=judgment.get("reason", ""),
        )
        if not proposal.explanation:
            raise SchemaError("阶段压缩失败：给不出当前最稳解释")
        if not proposal.open_boundaries:
            # 没有开放边界就宣布稳定版本 = 僵硬结论，按过早收敛失败模式拒绝
            raise SchemaError("阶段压缩失败：缺少至少一个开放边界")
        if not proposal.reason:
            raise SchemaError("阶段压缩失败：未说明为什么现在可以阶段收敛")

        if enforce_open_disposition:
            self._validate_open_disposition(state, judgment, proposal)
        return proposal

    @staticmethod
    def _validate_open_disposition(
        state: Any, judgment: dict[str, Any], proposal: CompressionProposal
    ) -> None:
        """压缩定稿时，全部 open 节点必须被 stabilize/retain 显式覆盖。"""
        tree = state.question_tree
        open_nodes = {
            q.id: q for q in tree.sub_questions
            if q.status == QuestionStatus.OPEN.value
        }
        if not open_nodes:
            return

        raw_stabilize = judgment.get("stabilize_question_ids", [])
        raw_retain = judgment.get("retain_open_questions", [])
        if not isinstance(raw_stabilize, list):
            raise SchemaError("阶段压缩失败：stabilize_question_ids 必须是列表")
        if not isinstance(raw_retain, list):
            raise SchemaError("阶段压缩失败：retain_open_questions 必须是列表")

        stabilize_ids = [str(x).strip() for x in raw_stabilize if str(x).strip()]
        retain_map: dict[str, str] = {}
        for item in raw_retain:
            if not isinstance(item, dict):
                raise SchemaError(
                    "阶段压缩失败：retain_open_questions 每项必须是 {id, reason}"
                )
            qid = str(item.get("id", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if not qid:
                raise SchemaError("阶段压缩失败：retain_open_questions 缺少节点 id")
            if not reason:
                raise SchemaError(
                    f"阶段压缩失败：节点 {qid} 保留 open 必须给出非空理由"
                    "（确属未决才允许带入新版本，理由并入开放边界）"
                )
            retain_map[qid] = reason

        if not stabilize_ids and not retain_map:
            raise SchemaError(
                f"阶段压缩失败：问题树仍有 {len(open_nodes)} 个悬置 open 节点"
                f"（{sorted(open_nodes)}），其维度已学稳但节点状态未闭合；"
                "压缩定稿必须逐个处置：规则已答的列入 stabilize_question_ids，"
                "确属未决的列入 retain_open_questions 并附理由；不允许遗忘"
            )

        overlap = set(stabilize_ids) & set(retain_map)
        if overlap:
            raise SchemaError(
                f"阶段压缩失败：节点 {sorted(overlap)} 同时被 stabilize 与 retain，"
                "一个节点只能有一种去向"
            )
        unknown = [qid for qid in stabilize_ids + list(retain_map)
                   if qid not in open_nodes]
        if unknown:
            raise SchemaError(
                f"阶段压缩失败：处置的节点 {unknown} 不在当前 open 集合"
                f"（{sorted(open_nodes)}）中：id 不存在或已经 stable，不得伪造"
            )
        covered = set(stabilize_ids) | set(retain_map)
        missing = sorted(set(open_nodes) - covered)
        if missing:
            raise SchemaError(
                f"阶段压缩失败：悬置 open 节点 {missing} 未被处置，"
                "stabilize_question_ids 与 retain_open_questions 的并集必须覆盖全部 open 节点"
            )

        proposal.stabilize_ids = stabilize_ids
        proposal.retain_open = retain_map

    def apply(
        self, state: Any, proposal: CompressionProposal,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        state.proposition.current_explanation = proposal.explanation
        state.proposition.open_boundaries = list(proposal.open_boundaries)

        # P1-4：retain 的未闭合子问题显式并入开放边界（节点保持 open）
        for qid, reason in proposal.retain_open.items():
            node = state.question_tree.get(qid)
            text = node.text if node is not None else qid
            boundary = f"未闭合子问题（{qid}）：{text}——{reason}"
            if boundary not in state.proposition.open_boundaries:
                state.proposition.open_boundaries.append(boundary)
        # stabilize 的节点随定稿回补 stable（stable/open 清单由 property 从状态派生）
        for qid in proposal.stabilize_ids:
            node = state.question_tree.get(qid)
            if node is not None:
                node.status = QuestionStatus.STABLE.value

        state.proposition.proposition_version += 1
        new_version = state.proposition.proposition_version
        # 证据簿：把本轮解释的支撑证据挂到新版本上
        for raw in evidence or []:
            if not isinstance(raw, dict) or not raw.get("content"):
                continue
            state.proposition.evidence_book.append(
                Evidence(
                    version=new_version,
                    evidence_type=raw.get("evidence_type", ""),
                    content=raw["content"],
                    source=raw.get("source", ""),
                    citation=raw.get("citation", ""),
                )
            )
        return {
            "new_version": new_version,
            "explanation": proposal.explanation,
            "open_boundaries": list(state.proposition.open_boundaries),
            "reason": proposal.reason,
            "evidence_count": len(evidence or []),
            "stabilized": list(proposal.stabilize_ids),
            "retained_open": dict(proposal.retain_open),
        }


def project_durable_learning_result(
    topic: TopicKnowledge,
    convergence: ConvergenceDecision,
) -> dict[str, Any]:
    """Project canonical durable state into the default learning result."""
    topic.validate()
    return {
        "topic_id": topic.topic_id,
        "knowledge_version": topic.version,
        "delta_history": [
            record.to_dict() for record in topic.convergence_history
        ],
        "unresolved_deferred_gaps": [
            gap.to_dict()
            for gap in topic.gaps
            if gap.status == GapStatus.DEFERRED.value
        ],
        "convergence_reason": {
            "code": convergence.reason_code,
            "message": convergence.reason,
        },
    }
