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
from tube.helpers import regex_search
from tube.exceptions import RegexMatchError
from tube.parser import find_object_from_startpoint
from typing import Any, List, Dict, Callable, Optional


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


def get_throttling_function_name(js: str) -> str:
    """Extracts the name of the function that calculates the
    throttle parameter.
    :param str js: Contents of the base.js asset file.
    :rtype: str
    :returns: Name of the function used to calculate the throttling parameter.
    """
    function_patterns = [
        r'a\.[a-zA-Z]\s*&&\s*\([a-z]\s*=\s*a\.get\("n"\)\)\s*&&\s*'
        r'\([a-z]\s*=\s*([a-zA-Z0-9$]+)(\[\d+\])?\([a-z]\)',
    ]
    logger.debug('Finding throttling function name')
    for pattern in function_patterns:
        regex = re.compile(pattern)
        function_match = regex.search(js)
        if function_match:
            logger.debug("finished regex search, matched: %s", pattern)
            if len(function_match.groups()) == 1:
                return function_match.group(1)
            idx = function_match.group(2)
            if idx:
                idx = idx.strip("[]")
                array = re.search(
                    r'var {nfunc}\s*=\s*(\[.+?\]);'.format(
                        nfunc=re.escape(function_match.group(1))),
                    js
                )
                if array:
                    array = array.group(1).strip("[]").split(",")
                    array = [x.strip() for x in array]
                    return array[int(idx)]

    raise RegexMatchError(
        caller="get_throttling_function_name", pattern="multiple"
    )


def get_throttling_function_code(js: str) -> str:
    """Extract the raw code for the throttle function.
    :param str js: Contents of the base.js asset file.
    :rtype: str
    :returns: Name of the function used to calculate the throttling parameter.
    """
    # Begin by extracting the correct function name
    name = re.escape(get_throttling_function_name(js))

    # Identify where the function is defined
    pattern_start = r"%s=function\(\w\)" % name
    regex = re.compile(pattern_start)
    match = regex.search(js)

    # Extract the code in curly braces for the
    # function itself and merge all split lines
    code_lines_list = find_object_from_startpoint(
        js, match.span()[1]).split('\n')
    joined_lines = "".join(code_lines_list)

    # Prepend function definition (e.g. `Dea=function(a)`)
    return match.group(0) + joined_lines


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


def throttling_mod_func(d: list, e: int):
    """Perform a modular function from the throttling array functions.
    In javascript the modular operation looks like this:
    e = (e % d.length + d.length) % d.length.
    Here we simply translate this into python.
    """
    return (e % len(d) + len(d)) % len(d)


def throttling_unshift(d: list, e: int):
    """Rotates the list items to the right.
    In javascript the operation looks like this:
    for(e=(e%d.length+d.length)%d.length;e--;)d.unshift(d.pop())
    """
    e = throttling_mod_func(d, e)
    new_arr = d[-e:] + d[:-e]
    d.clear()
    for el in new_arr:
        d.append(el)


def throttling_reverse(arr: list):
    """Inverts the input list.
    It is necessary to perform an inversion in
    place for the passed list to be modified.
    To do this, create an inverse copy and
    then modify each individual item.
    """
    reverse_copy = arr.copy()[::-1]
    for i in range(len(reverse_copy)):
        arr[i] = reverse_copy[i]


def throttling_push(d: list, e: Any):
    """Pushes an element to the list."""
    d.append(e)


def throttling_swap(d: list, e: int):
    """Swap the 0th and e'th elements."""
    e = throttling_mod_func(d, e)
    f = d[0]
    d[0] = d[e]
    d[e] = f


def throttling_cipher_function(d: list, e: str):
    """This encrypts d with e to create a new list.
    In javascript the operation looks like this:
    var h = [A-Za-z0-9-_], f = 96;  // simplified from switch-case loop
    d.forEach(
        function(l,m,n){
            this.push(
                n[m]=h[
                    (h.indexOf(l)-h.indexOf(this[m])+m-32+f--)%h.length
                ]
            )
        },
        e.split("")
    )
    """
    h = list(
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
    f = 96
    # by naming it "this" we can more closely reflect the js
    this = list(e)

    # This is to avoid the oddity of
    # using enumerate when changing the input list
    copied_list = d.copy()

    for m, l in enumerate(copied_list):
        bracket_val = (h.index(l) - h.index(this[m]) + m - 32 + f) % len(h)
        this.append(
            h[bracket_val]
        )
        d[m] = h[bracket_val]
        f -= 1
