""" imageio_ffmpeg, FFMPEG wrapper for Python.
"""

# flake8: noqa

from ._definitions import __version__
from ._io import count_frames_and_secs, read_frames, write_frames
from ._utils import get_ffmpeg_exe, get_ffmpeg_version
