"""Shared vNext artifact validation API."""

from __future__ import annotations

from .artifacts import (
    ArtifactValidationError,
    finalize_external_capture,
    load_artifact,
    replay_artifact,
    validate_artifact,
)
from .invariants import (
    build_invariant_profile,
    compare_cross_model_artifacts,
    normalize_cross_model_profile,
)


def run_suite(argv: list[str] | None = None) -> None:
    """Load scripted generation only when the suite entry point requests it."""
    from .suite import run_suite as run

    run(argv)

__all__ = [
    "ArtifactValidationError",
    "build_invariant_profile",
    "compare_cross_model_artifacts",
    "finalize_external_capture",
    "load_artifact",
    "normalize_cross_model_profile",
    "replay_artifact",
    "run_suite",
    "validate_artifact",
]
