#!/usr/bin/env python3
"""Finalize raw external model responses into a replayable vNext artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

from eval_vnext import (  # noqa: E402
    finalize_external_capture,
    load_artifact,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Accept only provenance, initial topic, raw stage responses, and "
            "receipts; replay locally to generate result and final_topic."
        )
    )
    parser.add_argument("raw_capture", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    artifact = finalize_external_capture(load_artifact(args.raw_capture))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(args.output),
                "case_id": artifact["case_id"],
                "model": artifact["declared_provenance"]["model"],
                "events_consumed": len(artifact["events"]),
                "collection_protocol": artifact["collection_protocol"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
