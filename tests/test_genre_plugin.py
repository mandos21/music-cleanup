from collections import Counter
from types import SimpleNamespace

from beetsplug.genre import (
    collect_genre_counts,
    delete_matching_genres,
    genre_count,
    has_matching_genre,
    iter_genre_values,
    parse_genre_string,
    replace_matching_genres,
    replace_matching_genres_with_map,
    render_genre_string,
    set_entity_genres,
)


def test_iter_genre_values_combines_genre_and_genres_without_duplicates():
    values = iter_genre_values(
        "Post-Metal; Sludge Metal",
        ["sludge metal", "Atmospheric Sludge", "Post-Metal"],
    )

    assert values == ["Post-Metal", "Sludge Metal", "Atmospheric Sludge"]


def test_has_matching_genre_checks_both_fields_with_exact_matching():
    row = SimpleNamespace(genre="Post-Metal", genres=["Atmospheric Sludge", "Drone"])

    assert has_matching_genre(row, "Post-Metal")
    assert has_matching_genre(row, "Drone")
    assert not has_matching_genre(row, "post-metal")
    assert not has_matching_genre(row, "drone")
    assert not has_matching_genre(row, "doom metal")


def test_has_matching_genre_supports_ignore_case():
    row = SimpleNamespace(genre="Post-Metal", genres=["Atmospheric Sludge", "Drone"])

    assert has_matching_genre(row, "post-metal", ignore_case=True)
    assert has_matching_genre(row, "drone", ignore_case=True)
    assert not has_matching_genre(row, "doom metal", ignore_case=True)


def test_has_matching_genre_supports_regex():
    row = SimpleNamespace(genre="Post-Metal", genres=["Atmospheric Sludge", "Drone"])

    assert has_matching_genre(row, r"^Post-", regex=True)
    assert has_matching_genre(row, r"sludge$", regex=True, ignore_case=True)
    assert not has_matching_genre(row, "doom metal")


def test_collect_genre_counts_counts_each_normalized_genre_once_per_row():
    rows = [
        SimpleNamespace(genre="Post-Metal", genres=["Atmospheric Sludge", "post-metal"]),
        SimpleNamespace(genre="Drone", genres="Atmospheric Sludge; Experimental"),
    ]

    assert collect_genre_counts(rows) == Counter(
        {
            "Post-Metal": 1,
            "Atmospheric Sludge": 2,
            "Drone": 1,
            "Experimental": 1,
        }
    )


def test_collect_genre_counts_can_be_sorted_alphabetically():
    counts = collect_genre_counts(
        [
            SimpleNamespace(genre="Drone", genres=["Experimental"]),
            SimpleNamespace(genre="Atmospheric Sludge", genres=["Post-Metal"]),
        ]
    )

    ordered = sorted(counts.items(), key=lambda item: (item[0].casefold(), item[0]))

    assert ordered == [
        ("Atmospheric Sludge", 1),
        ("Drone", 1),
        ("Experimental", 1),
        ("Post-Metal", 1),
    ]


def test_genre_count_uses_both_fields_and_normalizes_duplicates():
    row = SimpleNamespace(
        genre="Post-Metal; Sludge Metal",
        genres=["sludge metal", "Atmospheric Sludge"],
    )

    assert genre_count(row) == 3


def test_render_genre_string_joins_values_with_delimiter():
    assert render_genre_string(["Post-Metal", "Drone"]) == "Post-Metal; Drone"
    assert render_genre_string(["Post-Metal", "Drone"], delimiter=" | ") == "Post-Metal | Drone"


def test_parse_genre_string_splits_and_deduplicates():
    assert parse_genre_string("Post-Metal; Drone; post-metal") == ["Post-Metal", "Drone"]
    assert parse_genre_string("Post-Metal | Drone | post-metal", delimiter="|") == [
        "Post-Metal",
        "Drone",
    ]


def test_replace_matching_genres_supports_exact_and_deduplicates():
    result = replace_matching_genres(
        ["Post-Metal", "Sludge Metal", "post-metal"],
        "Post-Metal",
        "Atmospheric Sludge",
    )

    assert result == ["Atmospheric Sludge", "Sludge Metal", "post-metal"]


def test_replace_matching_genres_supports_regex_and_ignore_case():
    result = replace_matching_genres(
        ["Post-Metal", "Sludge Metal", "Black Metal"],
        r".*metal$",
        "Metal",
        regex=True,
        ignore_case=True,
    )

    assert result == ["Metal"]


def test_replace_matching_genres_with_map_uses_per_value_replacements():
    result = replace_matching_genres_with_map(
        ["Heavy Metal", "Speed Metal", "Doom Metal"],
        {
            "Heavy Metal": "Metal",
            "Speed Metal": "Speed/Power Metal",
        },
    )

    assert result == ["Metal", "Speed/Power Metal", "Doom Metal"]


def test_replace_matching_genres_with_map_supports_ignore_case():
    result = replace_matching_genres_with_map(
        ["Heavy Metal", "heavy metal", "Doom Metal"],
        {"heavy metal": "Metal"},
        ignore_case=True,
    )

    assert result == ["Metal", "Doom Metal"]


def test_delete_matching_genres_supports_exact_and_regex():
    exact = delete_matching_genres(
        ["Post-Metal", "Sludge Metal", "Drone"],
        "Drone",
    )
    regex = delete_matching_genres(
        ["Post-Metal", "Sludge Metal", "Drone"],
        r".*metal$",
        regex=True,
        ignore_case=True,
    )

    assert exact == ["Post-Metal", "Sludge Metal"]
    assert regex == ["Drone"]


def test_set_entity_genres_updates_both_fields():
    row = SimpleNamespace(genre="Old", genres=["Old"])

    set_entity_genres(row, ["Post-Metal", "Drone"])

    assert row.genres == ["Post-Metal", "Drone"]
    assert row.genre == "Post-Metal; Drone"
