import os
from unittest import mock
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
