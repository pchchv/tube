"""
This module contains all the logic needed to decrypt the signature.

YouTube's strategy for restricting video uploads is to send
an encrypted version of the signature to the client,
along with a decryption algorithm disguised in JavaScript.
In order for the clients to play the video,
the JavaScript has to accept the encrypted version,
pass it through a series of "conversion functions",
and then sign the URL of the media file with the result.
This module is responsible for finding and retrieving these
"conversion function functions", mapping them to Python equivalents,
and getting the encrypted signature and decoding it.

"""
import re
import logging
from itertools import chain
from typing import Any, List, Dict, Callable, Optional
from tube.helpers import regex_search
from tube.exceptions import RegexMatchError


logger = logging.getLogger(__name__)


def get_initial_function_name(js: str) -> str:
    """Extract the name of the function responsible for
    calculating the signature.
    :param str js: Contents of the base.js asset file.
    :rtype: str
    :returns: The name of the function from the regex match
    """

    function_patterns = [
        r"\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
        r"\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
        r'(?:\b|[^a-zA-Z0-9$])(?P<sig>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',  # noqa: E501
        r'(?P<sig>[a-zA-Z0-9$]+)\s*=\s*function\(\s*a\s*\)\s*{\s*a\s*=\s*a\.split\(\s*""\s*\)',  # noqa: E501
        r'(["\'])signature\1\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(',
        r"\.sig\|\|(?P<sig>[a-zA-Z0-9$]+)\(",
        r"yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?:encodeURIComponent\s*\()?\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
        r"\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
        r"\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
        r"\bc\s*&&\s*a\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
        r"\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
        r"\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<sig>[a-zA-Z0-9$]+)\(",  # noqa: E501
    ]
    logger.debug("finding initial function name")
    for pattern in function_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(js)
        if function_match:
            logger.debug("finished regex search, matched: %s", pattern)
            return function_match.group(1)

    raise RegexMatchError(
        caller="get_initial_function_name", pattern="multiple"
    )


def get_transform_plan(js: str) -> List[str]:
    """Extract the "transformation plan".
    The "conversion plan" is the functions through
    which theencrypted signature passes.
    which the encrypted signature goes through to get the real signature.
    :param str js: The contents of the base.js asset file.
    **Example**:
    ['DE.AJ(a,15)',
    'DE.VR(a,3)',
    'DE.AJ(a,51)',
    'DE.VR(a,3)',
    'DE.kT(a,51)',
    'DE.kT(a,8)',
    'DE.VR(a,3)',
    'DE.kT(a,21)']
    """
    name = re.escape(get_initial_function_name(js))
    pattern = r"%s=function\(\w\){[a-z=\.\(\"\)]*;(.*);(?:.+)}" % name
    logger.debug("getting transform plan")
    return regex_search(pattern, js, group=1).split(";")


def get_transform_object(js: str, var: str) -> List[str]:
    """Extract the "transformation object".
    The "conversion object" contains the definitions of
    the functions referenced in the ``conversion plan``.
    The argument ``var`` is an obfuscated variable name.
    which contains these functions, e.g., given a call to the function
    ``DE.AJ(a,15)`` returned by the conversion plan,
    the variable would be "DE".
    :param str js: The contents of the base.js asset file.
    :param str var: The obfuscated name of the variable that holds
    the object with all the functions that decrypt the signature.
    **Example**:
    >>> get_transform_object(js, 'DE')
    ['AJ:function(a){a.reverse()}',
    'VR:function(a,b){a.splice(0,b)}',
    'kT:function(a,b){var c=a[0];a[0]=a[b%a.length];a[b]=c}']
    """
    pattern = r"var %s={(.*?)};" % re.escape(var)
    logger.debug("getting transform object")
    regex = re.compile(pattern, flags=re.DOTALL)
    transform_match = regex.search(js)
    if not transform_match:
        raise RegexMatchError(caller="get_transform_object", pattern=pattern)

    return transform_match.group(1).replace("\n", " ").split(", ")


def get_transform_map(js: str, var: str) -> Dict:
    """Build a lookup table for conversion functions.
    Build a lookup table for obfuscated JavaScript function names and
    their equivalents in Python.
    :param str js: Contents of the base.js asset file.
    :param str var: The obfuscated variable name in which
    the object with all functions is stored that decrypt the signature.
    """
    transform_object = get_transform_object(js, var)
    mapper = {}
    for obj in transform_object:
        # AJ:function(a){a.reverse()} => AJ, function(a){a.reverse()}
        name, function = obj.split(":", 1)
        fn = map_functions(function)
        mapper[name] = fn
    return mapper


def map_functions(js_func: str) -> Callable:
    """For a given JavaScript transform function, return the Python equivalent.
    :param str js_func: The JavaScript version of the transform function.
    """
    mapper = (
        # function(a){a.reverse()}
        (r"{\w\.reverse\(\)}", reverse),
        # function(a,b){a.splice(0,b)}
        (r"{\w\.splice\(0,\w\)}", splice),
        # function(a,b){var c=a[0];a[0]=a[b%a.length];a[b]=c}
        (r"{var\s\w=\w\[0\];\w\[0\]=\w\[\w\%\w.length\];\w\[\w\]=\w}", swap),
        # function(a,b){var c=a[0];a[0]=a[b%a.length];a[b%a.length]=c}
        (
            r"{var\s\w=\w\[0\];\w\[0\]=\w\[\w\%\w.\
                length\];\w\[\w\%\w.length\]=\w}",
            swap,
        ),
    )

    for pattern, fn in mapper:
        if re.search(pattern, js_func):
            return fn
    raise RegexMatchError(caller="map_functions", pattern="multiple")


def reverse(arr: List, _: Optional[Any]):
    """Reverse elements in a list.
    This function is equivalent to:
    .. code-block:: javascript
        function(a, b) { a.reverse() }
    This method takes an unused ``b`` variable as their transform functions
    universally sent two arguments.
    **Example**:
    >>> reverse([1, 2, 3, 4])
    [4, 3, 2, 1]
    """
    return arr[::-1]


def splice(arr: List, b: int):
    """Add/remove items to/from a list.
    This function is equivalent to:
    .. code-block:: javascript
        function(a, b) { a.splice(0, b) }
    **Example**:
    >>> splice([1, 2, 3, 4], 2)
    [1, 2]
    """
    return arr[b:]


def swap(arr: List, b: int):
    """Swap positions at b modulus the list length.
    This function is equivalent to:
    .. code-block:: javascript
        function(a, b) { var c=a[0];a[0]=a[b%a.length];a[b]=c }
    **Example**:
    >>> swap([1, 2, 3, 4], 2)
    [3, 2, 1, 4]
    """
    r = b % len(arr)
    return list(chain([arr[r]], arr[1:r], [arr[0]], arr[r + 1:]))
