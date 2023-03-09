import pytest
from utub3.exceptions import RegexMatchError
from utub3.helpers import uniqueify, regex_search, safe_filename, cache


def test_regex_search_no_match():
    with pytest.raises(RegexMatchError):
        regex_search("^a$", "", group=0)


def test_regex_search():
    assert regex_search("^a$", "a", group=0) == "a"


def test_safe_filename():
    """Unsafe characters get stripped from generated filename"""
    assert safe_filename("abc1245$$") == "abc1245"
    assert safe_filename("abc##") == "abc"


def test_cache():
    call_count = 0

    @cache
    def cached_func(stuff):
        nonlocal call_count
        call_count += 1
        return stuff

    cached_func("hi")
    cached_func("hi")
    cached_func("bye")
    cached_func("bye")

    assert call_count == 2


def test_uniqueify():
    non_unique_list = [1, 2, 3, 3, 4, 5]
    expected = [1, 2, 3, 4, 5]
    result = uniqueify(non_unique_list)
    assert result == expected
