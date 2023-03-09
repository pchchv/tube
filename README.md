<div align="center">

# **utub3** <a href="https://pypi.org/project/utub3/"><img src="https://img.shields.io/pypi/v/utub3?style=flat-square" /></a>

</div>

*YouTube* is the world's most popular video hosting service, and you might come across a situation where you need a video download script. There is a **utub3** for this purpose.

**Utub3** is a lightweight, dependency-free Python library and command-line utility for downloading *YouTube* Videos.

**Utub3** also simplifies piping by allowing you to set callback functions for various download events, such as progress or completion.

In addition, **utub3** includes a command line utility that allows you to download videos directly from the terminal.

## Quickstart

### Installation

utub3 requires an installation of Python 3.6 or greater, as well as pip. (Pip is typically bundled with Python [installations](https://python.org/downloads).)

To install from PyPI with pip:

```bash
$ python -m pip install utub3
```

Sometimes, the PyPI release becomes slightly outdated. To install from the source with pip:

```bash
$ python -m pip install git+https://github.com/pchchv/utub3
```

### Using utub3 in a Python script

To download a video using the library in a script, you'll need to import the YouTube class from the library and pass an argument of the video URL. From there, you can access the streams and download them.

```python
 >>> from utub3 import YouTube
 >>> YouTube('https://youtu.be/HxCcKzRAGWk').streams.first().download()
 >>> yt = YouTube('http://youtube.com/watch?v=HxCcKzRAGWk')
 >>> yt.streams
  ... .filter(progressive=True, file_extension='mp4')
  ... .order_by('resolution')
  ... .desc()
  ... .first()
  ... .download()
```

### Using the command-line interface

Using the CLI is remarkably straightforward as well. To download a video at the highest progressive quality, you can use the following command:
```bash
$ utub3 https://youtube.com/watch?v=HxCcKzRAGWk
```

You can also do the same for a playlist:
```bash
$ utub3 https://www.youtube.com/watch?v=UP2XoGfhJ1Y&list=RDUP2XoGfhJ1Y&start_radio=1&t=3s
```