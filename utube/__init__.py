# flake8: noqa: F401
"""
Utube: a lightweight dependency-free Python library and
command-line utility for downloading YouTube Videos

"""

__title__ = "utube"
__author__ = "Evgenii Pochechuev"
__email__ = "ipchchv@gmail.com"
__license__ = "Apache-2.0 license"
__js__ = None
__js_url__ = None

from utube.search import Search
from utube.streams import Stream
from utube.channel import Channel
from utube.__main__ import YouTube
from utube.captions import Caption
from utube.playlist import Playlist
from utube.version import __version__
from utube.query import CaptionQuery, StreamQuery
