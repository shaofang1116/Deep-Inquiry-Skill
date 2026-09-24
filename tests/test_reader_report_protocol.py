"""Public protocol parity for reader-oriented report behavior."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReaderReportProtocolTests(unittest.TestCase):
    def test_canonical_english_and_chinese_mirror_reader_contract(self) -> None:
        english = (ROOT / "skill" / "deep-inquiry" / "SKILL.md").read_text()
        chinese = (
            ROOT / "skill" / "deep-inquiry" / "SKILL.zh-CN.md"
        ).read_text()
        normalized_english = " ".join(english.split())
        normalized_chinese = " ".join(chinese.split())

        for marker in (
            "integrate_learning",
            "skeptic_review",
            "reader_document",
        ):
            self.assertIn(marker, english)
            self.assertIn(marker, chinese)

        for marker in (
            "mechanism",
            "conditions",
            "cross-dimension",
            "application",
            "boundaries",
            "deterministic",
        ):
            self.assertIn(marker, english)
        self.assertIn("Eight", english)
        self.assertIn("八", chinese)
        self.assertIn(
            "reader-facing knowledge document",
            normalized_english,
        )
        self.assertIn(
            "reader-facing knowledge",
            normalized_chinese,
        )
        for phrase in ("mechanism chain", "conditions", "cross-dimension"):
            self.assertIn(phrase, english)
        for phrase in ("机制链", "条件", "跨维度综合"):
            self.assertIn(phrase, chinese)
        self.assertIn("never calls a model again", normalized_english)
        self.assertIn(
            "no claim, evidence, gap, or convergence-history registry",
            normalized_english,
        )
        self.assertIn("不再次调用模型", normalized_chinese)
        self.assertIn(
            "没有 claim、evidence、gap 或 convergence-history registry",
            normalized_chinese,
        )
        for protocol in (english, chinese):
            self.assertNotIn(
                "full claim/evidence/gap/history projection",
                protocol,
            )

    def test_readme_describes_reader_report_without_audit_as_primary_output(self) -> None:
        readme = (ROOT / "README.md").read_text()

        self.assertIn("reader-oriented knowledge document", readme)
        self.assertIn("not an audit export", readme)


if __name__ == "__main__":
    unittest.main()
