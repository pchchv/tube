"""This module provides a query interface for media streams and captions."""
from tube import Caption
from typing import List, Optional
from tube.helpers import deprecated
from collections.abc import Mapping, Sequence


class StreamQuery(Sequence):
    """Interface for querying the available media streams."""

    def __init__(self, fmt_streams):
        """Construct a :class:`StreamQuery <StreamQuery>`.
        param list fmt_streams:
            list of :class:`Stream <Stream>` instances.
        """
        self.fmt_streams = fmt_streams
        self.itag_index = {int(s.itag): s for s in fmt_streams}


class CaptionQuery(Mapping):
    """Interface for querying the available captions."""

    def __init__(self, captions: List[Caption]):
        """Construct a :class:`Caption <Caption>`.
        param list captions:
            list of :class:`Caption <Caption>` instances.
        """
        self.lang_code_index = {c.code: c for c in captions}

    @deprecated(
        "This object can be treated as a dictionary, i.e. captions['en']"
    )
    def get_by_language_code(
        self, lang_code: str
    ) -> Optional[Caption]:  # pragma: no cover
        """Get the :class:`Caption <Caption>` for a given ``lang_code``.
        :param str lang_code:
            The code that identifies the caption language.
        :rtype: :class:`Caption <Caption>` or None
        :returns:
            The :class:`Caption <Caption>` matching the
            given ``lang_code`` or None if it does not exist.
        """
        return self.lang_code_index.get(lang_code)

    @deprecated("This object can be treated as a dictionary")
    def all(self) -> List[Caption]:  # pragma: no cover
        """Get all the results represented by this query as a list.
        :rtype: list
        """
        return list(self.lang_code_index.values())

    def __getitem__(self, i: str):
        return self.lang_code_index[i]

    def __len__(self) -> int:
        return len(self.lang_code_index)

    def __iter__(self):
        return iter(self.lang_code_index.values())

    def __repr__(self) -> str:
        return f"{self.lang_code_index}"
