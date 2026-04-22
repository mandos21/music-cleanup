#!/usr/bin/env python3
"""
move_bad_albums.py

Scan a music import directory for corrupted audio files and move any album
directory containing at least one bad track into a rejected folder.

Supported checks:
- FLAC: flac --test --warnings-as-errors --silent
- MP3:  mp3val

Behavior:
- Walks SOURCE recursively
- Treats the parent directory of a bad track as the album directory
- Moves each bad album directory once, preserving its relative path
- Skips albums already under the rejected directory
- Prints a summary at the end

Examples:
    python move_bad_albums.py /music/incoming /music/rejected
    python move_bad_albums.py /music/incoming /music/rejected --dry-run
    python move_bad_albums.py /music/incoming /music/rejected --extensions .flac .mp3

Requirements:
- Python 3.9+
- External tools available on PATH:
    - flac
    - mp3val
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


SUPPORTED_EXTENSIONS = {".flac", ".mp3"}


@dataclass
class BadTrack:
    path: Path
    reason: str


@dataclass
class AlbumResult:
    album_dir: Path
    bad_tracks: list[BadTrack] = field(default_factory=list)

    @property
    def is_bad(self) -> bool:
        return bool(self.bad_tracks)


def run_command(cmd: list[str]) -> tuple[int, str]:
    """Run a command and return (exit_code, combined_output)."""
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip()


def check_flac(path: Path) -> tuple[bool, str]:
    code, output = run_command(
        ["flac", "--test", "--warnings-as-errors", "--silent", str(path)]
    )
    return code == 0, output


def check_mp3(path: Path) -> tuple[bool, str]:
    code, output = run_command(["mp3val", str(path)])
    return code == 0, output


def check_audio_file(path: Path) -> tuple[bool, str]:
    ext = path.suffix.lower()
    if ext == ".flac":
        return check_flac(path)
    if ext == ".mp3":
        return check_mp3(path)
    return True, ""


def find_audio_files(root: Path, extensions: set[str]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            yield path


def is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.resolve().relative_to(other.resolve())
        return True
    except ValueError:
        return False


def gather_bad_albums(source: Path, reject_dir: Path, extensions: set[str]) -> dict[Path, AlbumResult]:
    albums: dict[Path, AlbumResult] = {}

    for audio_file in find_audio_files(source, extensions):
        if is_relative_to(audio_file, reject_dir):
            continue

        ok, output = check_audio_file(audio_file)
        if ok:
            continue

        album_dir = audio_file.parent
        result = albums.setdefault(album_dir, AlbumResult(album_dir=album_dir))
        reason = output.splitlines()[-1] if output else "checker returned non-zero exit status"
        result.bad_tracks.append(BadTrack(path=audio_file, reason=reason))

    return albums


def safe_destination(album_dir: Path, source: Path, reject_dir: Path) -> Path:
    """
    Preserve source-relative layout under reject_dir when possible.
    If album_dir is not inside source for some reason, fall back to name only.
    """
    try:
        rel = album_dir.resolve().relative_to(source.resolve())
        return reject_dir / rel
    except ValueError:
        return reject_dir / album_dir.name


def move_album(album_dir: Path, source: Path, reject_dir: Path, dry_run: bool) -> Path:
    dest = safe_destination(album_dir, source, reject_dir)

    if dest.exists():
        raise FileExistsError(f"Destination already exists: {dest}")

    if dry_run:
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(album_dir), str(dest))
    return dest


def ensure_tool_exists(name: str) -> bool:
    return shutil.which(name) is not None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Move album directories containing corrupted tracks into a rejected folder."
    )
    parser.add_argument("source", type=Path, help="Root directory to scan")
    parser.add_argument("reject_dir", type=Path, help="Directory where bad albums will be moved")
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=sorted(SUPPORTED_EXTENSIONS),
        help="Audio file extensions to check (default: .flac .mp3)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be moved without moving anything",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print every bad track found",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = args.source.expanduser().resolve()
    reject_dir = args.reject_dir.expanduser().resolve()
    extensions = {ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in args.extensions}

    if not source.exists() or not source.is_dir():
        print(f"Error: source is not a directory: {source}", file=sys.stderr)
        return 2

    if is_relative_to(reject_dir, source):
        print(
            "Error: reject_dir must not be inside source, or moved albums may be rescanned.",
            file=sys.stderr,
        )
        return 2

    needed_tools = set()
    if ".flac" in extensions:
        needed_tools.add("flac")
    if ".mp3" in extensions:
        needed_tools.add("mp3val")

    missing_tools = [tool for tool in sorted(needed_tools) if not ensure_tool_exists(tool)]
    if missing_tools:
        print(
            f"Error: missing required external tool(s): {', '.join(missing_tools)}",
            file=sys.stderr,
        )
        return 2

    print(f"Scanning: {source}")
    print(f"Rejected albums destination: {reject_dir}")
    print(f"Extensions: {', '.join(sorted(extensions))}")
    if args.dry_run:
        print("Dry run enabled; nothing will be moved.")
    print()

    bad_albums = gather_bad_albums(source, reject_dir, extensions)

    if not bad_albums:
        print("No bad albums found.")
        return 0

    moved_count = 0
    failed_moves = 0
    total_bad_tracks = sum(len(result.bad_tracks) for result in bad_albums.values())

    for album_dir in sorted(bad_albums):
        result = bad_albums[album_dir]
        print(f"[BAD ALBUM] {album_dir}")
        if args.verbose:
            for bad_track in result.bad_tracks:
                print(f"  - {bad_track.path.name}: {bad_track.reason}")

        try:
            dest = move_album(album_dir, source, reject_dir, args.dry_run)
            action = "Would move" if args.dry_run else "Moved"
            print(f"  {action} -> {dest}")
            moved_count += 1
        except Exception as exc:
            failed_moves += 1
            print(f"  Failed to move: {exc}", file=sys.stderr)

        print()

    print("Summary")
    print(f"  Bad albums found: {len(bad_albums)}")
    print(f"  Bad tracks found: {total_bad_tracks}")
    print(f"  Albums {'to move' if args.dry_run else 'moved'}: {moved_count}")
    if failed_moves:
        print(f"  Move failures: {failed_moves}")

    return 1 if failed_moves else 0


if __name__ == "__main__":
    raise SystemExit(main())