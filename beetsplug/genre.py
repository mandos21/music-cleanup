from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
import re
import readline

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, decargs, print_


GENRE_SPLIT_RE = re.compile(r"\s*[;,]\s*")
ANSI_BOLD = "\033[1m"
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RESET = "\033[0m"


def iter_genre_values(*values: object) -> list[str]:
    genres: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value is None:
            continue

        raw_parts: Iterable[object]
        if isinstance(value, str):
            raw_parts = GENRE_SPLIT_RE.split(value)
        elif isinstance(value, Iterable):
            raw_parts = value
        else:
            raw_parts = (value,)

        for part in raw_parts:
            if part is None:
                continue
            genre = str(part).strip()
            if not genre:
                continue
            folded = genre.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            genres.append(genre)

    return genres


def make_genre_matcher(pattern: str, *, regex: bool = False, ignore_case: bool = False):
    if regex:
        flags = re.IGNORECASE if ignore_case else 0
        compiled = re.compile(pattern, flags)
        return lambda genre: compiled.search(genre) is not None

    if ignore_case:
        target = pattern.casefold()
        return lambda genre: genre.casefold() == target

    return lambda genre: genre == pattern


def has_matching_genre(
    entity,
    pattern: str,
    *,
    regex: bool = False,
    ignore_case: bool = False,
) -> bool:
    if not pattern.strip():
        return False

    matcher = make_genre_matcher(pattern, regex=regex, ignore_case=ignore_case)
    return any(
        matcher(genre)
        for genre in iter_genre_values(getattr(entity, "genre", None), getattr(entity, "genres", None))
    )


def collect_genre_counts(rows) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        for genre in iter_genre_values(getattr(row, "genre", None), getattr(row, "genres", None)):
            counts[genre] += 1
    return counts


def replace_matching_genres(
    values: list[str],
    pattern: str,
    replacement: str,
    *,
    regex: bool = False,
    ignore_case: bool = False,
) -> list[str]:
    matcher = make_genre_matcher(pattern, regex=regex, ignore_case=ignore_case)
    replaced: list[str] = []
    seen: set[str] = set()

    for value in values:
        new_value = replacement if matcher(value) else value
        folded = new_value.casefold()
        if folded in seen or not new_value.strip():
            continue
        seen.add(folded)
        replaced.append(new_value)

    return replaced


def replace_matching_genres_with_map(
    values: list[str],
    replacements: dict[str, str],
    *,
    ignore_case: bool = False,
) -> list[str]:
    replaced: list[str] = []
    seen: set[str] = set()

    for value in values:
        if ignore_case:
            new_value = replacements.get(value.casefold(), value)
        else:
            new_value = replacements.get(value, value)
        folded = new_value.casefold()
        if folded in seen or not new_value.strip():
            continue
        seen.add(folded)
        replaced.append(new_value)

    return replaced


def delete_matching_genres(
    values: list[str],
    pattern: str,
    *,
    regex: bool = False,
    ignore_case: bool = False,
) -> list[str]:
    matcher = make_genre_matcher(pattern, regex=regex, ignore_case=ignore_case)
    kept: list[str] = []
    seen: set[str] = set()

    for value in values:
        if matcher(value):
            continue
        folded = value.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        kept.append(value)

    return kept


def set_entity_genres(entity, values: list[str]) -> None:
    entity.genres = values
    entity.genre = "; ".join(values)


def entity_label(entity, *, albums: bool) -> str:
    if albums:
        return f"{entity.albumartist} - {entity.album}"
    return f"{entity.artist} - {entity.title}"


def genre_count(entity) -> int:
    return len(iter_genre_values(getattr(entity, "genre", None), getattr(entity, "genres", None)))


def render_genre_string(values: list[str], delimiter: str = "; ") -> str:
    return delimiter.join(values)


def parse_genre_string(value: str, delimiter: str = ";") -> list[str]:
    genres: list[str] = []
    seen: set[str] = set()

    for part in value.split(delimiter):
        genre = part.strip()
        if not genre:
            continue
        folded = genre.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        genres.append(genre)

    return genres


def input_with_prefill(prompt: str, text: str) -> str:
    def hook() -> None:
        readline.insert_text(text)
        readline.redisplay()

    try:
        readline.set_startup_hook(hook)
        return input(prompt)
    finally:
        readline.set_startup_hook(None)


def colorize(text: str, color: str) -> str:
    return f"{color}{text}{ANSI_RESET}"


class GenrePlugin(BeetsPlugin):
    def commands(self) -> list[Subcommand]:
        find_cmd = Subcommand("genrefind", help="find tracks or albums matching a genre pattern")
        find_cmd.parser.add_option(
            "-a",
            "--albums",
            action="store_true",
            dest="albums",
            help="search album-level genres instead of items",
        )
        find_cmd.parser.add_option(
            "-i",
            "--ignore-case",
            action="store_true",
            dest="ignore_case",
            help="match genres case-insensitively",
        )
        find_cmd.parser.add_option(
            "-r",
            "--regex",
            action="store_true",
            dest="regex",
            help="treat the genre pattern as a regular expression",
        )
        find_cmd.func = self._run_find

        count_cmd = Subcommand("genrecount", help="count genre tag frequency across tracks or albums")
        count_cmd.parser.add_option(
            "-a",
            "--albums",
            action="store_true",
            dest="albums",
            help="count album-level genres instead of item-level genres",
        )
        count_cmd.parser.add_option(
            "-n",
            "--limit",
            dest="limit",
            type="int",
            default=20,
            help="maximum number of rows to print",
        )
        count_cmd.parser.add_option(
            "--alpha",
            action="store_true",
            dest="alpha",
            help="sort output alphabetically by genre instead of by count",
        )
        count_cmd.func = self._run_count

        under_cmd = Subcommand(
            "genreunder",
            help="find tracks or albums with fewer than a given number of genres",
        )
        under_cmd.parser.add_option(
            "-a",
            "--albums",
            action="store_true",
            dest="albums",
            help="check album-level genres instead of item-level genres",
        )
        under_cmd.func = self._run_under

        audit_cmd = Subcommand(
            "genreaudit",
            help="step through albums or tracks and edit genres as one delimited string",
        )
        audit_cmd.parser.add_option(
            "--items",
            action="store_false",
            dest="albums",
            default=True,
            help="audit item-level genres instead of albums",
        )
        audit_cmd.parser.add_option(
            "--delimiter",
            dest="delimiter",
            default="; ",
            help="delimiter to show when editing genre strings",
        )
        audit_cmd.parser.add_option(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="show edits without writing to the beets database or files",
        )
        audit_cmd.parser.add_option(
            "--no-write-tags",
            action="store_true",
            dest="no_write_tags",
            help="update the beets DB only; do not rewrite file tags for items",
        )
        audit_cmd.func = self._run_audit

        replace_cmd = Subcommand("genrereplace", help="replace matching genre values")
        self._add_mutation_options(replace_cmd)
        replace_cmd.parser.add_option(
            "--ask",
            action="store_true",
            dest="ask",
            help="prompt for a replacement on each matching row instead of using one fixed value",
        )
        replace_cmd.func = self._run_replace

        delete_cmd = Subcommand("genredelete", help="delete matching genre values")
        self._add_mutation_options(delete_cmd)
        delete_cmd.func = self._run_delete

        return [find_cmd, count_cmd, under_cmd, audit_cmd, replace_cmd, delete_cmd]

    @staticmethod
    def _add_mutation_options(cmd: Subcommand) -> None:
        cmd.parser.add_option(
            "-a",
            "--albums",
            action="store_true",
            dest="albums",
            help="edit album-level genres instead of items",
        )
        cmd.parser.add_option(
            "-i",
            "--ignore-case",
            action="store_true",
            dest="ignore_case",
            help="match genres case-insensitively",
        )
        cmd.parser.add_option(
            "-r",
            "--regex",
            action="store_true",
            dest="regex",
            help="treat the genre pattern as a regular expression",
        )
        cmd.parser.add_option(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="show changes without writing to the beets database or files",
        )
        cmd.parser.add_option(
            "--no-write-tags",
            action="store_true",
            dest="no_write_tags",
            help="update the beets DB only; do not rewrite file tags for items",
        )

    def _run_find(self, lib, opts, args) -> None:
        if not args:
            raise ValueError("genrefind requires a genre name")

        genre_name = args[0]
        query = decargs(args[1:])
        rows = lib.albums(query) if opts.albums else lib.items(query)

        count = 0
        for row in rows:
            if not has_matching_genre(
                row,
                genre_name,
                regex=opts.regex,
                ignore_case=opts.ignore_case,
            ):
                continue
            count += 1
            if opts.albums:
                print_(f"{row.albumartist} - {row.album}")
            else:
                print_(f"{row.artist} - {row.title}")

        label = "album" if opts.albums else "track"
        print_(f"Matched {count} {label}(s) for genre pattern '{genre_name}'.")

    def _run_count(self, lib, opts, args) -> None:
        query = decargs(args)
        rows = lib.albums(query) if opts.albums else lib.items(query)
        counts = collect_genre_counts(rows)

        if opts.alpha:
            rows_to_print = sorted(
                counts.items(),
                key=lambda item: (item[0].casefold(), item[0]),
            )[: max(opts.limit, 0)]
        else:
            rows_to_print = counts.most_common(max(opts.limit, 0))

        for genre, count in rows_to_print:
            print_(f"{count}\t{genre}")

        label = "album" if opts.albums else "track"
        print_(f"Counted {len(counts)} unique genre(s) across {label}s.")

    def _run_under(self, lib, opts, args) -> None:
        if not args:
            raise ValueError("genreunder requires a minimum genre count threshold")

        try:
            threshold = int(args[0])
        except ValueError as exc:
            raise ValueError("genreunder threshold must be an integer") from exc

        query = decargs(args[1:])
        rows = lib.albums(query) if opts.albums else lib.items(query)

        count = 0
        for row in rows:
            current = genre_count(row)
            if current >= threshold:
                continue
            count += 1
            print_(f"{entity_label(row, albums=opts.albums)} [{current}]")

        label = "album" if opts.albums else "track"
        print_(f"Matched {count} {label}(s) with fewer than {threshold} genre(s).")

    def _run_audit(self, lib, opts, args) -> None:
        query = decargs(args)
        rows = lib.albums(query) if opts.albums else lib.items(query)

        count = 0
        aborted = False
        for row in rows:
            original = iter_genre_values(getattr(row, "genre", None), getattr(row, "genres", None))
            current = render_genre_string(original, delimiter=opts.delimiter)

            print_("")
            print_(colorize(entity_label(row, albums=opts.albums), ANSI_BOLD + ANSI_CYAN))
            print_(f"  {colorize('Current:', ANSI_YELLOW)} {current or '<empty>'}")
            action = input(colorize("[E=edit, Enter=skip, Q=quit] ", ANSI_YELLOW)).strip()

            if not action:
                continue
            if action.casefold() in {"q", "quit"}:
                aborted = True
                break
            if action.casefold() not in {"e", "edit"}:
                continue

            answer = input_with_prefill(colorize("  New genres: ", ANSI_GREEN), current).strip()
            if not answer:
                continue
            if answer.casefold() in {"q", "quit"}:
                aborted = True
                break

            updated = parse_genre_string(answer, delimiter=opts.delimiter.strip())
            if updated == original:
                continue

            count += 1
            print_(f"  {colorize('Updated:', ANSI_GREEN)} {render_genre_string(updated, delimiter=opts.delimiter)}")

            if opts.dry_run:
                continue

            set_entity_genres(row, updated)
            row.store()
            if not opts.albums and not opts.no_write_tags:
                row.try_write()

        label = "album" if opts.albums else "track"
        print_(f"Changed {count} {label}(s).")
        if aborted:
            print_("Stopped by user.")
        if opts.dry_run:
            print_("Dry run only: no database rows or file tags were modified.")

    def _run_replace(self, lib, opts, args) -> None:
        if getattr(opts, "ask", False):
            if len(args) < 1:
                raise ValueError("genrereplace --ask requires a genre pattern")
        elif len(args) < 2:
            raise ValueError("genrereplace requires an old genre pattern and a replacement value")

        pattern = args[0]
        replacement = args[1].strip() if not getattr(opts, "ask", False) else None
        query = decargs(args[2:] if not getattr(opts, "ask", False) else args[1:])
        rows = lib.albums(query) if opts.albums else lib.items(query)
        matcher = make_genre_matcher(pattern, regex=opts.regex, ignore_case=opts.ignore_case)

        count = 0
        aborted = False
        for row in rows:
            original = iter_genre_values(getattr(row, "genre", None), getattr(row, "genres", None))
            if getattr(opts, "ask", False):
                replacements: dict[str, str] = {}
                for genre in original:
                    if not matcher(genre):
                        continue
                    prompt = (
                        f"Replace genre '{genre}' for {entity_label(row, albums=opts.albums)} "
                        "[Enter=skip, q=quit]: "
                    )
                    answer = input(prompt).strip()
                    if not answer:
                        continue
                    if answer.casefold() in {"q", "quit"}:
                        aborted = True
                        break
                    key = genre.casefold() if opts.ignore_case else genre
                    replacements[key] = answer
                if aborted:
                    break
                if not replacements:
                    continue
                updated = replace_matching_genres_with_map(
                    original,
                    replacements,
                    ignore_case=opts.ignore_case,
                )
            else:
                updated = replace_matching_genres(
                    original,
                    pattern,
                    replacement,
                    regex=opts.regex,
                    ignore_case=opts.ignore_case,
                )
            if updated == original:
                continue

            count += 1
            print_(f"{entity_label(row, albums=opts.albums)}")
            print_(f"  old: {original}")
            print_(f"  new: {updated}")

            if opts.dry_run:
                continue

            set_entity_genres(row, updated)
            row.store()
            if not opts.albums and not opts.no_write_tags:
                row.try_write()

        label = "album" if opts.albums else "track"
        print_(f"Changed {count} {label}(s).")
        if aborted:
            print_("Stopped by user.")
        if opts.dry_run:
            print_("Dry run only: no database rows or file tags were modified.")

    def _run_delete(self, lib, opts, args) -> None:
        if not args:
            raise ValueError("genredelete requires a genre pattern")

        pattern = args[0]
        query = decargs(args[1:])
        rows = lib.albums(query) if opts.albums else lib.items(query)

        count = 0
        for row in rows:
            original = iter_genre_values(getattr(row, "genre", None), getattr(row, "genres", None))
            updated = delete_matching_genres(
                original,
                pattern,
                regex=opts.regex,
                ignore_case=opts.ignore_case,
            )
            if updated == original:
                continue

            count += 1
            print_(f"{entity_label(row, albums=opts.albums)}")
            print_(f"  old: {original}")
            print_(f"  new: {updated}")

            if opts.dry_run:
                continue

            set_entity_genres(row, updated)
            row.store()
            if not opts.albums and not opts.no_write_tags:
                row.try_write()

        label = "album" if opts.albums else "track"
        print_(f"Changed {count} {label}(s).")
        if opts.dry_run:
            print_("Dry run only: no database rows or file tags were modified.")
