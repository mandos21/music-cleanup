from scripts.cleanup_bad_genres import clean_genres


def test_clean_genres_removes_bad_values_case_insensitively():
    result = clean_genres(
        ["Post-Metal", "Seen Live", "post-metal", "Atmospheric Sludge"],
        {"seen live"},
    )

    assert result == ["Post-Metal", "Atmospheric Sludge"]


def test_clean_genres_removes_digit_and_phrase_based_junk():
    result = clean_genres(
        ["Post-Metal", "2017 Releases", "Album of the Year", "Best Of 2020"],
        set(),
    )

    assert result == ["Post-Metal"]


def test_clean_genres_removes_nationalities_and_adjectives():
    result = clean_genres(
        ["American", "Amazing", "Atmospheric Sludge", "White"],
        set(),
    )

    assert result == ["Atmospheric Sludge"]


def test_clean_genres_removes_artist_and_album_self_tags():
    result = clean_genres(
        ["Radiohead", "Kid A", "Art Rock", "radiohead"],
        set(),
        artist="Radiohead",
        album="Kid A",
    )

    assert result == ["Art Rock"]


def test_clean_genres_handles_empty_input():
    assert clean_genres(None, {"bad"}) == []
    assert clean_genres([], {"bad"}) == []
