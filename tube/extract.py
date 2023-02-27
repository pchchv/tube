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
