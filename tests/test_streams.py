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
