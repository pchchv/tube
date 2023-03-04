"""Module to download a complete playlist from a youtube channel."""
from typing import Dict, Optional
from collections.abc import Sequence
from tube.helpers import install_proxy


class Playlist(Sequence):
    """Load a YouTube playlist with URL"""
    def __init__(self, url: str, proxies: Optional[Dict[str, str]] = None):
        if proxies:
            install_proxy(proxies)

        self._input_url = url

        # These need to be initialized as None for the properties.
        self._html = None
        self._ytcfg = None
        self._initial_data = None
        self._sidebar_info = None

        self._playlist_id = None
