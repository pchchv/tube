import argparse
from utub3 import Caption, CaptionQuery, cli

def test_print_available_captions(capsys):
    # Given
    caption1 = Caption(
        {"url": "url1", "name": {"simpleText": "name1"}, "languageCode": "en", "vssId": ".en"}
    )
    caption2 = Caption(
        {"url": "url2", "name": {"simpleText": "name2"}, "languageCode": "fr", "vssId": ".fr"}
    )
    query = CaptionQuery([caption1, caption2])
    # When
    cli._print_available_captions(query)
    # Then
    captured = capsys.readouterr()
    assert captured.out == "Available caption codes are: en, fr\n"


def test_display_progress_bar(capsys):
    cli.display_progress_bar(bytes_received=25, filesize=100, scale=0.55)
    out, _ = capsys.readouterr()
    assert "25.0%" in out


def test_parse_args_falsey():
    parser = argparse.ArgumentParser()
    args = cli._parse_args(parser, ["http://youtube.com/watch?v=9bZkp7q19f0"])
    assert args.url == "http://youtube.com/watch?v=9bZkp7q19f0"
    assert args.build_playback_report is False
    assert args.itag is None
    assert args.list is False
    assert args.verbose is False


def test_parse_args_truthy():
    parser = argparse.ArgumentParser()
    args = cli._parse_args(
        parser,
        [
            "http://youtube.com/watch?v=9bZkp7q19f0",
            "--build-playback-report",
            "-c",
            "en",
            "-l",
            "--itag=10",
            "-vvv",
        ],
    )
    assert args.url == "http://youtube.com/watch?v=9bZkp7q19f0"
    assert args.build_playback_report is True
    assert args.itag == 10
    assert args.list is True
    assert args.verbose is True
