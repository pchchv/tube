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
