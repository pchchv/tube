"""Library specific exception definitions."""
from typing import Pattern, Union


class TubeError(Exception):
    """The basic tube exception that all others inherit.
    This is done to avoid contaminating the built-in exceptions,
    which *could* lead to unintended errors being handled unexpectedly and
    incorrectly in the executor's code.
    """


class ExtractError(TubeError):
    """Data extraction based exception."""


class RegexMatchError(ExtractError):
    """Regex pattern did not return any matches."""

    def __init__(self, caller: str, pattern: Union[str, Pattern]):
        """
        :param str caller:
            Calling function
        :param str pattern:
            Pattern that failed to match
        """
        super().__init__(f"{caller}: could not find match for {pattern}")
        self.caller = caller
        self.pattern = pattern


class HTMLParseError(TubeError):
    """HTML could not be parsed"""


class VideoUnavailable(TubeError):
    """Base video unavailable error."""
    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.error_string)

    @property
    def error_string(self):
        return f'{self.video_id} is unavailable'


class LiveStreamError(VideoUnavailable):
    """Video is a live stream."""
    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f'{self.video_id} is streaming live and cannot be loaded'
