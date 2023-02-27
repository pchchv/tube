"""
This module contains a container for the stream manifest data.

Media stream container object (video only / audio only / video+audio
combined).
"""
import os
import logging
import datetime
from math import ceil
from urllib import HTTPError
from urllib.parse import parse_qs
from tube import extract, request
from tube.monostate import Monostate
from tube.itags import get_format_profile
from typing import Dict, Optional, Tuple, BinaryIO
from tube.helpers import safe_filename, target_directory


logger = logging.getLogger(__name__)


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

    @property
    def is_adaptive(self) -> bool:
        """Whether the stream is DASH.
        :rtype: bool
        """
        # if codecs has two elements (e.g.: ['vp8', 'vorbis']): 2 % 2 = 0
        # if codecs has one element (e.g.: ['vp8']) 1 % 2 = 1
        return bool(len(self.codecs) % 2)

    @property
    def is_progressive(self) -> bool:
        """Whether the stream is progressive.
        :rtype: bool
        """
        return not self.is_adaptive

    @property
    def includes_audio_track(self) -> bool:
        """Whether the stream only contains audio.
        :rtype: bool
        """
        return self.is_progressive or self.type == "audio"

    @property
    def includes_video_track(self) -> bool:
        """Whether the stream only contains video.
        :rtype: bool
        """
        return self.is_progressive or self.type == "video"

    def parse_codecs(self) -> Tuple[Optional[str], Optional[str]]:
        """Get video/audio codecs from codec list.
        Parses the list of codecs of variable length and returns a
        constant tuple of two elements, where video codec is
        the first element and audio is the second.
        Returns None if no codec is available (adaptive only).
        :rtype: tuple
        :return: A tuple of two elements with audio and video codecs.
        """
        video = None
        audio = None
        if not self.is_adaptive:
            video, audio = self.codecs
        elif self.includes_video_track:
            video = self.codecs[0]
        elif self.includes_audio_track:
            audio = self.codecs[0]
        return video, audio

    @property
    def filesize(self) -> int:
        """File size of the media stream in bytes.
        :rtype: int
        :returns: Filesize (in bytes) of the stream.
        """
        if self._filesize == 0:
            try:
                self._filesize = request.filesize(self.url)
            except HTTPError as e:
                if e.code != 404:
                    raise
                self._filesize = request.seq_filesize(self.url)
        return self._filesize

    @property
    def filesize_kb(self) -> float:
        """File size of the media stream in kilobytes.
        :rtype: float
        :returns: Rounded filesize (in kilobytes) of the stream.
        """
        if self._filesize_kb == 0:
            try:
                self._filesize_kb = float(
                    ceil(request.filesize(self.url)/1024 * 1000) / 1000)
            except HTTPError as e:
                if e.code != 404:
                    raise
                self._filesize_kb = float(
                    ceil(request.seq_filesize(self.url)/1024 * 1000) / 1000)
        return self._filesize_kb

    @property
    def filesize_mb(self) -> float:
        """File size of the media stream in megabytes.
        :rtype: float
        :returns: Rounded filesize (in megabytes) of the stream.
        """
        if self._filesize_mb == 0:
            try:
                self._filesize_mb = float(
                    ceil(request
                         .filesize(self.url)/1024/1024 * 1000) / 1000)
            except HTTPError as e:
                if e.code != 404:
                    raise
                self._filesize_mb = float(
                    ceil(request
                         .seq_filesize(self.url)/1024/1024 * 1000) / 1000)
        return self._filesize_mb

    @property
    def filesize_gb(self) -> float:
        """File size of the media stream in gigabytes.
        :rtype: float
        :returns: Rounded filesize (in gigabytes) of the stream.
        """
        if self._filesize_gb == 0:
            try:
                self._filesize_gb = float(
                    ceil(request
                         .filesize(self.url)/1024/1024/1024 * 1000) / 1000)
            except HTTPError as e:
                if e.code != 404:
                    raise
                self._filesize_gb = float(
                    ceil(request
                         .seq_filesize(self.url)/1024/1024/1024 * 1000) / 1000)
        return self._filesize_gb

    @property
    def title(self) -> str:
        """Get title of video
        :rtype: str
        :returns: Youtube video title
        """
        return self._monostate.title or "Unknown YouTube Video Title"

    @property
    def filesize_approx(self) -> int:
        """Get approximate filesize of the video
        Falls back to HTTP call if there is
        not sufficient information to approximate
        :rtype: int
        :returns: size of video in bytes
        """
        if self._monostate.duration and self.bitrate:
            bits_in_byte = 8
            return int(
                (self._monostate.duration * self.bitrate) / bits_in_byte
            )

        return self.filesize

    @property
    def expiration(self) -> datetime:
        expire = parse_qs(self.url.split("?")[1])["expire"][0]
        return datetime.utcfromtimestamp(int(expire))

    @property
    def default_filename(self) -> str:
        """Generate filename based on the video title.
        :rtype: str
        :returns:
            An os file system compatible filename.
        """
        filename = safe_filename(self.title)
        return f"{filename}.{self.subtype}"

    def download(
        self,
        output_path: Optional[str] = None,
        filename: Optional[str] = None,
        filename_prefix: Optional[str] = None,
        skip_existing: bool = True,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = 0
    ) -> str:
        """Write the media stream to disk.
    :param output_path: (optional) The output path for writing the media file.
        If it is not specified,
        the current working directory is used by default.
    :type output_path: str or None
    :param filename: (optional) The name of the output file
        (stem only) for media file recording.
        If no name is specified, the default name is used.
    :type filename: str or None
    :param filename_prefix: (optional) The string to be added to the filename.
        For example, a number in a playlist or a series name.
        If no string is specified, nothing will be added.
        This parameter is separate from the filename,
        so you can use the default filename but add a prefix.
    :type filename_prefix: str or None
    :param skip_existing: (optional) Skip existing files, defaults to True
    :type skip_existing: bool
    :param timeout: (Optional) Request timeout time in seconds.
        The system default is used.
    :type timeout: int
    :param max_retries: (optional) The number of retries after a
        socket timeout. Defaults to 0.
    :type max_retries: int
    :return: The path to the stored video.
    :rtype: str
        """
        file_path = self.get_file_path(
            filename=filename,
            output_path=output_path,
            filename_prefix=filename_prefix,
        )

        if skip_existing and self.exists_at_path(file_path):
            logger.debug(f'file {file_path} already exists, skipping')
            self.on_complete(file_path)
            return file_path

        bytes_remaining = self.filesize
        logger.debug(
            f'downloading ({self.filesize} total bytes) file to {file_path}')

        with open(file_path, "wb") as fh:
            try:
                for chunk in request.stream(
                    self.url,
                    timeout=timeout,
                    max_retries=max_retries
                ):
                    # reduce the remainder (bytes) by the chunk length.
                    bytes_remaining -= len(chunk)
                    # send to the on_progress callback.
                    self.on_progress(chunk, fh, bytes_remaining)
            except HTTPError as e:
                if e.code != 404:
                    raise
                # Some adaptive threads must be queried with ordinal numbers
                for chunk in request.seq_stream(
                    self.url,
                    timeout=timeout,
                    max_retries=max_retries
                ):
                    # reduce the remainder (bytes) by the chunk length.
                    bytes_remaining -= len(chunk)
                    # send to the on_progress callback.
                    self.on_progress(chunk, fh, bytes_remaining)
        self.on_complete(file_path)
        return file_path

    def get_file_path(
        self,
        filename: Optional[str] = None,
        output_path: Optional[str] = None,
        filename_prefix: Optional[str] = None,
    ) -> str:
        if not filename:
            filename = self.default_filename
        if filename_prefix:
            filename = f"{filename_prefix}{filename}"
        return os.path.join(target_directory(output_path), filename)

    def exists_at_path(self, file_path: str) -> bool:
        return (
            os.path.isfile(file_path)
            and os.path.getsize(file_path) == self.filesize
        )

    def stream_to_buffer(self, buffer: BinaryIO) -> None:
        """Write the media stream to buffer
        :rtype: io.BytesIO buffer
        """
        bytes_remaining = self.filesize
        logger.info(
            "downloading (%s total bytes) file to buffer", self.filesize,
        )

        for chunk in request.stream(self.url):
            # reduce the (bytes) remainder by the length of the chunk
            bytes_remaining -= len(chunk)
            # send to the on_progress callback
            self.on_progress(chunk, buffer, bytes_remaining)
        self.on_complete(None)

    def on_progress(
        self, chunk: bytes, file_handler: BinaryIO, bytes_remaining: int
    ):
        """The callback function at runtime.
        This function writes binary data to a file,
        then checks to see if an additional callback is defined in monostate.
        This is expanded to display a runtime indicator.
            :param bytes Chunk: The binary data segment of
                the media file not yet written to disk.
            :param file_handler: The file handler where the
                media file is written to.
            :type file_handler:
                :py:class:`io.BufferedWriter`.
            :param int bytes_remaining: The delta between the
                total file size in bytes and the amount already loaded.
            :rtype: None
        """
        file_handler.write(chunk)
        logger.debug("download remaining: %s", bytes_remaining)
        if self._monostate.on_progress:
            self._monostate.on_progress(self, chunk, bytes_remaining)

    def on_complete(self, file_path: Optional[str]):
        """When loaded, the full handler function.
        :param file_path:
            The name of the file where the media file is written to.
        :type file_path: str
        :rtype: None
        """
        logger.debug("download finished")
        on_complete = self._monostate.on_complete
        if on_complete:
            logger.debug("calling on_complete callback %s", on_complete)
            on_complete(self, file_path)
