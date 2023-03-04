"""Module to download a complete playlist from a youtube channel."""
import json
import logging
from tube import request
from collections.abc import Sequence
from tube.helpers import install_proxy
from typing import Dict, Optional, Iterable, List
from tube.extract import playlist_id, get_ytcfg, initial_data


logger = logging.getLogger(__name__)


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

    @property
    def html(self):
        """Get the playlist page html.
        :rtype: str
        """
        if self._html:
            return self._html
        self._html = request.get(self.playlist_url)
        return self._html

    @property
    def ytcfg(self):
        """Extract the ytcfg from the playlist page html.
        :rtype: dict
        """
        if self._ytcfg:
            return self._ytcfg
        self._ytcfg = get_ytcfg(self.html)
        return self._ytcfg

    @property
    def initial_data(self):
        """Extract the initial data from the playlist page html.
        :rtype: dict
        """
        if self._initial_data:
            return self._initial_data
        else:
            self._initial_data = initial_data(self.html)
            return self._initial_data

    @property
    def sidebar_info(self):
        """Extract the sidebar info from the playlist page html.
        :rtype: dict
        """
        if self._sidebar_info:
            return self._sidebar_info
        else:
            self._sidebar_info = self.initial_data['sidebar'][
                'playlistSidebarRenderer']['items']
            return self._sidebar_info

    @property
    def yt_api_key(self):
        """Extract the INNERTUBE_API_KEY from the playlist ytcfg.
        :rtype: str
        """
        return self.ytcfg['INNERTUBE_API_KEY']

    @property
    def owner_url(self):
        """Create the channel url of the owner of the playlist.
        :return: Playlist owner's channel url.
        :rtype: str
        """
        return f'https://www.youtube.com/channel/{self.owner_id}'

    def _paginate(
        self, until_watch_id: Optional[str] = None
    ) -> Iterable[List[str]]:
        """Parse the video links from the page source,
        yields the /watch?v= part from video link
        :param until_watch_id Optional[str]:
            YouTube Video watch id until which the playlist should be read.
        :rtype: Iterable[List[str]]
        :returns: Iterable of lists of YouTube watch ids
        """
        videos_urls, continuation = self._extract_videos(
            json.dumps(initial_data(self.html))
        )
        if until_watch_id:
            try:
                trim_index = videos_urls.index(f"/watch?v={until_watch_id}")
                yield videos_urls[:trim_index]
                return
            except ValueError:
                pass
        yield videos_urls

        # Extract from a playlist only returns 100 videos at a time,
        # if self._extract_videos returns a continue,
        # there are more than 100 songs inside a playlist,
        # so need to add further requests to gather all of them
        if continuation:
            load_more_url, headers, data = self._build_continuation_url(
                continuation)
        else:
            load_more_url, headers, data = None, None, None

        while load_more_url and headers and data:  # there is an url found
            logger.debug("load more url: %s", load_more_url)
            # requesting the next video page with the url generated from
            # the previous page must be a post
            req = request.post(load_more_url, extra_headers=headers, data=data)
            # extract up to 100 songs from the page loaded
            # returns another continuation if more videos are available
            videos_urls, continuation = self._extract_videos(req)
            if until_watch_id:
                try:
                    trim_index = videos_urls.index(
                        f"/watch?v={until_watch_id}")
                    yield videos_urls[:trim_index]
                    return
                except ValueError:
                    pass
            yield videos_urls

            if continuation:
                load_more_url, headers, data = self._build_continuation_url(
                    continuation
                )
            else:
                load_more_url, headers, data = None, None, None

    @staticmethod
    def _video_url(watch_path: str):
        return f"https://www.youtube.com{watch_path}"
