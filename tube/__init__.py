# flake8: noqa: F401
"""
Tube: a lightweight dependency-free Python library and
command-line utility for downloading YouTube Videos

"""

__title__ = "tube"
__author__ = "Evgenii Pochechuev"
__email__ = "ipchchv@gmail.com"
__license__ = "Apache-2.0 license"
__js__ = None
__js_url__ = None

from tube.search import Search
from tube.streams import Stream
from tube.channel import Channel
from tube.__main__ import YouTube
from tube.captions import Caption
from tube.playlist import Playlist
from tube.version import __version__
from tube.query import CaptionQuery, StreamQuery
