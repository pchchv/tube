"""This module contains all non-cipher related data extraction logic."""
import re
import logging
from datetime import datetime
from tube.cipher import Cipher
from tube.helpers import regex_search
from tube.parser import parse_for_object
from typing import Any, Dict, Tuple, List
from urllib.parse import parse_qs, urlparse, urlencode
from tube.exceptions import RegexMatchError, HTMLParseError, LiveStreamError


logger = logging.getLogger(__name__)


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


def js_url(html: str) -> str:
    """Get a basic JavaScript url.
    Construct a basic JavaScript url that contains the transcript "transforms".
    :param str html: html-content of the view page.
    """
    try:
        base_js = get_ytplayer_config(html)['assets']['js']
    except (KeyError, RegexMatchError):
        base_js = get_ytplayer_js(html)
    return "https://youtube.com" + base_js


def initial_data(watch_html: str) -> str:
    """Extract the ytInitialData json from the watch_html page.
    This is basically the metadata needed to display the page when it loads,
    such as video information, copyright notices, etc.
    :param watch_html: Html of the watch page.
    :return:
    """
    patterns = [
        r"window\[['\"]ytInitialData['\"]]\s*=\s*",
        r"ytInitialData\s*=\s*"
    ]
    for pattern in patterns:
        try:
            return parse_for_object(watch_html, pattern)
        except HTMLParseError:
            pass

    raise RegexMatchError(caller='initial_data',
                          pattern='initial_data_pattern')


def apply_descrambler(stream_data: Dict) -> None:
    """Applies various in situ transformations to YouTube media stream data.
    Creates a ``list'' of dictionaries by splitting lines with commas,
    then takes each element in the list, parses it as a query string,
    converts it to ``dict'' and unfolds the value.
    :param dict stream_data:
        A dictionary containing the encoded values of the query string.
    """
    if 'url' in stream_data:
        return None

    # Merge formats and adaptiveFormats into a single list
    formats = []
    if 'formats' in stream_data.keys():
        formats.extend(stream_data['formats'])
    if 'adaptiveFormats' in stream_data.keys():
        formats.extend(stream_data['adaptiveFormats'])

    # Extract url and s from signatureCiphers as necessary
    for data in formats:
        if 'url' not in data:
            if 'signatureCipher' in data:
                cipher_url = parse_qs(data['signatureCipher'])
                data['url'] = cipher_url['url'][0]
                data['s'] = cipher_url['s'][0]
        data['is_otf'] = data.get('type') == 'FORMAT_STREAM_TYPE_OTF'

    logger.debug("applying descrambler")
    return formats


def apply_signature(stream_manifest: Dict, vid_info: Dict, js: str) -> None:
    """Apply a decrypted signature to the stream manifest.
    :param dict stream_manifest: Details of available media streams.
    :param str js: Contents of the base.js asset file.
    """
    cipher = Cipher(js=js)

    for i, stream in enumerate(stream_manifest):
        try:
            url: str = stream["url"]
        except KeyError:
            live_stream = (
                vid_info.get("playabilityStatus", {},)
                .get("liveStreamability")
            )
            if live_stream:
                raise LiveStreamError("UNKNOWN")
        # 403 Forbidden fix.
        if "signature" in url or (
            "s" not in stream and ("&sig=" in url or "&lsig=" in url)
        ):
            # For certain videos, YouTube will just provide them pre-signed,
            # in which case there's no real magic to download them and
            # we can skip the whole signature descrambling entirely.
            logger.debug("signature found, skip decipher")
            continue

        signature = cipher.get_signature(ciphered_signature=stream["s"])

        logger.debug(
            "finished descrambling signature for itag=%s", stream["itag"]
        )
        parsed_url = urlparse(url)

        # Convert query params off url to dict
        query_params = parse_qs(urlparse(url).query)
        query_params = {
            k: v[0] for k, v in query_params.items()
        }
        query_params['sig'] = signature
        if 'ratebypass' not in query_params.keys():
            # Cipher n to get the updated value

            initial_n = list(query_params['n'])
            new_n = cipher.calculate_n(initial_n)
            query_params['n'] = new_n

        url = f'{parsed_url.scheme}://{parsed_url.netloc}\
            {parsed_url.path}?{urlencode(query_params)}'  # noqa:E501

        # 403 forbidden fix
        stream_manifest[i]["url"] = url


def recording_available(watch_html):
    """Check if live stream recording is available.
    :param str watch_html: The html contents of the watch page.
    :rtype: bool
    :returns: Whether or not the content is private.
    """
    unavailable_strings = [
        'This live stream recording is not available.'
    ]
    for string in unavailable_strings:
        if string in watch_html:
            return False
    return True


def is_private(watch_html):
    """Check if content is private.
    :param str watch_html: The html contents of the watch page.
    :rtype: bool
    :returns: Whether or not the content is private.
    """
    private_strings = [
        "This is a private video. \
            Please sign in to verify that you may see it.",
        "\"simpleText\":\"Private video\"",
        "This video is private."
    ]
    for string in private_strings:
        if string in watch_html:
            return True
    return False
