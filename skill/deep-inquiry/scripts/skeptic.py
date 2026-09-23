"""怀疑者逻辑：防止错误稳定化。

不调用模型：简审/深审内容来自 agent 的判断响应，本模块负责固定四问
（三结构问 + 一领域完备性问）、结构击中判定、深审触发规则与回流缺口登记。
是否回流由 loop 中的规则裁决。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .judgments import BRIEF_QUESTIONS
from .schema import DimensionDepth, GapState, SchemaError, TriggerSource


@dataclass
class Finding:
    question: str
    answer: str
    structural_hit: bool
    loop_gap: dict[str, Any] | None = None
    counterexample: str = ""


@dataclass
class BriefReviewResult:
    attempt: int
    findings: list[Finding] = field(default_factory=list)

    @property
    def structural_hit(self) -> bool:
        return any(f.structural_hit for f in self.findings)

    def first_hit_gap(self) -> dict[str, Any] | None:
        for f in self.findings:
            if f.structural_hit and f.loop_gap:
                return f.loop_gap
        return None


@dataclass
class DeepReviewResult:
    passed: bool
    premises: list[str]
    boundary_clear: bool
    counterexample_pierces: bool
    only_high_cognition: bool
    critical_issue: str
    loop_gap: dict[str, Any] | None
    counterexample: str = ""


class Skeptic:
    BRIEF_QUESTIONS = BRIEF_QUESTIONS  # 固定四问，不允许模型更改

    # ---- 阶段 5 ----
    def parse_brief(
        self, state: Any, explanation: str, attempt: int,
        judgment: dict[str, Any],
    ) -> BriefReviewResult:
        raw_findings = judgment.get("findings", [])
        if len(raw_findings) != 4:
            raise SchemaError("简审必须回答固定四问（含领域完备性第四问）")
        findings = []
        for i, item in enumerate(raw_findings):
            loop_gap = item.get("loop_gap")
            if loop_gap is not None and not isinstance(loop_gap, dict):
                raise SchemaError(
                    "简审第 %d 问的 loop_gap 必须是缺口对象，不能是字符串；"
                    "形状为 {\"gap_type\": 概念缺口|结构缺口|证据缺口|反例冲突|教学缺口|迁移缺口, "
                    "\"gap_statement\": 缺口描述, \"why_priority\": 可选, "
                    "\"trigger_source\": 可选（怀疑/教学/迁移练习）}" % (i + 1)
                )
            findings.append(
                Finding(
                    question=self.BRIEF_QUESTIONS[i],
                    answer=str(item.get("answer", "")),
                    structural_hit=bool(item.get("structural_hit", False)),
                    loop_gap=loop_gap,
                    counterexample=str(item.get("counterexample", "")),
                )
            )
        return BriefReviewResult(attempt=attempt, findings=findings)

    # ---- 阶段 6 ----
    def needs_deep_review(
        self,
        state: Any,
        *,
        about_to_stabilize: bool,
        as_teaching_backbone: bool,
        counterexample_conflict: bool,
        competing_explanations: bool,
    ) -> bool:
        """深审触发规则（v3.1）：四条件任一满足即深审，默认只做简审。"""
        return (
            about_to_stabilize
            or as_teaching_backbone
            or counterexample_conflict
            or competing_explanations
        )

    def parse_deep(self, state: Any, judgment: dict[str, Any]) -> DeepReviewResult:
        loop_gap = judgment.get("loop_gap")
        if loop_gap is not None and not isinstance(loop_gap, dict):
            raise SchemaError(
                "深审 loop_gap 必须是缺口对象，不能是字符串；形状为 "
                "{\"gap_type\": 概念缺口|结构缺口|证据缺口|反例冲突|教学缺口|迁移缺口, "
                "\"gap_statement\": 缺口描述, \"why_priority\": 可选, "
                "\"trigger_source\": 可选（怀疑/教学/迁移练习）}"
            )
        result = DeepReviewResult(
            passed=bool(judgment.get("passed", False)),
            premises=list(judgment.get("premises", [])),
            boundary_clear=bool(judgment.get("boundary_clear", False)),
            counterexample_pierces=bool(judgment.get("counterexample_pierces", False)),
            only_high_cognition=bool(judgment.get("only_high_cognition", False)),
            critical_issue=str(judgment.get("critical_issue", "")),
            loop_gap=loop_gap,
            counterexample=str(judgment.get("counterexample", "")),
        )
        if not result.premises:
            raise SchemaError("深审失败：关键前提未显式化")
        return result

    def parse_migration_assessment(
        self, judgment: dict[str, Any],
    ) -> dict[str, Any]:
        """解析迁移练习判分：通过则记录应用的结构；未通过则返回缺口。"""
        return {
            "passed": bool(judgment.get("passed", False)),
            "structure_applied": str(judgment.get("structure_applied", "")),
            "gap_if_failed": str(judgment.get("gap_if_failed", "")),
            "note": str(judgment.get("note", "")),
        }

    def install_loop_gap(self, state: Any, gap_data: dict[str, Any]) -> None:
        """把怀疑击中的问题登记为新的主认知缺口，触发回流。"""
        state.gap = GapState(
            gap_type=gap_data["gap_type"],
            gap_statement=gap_data["gap_statement"],
            why_priority=gap_data.get("why_priority", ""),
            secondary_gaps=list(gap_data.get("secondary_gaps", [])),
            trigger_source=gap_data.get(
                "trigger_source", TriggerSource.SKEPTIC.value
            ),
        )

    def apply_no_increment_verdicts(
        self, state: Any, judgment: dict[str, Any]
    ) -> int:
        """登记怀疑者的「本命题下该维度无专项增量」裁决（P0-1）。

        这是维度满足最低深度的两种方式之一，与「沉淀可执行规则」互斥。
        内核只做形状与一致性校验，「是否真的无增量」是怀疑者的认识论判断：
        - 维度必须在锚定声明的 coverage_dimensions 内；
        - 必须给非空理由；
        - 该维度已有可执行规则时禁止裁决（自相矛盾）。
        返回本次登记的裁决条数。
        """
        verdicts = judgment.get("no_increment_verdicts") or []
        if not isinstance(verdicts, list):
            raise SchemaError("no_increment_verdicts 必须是列表")
        valid = set(state.proposition.coverage_dimensions)
        applied = 0
        for item in verdicts:
            if not isinstance(item, dict):
                raise SchemaError(
                    "无增量裁决每项必须是 {dimension, reason} 对象"
                )
            dim = str(item.get("dimension", "")).strip()
            reason = str(item.get("reason", "")).strip()
            if dim not in valid:
                raise SchemaError(
                    f"无增量裁决的维度 {dim!r} 不在锚定声明的主干维度中："
                    f"{sorted(valid)}"
                )
            if not reason:
                raise SchemaError(
                    f"裁决维度 {dim} 无专项增量时必须给出理由，空理由不能过闸"
                )
            record = state.proposition.get_dimension_depth(dim)
            if record is not None and record.rules:
                raise SchemaError(
                    f"维度 {dim} 已沉淀 {len(record.rules)} 条可执行规则，"
                    "不能再裁决为「无专项增量」（规则与裁决互斥）"
                )
            if record is None:
                record = DimensionDepth(dimension=dim)
                state.proposition.dimension_depth.append(record)
            record.no_increment = True
            record.no_increment_reason = reason
            record.decided_version = state.proposition.proposition_version
            applied += 1
        return applied
