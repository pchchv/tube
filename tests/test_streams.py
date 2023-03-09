import os
import random
from unittest import mock
from datetime import datetime
from utub3 import request, Stream
from unittest.mock import MagicMock, Mock


@mock.patch("utub3.streams.request")
def test_stream_to_buffer(mock_request, cipher_signature):
    # Given
    stream_bytes = iter(
        [
            bytes(os.urandom(8 * 1024)),
            bytes(os.urandom(8 * 1024)),
            bytes(os.urandom(8 * 1024)),
        ]
    )
    mock_request.stream.return_value = stream_bytes
    buffer = MagicMock()
    # When
    cipher_signature.streams[0].stream_to_buffer(buffer)
    # Then
    assert buffer.write.call_count == 3


def test_filesize(cipher_signature):
    assert cipher_signature.streams[0].filesize == 3399554


def test_filesize_kb(cipher_signature):
    assert cipher_signature.streams[0].filesize_kb == float(3319.877)


def test_filesize_mb(cipher_signature):
    assert cipher_signature.streams[0].filesize_mb == float(3.243)


def test_filesize_gb(cipher_signature):
    assert cipher_signature.streams[0].filesize_gb == float(0.004)


def test_filesize_approx(cipher_signature):
    stream = cipher_signature.streams[0]

    assert stream.filesize_approx == 3403320
    stream.bitrate = None
    assert stream.filesize_approx == 3399554


def test_default_filename(cipher_signature):
    expected = "YouTube Rewind 2019 For the Record  YouTubeRewind.3gpp"
    stream = cipher_signature.streams[0]
    assert stream.default_filename == expected


def test_title(cipher_signature):
    expected = "YouTube Rewind 2019: For the Record | #YouTubeRewind"
    assert cipher_signature.title == expected


def test_expiration(cipher_signature):
    assert cipher_signature.streams[0].expiration >= datetime(2020, 10, 30, 5, 39, 41)


def test_caption_tracks(presigned_video):
    assert len(presigned_video.caption_tracks) == 13


def test_captions(presigned_video):
    assert len(presigned_video.captions) == 13


def test_description(cipher_signature):
    expected = (
        "In 2018, we made something you didn’t like. "
        "For Rewind 2019, let’s see what you DID like.\n\n"
        "Celebrating the creators, music and moments "
        "that mattered most to you in 2019. \n\n"
        "To learn how the top lists in Rewind were generated: "
        "https://rewind.youtube/about\n\n"
        "Top lists featured the following channels:\n\n"
        "@1MILLION Dance Studio \n@A4 \n@Anaysa \n"
        "@Andymation \n@Ariana Grande \n@Awez Darbar \n"
        "@AzzyLand \n@Billie Eilish \n@Black Gryph0n \n"
        "@BLACKPINK \n@ChapkisDanceUSA \n@Daddy Yankee \n"
        "@David Dobrik \n@Dude Perfect \n@Felipe Neto \n"
        "@Fischer's-フィッシャーズ- \n@Galen Hooks \n@ibighit \n"
        "@James Charles \n@jeffreestar \n@Jelly \n@Kylie Jenner \n"
        "@LazarBeam \n@Lil Dicky \n@Lil Nas X \n@LOUD \n@LOUD Babi \n"
        "@LOUD Coringa \n@Magnet World \n@MrBeast \n"
        "@Nilson Izaias Papinho Oficial \n@Noah Schnapp\n"
        "@백종원의 요리비책 Paik's Cuisine \n@Pencilmation \n@PewDiePie \n"
        "@SethEverman \n@shane \n@Shawn Mendes \n@Team Naach \n"
        "@whinderssonnunes \n@워크맨-Workman \n@하루한끼 one meal a day \n\n"
        "To see the full list of featured channels in Rewind 2019, "
        "visit: https://rewind.youtube/about"
    )
    assert cipher_signature.description == expected


def test_rating(cipher_signature):
    """Test the rating value of a YouTube object.
    This changes each time we rebuild the json files, so we want to use
    an estimate of where it will be. The two values seen to make this
    estimate were 2.073431 and 2.0860765. This represents a range of
    ~0.007 below and ~0.006 above 2.08. Allowing for up to 0.02 in either
    direction should provide a steady indicator of correctness.
    """
    assert abs(cipher_signature.rating - 2.08) < 0.02


def test_length(cipher_signature):
    assert cipher_signature.length == 337


def test_views(cipher_signature):
    assert cipher_signature.views >= 108531745


@mock.patch(
    "utub3.request.head", MagicMock(return_value={"content-length": "6796391"})
)
@mock.patch(
    "utub3.request.stream",
    MagicMock(return_value=iter([str(random.getrandbits(8 * 1024))])),
)
def test_download(cipher_signature):
    with mock.patch("utub3.streams.open", mock.mock_open(), create=True):
        stream = cipher_signature.streams[0]
        stream.download()


@mock.patch(
    "utub3.request.head", MagicMock(return_value={"content-length": "16384"})
)
@mock.patch(
    "utub3.request.stream",
    MagicMock(return_value=iter([str(random.getrandbits(8 * 1024))])),
)
@mock.patch("utub3.streams.target_directory", MagicMock(return_value="/target"))
def test_download_with_prefix(cipher_signature):
    with mock.patch("utub3.streams.open", mock.mock_open(), create=True):
        stream = cipher_signature.streams[0]
        file_path = stream.download(filename_prefix="prefix")
        assert file_path == os.path.join(
            "/target",
            "prefixYouTube Rewind 2019 For the Record  YouTubeRewind.3gpp"
        )


@mock.patch(
    "utub3.request.head", MagicMock(return_value={"content-length": "16384"})
)
@mock.patch(
    "utub3.request.stream",
    MagicMock(return_value=iter([str(random.getrandbits(8 * 1024))])),
)
@mock.patch("utub3.streams.target_directory", MagicMock(return_value="/target"))
def test_download_with_filename(cipher_signature):
    with mock.patch("utub3.streams.open", mock.mock_open(), create=True):
        stream = cipher_signature.streams[0]
        file_path = stream.download(filename="cool name bro")
        assert file_path == os.path.join(
            "/target",
            "cool name bro"
        )


@mock.patch(
    "utub3.request.head", MagicMock(return_value={"content-length": "16384"})
)
@mock.patch(
    "utub3.request.stream",
    MagicMock(return_value=iter([str(random.getrandbits(8 * 1024))])),
)
@mock.patch("utub3.streams.target_directory", MagicMock(return_value="/target"))
@mock.patch("os.path.isfile", MagicMock(return_value=True))
def test_download_with_existing(cipher_signature):
    with mock.patch("utub3.streams.open", mock.mock_open(), create=True):
        stream = cipher_signature.streams[0]
        os.path.getsize = Mock(return_value=stream.filesize)
        file_path = stream.download()
        assert file_path == os.path.join(
            "/target",
            "YouTube Rewind 2019 For the Record  YouTubeRewind.3gpp"
        )
        assert not request.stream.called


@mock.patch(
    "utub3.request.head", MagicMock(return_value={"content-length": "16384"})
)
@mock.patch(
    "utub3.request.stream",
    MagicMock(return_value=iter([str(random.getrandbits(8 * 1024))])),
)
@mock.patch("utub3.streams.target_directory", MagicMock(return_value="/target"))
@mock.patch("os.path.isfile", MagicMock(return_value=True))
def test_download_with_existing_no_skip(cipher_signature):
    with mock.patch("utub3.streams.open", mock.mock_open(), create=True):
        stream = cipher_signature.streams[0]
        os.path.getsize = Mock(return_value=stream.filesize)
        file_path = stream.download(skip_existing=False)
        assert file_path == os.path.join(
            "/target",
            "YouTube Rewind 2019 For the Record  YouTubeRewind.3gpp"
        )
        assert request.stream.called


def test_progressive_streams_return_includes_audio_track(cipher_signature):
    stream = cipher_signature.streams.filter(progressive=True)[0]
    assert stream.includes_audio_track


def test_progressive_streams_return_includes_video_track(cipher_signature):
    stream = cipher_signature.streams.filter(progressive=True)[0]
    assert stream.includes_video_track


@mock.patch(
    "utub3.request.head", MagicMock(return_value={"content-length": "16384"})
)
@mock.patch(
    "utub3.request.stream",
    MagicMock(return_value=iter([str(random.getrandbits(8 * 1024))])),
)
def test_on_progress_hook(cipher_signature):
    callback_fn = mock.MagicMock()
    cipher_signature.register_on_progress_callback(callback_fn)

    with mock.patch("utub3.streams.open", mock.mock_open(), create=True):
        stream = cipher_signature.streams[0]
        stream.download()
    assert callback_fn.called
    args, _ = callback_fn.call_args
    assert len(args) == 3
    stream, _, _ = args
    assert isinstance(stream, Stream)


@mock.patch(
    "utub3.request.head", MagicMock(return_value={"content-length": "16384"})
)
@mock.patch(
    "utub3.request.stream",
    MagicMock(return_value=iter([str(random.getrandbits(8 * 1024))])),
)
def test_on_complete_hook(cipher_signature):
    callback_fn = mock.MagicMock()
    cipher_signature.register_on_complete_callback(callback_fn)

    with mock.patch("utub3.streams.open", mock.mock_open(), create=True):
        stream = cipher_signature.streams[0]
        stream.download()
    assert callback_fn.called
