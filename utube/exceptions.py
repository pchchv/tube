"""Library specific exception definitions."""
from typing import Pattern, Union


class UtubeError(Exception):
    """The basic utube exception that all others inherit.
    This is done to avoid contaminating the built-in exceptions,
    which *could* lead to unintended errors being handled unexpectedly and
    incorrectly in the executor's code.
    """


class ExtractError(UtubeError):
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


class HTMLParseError(UtubeError):
    """HTML could not be parsed"""


class VideoUnavailable(UtubeError):
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


class MembersOnly(VideoUnavailable):
    """Video is members-only.
    YouTube has special videos that are only viewable to
    users who have subscribed to a content creator.
    """
    def __init__(self, video_id: str):
        """
        :param str video_id:
            A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f'{self.video_id} is a members-only video'


class RecordingUnavailable(VideoUnavailable):
    def __init__(self, video_id: str):
        """
        :param str video_id: A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f'{self.video_id} \
            does not have a live stream recording available'


class VideoPrivate(VideoUnavailable):
    def __init__(self, video_id: str):
        """
        :param str video_id: A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f'{self.video_id} is a private video'


class AgeRestrictedError(VideoUnavailable):
    """Video is age restricted, and cannot be accessed without OAuth."""
    def __init__(self, video_id: str):
        """
        :param str video_id: A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f"{self.video_id} is age restricted, \
            and can't be accessed without logging in."


class MaxRetriesExceeded(UtubeError):
    """Maximum number of retries exceeded."""


class VideoRegionBlocked(VideoUnavailable):
    def __init__(self, video_id: str):
        """
        :param str video_id: A YouTube video identifier.
        """
        self.video_id = video_id
        super().__init__(self.video_id)

    @property
    def error_string(self):
        return f'{self.video_id} is not available in your region'
