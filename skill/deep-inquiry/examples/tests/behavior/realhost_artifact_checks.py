#!/usr/bin/env python3
"""真实宿主产物完整性回归。"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, SKILL_ROOT)
sys.path.insert(0, os.path.join(SKILL_ROOT, "examples"))

from tests.behavior.eval.realhost_profile import (  # noqa: E402
    _load_envelopes,
    _validate_learning_result,
)


def _write(path: str, judgment: str, response: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"judgment": judgment, "response": response}, f)


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="mentor-realhost-artifacts-")
    try:
        _write(os.path.join(tmp, "01_deep_review.json"), "deep_review", {"passed": True})
        _write(
            os.path.join(tmp, "02_compress_explanation.json"),
            "compress_explanation",
            {"explanation": "稳定解释", "open_boundaries": ["边界 A", "边界 B"]},
        )
        envelopes, errors = _load_envelopes(tmp)
        assert not errors, errors
        assert [name for name, _ in envelopes] == ["deep_review", "compress_explanation"]
        print("[1/4] 唯一连续编号且单一压缩信封可正常加载 ✓")

        _write(os.path.join(tmp, "02_deep_review_duplicate.json"), "deep_review", {"passed": True})
        _, errors = _load_envelopes(tmp)
        assert any("重复编号 02" in error for error in errors), errors
        print("[2/4] 同编号多信封被判为混合运行产物 ✓")

        os.remove(os.path.join(tmp, "02_deep_review_duplicate.json"))
        _write(
            os.path.join(tmp, "03_compress_explanation.json"),
            "compress_explanation",
            {"explanation": "另一轮解释", "open_boundaries": ["边界 C", "边界 D"]},
        )
        _, errors = _load_envelopes(tmp)
        assert any("compress_explanation 信封应恰好 1 个" in error for error in errors), errors
        print("[3/4] 多个压缩信封被判为混合运行产物 ✓")

        state = SimpleNamespace(
            proposition=SimpleNamespace(
                proposition_version=1,
                current_explanation="稳定解释",
                open_boundaries=["边界 A", "边界 B"],
            )
        )
        valid = {
            "status": "compressed",
            "proposition_version": 1,
            "explanation": "稳定解释",
            "open_boundaries": ["边界 A", "边界 B"],
        }
        compress = {"explanation": "稳定解释", "open_boundaries": ["边界 A", "边界 B"]}
        assert not _validate_learning_result(valid, state, compress)
        bad = dict(valid)
        bad.pop("explanation")
        errors = _validate_learning_result(bad, state, compress)
        assert any("缺少字段 explanation" in error for error in errors), errors
        bad = dict(valid, explanation="另一轮解释")
        errors = _validate_learning_result(bad, state, compress)
        assert any("与当前 session 不一致" in error for error in errors), errors
        assert any("与压缩信封不一致" in error for error in errors), errors
        print("[4/4] 学习 done 结果缺字段或与信封/session 不同源时被拒 ✓")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n真实宿主产物完整性 4/4 通过。")


if __name__ == "__main__":
    main()
