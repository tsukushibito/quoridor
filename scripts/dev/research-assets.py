#!/usr/bin/env python3
"""Resolve retained research assets without importing models or starting jobs."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KINDS = ("models", "checkpoints", "inputs")


def resolve_asset(root: Path, kind: str, name: str) -> Path:
    """Resolve an existing file inside one configured asset category."""
    if kind not in KINDS:
        raise ValueError(f"Unknown asset category: {kind}")
    layout = json.loads((root / "research-paths.json").read_text())
    category = (root / layout[kind]).resolve(strict=True)
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Asset name must be relative and contain no '..'")
    asset = (category / relative).resolve(strict=True)
    if not asset.is_relative_to(category) or not asset.is_file():
        raise ValueError("Asset must be a file within its configured category")
    return asset


def resolve_legacy(root: Path, old_path: str) -> Path:
    """Follow the migration manifest; historical run records remain unchanged."""
    layout = json.loads((root / "research-paths.json").read_text())
    mapping = json.loads((root / layout["asset_migration_manifest"]).read_text())
    matches = [row for row in mapping["assets"] if row["old_path"] == old_path]
    if len(matches) != 1:
        raise ValueError("Historical path has no unique retained-asset mapping")
    row = matches[0]
    asset = resolve_asset(root, row["kind"], row["name"])
    if asset.stat().st_size != row["bytes"] or sha256(asset) != row["sha256"]:
        raise ValueError("Retained asset bytes differ from migration manifest")
    return asset


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--kind", choices=KINDS)
    selection.add_argument("--legacy-path")
    parser.add_argument("--name", help="Relative path inside --kind")
    parser.add_argument("--sha256", action="store_true", help="Also verify/report file bytes")
    args = parser.parse_args()
    if bool(args.kind) != bool(args.name):
        parser.error("--kind and --name must be supplied together")
    try:
        asset = (
            resolve_legacy(ROOT, args.legacy_path)
            if args.legacy_path
            else resolve_asset(ROOT, args.kind, args.name)
        )
        if args.sha256:
            print(
                json.dumps(
                    {"path": str(asset), "bytes": asset.stat().st_size, "sha256": sha256(asset)}
                )
            )
        else:
            print(asset)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f"research-assets: {error}\n")


if __name__ == "__main__":
    main()
