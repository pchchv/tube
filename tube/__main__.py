"""
This module implements the basic developer interface for tube.
The problem domain of the :class:`YouTube <YouTube> class
focuses almost exclusively on the developer interface.
Tube offloads all the hard work to smaller peripheral modules and functions.

"""
from tube import Stream, extract
from tube.monostate import Monostate
from tube.helpers import install_proxy
from tube.metadata import YouTubeMetadata
from typing import Optional, Callable, Any, Dict, List


class YouTube:
    """Core developer interface for tube."""

    def __init__(
        self,
        url: str,
        on_progress_callback:
        Optional[Callable[[Any, bytes, int], None]] = None,
        on_complete_callback:
        Optional[Callable[[Any, Optional[str]], None]] = None,
        proxies: Dict[str, str] = None,
        use_oauth: bool = False,
        allow_oauth_cache: bool = True
    ):
        """Create :class:`YouTube <YouTube>`.
        :param str url: The actual URL of the YouTube viewer.
        :param func on_progress_callback:
            (Optional) User-defined callback function for
            stream loading events progress events.
        :param func on_complete_callback:
            (Optional) User-defined callback function for
            flow loading progress events completion events.
        :param dict proxies:
            (Optional) Matching protocol and
            proxy address to be used by tube.
        :param bool use_oauth:
            (Optional) Invite the user to authenticate to YouTube.
            If allow_oauth_cache is set to True,
            the user will be asked to authenticate only once.
        :param bool allow_oauth_cache:
            (Optional) Cache OAuth tokens locally on the machine.
            The default setting is True.
            These tokens are generated only if
            the use_oauth parameter is also set to True.
        """
        # js fetched by js_url
        self._js: Optional[str] = None
        # the url to the js, parsed from watch html
        self._js_url: Optional[str] = None

        # content fetched from innertube/player
        self._vid_info: Optional[Dict] = None

        # the html of /watch?v=<video_id>
        self._watch_html: Optional[str] = None
        self._embed_html: Optional[str] = None
        # inline js in the html containing
        self._player_config_args: Optional[Dict] = None
        self._age_restricted: Optional[bool] = None

        self._fmt_streams: Optional[List[Stream]] = None

        self._initial_data = None
        self._metadata: Optional[YouTubeMetadata] = None

        # video_id part of /watch?v=<video_id>
        self.video_id = extract.video_id(url)

        self.watch_url = f"https://youtube.com/watch?v={self.video_id}"
        self.embed_url = f"https://www.youtube.com/embed/{self.video_id}"

        # Shared between all instances of `Stream` (Borg pattern).
        self.stream_monostate = Monostate(
            on_progress=on_progress_callback, on_complete=on_complete_callback
        )

        if proxies:
            install_proxy(proxies)

        self._author = None
        self._title = None
        self._publish_date = None

        self.use_oauth = use_oauth
        self.allow_oauth_cache = allow_oauth_cache

    def __repr__(self):
        return f'<tube.__main__.YouTube object: videoId={self.video_id}>'

    def __eq__(self, obj: object) -> bool:
        # Compare types and urls, if they are the same,
        # return true,
        # else return false.
        return type(obj) == type(self) and obj.watch_url == self.watch_url
