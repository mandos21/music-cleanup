#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from beets import config as beets_config
from beets.library import Library


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove beets DB entries whose files no longer exist on disk."
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to the beets config file",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist removals to the beets database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of missing paths to print",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    beets_config.set_file(args.config, base_for_paths=True)
    library_path = beets_config["library"].as_filename()
    lib = Library(library_path)

    items = list(lib.items())
    missing = []
    empty_album_ids = set()

    for item in items:
        path = Path(item.path.decode())
        if path.exists():
            continue
        missing.append(item)
        album = item.get_album()
        if album:
            album_id = album.id
            album_items = list(album.items())
            if all(Path(album_item.path.decode()).exists() is False for album_item in album_items):
                empty_album_ids.add(album_id)

    print(f"Library DB: {library_path}")
    print(f"Missing item entries: {len(missing)}")
    print(f"Albums that would become empty: {len(empty_album_ids)}")

    for item in missing[: max(args.limit, 0)]:
        print(f"{item.artist} - {item.title}")
        print(f"  {item.path.decode()}")

    if not args.apply:
        print("Dry run only: no database rows were modified. Re-run with --apply to persist changes.")
        return 0

    for item in missing:
        item.remove(delete=False, with_album=True)

    print(f"Removed {len(missing)} missing item(s) from the beets database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
