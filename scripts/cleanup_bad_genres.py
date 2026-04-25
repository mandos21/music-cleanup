#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from beets import config as beets_config
from beets.library import Library

NATIONALITIES = {
    "american",
    "argentine",
    "australian",
    "austrian",
    "belgian",
    "brazilian",
    "british",
    "canadian",
    "chilean",
    "chinese",
    "colombian",
    "danish",
    "dutch",
    "english",
    "finnish",
    "french",
    "german",
    "greek",
    "hungarian",
    "icelandic",
    "indian",
    "irish",
    "italian",
    "japanese",
    "korean",
    "mexican",
    "new zealander",
    "new zealandi",
    "norwegian",
    "polish",
    "portuguese",
    "russian",
    "scottish",
    "spanish",
    "swedish",
    "swiss",
    "turkish",
    "ukrainian",
    "welsh",
}

ADJECTIVES = {
    "amazing",
    "awesome",
    "beautiful",
    "catchy",
    "cool",
    "floating",
    "good",
    "great",
    "hype",
    "masterpiece",
    "nice",
    "playful",
    "raw",
    "sexy",
    "summer",
    "white",
}

AOTY_PATTERN = re.compile(
    r"\b(?:aoty|album(?:s)? of the year|album(?:s)? of year)\b",
    re.IGNORECASE,
)
BEST_OF_PATTERN = re.compile(r"\bbest of\b", re.IGNORECASE)
DIGIT_PATTERN = re.compile(r"\d")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


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


def normalize_value(value: str) -> str:
    normalized = NON_ALNUM_PATTERN.sub(" ", value.casefold()).strip()
    return " ".join(normalized.split())


def should_remove_genre(
    genre: str,
    bad_values: set[str],
    artist: str | None = None,
    album: str | None = None,
) -> bool:
    folded = genre.casefold()
    normalized = normalize_value(genre)

    if folded in bad_values:
        return True
    if DIGIT_PATTERN.search(genre):
        return True
    if normalized in NATIONALITIES:
        return True
    if normalized in ADJECTIVES:
        return True
    if AOTY_PATTERN.search(genre):
        return True
    if BEST_OF_PATTERN.search(genre):
        return True

    for candidate in (artist, album):
        if candidate and normalized == normalize_value(candidate):
            return True

    return False


def clean_genres(
    genres: list[str] | None,
    bad_values: set[str],
    artist: str | None = None,
    album: str | None = None,
) -> list[str]:
    if not genres:
        return []
    kept: list[str] = []
    seen: set[str] = set()
    for genre in genres:
        folded = genre.casefold()
        if should_remove_genre(genre, bad_values, artist=artist, album=album):
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
        cleaned = clean_genres(original, bad_values, artist=item.artist, album=item.album)
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
        cleaned = clean_genres(
            original,
            bad_values,
            artist=album.albumartist,
            album=album.album,
        )
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
