#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from beets import config as beets_config
from beets.library import Library


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rewrite beets DB item paths from one library prefix to another."
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to the beets config file",
    )
    parser.add_argument(
        "--old-prefix",
        default="managed",
        help=(
            "Path segment to remove from item paths. "
            "Relative values are resolved under the configured library directory."
        ),
    )
    parser.add_argument(
        "--new-prefix",
        default=".",
        help=(
            "Replacement path segment under the configured library directory. "
            "Use '.' for the library root."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist the rewritten paths to the beets database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of path rewrites to print",
    )
    parser.add_argument(
        "--missing-ok",
        action="store_true",
        help="Allow rewritten paths that do not currently exist on disk",
    )
    return parser.parse_args()


def resolve_prefix(base: Path, prefix: str) -> Path:
    candidate = Path(prefix)
    if candidate.is_absolute():
        return candidate.resolve()
    if prefix == ".":
        return base.resolve()
    return (base / candidate).resolve()


def rewrite_path(path: Path, old_prefix: Path, new_prefix: Path) -> Path | None:
    try:
        suffix = path.resolve().relative_to(old_prefix)
    except ValueError:
        return None
    return (new_prefix / suffix).resolve()


def main() -> int:
    args = parse_args()

    beets_config.set_file(args.config, base_for_paths=True)
    library_path = Path(beets_config["library"].as_filename()).resolve()
    library_dir = Path(beets_config["directory"].as_filename()).resolve()
    lib = Library(str(library_path))

    old_prefix = resolve_prefix(library_dir, args.old_prefix)
    new_prefix = resolve_prefix(library_dir, args.new_prefix)

    updates: list[tuple[object, Path, Path]] = []
    missing: list[tuple[object, Path, Path]] = []

    for item in lib.items():
        current = Path(item.path.decode())
        updated = rewrite_path(current, old_prefix, new_prefix)
        if updated is None or updated == current.resolve():
            continue
        if not updated.exists():
            missing.append((item, current, updated))
            if not args.missing_ok:
                continue
        updates.append((item, current, updated))

    print(f"Library DB: {library_path}")
    print(f"Old prefix: {old_prefix}")
    print(f"New prefix: {new_prefix}")
    print(f"Candidate updates: {len(updates)}")
    print(f"Missing rewritten targets: {len(missing)}")

    for item, current, updated in updates[: max(args.limit, 0)]:
        print(f"{item.artist} - {item.title}")
        print(f"  old: {current}")
        print(f"  new: {updated}")

    if missing and not args.missing_ok:
        print("Aborting apply because some rewritten paths do not exist. Re-run with --missing-ok to override.")
        return 1

    if not args.apply:
        print("Dry run only: no database rows were modified. Re-run with --apply to persist changes.")
        return 0

    for item, _current, updated in updates:
        item.path = bytes(updated)
        item.store()

    print(f"Updated {len(updates)} item path(s) in the beets database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
