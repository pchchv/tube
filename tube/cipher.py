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
from tube.helpers import regex_search, cache
from tube.exceptions import RegexMatchError, ExtractError
from typing import Any, List, Dict, Callable, Optional, Tuple
from tube.parser import find_object_from_startpoint, throttling_array_split


logger = logging.getLogger(__name__)


class Cipher:
    def __init__(self, js: str):
        self.transform_plan: List[str] = get_transform_plan(js)
        var_regex = re.compile(r"^\w+\W")
        var_match = var_regex.search(self.transform_plan[0])
        if not var_match:
            raise RegexMatchError(
                caller="__init__", pattern=var_regex.pattern
            )
        var = var_match.group(0)[:-1]
        self.transform_map = get_transform_map(js, var)
        self.js_func_patterns = [
            r"\w+\.(\w+)\(\w,(\d+)\)",
            r"\w+\[(\"\w+\")\]\(\w,(\d+)\)"
        ]

        self.throttling_plan = get_throttling_plan(js)
        self.throttling_array = get_throttling_function_array(js)
        self.calculated_n = None

    def calculate_n(self, initial_n: list):
        """Converts n to the correct value to prevent throttling."""
        if self.calculated_n:
            return self.calculated_n

        # First, update all instances of 'b' with the list(initial_n)
        for i in range(len(self.throttling_array)):
            if self.throttling_array[i] == 'b':
                self.throttling_array[i] = initial_n

        for step in self.throttling_plan:
            curr_func = self.throttling_array[int(step[0])]
            if not callable(curr_func):
                logger.debug(f'{curr_func} is not callable.')
                logger.debug(f'Throttling array:\n{self.throttling_array}\n')
                raise ExtractError(f'{curr_func} is not callable.')

            first_arg = self.throttling_array[int(step[1])]

            if len(step) == 2:
                curr_func(first_arg)
            elif len(step) == 3:
                second_arg = self.throttling_array[int(step[2])]
                curr_func(first_arg, second_arg)

        self.calculated_n = ''.join(initial_n)
        return self.calculated_n

    def get_signature(self, ciphered_signature: str) -> str:
        """Decrypt the signature.
        Having received the decrypted signature,
        applies the conversion functions.
        :param str ciphered_signature:
        Encrypted signature sent to ``player_config''.
        :rtype: str
        :return: The decrypted signature needed to load media content.
        """
        signature = list(ciphered_signature)

        for js_func in self.transform_plan:
            name, argument = self.parse_function(js_func)  # type: ignore
            signature = self.transform_map[name](signature, argument)
            logger.debug(
                "applied transform function\n"
                "output: %s\n"
                "js_function: %s\n"
                "argument: %d\n"
                "function: %s",
                "".join(signature),
                name,
                argument,
                self.transform_map[name],
            )

        return "".join(signature)

    @cache
    def parse_function(self, js_func: str) -> Tuple[str, int]:
        """Parsing a Javascript conversion function.
        Explode the JavaScript conversion function into
        a two-element ``cortex'' containing the function name
        and some integer argument.
        :param str js_func: JavaScript version of the conversion function.
        :rtype: tuple
        :returns:
        a two-element tuple, containing the function name and the argument.
        **Example**:
        parse_function('DE.AJ(a,15)')
        ('AJ', 15)
        """
        logger.debug("parsing transform function")
        for pattern in self.js_func_patterns:
            regex = re.compile(pattern)
            parse_match = regex.search(js_func)
            if parse_match:
                fn_name, fn_arg = parse_match.groups()
                return fn_name, int(fn_arg)

        raise RegexMatchError(
            caller="parse_function", pattern="js_func_patterns"
        )


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


def get_throttling_function_array(js: str) -> List[Any]:
    """Extract the array "c".
    :param str js: Contents of the base.js asset file.
    :return: An array of various integers, arrays, and functions.
    """
    raw_code = get_throttling_function_code(js)

    array_start = r",c=\["
    array_regex = re.compile(array_start)
    match = array_regex.search(raw_code)

    array_raw = find_object_from_startpoint(raw_code, match.span()[1] - 1)
    str_array = throttling_array_split(array_raw)

    converted_array = []
    for el in str_array:
        try:
            converted_array.append(int(el))
            continue
        except ValueError:
            # Not an integer value.
            pass

        if el == 'null':
            converted_array.append(None)
            continue

        if el.startswith('"') and el.endswith('"'):
            # Convert e.g. '"abcdef"' to string without quotation marks,
            # 'abcdef'
            converted_array.append(el[1:-1])
            continue

        if el.startswith('function'):
            mapper = (
                (r"{for\(\w=\(\w%\w\.length\+\w\.length\)%\w\
                 .length;\w--;\)\w\.unshift\(\w.pop\(\)\)}", throttling_unshift),  # noqa:E501
                (r"{\w\.reverse\(\)}", throttling_reverse),
                (r"{\w\.push\(\w\)}", throttling_push),
                (r";var\s\w=\w\[0\];\w\[0\]=\w\[\w\];\w\[\w\]=\w}",
                 throttling_swap),
                (r"case\s\d+", throttling_cipher_function),
                (r"\w\.splice\(0,1,\w\.splice\(\w,1,\w\[0\]\)\[0\]\)", throttling_nested_splice),  # noqa:E501
                (r";\w\.splice\(\w,1\)}", js_splice),
                (r"\w\.splice\(-\w\)\.reverse\(\)\
                 .forEach\(function\(\w\){\w\.unshift\(\w\)}\)", throttling_prepend),  # noqa:E501
                (r"for\(var \w=\w\.length;\w;\)\w\.push\(\w\.splice\(--\w,1\)\[0\]\)}", throttling_reverse),  # noqa:E501
            )

            found = False
            for pattern, fn in mapper:
                if re.search(pattern, el):
                    converted_array.append(fn)
                    found = True
            if found:
                continue

        converted_array.append(el)

    # Replace null elements with array itself
    for i in range(len(converted_array)):
        if converted_array[i] is None:
            converted_array[i] = converted_array

    return converted_array


def js_splice(arr: list, start: int, delete_count=None, *items):
    """Implementation of the splice function from javascript.
    :param list arr: Array for splice
    :param int start: The index from which to start changing the array
    :param int delete_count: Number of elements to delete from the array
    :param *items: Elements to add to the array
    """
    # Special conditions for start value
    try:
        if start > len(arr):
            start = len(arr)
        # If start is negative, count backwards from end
        if start < 0:
            start = len(arr) - start
    except TypeError:
        # Non-integer start values are treated as 0 in js
        start = 0

    # Special condition when delete_count is greater than remaining elements
    if not delete_count or delete_count >= len(arr) - start:
        delete_count = len(arr) - start  # noqa: N806

    deleted_elements = arr[start:start + delete_count]

    # Splice appropriately.
    new_arr = arr[:start] + list(items) + arr[start + delete_count:]

    # Replace contents of input array
    arr.clear()
    for el in new_arr:
        arr.append(el)

    return deleted_elements


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


def get_throttling_plan(js: str):
    """Extract the "throttling plan".
    The "throttling plan" is a list of tuples used
    to call functions in the array c.
    The first element of the tuple is the index of the function to call,
    and all other elements of the tuple are arguments passed to this function.
    :param str js: The contents of the base.js asset file.
    :return: Full function code for calculating the throttlign parameter.
    """
    raw_code = get_throttling_function_code(js)
    transform_start = r"try{"
    plan_regex = re.compile(transform_start)
    match = plan_regex.search(raw_code)
    transform_plan_raw = find_object_from_startpoint(raw_code,
                                                     match.span()[1] - 1)

    # Steps are either c[x](c[y]) or c[x](c[y],c[z])
    step_start = r"c\[(\d+)\]\(c\[(\d+)\](,c(\[(\d+)\]))?\)"
    step_regex = re.compile(step_start)
    matches = step_regex.findall(transform_plan_raw)
    transform_steps = []
    for match in matches:
        if match[4] != '':
            transform_steps.append((match[0], match[1], match[4]))
        else:
            transform_steps.append((match[0], match[1]))

    return transform_steps


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


def throttling_nested_splice(d: list, e: int):
    """Nested splicing function in throttling js.
    In javascript the operation looks as follows:
    function(d,e){
        e=(e%d.length+d.length)%d.length;
        d.splice(
            0,
            1,
            d.splice(
                e,
                1,
                d[0]
            )[0]
        )
    }
    """
    e = throttling_mod_func(d, e)
    inner_splice = js_splice(
        d,
        e,
        1,
        d[0]
    )
    js_splice(
        d,
        0,
        1,
        inner_splice[0]
    )


def throttling_prepend(d: list, e: int):
    """This moves the last e elements of d to the beginning.
    In javascript, the operation looks like this:
    function(d,e){
        e=(e%d.length+d.length)%d.length;
        d.splice(-e).reverse().forEach(
            function(f){
                d.unshift(f)
            }
        )
    }
    """
    start_len = len(d)
    # First, calculate e
    e = throttling_mod_func(d, e)

    # Then do the prepending
    new_arr = d[-e:] + d[:-e]

    # And update the input list
    d.clear()
    for el in new_arr:
        d.append(el)

    end_len = len(d)
    assert start_len == end_len
