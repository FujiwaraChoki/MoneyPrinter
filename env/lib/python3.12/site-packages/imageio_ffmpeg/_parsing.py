import re
import threading
import time

from ._utils import logger


class LogCatcher(threading.Thread):
    """Thread to keep reading from stderr so that the buffer does not
    fill up and stalls the ffmpeg process. On stderr a message is send
    on every few frames with some meta information. We only keep the
    last ones.
    """

    def __init__(self, file):
        self._file = file
        self._header = ""
        self._lines = []
        self._remainder = b""
        threading.Thread.__init__(self)
        self.daemon = True  # do not let this thread hold up Python shutdown
        self._should_stop = False
        self.start()

    def stop_me(self):
        self._should_stop = True

    @property
    def header(self):
        """Get header text. Empty string if the header is not yet parsed."""
        return self._header

    def get_text(self, timeout=0):
        """Get the whole text written to stderr so far. To preserve
        memory, only the last 50 to 100 frames are kept.

        If a timeout is given, wait for this thread to finish. When
        something goes wrong, we stop ffmpeg and want a full report of
        stderr, but this thread might need a tiny bit more time.
        """

        # Wait?
        if timeout > 0:
            etime = time.time() + timeout
            while self.is_alive() and time.time() < etime:  # pragma: no cover
                time.sleep(0.01)
        # Return str
        lines = b"\n".join(self._lines)
        return self._header + "\n" + lines.decode("utf-8", "ignore")

    def run(self):
        # Create ref here so it still exists even if Py is shutting down
        limit_lines_local = limit_lines

        while not self._should_stop:
            time.sleep(0)
            # Read one line. Detect when closed, and exit
            try:
                line = self._file.read(20)
            except ValueError:  # pragma: no cover
                break
            if not line:
                break
            # Process to divide in lines
            line = line.replace(b"\r", b"\n").replace(b"\n\n", b"\n")
            lines = line.split(b"\n")
            lines[0] = self._remainder + lines[0]
            self._remainder = lines.pop(-1)
            # Process each line
            self._lines.extend(lines)
            if not self._header:
                if get_output_video_line(self._lines):
                    header = b"\n".join(self._lines)
                    self._header += header.decode("utf-8", "ignore")
            elif self._lines:
                self._lines = limit_lines_local(self._lines)

        # Close the file when we're done
        # See #61 and #69
        try:
            self._file.close()
        except Exception:
            pass


def get_output_video_line(lines):
    """Get the line that defines the video stream that ffmpeg outputs,
    and which we read.
    """
    in_output = False
    for line in lines:
        sline = line.lstrip()
        if sline.startswith(b"Output "):
            in_output = True
        elif in_output:
            if sline.startswith(b"Stream ") and b" Video:" in sline:
                return line


def limit_lines(lines, N=32):
    """When number of lines > 2*N, reduce to N."""
    if len(lines) > 2 * N:
        lines = [b"... showing only last few lines ..."] + lines[-N:]
    return lines


def cvsecs(*args):
    """converts a time to second. Either cvsecs(min, secs) or
    cvsecs(hours, mins, secs).
    """
    if len(args) == 1:
        return float(args[0])
    elif len(args) == 2:
        return 60 * float(args[0]) + float(args[1])
    elif len(args) == 3:
        return 3600 * float(args[0]) + 60 * float(args[1]) + float(args[2])


def parse_ffmpeg_header(text):
    lines = text.splitlines()
    meta = {}

    # meta["header"] = text  # Can enable this for debugging

    # Get version
    ver = lines[0].split("version", 1)[-1].split("Copyright")[0]
    meta["ffmpeg_version"] = ver.strip() + " " + lines[1].strip()

    # get the output line that speaks about video
    videolines = [
        l for l in lines if l.lstrip().startswith("Stream ") and " Video: " in l
    ]

    # Codec and pix_fmt hint
    line = videolines[0]
    meta["codec"] = line.split("Video: ", 1)[-1].lstrip().split(" ", 1)[0].strip()
    meta["pix_fmt"] = re.split(
        # use a negative lookahead regexp to ignore commas that are contained
        # within a parenthesis
        # this helps consider a pix_fmt of the kind
        #     yuv420p(tv, progressive)
        # as what it is, instead of erroneously reporting as
        #     yuv420p(tv
        r",\s*(?![^()]*\))",
        line.split("Video: ", 1)[-1],
    )[1].strip()

    # get the output line that speaks about audio
    audiolines = [
        l for l in lines if l.lstrip().startswith("Stream ") and " Audio: " in l
    ]

    if len(audiolines) > 0:
        audio_line = audiolines[0]
        meta["audio_codec"] = (
            audio_line.split("Audio: ", 1)[-1].lstrip().split(" ", 1)[0].strip()
        )

    # get the frame rate.
    # matches can be empty, see #171, assume nframes = inf
    # the regexp omits values of "1k tbr" which seems a specific edge-case #262
    # it seems that tbr is generally to be preferred #262
    fps = 0
    for line in [videolines[0]]:
        matches = re.findall(r" ([0-9]+\.?[0-9]*) (fps)", line)
        if matches:
            fps = float(matches[0][0].strip())
    meta["fps"] = fps

    # get the size of the original stream, of the form 460x320 (w x h)
    line = videolines[0]
    match = re.search(" [0-9]*x[0-9]*(,| )", line)
    parts = line[match.start() : match.end() - 1].split("x")
    meta["source_size"] = tuple(map(int, parts))

    # get the size of what we receive, of the form 460x320 (w x h)
    line = videolines[-1]  # Pipe output
    match = re.search(" [0-9]*x[0-9]*(,| )", line)
    parts = line[match.start() : match.end() - 1].split("x")
    meta["size"] = tuple(map(int, parts))

    # Check the two sizes
    if meta["source_size"] != meta["size"]:
        logger.warning(
            "The frame size for reading {} is "
            "different from the source frame size {}.".format(
                meta["size"], meta["source_size"]
            )
        )

    # get the rotate metadata
    reo_rotate = re.compile(r"rotate\s+:\s([0-9]+)")
    match = reo_rotate.search(text)
    rotate = 0
    if match is not None:
        rotate = match.groups()[0]
    meta["rotate"] = int(rotate)

    # get duration (in seconds)
    line = [l for l in lines if "Duration: " in l][0]
    match = re.search(" [0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9]", line)
    duration = 0
    if match is not None:
        hms = line[match.start() + 1 : match.end()].split(":")
        duration = cvsecs(*hms)
    meta["duration"] = duration

    return meta
