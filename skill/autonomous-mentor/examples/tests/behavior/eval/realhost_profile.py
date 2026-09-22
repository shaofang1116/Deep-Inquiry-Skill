#!/usr/bin/env python3
"""真实模型宿主画像复算器（阶段三-B）。

用法（真实宿主通过 CLI 文件协议逐判断作答后）：

    # 主会话：sessions/eval-real-mechanism/
    #   .mentor-state/session.json        内核状态
    #   artifacts/NN_<judgment>.json      每次写入 judgment.json 的信封（按序号）
    #   artifacts/result_learning.json    学习轮 done 的 --json 输出（trace.result）
    #   artifacts/result_teaching_1.json  三个画像用户教学轮 done 的 --json 输出
    #   artifacts/result_teaching_2.json
    #   artifacts/result_teaching_3.json
    # 仅锚定的新会话（need_learn 验证）：--fresh-state 指向其 session.json

    python3 examples/tests/behavior/eval/realhost_profile.py \
        --case mechanism \
        --session sessions/eval-real-mechanism/.mentor-state/session.json \
        --artifacts sessions/eval-real-mechanism/artifacts \
        --fresh-state sessions/eval-real-mechanism-fresh/.mentor-state/session.json

复算器只调用 runner.profile_* 同一批断言函数：真实宿主与脚本宿主共用一把尺子，
阈值没有任何放宽。退出码 0=画像全绿，1=有失败断言。
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, SKILL_ROOT)

from scripts.store import StateStore  # noqa: E402
from scripts.judgments import BRIEF_QUESTIONS  # noqa: E402
from scripts.learner import _NUMERIC_RULE_RE  # noqa: E402
from scripts.schema import QuestionStatus  # noqa: E402

from tests.behavior.eval.cases import ConceptCase, ControversyCase, MechanismCase  # noqa: E402
from tests.behavior.eval.runner import (  # noqa: E402
    CaseReport,
    finalize,
    new_report,
    profile_learning,
    profile_need_learn,
    profile_teaching,
)

CASES = {
    "mechanism": MechanismCase,
    "concept": ConceptCase,
    "controversy": ControversyCase,
}
GENERIC_CASE = "generic"


def _load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_envelopes(artifacts_dir: str) -> tuple[list[tuple[str, dict]], list[str]]:
    paths = [
        p for p in glob.glob(os.path.join(artifacts_dir, "*_*.json"))
        if os.path.basename(p)[0].isdigit()
    ]
    numbered: list[tuple[int, str]] = []
    by_number: dict[int, list[str]] = {}
    errors: list[str] = []
    for path in paths:
        match = re.match(r"(\d+)_", os.path.basename(path))
        if match is None:
            continue
        number = int(match.group(1))
        numbered.append((number, path))
        by_number.setdefault(number, []).append(os.path.basename(path))

    for number, names in sorted(by_number.items()):
        if len(names) > 1:
            errors.append(f"artifacts 存在重复编号 {number:02d}：{sorted(names)}")
    if numbered:
        present = set(by_number)
        missing = sorted(set(range(1, max(present) + 1)) - present)
        if missing:
            errors.append(f"artifacts 编号不连续，缺少：{missing}")

    envelopes = []
    for _, path in sorted(numbered):
        data = _load_json(path)
        envelopes.append((data["judgment"], data.get("response", {})))
    compress_count = sum(1 for name, _ in envelopes if name == "compress_explanation")
    if compress_count != 1:
        errors.append(
            f"compress_explanation 信封应恰好 1 个，实际 {compress_count} 个"
        )
    return envelopes, errors


def _validate_learning_result(
    result: dict,
    state: object,
    compress_response: dict,
) -> list[str]:
    errors: list[str] = []
    required = ("status", "proposition_version", "explanation", "open_boundaries")
    for field in required:
        if field not in result:
            errors.append(f"result_learning.json 缺少字段 {field}")

    proposition = state.proposition
    comparisons = (
        ("proposition_version", proposition.proposition_version),
        ("explanation", proposition.current_explanation),
        ("open_boundaries", list(proposition.open_boundaries)),
    )
    for field, expected in comparisons:
        if field in result and result[field] != expected:
            errors.append(f"result_learning.{field} 与当前 session 不一致")
    for field in ("explanation", "open_boundaries"):
        if (
            field in result
            and field in compress_response
            and result[field] != compress_response[field]
        ):
            errors.append(f"result_learning.{field} 与压缩信封不一致")
    return errors


def _profile_learning_generic(
    report: CaseReport,
    store: StateStore,
    result: dict,
    transcript: list[tuple[str, dict]],
) -> None:
    """Validate protocol invariants without a domain-specific CasePack."""
    report.check(result.get("status") == "compressed",
                 f"学习闭环压缩定稿（实际：{result.get('status')}）")
    report.check(result.get("proposition_version") == 1,
                 f"定稿版本为 v1（实际：v{result.get('proposition_version')}）")
    report.check(bool(result.get("explanation")), "定稿解释非空")

    brief_responses = [
        response for name, response in transcript if name == "brief_review"
    ]
    deep_count = sum(1 for name, _ in transcript if name == "deep_review")
    compress_count = sum(
        1 for name, _ in transcript if name == "compress_explanation"
    )
    exact_brief_questions = all(
        [finding.get("question") for finding in response.get("findings", [])]
        == list(BRIEF_QUESTIONS)
        for response in brief_responses
    )
    report.check(bool(brief_responses), "至少完成一次简审")
    report.check(exact_brief_questions, "简审四问均逐字使用固定问法")
    report.check(deep_count >= 1, f"至少完成一次深审（实际：{deep_count}）")
    report.check(compress_count == 1,
                 f"压缩请求仅 {compress_count} 次")

    state = store.load()
    boundaries = result.get("open_boundaries") or list(
        state.proposition.open_boundaries
    )
    report.check(len(boundaries) >= 1,
                 f"开放边界 {len(boundaries)} 条（≥1）")
    report.check(len(state.proposition.coverage_dimensions) >= 2,
                 f"主干维度 {len(state.proposition.coverage_dimensions)} 个（≥2）")

    depths = {depth.dimension: depth for depth in state.proposition.dimension_depth}
    for dimension in state.proposition.coverage_dimensions:
        depth = depths.get(dimension)
        report.check(depth is not None and depth.depth_satisfied,
                     f"维度「{dimension}」满足最低深度")

    rule_total = 0
    bare_numeric = []
    for depth in state.proposition.dimension_depth:
        for rule in depth.rules:
            rule_total += 1
            meta = depth.rule_meta.get(rule, {})
            if (
                _NUMERIC_RULE_RE.search(rule)
                and not meta.get("basis")
                and not meta.get("heuristic")
            ):
                bare_numeric.append(rule)
    report.check(not bare_numeric,
                 f"裸数值规则零逃逸（{rule_total} 条规则）"
                 + ("" if not bare_numeric else f"；逃逸：{bare_numeric}"))

    nodes = {question.id: question for question in state.question_tree.sub_questions}
    open_ids = {
        question_id for question_id, question in nodes.items()
        if question.status == QuestionStatus.OPEN.value
    }
    undisclosed_open = [
        question_id for question_id in open_ids
        if not any(f"未闭合子问题（{question_id}）" in boundary
                   for boundary in boundaries)
    ]
    report.check(not undisclosed_open,
                 "所有定稿 open 节点均显式并入开放边界"
                 + ("" if not undisclosed_open
                    else f"；遗漏：{sorted(undisclosed_open)}"))

    report.counters.update({
        "brief_hits": sum(
            1 for response in brief_responses
            for finding in response.get("findings", [])
            if finding.get("structural_hit")
        ),
        "completeness_hits": sum(
            1 for response in brief_responses
            for finding in response.get("findings", [])
            if finding.get("structural_hit")
            and finding.get("question") == BRIEF_QUESTIONS[3]
        ),
        "deep_pierces": sum(
            1 for name, response in transcript
            if name == "deep_review" and response.get("counterexample_pierces")
        ),
        "rule_total": rule_total,
        "dim_total": len(state.proposition.coverage_dimensions),
        "boundaries": len(boundaries),
        "stabilized": sum(
            1 for question in nodes.values()
            if question.status == QuestionStatus.STABLE.value
        ),
        "retained": len(open_ids),
    })


def _profile_teaching_generic(
    report: CaseReport,
    teaching_results: list[dict],
) -> None:
    """Validate the three domain-independent learner entry points."""
    expected_actions = ["先定义", "先搭框架", "先做迁移"]
    report.check(len(teaching_results) == len(expected_actions),
                 f"教学闭环 {len(teaching_results)} 个（期望 3）")
    actions = []
    for expected_action, result in zip(expected_actions, teaching_results):
        delivered = "reply" in result or "structure_applied" in result
        report.check(delivered,
                     f"教学动作「{expected_action}」done 信封包含交付内容")
        report.check(result.get("teaching_action") == expected_action,
                     f"教学动作按画像分流为「{expected_action}」"
                     f"（实际：{result.get('teaching_action')}）")
        actions.append(result.get("teaching_action", ""))
    report.check(teaching_results[-1].get("status") == "migration_passed",
                 "迁移用户闭环至 migration_passed")
    report.check(len(set(actions)) == 3,
                 f"三类用户走出三条互异进入点（实际 {len(set(actions))} 种）")
    report.counters["teaching_actions"] = len(set(actions))


def main() -> int:
    parser = argparse.ArgumentParser(description="真实模型宿主 eval 画像复算器")
    parser.add_argument(
        "--case",
        choices=sorted([*CASES, GENERIC_CASE]),
        default="mechanism",
    )
    parser.add_argument("--session", required=True, help="主会话 session.json")
    parser.add_argument("--artifacts", required=True, help="judgment 信封与 done 结果目录")
    parser.add_argument("--fresh-state", default="", help="仅锚定新会话的 session.json")
    args = parser.parse_args()

    case = CASES[args.case]() if args.case != GENERIC_CASE else None
    report = (
        new_report(case)
        if case is not None
        else CaseReport(
            case_id="generic",
            label="陌生命题通用画像",
            passed=False,
        )
    )

    # ---- judgment 信封序列（真实宿主全部作答的留痕） ----
    envelopes, artifact_errors = _load_envelopes(args.artifacts)
    report.failures.extend(artifact_errors)

    # 学习轮应答 = 截止第一个 compress_explanation（含）；之后是教学/迁移应答
    compress_indexes = [
        i for i, (name, _) in enumerate(envelopes) if name == "compress_explanation"
    ]
    compress_idx = compress_indexes[0] if len(compress_indexes) == 1 else None
    if compress_idx is None:
        report.failures.append(
            "artifacts 中无法确定唯一 compress_explanation 应答（学习轮产物不完整）"
        )
    learning_transcript = envelopes[: compress_idx + 1] if compress_idx is not None else []

    learning_result_path = os.path.join(args.artifacts, "result_learning.json")
    if os.path.isfile(learning_result_path):
        result = _load_json(learning_result_path)["trace"]["result"]
        store = StateStore(args.session)
        state = store.load()
        compress_response = envelopes[compress_idx][1] if compress_idx is not None else {}
        report.failures.extend(
            _validate_learning_result(result, state, compress_response)
        )
        if case is None:
            _profile_learning_generic(report, store, result, learning_transcript)
        else:
            profile_learning(case, report, store, result, learning_transcript)
    else:
        report.failures.append("缺少 result_learning.json（学习轮 done 输出）")

    # ---- 三个画像用户教学轮 done 结果 ----
    teaching_results = []
    for i in (1, 2, 3):
        p = os.path.join(args.artifacts, f"result_teaching_{i}.json")
        if os.path.isfile(p):
            teaching_results.append(_load_json(p)["trace"]["result"])
        else:
            report.failures.append(f"缺少 result_teaching_{i}.json")
    if len(teaching_results) == 3:
        if case is None:
            _profile_teaching_generic(report, teaching_results)
        else:
            profile_teaching(case, report, teaching_results)

    # ---- need_learn：仅锚定新会话 ----
    if args.fresh_state and os.path.isfile(args.fresh_state):
        status = None
        p = os.path.join(args.artifacts, "result_need_learn.json")
        if os.path.isfile(p):
            status = _load_json(p)["trace"]["result"]["status"]
        if os.path.isfile(p):
            status = _load_json(p)["trace"]["result"]["status"]
        profile_need_learn(report, StateStore(args.fresh_state), status)
    else:
        report.failures.append("缺少 --fresh-state（need_learn 闸门未验证）")

    finalize(report)
    print("阶段三-B 真实模型宿主画像：" + report.line())
    for ok in report.checks:
        print(f"  ✓ {ok}")
    for bad in report.failures:
        print(f"  ✗ {bad}")
    print(f"\n学习轮判断点应答数：{len(learning_transcript)}；artifacts 总应答数：{len(envelopes)}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
