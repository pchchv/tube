# flake8: noqa: F401
"""
Utub3: a lightweight dependency-free Python library and
command-line utility for downloading YouTube Videos

"""

__title__ = "utub3"
__author__ = "Evgenii Pochechuev"
__email__ = "ipchchv@gmail.com"
__license__ = "Apache-2.0 license"
__js__ = None
__js_url__ = None

from utub3.search import Search
from utub3.streams import Stream
from utub3.channel import Channel
from utub3.__main__ import YouTube
from utub3.captions import Caption
from utub3.playlist import Playlist
from utub3.version import __version__
from utub3.query import CaptionQuery, StreamQuery
