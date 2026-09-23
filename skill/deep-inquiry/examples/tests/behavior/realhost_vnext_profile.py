#!/usr/bin/env python3
"""Replay externally supplied vNext response artifacts without model calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SKILL_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "examples"))

from tests.behavior.eval_vnext import (  # noqa: E402
    compare_cross_model_artifacts,
    load_artifact,
    validate_artifact,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate external recorded artifacts by replaying their responses "
            "through the vNext autonomous loop. This does not call or attest "
            "an external model."
        )
    )
    parser.add_argument(
        "artifacts",
        nargs="+",
        type=Path,
        help="artifact JSON file(s) to validate",
    )
    parser.add_argument(
        "--compare-models",
        action="store_true",
        help=(
            "require two raw-events model captures covering all four cases "
            "and compare their normalized invariant profiles"
        ),
    )
    args = parser.parse_args()

    artifacts = [load_artifact(path) for path in args.artifacts]
    if args.compare_models:
        print(
            json.dumps(
                compare_cross_model_artifacts(artifacts),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    reports = []
    for path, artifact in zip(args.artifacts, artifacts):
        report = validate_artifact(artifact)
        reports.append(
            {
                "artifact": str(path),
                "status": report["status"],
                "validation_mode": report["validation_mode"],
                "artifact_origin": report["artifact_origin"],
                "external_call_attestation": report[
                    "external_call_attestation"
                ],
                "case_id": report["case_id"],
                "profile_id": report["profile_id"],
                "events_consumed": report["events_consumed"],
                "receipt_scope": report["receipt_scope"],
                "invariant_profile": report["invariant_profile"],
            }
        )
    print(json.dumps(reports, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
