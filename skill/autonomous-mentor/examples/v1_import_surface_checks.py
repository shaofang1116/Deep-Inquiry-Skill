#!/usr/bin/env python3
"""Executable contract for the legacy v1 importer input surface."""

from __future__ import annotations

from pathlib import Path
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))


def main() -> None:
    from scripts.schema import SessionState
    from scripts.v1_import_record import report_v1_import_surface

    surface = report_v1_import_surface()
    assert surface["schema_version"] == 1
    assert surface["source_model"] == "SessionState"
    assert set(surface["mapped"]) >= {
        "schema_version",
        "created_at",
        "updated_at",
        "proposition.proposition_text",
        "proposition.coverage_dimensions",
        "proposition.dimension_depth",
        "proposition.evidence_book",
        "proposition.counterexample_library",
        "proposition.open_boundaries",
        "gap",
    }
    assert set(surface["provenance_only"]) >= {
        "teaching",
        "proposition.dimension_depth.rule_meta",
        "proposition.evidence_book.version",
        "proposition.counterexample_library.pierced_version",
    }
    assert set(surface["validated_only"]) >= {
        "topic_id",
        "knowledge_root",
        "base_version",
        "question_tree",
        "decision",
        "progress_log",
        "round_count",
    }
    categories = [
        set(surface["mapped"]),
        set(surface["provenance_only"]),
        set(surface["validated_only"]),
    ]
    assert not categories[0] & categories[1]
    assert not categories[0] & categories[2]
    assert not categories[1] & categories[2]
    declared_top_level = {
        path.split(".", 1)[0]
        for category in categories
        for path in category
    }
    assert declared_top_level == set(SessionState.__dataclass_fields__)
    print("v1 importer input surface checks passed.")


if __name__ == "__main__":
    main()
