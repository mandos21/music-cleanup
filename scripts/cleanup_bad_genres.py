#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from beets import config as beets_config
from beets.library import Library


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove unwanted genre values from the beets library and tags."
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to the beets config file",
    )
    parser.add_argument(
        "--bad-file",
        default="config/bad-genres.txt",
        help="Path to newline-delimited bad genre values to remove",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without updating the library or files",
    )
    parser.add_argument(
        "--no-write-tags",
        action="store_true",
        help="Update the beets DB only; do not rewrite file tags",
    )
    return parser.parse_args()


def load_bad_values(path: Path) -> set[str]:
    return {
        line.strip().casefold()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def clean_genres(genres: list[str] | None, bad_values: set[str]) -> list[str]:
    if not genres:
        return []
    kept: list[str] = []
    seen: set[str] = set()
    for genre in genres:
        folded = genre.casefold()
        if folded in bad_values:
            continue
        if folded in seen:
            continue
        seen.add(folded)
        kept.append(genre)
    return kept


def main() -> int:
    args = parse_args()
    bad_values = load_bad_values(Path(args.bad_file))

    beets_config.set_file(args.config)
    library_path = beets_config["library"].as_filename()
    lib = Library(library_path)

    item_changes = 0
    album_changes = 0

    for item in lib.items():
        original = item.genres or []
        cleaned = clean_genres(original, bad_values)
        if cleaned == original:
            continue
        print(f"ITEM  {item.artist} - {item.title}\n  old: {original}\n  new: {cleaned}\n")
        item_changes += 1
        if not args.dry_run:
            item.genres = cleaned
            item.genre = ""
            item.store()
            if not args.no_write_tags:
                item.try_write()

    for album in lib.albums():
        original = album.genres or []
        cleaned = clean_genres(original, bad_values)
        if cleaned == original:
            continue
        print(
            f"ALBUM {album.albumartist} - {album.album}\n  old: {original}\n  new: {cleaned}\n"
        )
        album_changes += 1
        if not args.dry_run:
            album.genres = cleaned
            album.genre = ""
            album.store()

    print(f"Changed {item_changes} items and {album_changes} albums.")
    if args.dry_run:
        print("Dry run only: no database rows or file tags were modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
