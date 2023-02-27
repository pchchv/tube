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
