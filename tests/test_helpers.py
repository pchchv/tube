import io
import os
import gzip
import json
import pytest
from unittest import mock
from utub3.exceptions import RegexMatchError
from utub3.helpers import uniqueify, regex_search, safe_filename, cache, deprecated, target_directory, setup_logger, create_mock_html_json


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


@mock.patch("warnings.warn")
def test_deprecated(warn):
    @deprecated("oh no")
    def deprecated_function():
        return None

    deprecated_function()
    warn.assert_called_with(
        "Call to deprecated function deprecated_function (oh no).",
        category=DeprecationWarning,
        stacklevel=2,
    )


@mock.patch("os.path.isabs", return_value=False)
@mock.patch("os.getcwd", return_value="/cwd")
@mock.patch("os.makedirs")
def test_target_directory_with_relative_path(_, __, makedirs):  # noqa: PT019
    assert target_directory("test") == os.path.join("/cwd", "test")
    makedirs.assert_called()


@mock.patch("os.path.isabs", return_value=True)
@mock.patch("os.makedirs")
def test_target_directory_with_absolute_path(_, makedirs):  # noqa: PT019
    assert target_directory("/test") == "/test"
    makedirs.assert_called()


@mock.patch("os.getcwd", return_value="/cwd")
@mock.patch("os.makedirs")
def test_target_directory_with_no_path(_, makedirs):  # noqa: PT019
    assert target_directory() == "/cwd"
    makedirs.assert_called()


@mock.patch("utub3.helpers.logging")
def test_setup_logger(logging):
    # Given
    logger = logging.getLogger.return_value
    # When
    setup_logger(20)
    # Then
    logging.getLogger.assert_called_with("utub3")
    logger.addHandler.assert_called()
    logger.setLevel.assert_called_with(20)


@mock.patch('builtins.open', new_callable=mock.mock_open)
@mock.patch('utub3.request.urlopen')
def test_create_mock_html_json(mock_url_open, mock_open):
    video_id = '2lAe1cqCOXo'
    gzip_html_filename = 'yt-video-%s-html.json.gz' % video_id

    # Get the utub3 directory in order to navigate to /tests/mocks
    utube_dir_pat3 = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            os.path.pardir
        )
    )
    utube_mocks_pat3 = os.path.join(utube_dir_pat3, 'tests', 'mocks')
    gzip_html_filepath = os.path.join(utube_mocks_pat3, gzip_html_filename)

    # Mock the responses to YouTube
    mock_url_open_object = mock.Mock()

    # Order is:
    # 1. watch_html -- must have jsurl match
    # 2. embed html
    # 3. watch html
    # 4. raw vid info
    mock_url_open_object.read.side_effect = [
        (b'yt.setConfig({"PLAYER_CONFIG":{"args":[]}});ytInitialData = {};ytInitialPlayerResponse = {};'  # noqa: E501
         b'"jsUrl":"/s/player/13371337/player_ias.vflset/en_US/base.js"'),
        b'embed_html',
        b'watch_html',
        b'{\"responseContext\":{}}',
    ]
    mock_url_open.return_value = mock_url_open_object

    # Generate a json with sample html json
    result_data = create_mock_html_json(video_id)

    # Assert that a write was only made once
    mock_open.assert_called_once_with(gzip_html_filepath, 'wb')

    # The result data should look like this:
    gzip_file = io.BytesIO()
    with gzip.GzipFile(
        filename=gzip_html_filename,
        fileobj=gzip_file,
        mode='wb'
    ) as f:
        f.write(json.dumps(result_data).encode('utf-8'))
    gzip_data = gzip_file.getvalue()

    file_handle = mock_open.return_value.__enter__.return_value

    # write is called several times, so you must combine all write calls to get
    # the full data before comparing it with the value of the BytesIO object.
    full_content = b''
    for call in file_handle.write.call_args_list:
        args, kwargs = call
        full_content += b''.join(args)

    # The file header contains time metadata,
    # so *sometimes* one byte at the very beginning will be offset.
    # Theoretically, this difference should only affect
    # bytes 5-8 (or [4:8] due to zero indexing).
    # The 10-byte metadata header is excluded from the check just in case.
    assert gzip_data[10:] == full_content[10:]
