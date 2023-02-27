"""
This module contains a container for the stream manifest data.

Media stream container object (video only / audio only / video+audio
combined).
"""
from tube import extract
from math import ceil
from typing import Dict, Optional
from tube.monostate import Monostate
from tube.itags import get_format_profile


class Stream:
    """Container for stream manifest data."""

    def __init__(
        self, stream: Dict, monostate: Monostate
    ):
        """Construct a :class:`Stream <Stream>`.
        :param dict stream:
            The unscrambled data extracted from YouTube.
        :param dict monostate:
            Dictionary of data shared across all instances of
            :class:`Stream <Stream>`.
        """
        # Dictionary shared between all instances of :class:`Stream <Stream>`
        # (Borg pattern).
        self._monostate = monostate

        self.url = stream["url"]  # signed download url
        self.itag = int(
            stream["itag"]
        )  # stream format id (youtube nomenclature)

        # set type and codec info

        # 'video/webm; codecs="vp8, vorbis"' -> 'video/webm', ['vp8', 'vorbis']
        self.mime_type, self.codecs = extract.mime_type_codec(
            stream["mimeType"]
        )

        # 'video/webm' -> 'video', 'webm'
        self.type, self.subtype = self.mime_type.split("/")

        # ['vp8', 'vorbis'] -> video_codec: vp8, audio_codec: vorbis. DASH
        # streams return NoneType for audio/video depending.
        self.video_codec, self.audio_codec = self.parse_codecs()

        self.is_otf: bool = stream["is_otf"]
        self.bitrate: Optional[int] = stream["bitrate"]

        # filesize in bytes
        self._filesize: Optional[int] = int(stream.get('contentLength', 0))

        # filesize in kilobytes
        self._filesize_kb: Optional[float] = float(ceil(float(stream.get(
            'contentLength', 0)) / 1024 * 1000) / 1000
        )

        # filesize in megabytes
        self._filesize_mb: Optional[float] = float(ceil(float(stream.get(
            'contentLength', 0)) / 1024 / 1024 * 1000) / 1000
        )

        # filesize in gigabytes
        # (fingers crossed we don't need terabytes going forward though)
        self._filesize_gb: Optional[float] = float(ceil(float(stream.get(
            'contentLength', 0)) / 1024 / 1024 / 1024 * 1000) / 1000
        )

        # Additional information about the stream format, such as resolution,
        # frame rate, and whether the stream is live (HLS) or 3D.
        itag_profile = get_format_profile(self.itag)
        self.is_dash = itag_profile["is_dash"]
        self.abr = itag_profile["abr"]  # average bitrate (audio streams only)
        if 'fps' in stream:
            self.fps = stream['fps']  # Video streams only
        self.resolution = itag_profile[
            "resolution"
        ]  # resolution (e.g.: "480p")
        self.is_3d = itag_profile["is_3d"]
        self.is_hdr = itag_profile["is_hdr"]
        self.is_live = itag_profile["is_live"]
