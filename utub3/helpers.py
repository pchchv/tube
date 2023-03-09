"""Various helper functions implemented by utub3."""
import re
import os
import logging
import warnings
import functools
from urllib import request
from functools import lru_cache
from utub3.exceptions import RegexMatchError
from typing import Optional, Dict, Callable, TypeVar, Any, List


logger = logging.getLogger(__name__)


GenericType = TypeVar("GenericType")


class DeferredGeneratorList:
    """A wrapper class for delayed list generation.
    Utub3 has some continuation generators that generate web calls,
    which means that every time a full list is requested,
    all of those web calls have to be at the same time,
    which can cause slowdowns. This will allow the individual items
    to be queried so that the slowdown occurs only as needed.
    For example, it could be possible to iterate through list items
    without requesting all of them at the same time.
    This will increase the speed of playlist and channel interaction.
    """
    def __init__(self, generator):
        """Construct a :class:`DeferredGeneratorList <DeferredGeneratorList>`.
        :param generator generator:
            The deferrable generator to create a wrapper for.
        :param func func: (Optional)
            A function to call on the generator items to produce the list.
        """
        self.gen = generator
        self._elements = []

    def __eq__(self, other):
        """Need to mimic the behavior of the list for comparison."""
        return list(self) == other

    def __getitem__(self, key) -> Any:
        """Only generate items as they're asked for."""
        # Allow queries with indexes only.
        if not isinstance(key, (int, slice)):
            raise TypeError('Key must be either a slice or int.')

        # Convert int keys to slice
        key_slice = key
        if isinstance(key, int):
            key_slice = slice(key, key + 1, 1)

        # Generate all elements up to the final item
        while len(self._elements) < key_slice.stop:
            try:
                next_item = next(self.gen)
            except StopIteration:
                # If there are not enough elements to cut,
                # an IndexError is issued
                raise IndexError
            else:
                self._elements.append(next_item)

        return self._elements[key]

    def __iter__(self):
        """Custom iterator for dynamically generated list."""
        iter_index = 0
        while True:
            try:
                curr_item = self[iter_index]
            except IndexError:
                return
            else:
                yield curr_item
                iter_index += 1

    def __next__(self) -> Any:
        """Fetch next element in iterator."""
        try:
            curr_element = self[self.iter_index]
        except IndexError:
            raise StopIteration
        self.iter_index += 1
        return curr_element  # noqa:R504

    def __len__(self) -> int:
        """Return length of list of all items."""
        self.generate_all()
        return len(self._elements)

    def __repr__(self) -> str:
        """String representation of all items."""
        self.generate_all()
        return str(self._elements)

    def __reversed__(self):
        self.generate_all()
        return self._elements[::-1]

    def generate_all(self):
        """Generate all items."""
        while True:
            try:
                next_item = next(self.gen)
            except StopIteration:
                break
            else:
                self._elements.append(next_item)


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


def target_directory(output_path: Optional[str] = None) -> str:
    """Function to determine the target directory to load.
    Returns absolute path (if relative) or current path (if none).
    Creates a directory if it does not exist.
    :type output_path: str
    :rtype: str
    :return: Absolute path to the directory as a string.
    """
    if output_path:
        if not os.path.isabs(output_path):
            output_path = os.path.join(os.getcwd(), output_path)
    else:
        output_path = os.getcwd()
    os.makedirs(output_path, exist_ok=True)
    return output_path


def install_proxy(proxy_handler: Dict[str, str]) -> None:
    proxy_support = request.ProxyHandler(proxy_handler)
    opener = request.build_opener(proxy_support)
    request.install_opener(opener)


def cache(func: Callable[..., GenericType]) -> GenericType:
    """ mypy compatible annotation wrapper for lru_cache"""
    return lru_cache()(func)  # type: ignore


def deprecated(reason: str) -> Callable:
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.
    """

    def decorator(func1):
        message = "Call to deprecated function {name} ({reason})."

        @functools.wraps(func1)
        def new_func1(*args, **kwargs):
            warnings.simplefilter("always", DeprecationWarning)
            warnings.warn(
                message.format(name=func1.__name__, reason=reason),
                category=DeprecationWarning,
                stacklevel=2,
            )
            warnings.simplefilter("default", DeprecationWarning)
            return func1(*args, **kwargs)

        return new_func1

    return decorator


def setup_logger(level: int = logging.ERROR,
                 log_filename: Optional[str] = None) -> None:
    """Create a configured instance of logger.
    :param int level: Describe the severity level of the logs to handle.
    """
    fmt = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    date_fmt = "%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    logger = logging.getLogger("utub3")
    logger.setLevel(level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_filename is not None:
        file_handler = logging.FileHandler(log_filename)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def uniqueify(duped_list: List) -> List:
    """Remove duplicate items from a list, while maintaining list order.
    :param List duped_list: List to remove duplicates from
    :return List result: De-duplicated list
    """
    seen: Dict[Any, bool] = {}
    result = []
    for item in duped_list:
        if item in seen:
            continue
        seen[item] = True
        result.append(item)
    return result
