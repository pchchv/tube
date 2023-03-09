import os
from unittest import mock
from datetime import datetime
from unittest.mock import MagicMock


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
