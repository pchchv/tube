# flake8: noqa: F401
"""
Tube: a lightweight dependency-free Python library and
command-line utility for downloading YouTube Videos

"""

__title__ = "tube"
__author__ = "Evgenii Pochechuev"
__email__ = "ipchchv@gmail.com"
__license__ = "Apache-2.0 license"

from tube.streams import Stream
from tube.captions import Caption
from tube.__main__ import YouTube
from tube.version import __version__
from tube.query import CaptionQuery, StreamQuery