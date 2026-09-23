#!/usr/bin/env python3
"""Run and verify the owned Deep Inquiry executable test layers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

TESTS_ROOT = Path(__file__).resolve().parent
SKILL_ROOT = TESTS_ROOT.parent.parent
LAYERS = ("core_contract", "behavior", "migration", "adapter")


def _manifest() -> dict[str, list[str]]:
    path = TESTS_ROOT / "layer_manifest.json"
    if not path.is_file():
        raise AssertionError(f"missing layer manifest: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != set(LAYERS):
        raise AssertionError(f"manifest must define exactly {LAYERS}")
    result: dict[str, list[str]] = {}
    for layer in LAYERS:
        entries = raw[layer]
        if not isinstance(entries, list) or not entries:
            raise AssertionError(f"manifest layer {layer!r} must be non-empty")
        result[layer] = entries
    return result


def verify_manifest() -> dict[str, list[str]]:
    manifest = _manifest()
    assigned = [entry for entries in manifest.values() for entry in entries]
    if len(assigned) != len(set(assigned)):
        raise AssertionError("manifest assigns one or more modules multiple times")
    for entry in assigned:
        path = SKILL_ROOT / entry
        if not path.is_file():
            raise AssertionError(f"manifest module does not exist: {entry}")
        if "examples/tests/" not in entry:
            raise AssertionError(f"manifest module is outside test layers: {entry}")
    root_checks = sorted(
        path.relative_to(SKILL_ROOT).as_posix()
        for path in (SKILL_ROOT / "examples").glob("*_checks.py")
    )
    if root_checks:
        raise AssertionError(
            f"root-level check wrappers remain: {', '.join(root_checks)}"
        )
    return manifest


def run_layer(layer: str, manifest: dict[str, list[str]]) -> None:
    for entry in manifest[layer]:
        result = subprocess.run(
            [sys.executable, entry],
            cwd=SKILL_ROOT,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(result.returncode)
    print(f"{layer}: {len(manifest[layer])}/{len(manifest[layer])} passed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-manifest", action="store_true")
    parser.add_argument("--layer", choices=LAYERS)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if sum((args.verify_manifest, args.layer is not None, args.all)) != 1:
        parser.error("choose exactly one of --verify-manifest, --layer, or --all")
    manifest = verify_manifest()
    if args.verify_manifest:
        print("layer manifest is valid")
        return
    for layer in LAYERS if args.all else (args.layer,):
        run_layer(layer, manifest)


if __name__ == "__main__":
    main()
