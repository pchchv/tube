"""
This module implements the basic developer interface for tube.
The problem domain of the :class:`YouTube <YouTube> class
focuses almost exclusively on the developer interface.
Tube offloads all the hard work to smaller peripheral modules and functions.

"""
import tube
from tube.query import StreamQuery
from tube.monostate import Monostate
from tube.innertube import InnerTube
from tube.helpers import install_proxy
from tube.metadata import YouTubeMetadata
from tube import Stream, extract, request
from typing import Optional, Callable, Any, Dict, List
from tube.exceptions import (
    TubeError,
    MembersOnly,
    ExtractError,
    VideoPrivate,
    LiveStreamError,
    VideoUnavailable,
    AgeRestrictedError,
    RecordingUnavailable
    )


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

    @property
    def watch_html(self):
        if self._watch_html:
            return self._watch_html
        self._watch_html = request.get(url=self.watch_url)
        return self._watch_html

    @property
    def embed_html(self):
        if self._embed_html:
            return self._embed_html
        self._embed_html = request.get(url=self.embed_url)
        return self._embed_html

    @property
    def age_restricted(self):
        if self._age_restricted:
            return self._age_restricted
        self._age_restricted = extract.is_age_restricted(self.watch_html)
        return self._age_restricted

    @property
    def js_url(self):
        if self._js_url:
            return self._js_url

        if self.age_restricted:
            self._js_url = extract.js_url(self.embed_html)
        else:
            self._js_url = extract.js_url(self.watch_html)

        return self._js_url

    @property
    def js(self):
        if self._js:
            return self._js

        # If the js_url does not match the cached url,
        # retrieve the new js and refresh the cache,
        # otherwise load the cache.
        if tube.__js_url__ != self.js_url:
            self._js = request.get(self.js_url)
            tube.__js__ = self._js
            tube.__js_url__ = self.js_url
        else:
            self._js = tube.__js__

        return self._js

    @property
    def initial_data(self):
        if self._initial_data:
            return self._initial_data
        self._initial_data = extract.initial_data(self.watch_html)
        return self._initial_data

    @property
    def streaming_data(self):
        """Return streamingData from video info."""
        if 'streamingData' in self.vid_info:
            return self.vid_info['streamingData']
        else:
            self.bypass_age_gate()
            return self.vid_info['streamingData']

    @property
    def fmt_streams(self):
        """Returns a list of threads if they have been initialized.
        If threads were not initialized,
        finds all relevant threads and initializes them.
        """
        self.check_availability()
        if self._fmt_streams:
            return self._fmt_streams

        self._fmt_streams = []

        stream_manifest = extract.apply_descrambler(self.streaming_data)

        try:
            extract.apply_signature(stream_manifest, self.vid_info, self.js)
        except ExtractError:
            # To force an update of the js-file, clear the cache and try again
            self._js = None
            self._js_url = None
            tube.__js__ = None
            tube.__js_url__ = None
            extract.apply_signature(stream_manifest, self.vid_info, self.js)

        # Create instances of :class:`Stream <Stream>`
        # Initialize stream objects
        for stream in stream_manifest:
            video = Stream(
                stream=stream,
                monostate=self.stream_monostate,
            )
            self._fmt_streams.append(video)

        self.stream_monostate.title = self.title
        self.stream_monostate.duration = self.length

        return self._fmt_streams

    def check_availability(self):
        """Check whether the video is available.
        Raises different exceptions based on why the video is unavailable,
        otherwise does nothing.
        """
        status, messages = extract.playability_status(self.watch_html)

        for reason in messages:
            if status == 'UNPLAYABLE':
                if reason == (
                    'Join this channel to get access to members-only content '
                    'like this video, and other exclusive perks.'
                ):
                    raise MembersOnly(video_id=self.video_id)
                elif reason == 'This live stream recording is not available.':
                    raise RecordingUnavailable(video_id=self.video_id)
                else:
                    raise VideoUnavailable(video_id=self.video_id)
            elif status == 'LOGIN_REQUIRED':
                if reason == (
                    'This is a private video. '
                    'Please sign in to verify that you may see it.'
                ):
                    raise VideoPrivate(video_id=self.video_id)
            elif status == 'ERROR':
                if reason == 'Video unavailable':
                    raise VideoUnavailable(video_id=self.video_id)
            elif status == 'LIVE_STREAM':
                raise LiveStreamError(video_id=self.video_id)

    @property
    def vid_info(self):
        """Parse the raw vid info and return the parsed result.
        :rtype: Dict[Any, Any]
        """
        if self._vid_info:
            return self._vid_info

        innertube = InnerTube(
            use_oauth=self.use_oauth, allow_cache=self.allow_oauth_cache)

        innertube_response = innertube.player(self.video_id)
        self._vid_info = innertube_response
        return self._vid_info

    def bypass_age_gate(self):
        """Attempt to update the vid_info by bypassing the age gate."""
        innertube = InnerTube(
            client='ANDROID_EMBED',
            use_oauth=self.use_oauth,
            allow_cache=self.allow_oauth_cache
        )
        innertube_response = innertube.player(self.video_id)
        playability_status =\
            innertube_response['playabilityStatus'].get('status', None)

        # If we still can't access the video,
        # raise an exception (tier 3 age restriction)
        if playability_status == 'UNPLAYABLE':
            raise AgeRestrictedError(self.video_id)

        self._vid_info = innertube_response

    @property
    def caption_tracks(self) -> List[tube.Caption]:
        """Get a list of :class:`Caption <Caption>`.
        :rtype: List[Caption]
        """
        raw_tracks = (
            self.vid_info.get("captions", {})
            .get("playerCaptionsTracklistRenderer", {})
            .get("captionTracks", [])
        )
        return [tube.Caption(track) for track in raw_tracks]

    @property
    def captions(self) -> tube.CaptionQuery:
        """Interface to query caption tracks.
        :rtype: :class:`CaptionQuery <CaptionQuery>`.
        """
        return tube.CaptionQuery(self.caption_tracks)

    @property
    def thumbnail_url(self) -> str:
        """Get the thumbnail url image.
        :rtype: str
        """
        thumbnail_details = (
            self.vid_info.get("videoDetails", {})
            .get("thumbnail", {})
            .get("thumbnails")
        )
        if thumbnail_details:
            thumbnail_details = thumbnail_details[-1]  # last item has max size
            return thumbnail_details["url"]

        return f"https://img.youtube.com/vi/{self.video_id}/maxresdefault.jpg"

    @property
    def publish_date(self):
        """Get the publish date.
        :rtype: datetime
        """
        if self._publish_date:
            return self._publish_date
        self._publish_date = extract.publish_date(self.watch_html)
        return self._publish_date

    @publish_date.setter
    def publish_date(self, value):
        """Sets the publish date."""
        self._publish_date = value

    @property
    def streams(self) -> StreamQuery:
        """Interface to query both adaptive (DASH) and progressive streams.
        :rtype: :class:`StreamQuery <StreamQuery>`.
        """
        self.check_availability()
        return StreamQuery(self.fmt_streams)

    @property
    def title(self) -> str:
        """Get the video title.
        :rtype: str
        """
        if self._title:
            return self._title

        try:
            self._title = self.vid_info['videoDetails']['title']
        except KeyError:
            # Check_availability will raise the correct exception in
            # most cases, if not, ask for a report.
            self.check_availability()
            raise TubeError(
                (
                    f'Exception when accessing the {self.watch_url} header. '
                    'Please send an error message to \
                        https://github.com/pchchv/tube.'
                )
            )

        return self._title

    @title.setter
    def title(self, value):
        """Sets the title value."""
        self._title = value

    @property
    def description(self) -> str:
        """Get the video description.
        :rtype: str
        """
        return self.vid_info.get("videoDetails", {}).get("shortDescription")

    @property
    def rating(self) -> float:
        """Get the video average rating.
        :rtype: float
        """
        return self.vid_info.get("videoDetails", {}).get("averageRating")

    @property
    def length(self) -> int:
        """Get the video length in seconds.
        :rtype: int
        """
        return int(self.vid_info.get('videoDetails', {}).get('lengthSeconds'))

    @property
    def views(self) -> int:
        """Get the number of the times the video has been viewed.
        :rtype: int
        """
        return int(self.vid_info.get("videoDetails", {}).get("viewCount"))

    @property
    def author(self) -> str:
        """Get the video author.
        :rtype: str
        """
        if self._author:
            return self._author
        self._author = self.vid_info.get("videoDetails", {}).get(
            "author", "unknown"
        )
        return self._author

    @author.setter
    def author(self, value):
        """Set the video author."""
        self._author = value

    @property
    def keywords(self) -> List[str]:
        """Get the video keywords.
        :rtype: List[str]
        """
        return self.vid_info.get('videoDetails', {}).get('keywords', [])

    @property
    def channel_id(self) -> str:
        """Get the video poster's channel id.
        :rtype: str
        """
        return self.vid_info.get('videoDetails', {}).get('channelId', None)

    @property
    def channel_url(self) -> str:
        """Construct the channel url for the video poster from the channel id.
        :rtype: str
        """
        return f'https://www.youtube.com/channel/{self.channel_id}'

    @property
    def metadata(self) -> Optional[YouTubeMetadata]:
        """Get the metadata for the video.
        :rtype: YouTubeMetadata
        """
        if self._metadata:
            return self._metadata
        else:
            self._metadata = extract.metadata(self.initial_data)
            return self._metadata

    def register_on_progress_callback(
            self,
            func: Callable[[Any, bytes, int], None]):
        """Register a download progress callback function post initialization.
        :param callable func:
            A callback function that takes ``stream``, ``chunk``,
            and ``bytes_remaining`` as parameters.
        :rtype: None
        """
        self.stream_monostate.on_progress = func

    def register_on_complete_callback(self,
                                      func: Callable[[Any, Optional[str]],
                                                     None]):
        """Register a download complete callback function post initialization.
        :param callable func:
            A callback function that takes ``stream`` and  ``file_path``.
        :rtype: None
        """
        self.stream_monostate.on_complete = func

