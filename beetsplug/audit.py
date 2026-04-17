from __future__ import annotations

from collections.abc import Iterable

from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, decargs, print_


class AuditPlugin(BeetsPlugin):
    def commands(self) -> list[Subcommand]:
        cmd = Subcommand("auditfields", help="report missing metadata useful for cleanup")
        cmd.parser.add_option(
            "-a",
            "--albums",
            action="store_true",
            dest="albums",
            help="audit album-level metadata instead of items",
        )
        cmd.func = self._run
        return [cmd]

    def _run(self, lib, opts, args) -> None:
        query = decargs(args)
        rows = lib.albums(query) if opts.albums else lib.items(query)
        if opts.albums:
            self._audit_albums(rows)
        else:
            self._audit_items(rows)

    @staticmethod
    def _missing_fields(values: Iterable[tuple[str, object]]) -> list[str]:
        missing: list[str] = []
        for field_name, value in values:
            if value is None:
                missing.append(field_name)
                continue
            if isinstance(value, str) and not value.strip():
                missing.append(field_name)
        return missing

    def _audit_items(self, items) -> None:
        count = 0
        for item in items:
            missing = self._missing_fields(
                (
                    ("artist", item.artist),
                    ("album", item.album),
                    ("title", item.title),
                    ("mb_trackid", item.mb_trackid),
                    ("mb_albumid", item.mb_albumid),
                )
            )
            if not missing:
                continue
            count += 1
            print_(f"ITEM  {item.path} :: missing {', '.join(missing)}")
        print_(f"Audited {count} item(s) with missing metadata.")

    def _audit_albums(self, albums) -> None:
        count = 0
        for album in albums:
            missing = self._missing_fields(
                (
                    ("albumartist", album.albumartist),
                    ("album", album.album),
                    ("mb_albumid", album.mb_albumid),
                    ("albumtype", album.albumtype),
                    ("year", album.year),
                )
            )
            if not missing:
                continue
            count += 1
            print_(f"ALBUM {album.path} :: missing {', '.join(missing)}")
        print_(f"Audited {count} album(s) with missing metadata.")
