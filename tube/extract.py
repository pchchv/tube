"""This module contains all non-cipher related data extraction logic."""
import re
from datetime import datetime
from typing import Tuple, List
from tube.helpers import regex_search
from tube.exceptions import RegexMatchError


def publish_date(watch_html: str):
    """Extract publication date
    :param str watch_html:
        html content of the watch page.
    :rtype: str
    :returns:
        Video publication date.
    """
    try:
        result = regex_search(
            r"(?<=itemprop=\"datePublished\" content=\")\d{4}-\d{2}-\d{2}",
            watch_html, group=0
        )
    except RegexMatchError:
        return None
    return datetime.strptime(result, '%Y-%m-%d')


def mime_type_codec(mime_type_codec: str) -> Tuple[str, List[str]]:
    """Type data parsing.
    Parses the data in the ``type'' key of the manifest, which contains
    mime type and codecs serialized together, and parses them into separate
    elements.
    **Example**:
    mime_type_codec('audio/webm; codecs='opus') -> ('audio/webm', ['opus'])
    :param str mime_type_codec:
        String containing mime type and codecs.
    :rtype: tuple
    :returns:
        The mime type and list of codecs.
    """
    pattern = r"(\w+\/\w+)\;\scodecs=\"([a-zA-Z-0-9.,\s]*)\""
    regex = re.compile(pattern)
    results = regex.search(mime_type_codec)
    if not results:
        raise RegexMatchError(caller="mime_type_codec", pattern=pattern)
    mime_type, codecs = results.groups()
    return mime_type, [c.strip() for c in codecs.split(",")]


def video_id(url: str) -> str:
    """Extract the ``video_id`` from a YouTube url.
    This function supports the following patterns:
    - :samp:`https://youtube.com/watch?v={video_id}`
    - :samp:`https://youtube.com/embed/{video_id}`
    - :samp:`https://youtu.be/{video_id}`
    :param str url: A YouTube url containing a video id.
    :rtype: str
    :returns: YouTube video id.
    """
    return regex_search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url, group=1)


def is_age_restricted(watch_html: str) -> bool:
    """Checks if the content is age restricted.
    :param str watch_html: The html content of the watch page.
    :rtype: bool
    :returns: Whether the page content is age restricted or not.
    """
    try:
        regex_search(r"og:restrictions:age", watch_html, group=0)
    except RegexMatchError:
        return False
    return True


def get_ytplayer_js(html: str) -> Any:
    """Get the JavaScript path of the YouTube player base.
    :param str html: html content of the view page.
    :rtype: str
    :return: Path to the base.js file of the YouTube player.
    """
    js_url_patterns = [
        r"(/s/player/[\w\d]+/[\w\d_/.]+/base\.js)"
    ]
    for pattern in js_url_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(html)
        if function_match:
            logger.debug("finished regex search, matched: %s", pattern)
            yt_player_js = function_match.group(1)
            return yt_player_js

    raise RegexMatchError(
        caller="get_ytplayer_js", pattern="js_url_patterns"
    )


def get_ytplayer_config(html: str) -> Any:
    """Get the YouTube player configuration data from the html viewer file.
    Extract ``ytplayer_config``, which is json data embedded in
    watch html and serves as the primary source for the stream
    manifest data.
    :param str html: html-content of the watch page.
    :rtype: str
    :returns: The html substring containing the encoded manifest data.
    """
    logger.debug("finding initial function name")
    config_patterns = [
        r"ytplayer\.config\s*=\s*",
        r"ytInitialPlayerResponse\s*=\s*"
    ]
    for pattern in config_patterns:
        # Try each pattern consecutively if they don't find a match
        try:
            return parse_for_object(html, pattern)
        except HTMLParseError as e:
            logger.debug(f'Pattern failed: {pattern}')
            logger.debug(e)
            continue

    # setConfig() needs to be handled a little differently.
    # We want to parse the entire argument to setConfig()
    #  and use then load that as json to find PLAYER_CONFIG
    #  inside of it.
    setconfig_patterns = [
        r"yt\.setConfig\(.*['\"]PLAYER_CONFIG['\"]:\s*"
    ]
    for pattern in setconfig_patterns:
        # Try each pattern consecutively if they don't find a match
        try:
            return parse_for_object(html, pattern)
        except HTMLParseError:
            continue

    raise RegexMatchError(
        caller="get_ytplayer_config",
        pattern="config_patterns, setconfig_patterns"
    )
