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

    @property
    def playlist_id(self):
        """Get the playlist id.
        :rtype: str
        """
        if self._playlist_id:
            return self._playlist_id
        self._playlist_id = playlist_id(self._input_url)
        return self._playlist_id

    @property
    def playlist_url(self):
        """Get the base playlist url.
        :rtype: str
        """
        return f"https://www.youtube.com/playlist?list={self.playlist_id}"
