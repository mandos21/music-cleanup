from scripts.cleanup_bad_genres import clean_genres


def test_clean_genres_removes_bad_values_case_insensitively():
    result = clean_genres(
        ["Post-Metal", "Seen Live", "post-metal", "Atmospheric Sludge"],
        {"seen live"},
    )

    assert result == ["Post-Metal", "Atmospheric Sludge"]


def test_clean_genres_handles_empty_input():
    assert clean_genres(None, {"bad"}) == []
    assert clean_genres([], {"bad"}) == []
