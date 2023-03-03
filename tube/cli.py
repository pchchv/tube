"""A simple command line application to download youtube videos."""
import sys
import shutil
import argparse
from typing import List, Optional
from tube import __version__, Stream


def _parse_args(
    parser: argparse.ArgumentParser, args: Optional[List] = None
) -> argparse.Namespace:
    parser.add_argument(
        "url", help="The YouTube /watch or /playlist url", nargs="?"
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s " + __version__,
    )
    parser.add_argument(
        "--itag", type=int, help="The itag for the desired stream",
    )
    parser.add_argument(
        "-r",
        "--resolution",
        type=str,
        help="The resolution for the desired stream",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help=(
            "The list option causes tube cli to return a list of streams "
            "available to download"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        dest="verbose",
        help="Set logger output to verbose output.",
    )
    parser.add_argument(
        "--logfile",
        action="store",
        help="logging debug and error messages into a log file",
    )
    parser.add_argument(
        "--build-playback-report",
        action="store_true",
        help="Save the html and js to disk",
    )
    parser.add_argument(
        "-c",
        "--caption-code",
        type=str,
        help=(
            "Download srt captions for given language code. "
            "Prints available language codes if no argument given"
        ),
    )
    parser.add_argument(
        '-lc',
        '--list-captions',
        action='store_true',
        help=(
            "List available caption codes for a video"
        )
    )
    parser.add_argument(
        "-t",
        "--target",
        help=(
            "The output directory for the downloaded stream. "
            "Default is current working directory"
        ),
    )
    parser.add_argument(
        "-a",
        "--audio",
        const="mp4",
        nargs="?",
        help=(
            "Download the audio for a given URL at \
                the highest bitrate available"
            "Defaults to mp4 format if none is specified"
        ),
    )
    parser.add_argument(
        "-f",
        "--ffmpeg",
        const="best",
        nargs="?",
        help=(
            "Downloads the audio and video stream for resolution provided"
            "If no resolution is provided, downloads the best resolution"
            "Runs the command line program ffmpeg to \
                combine the audio and video"
        ),
    )

    return parser.parse_args(args)


def display_progress_bar(
    bytes_received: int, filesize: int, ch: str = "█", scale: float = 0.55
) -> None:
    """Display a simple, pretty progress bar.
    Example:
    ~~~~~~~~
    PSY - GANGNAM STYLE(강남스타일) MV.mp4
    ↳ |███████████████████████████████████████| 100.0%
    :param int bytes_received:
        The delta between the total file size (bytes) and bytes already
        written to disk.
    :param int filesize:
        File size of the media stream in bytes.
    :param str ch:
        Character to use for presenting progress segment.
    :param float scale:
        Scale multiplier to reduce progress bar size.
    """
    columns = shutil.get_terminal_size().columns
    max_width = int(columns * scale)

    filled = int(round(max_width * bytes_received / float(filesize)))
    remaining = max_width - filled
    progress_bar = ch * filled + " " * remaining
    percent = round(100.0 * bytes_received / float(filesize), 1)
    text = f" ↳ |{progress_bar}| {percent}%\r"
    sys.stdout.write(text)
    sys.stdout.flush()


# noinspection PyUnusedLocal
def on_progress(
    stream: Stream, chunk: bytes, bytes_remaining: int
) -> None:  # pylint: disable=W0613
    filesize = stream.filesize
    bytes_received = filesize - bytes_remaining
    display_progress_bar(bytes_received, filesize)


def _download(
    stream: Stream,
    target: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    filesize_megabytes = stream.filesize // 1048576
    print(f"{filename or stream.default_filename} | {filesize_megabytes} MB")
    file_path = stream.get_file_path(filename=filename, output_path=target)
    if stream.exists_at_path(file_path):
        print(f"Already downloaded at:\n{file_path}")
        return

    stream.download(output_path=target, filename=filename)
    sys.stdout.write("\n")
