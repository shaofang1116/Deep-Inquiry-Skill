"""Declared legacy v1 input surface for the one-way importer."""

from __future__ import annotations


_MAPPED = (
    "schema_version",
    "created_at",
    "updated_at",
    "proposition",
    "proposition.proposition_text",
    "proposition.proposition_version",
    "proposition.current_explanation",
    "proposition.proposition_scope",
    "proposition.coverage_dimensions",
    "proposition.dimension_depth",
    "proposition.dimension_depth.dimension",
    "proposition.dimension_depth.rules",
    "proposition.evidence_book",
    "proposition.evidence_book.evidence_type",
    "proposition.evidence_book.content",
    "proposition.evidence_book.source",
    "proposition.evidence_book.citation",
    "proposition.counterexample_library",
    "proposition.counterexample_library.content",
    "proposition.open_boundaries",
    "gap",
    "gap.resolved",
    "gap.gap_statement",
    "gap.why_priority",
)

_PROVENANCE_ONLY = (
    "teaching",
    "proposition.dimension_depth.rule_meta",
    "proposition.dimension_depth.no_increment",
    "proposition.dimension_depth.no_increment_reason",
    "proposition.dimension_depth.decided_version",
    "proposition.evidence_book.version",
    "proposition.counterexample_library.pierced_version",
    "proposition.counterexample_library.review_stage",
)

_VALIDATED_ONLY = (
    "topic_id",
    "knowledge_root",
    "base_version",
    "question_tree",
    "decision",
    "progress_log",
    "round_count",
    "turns_since_explanation_update",
    "proposition.adjacent_topics",
    "proposition.scope_qualifiers",
    "proposition.dimension_sources",
    "gap.gap_type",
    "gap.secondary_gaps",
    "gap.trigger_source",
)


def report_v1_import_surface() -> dict[str, object]:
    """Return the fixed v1 fields consumed by validation or import mapping."""
    return {
        "schema_version": 1,
        "source_model": "SessionState",
        "mapped": _MAPPED,
        "provenance_only": _PROVENANCE_ONLY,
        "validated_only": _VALIDATED_ONLY,
    }
