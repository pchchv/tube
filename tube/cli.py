"""A simple command line application to download youtube videos."""
import argparse
from tube import __version__
from typing import List, Optional


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
