"""Implements a simple wrapper around urlopen."""
import json
import socket
from functools import lru_cache
from urllib3.request import Request, urlopen


def _execute_request(
    url,
    method=None,
    headers=None,
    data=None,
    timeout=socket._GLOBAL_DEFAULT_TIMEOUT
):
    base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}
    if headers:
        base_headers.update(headers)
    if data:
        # encode data for request
        if not isinstance(data, bytes):
            data = bytes(json.dumps(data), encoding="utf-8")
    if url.lower().startswith("http"):
        request = Request(url, headers=base_headers, method=method, data=data)
    else:
        raise ValueError("Invalid URL")
    return urlopen(request, timeout=timeout)  # nosec


@lru_cache()
def filesize(url):
    """Fetch file size in bytes from given URL
    :param str url: URL for getting the size
    :return: int: size in bytes of the deleted file
    """
    return int(head(url)["content-length"])


def head(url):
    """Fetch the headers returned by the http GET request.
    :param str url: URL to perform a GET request.
    :rtype: dict
    :returns: lowercase header dictionary
    """
    response_headers = _execute_request(url, method="HEAD").info()
    return {k.lower(): v for k, v in response_headers.items()}
