from beetsplug.audit import AuditPlugin


def test_missing_fields_flags_none_and_blank_strings():
    missing = AuditPlugin._missing_fields(
        (
            ("artist", "Neurosis"),
            ("album", ""),
            ("title", "Through Silver in Blood"),
            ("mb_albumid", None),
        )
    )

    assert missing == ["album", "mb_albumid"]


def test_missing_fields_ignores_zero_like_values():
    missing = AuditPlugin._missing_fields(
        (
            ("year", 0),
            ("month", 1),
            ("artist", "Pelican"),
        )
    )

    assert missing == []
