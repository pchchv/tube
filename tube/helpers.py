"""Various helper functions implemented by tube."""
import re
import logging
from tube.exceptions import RegexMatchError


logger = logging.getLogger(__name__)


def regex_search(pattern: str, string: str, group: int) -> str:
    """Shortcut method to search a string for a given pattern.
    :param str pattern:
        A regular expression pattern.
    :param str string:
        A target string to search.
    :param int group:
        Index of group to return.
    :rtype:
        str or tuple
    :returns:
        Substring pattern matches.
    """
    regex = re.compile(pattern)
    results = regex.search(string)
    if not results:
        raise RegexMatchError(caller="regex_search", pattern=pattern)

    logger.debug("matched regex search: %s", pattern)

    return results.group(group)


def safe_filename(s: str, max_length: int = 255) -> str:
    """Sanitizes a string, making it safe to use as a filename.
    :param str s: The string to be made safe for use as a filename.
    :param int max_length: Maximum character length of the filename.
    :rtype: str
    :return: The sanitized string.
    """
    # Characters in range 0-31 (0x00-0x1F) are not allowed in ntfs filenames.
    ntfs_characters = [chr(i) for i in range(0, 31)]
    characters = [
        r'"',
        r"\#",
        r"\$",
        r"\%",
        r"'",
        r"\*",
        r"\,",
        r"\.",
        r"\/",
        r"\:",
        r'"',
        r"\;",
        r"\<",
        r"\>",
        r"\?",
        r"\\",
        r"\^",
        r"\|",
        r"\~",
        r"\\\\",
    ]
    pattern = "|".join(ntfs_characters + characters)
    regex = re.compile(pattern, re.UNICODE)
    filename = regex.sub("", s)
    return filename[:max_length].rsplit(" ", 0)[0]
