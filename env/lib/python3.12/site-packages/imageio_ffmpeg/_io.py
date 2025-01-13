import pathlib
import subprocess
import sys
import time
from collections import defaultdict
from functools import lru_cache

from ._parsing import LogCatcher, cvsecs, parse_ffmpeg_header
from ._utils import _popen_kwargs, get_ffmpeg_exe, logger

ISWIN = sys.platform.startswith("win")

h264_encoder_preference = defaultdict(lambda: -1)
# The libx264 was the default encoder for a longe time with imageio
h264_encoder_preference["libx264"] = 100

# Encoder with the nvidia graphics card dedicated hardware
h264_encoder_preference["h264_nvenc"] = 90
# Deprecated names for the same encoder
h264_encoder_preference["nvenc_h264"] = 90
h264_encoder_preference["nvenc"] = 90

# vaapi provides hardware encoding with intel integrated graphics chipsets
h264_encoder_preference["h264_vaapi"] = 80

# openh264 is cisco's open source encoder
h264_encoder_preference["libopenh264"] = 70

h264_encoder_preference["libx264rgb"] = 50


def ffmpeg_test_encoder(encoder):
    # Use the null streams to validate if we can encode anything
    # https://trac.ffmpeg.org/wiki/Null
    cmd = [
        get_ffmpeg_exe(),
        "-hide_banner",
        "-f",
        "lavfi",
        "-i",
        "nullsrc=s=256x256:d=8",
        "-vcodec",
        encoder,
        "-f",
        "null",
        "-",
    ]
    p = subprocess.run(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return p.returncode == 0


def get_compiled_h264_encoders():
    cmd = [get_ffmpeg_exe(), "-hide_banner", "-encoders"]
    p = subprocess.run(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = p.stdout.decode().replace("\r", "")
    # 2022/04/08: hmaarrfk
    # I couldn't find a good way to get the list of available encoders from
    # the ffmpeg command
    # The ffmpeg command return a table that looks like
    # Notice the leading space at the very beginning
    # On ubuntu with libffmpeg-nvenc-dev we get
    # $ ffmpeg -hide_banner -encoders | grep -i h.264
    #
    # Encoders:
    #  V..... = Video
    #  A..... = Audio
    #  S..... = Subtitle
    #  .F.... = Frame-level multithreading
    #  ..S... = Slice-level multithreading
    #  ...X.. = Codec is experimental
    #  ....B. = Supports draw_horiz_band
    #  .....D = Supports direct rendering method 1
    #  ------
    #  V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (codec h264)
    #  V..... libx264rgb           libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 RGB (codec h264)
    #  V....D h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)
    #  V..... h264_omx             OpenMAX IL H.264 video encoder (codec h264)
    #  V..... h264_qsv             H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10 (Intel Quick Sync Video acceleration) (codec h264)
    #  V..... h264_v4l2m2m         V4L2 mem2mem H.264 encoder wrapper (codec h264)
    #  V....D h264_vaapi           H.264/AVC (VAAPI) (codec h264)
    #  V..... nvenc                NVIDIA NVENC H.264 encoder (codec h264)
    #  V..... nvenc_h264           NVIDIA NVENC H.264 encoder (codec h264)
    #
    # However, just because ffmpeg was compiled with the options enabled
    # it doesn't mean that it will be successful
    header_footer = stdout.split("------")
    footer = header_footer[1].strip("\n")
    encoders = []
    for line in footer.split("\n"):
        # Strip to remove any leading spaces
        line = line.strip()
        encoder = line.split(" ")[1]

        if encoder in h264_encoder_preference:
            # These encoders are known to support H.264
            # We forcibly include them in case their description changes to
            # not include the string "H.264"
            encoders.append(encoder)
        elif (line[0] == "V") and ("H.264" in line):
            encoders.append(encoder)

    encoders.sort(reverse=True, key=lambda x: h264_encoder_preference[x])
    if "h264_nvenc" in encoders:
        # Remove deprecated names for the same encoder
        for encoder in ["nvenc", "nvenc_h264"]:
            if encoder in encoders:
                encoders.remove(encoder)
    # Return an immutable tuple to avoid users corrupting the lru_cache
    return tuple(encoders)


@lru_cache()
def get_first_available_h264_encoder():
    compiled_encoders = get_compiled_h264_encoders()
    for encoder in compiled_encoders:
        if ffmpeg_test_encoder(encoder):
            return encoder
    else:
        raise RuntimeError(
            "No valid H.264 encoder was found with the ffmpeg installation"
        )


def count_frames_and_secs(path):
    """
    Get the number of frames and number of seconds for the given video
    file. Note that this operation can be quite slow for large files.

    Disclaimer: I've seen this produce different results from actually reading
    the frames with older versions of ffmpeg (2.x). Therefore I cannot say
    with 100% certainty that the returned values are always exact.
    """
    # https://stackoverflow.com/questions/2017843/fetch-frame-count-with-ffmpeg

    if isinstance(path, pathlib.PurePath):
        path = str(path)
    if not isinstance(path, str):
        raise TypeError("Video path must be a string or pathlib.Path.")

    cmd = [
        get_ffmpeg_exe(),
        "-i",
        path,
        "-map",
        "0:v:0",
        "-vf",
        "null",
        "-f",
        "null",
        "-",
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, **_popen_kwargs())
    except subprocess.CalledProcessError as err:
        out = err.output.decode(errors="ignore")
        raise RuntimeError(
            "FFMPEG call failed with {}:\n{}".format(err.returncode, out)
        )

    # Note that other than with the subprocess calls below, ffmpeg wont hang here.
    # Worst case Python will stop/crash and ffmpeg will continue running until done.

    nframes = nsecs = None
    for line in reversed(out.splitlines()):
        if line.startswith(b"frame="):
            line = line.decode(errors="ignore")
            i = line.find("frame=")
            if i >= 0:
                s = line[i:].split("=", 1)[-1].lstrip().split(" ", 1)[0].strip()
                nframes = int(s)
            i = line.find("time=")
            if i >= 0:
                s = line[i:].split("=", 1)[-1].lstrip().split(" ", 1)[0].strip()
                nsecs = cvsecs(*s.split(":"))
            return nframes, nsecs

    raise RuntimeError("Could not get number of frames")  # pragma: no cover


def read_frames(
    path,
    pix_fmt="rgb24",
    bpp=None,
    input_params=None,
    output_params=None,
    bits_per_pixel=None,
):
    """
    Create a generator to iterate over the frames in a video file.

    It first yields a small metadata dictionary that contains:

    * ffmpeg_version: the ffmpeg version in use (as a string).
    * codec: a hint about the codec used to encode the video, e.g. "h264".
    * source_size: the width and height of the encoded video frames.
    * size: the width and height of the frames that will be produced.
    * fps: the frames per second. Can be zero if it could not be detected.
    * duration: duration in seconds. Can be zero if it could not be detected.

    After that, it yields frames until the end of the video is reached. Each
    frame is a bytes object.

    This function makes no assumptions about the number of frames in
    the data. For one because this is hard to predict exactly, but also
    because it may depend on the provided output_params. If you want
    to know the number of frames in a video file, use count_frames_and_secs().
    It is also possible to estimate the number of frames from the fps and
    duration, but note that even if both numbers are present, the resulting
    value is not always correct.

    Example:

        gen = read_frames(path)
        meta = gen.__next__()
        for frame in gen:
            print(len(frame))

    Parameters:
        path (str): the filename of the file to read from.
        pix_fmt (str): the pixel format of the frames to be read.
            The default is "rgb24" (frames are uint8 RGB images).
        input_params (list): Additional ffmpeg input command line parameters.
        output_params (list): Additional ffmpeg output command line parameters.
        bits_per_pixel (int): The number of bits per pixel in the output frames.
            This depends on the given pix_fmt. Default is 24 (RGB)
        bpp (int): DEPRECATED, USE bits_per_pixel INSTEAD. The number of bytes per pixel in the output frames.
            This depends on the given pix_fmt. Some pixel formats like yuv420p have 12 bits per pixel
            and cannot be set in bytes as integer. For this reason the bpp argument is deprecated.
    """

    # ----- Input args

    if isinstance(path, pathlib.PurePath):
        path = str(path)
    if not isinstance(path, str):
        raise TypeError("Video path must be a string or pathlib.Path.")
    # Note: Dont check whether it exists. The source could be e.g. a camera.

    pix_fmt = pix_fmt or "rgb24"
    bpp = bpp or 3
    bits_per_pixel = bits_per_pixel or bpp * 8
    input_params = input_params or []
    output_params = output_params or []

    assert isinstance(pix_fmt, str), "pix_fmt must be a string"
    assert isinstance(bits_per_pixel, int), "bpp and bits_per_pixel must be an int"
    assert isinstance(input_params, list), "input_params must be a list"
    assert isinstance(output_params, list), "output_params must be a list"

    # ----- Prepare

    pre_output_params = ["-pix_fmt", pix_fmt, "-vcodec", "rawvideo", "-f", "image2pipe"]

    cmd = [get_ffmpeg_exe()]
    cmd += input_params + ["-i", path]
    cmd += pre_output_params + output_params + ["-"]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **_popen_kwargs(prevent_sigint=True)
    )

    log_catcher = LogCatcher(process.stderr)

    # Init policy by which to terminate ffmpeg. May be set to "kill" later.
    stop_policy = "timeout"  # not wait; ffmpeg should be able to quit quickly

    # Enter try block directly after opening the process.
    # We terminate ffmpeg in the finally clause.
    # Generators are automatically closed when they get deleted,
    # so the finally block is guaranteed to run.
    try:
        # ----- Load meta data

        # Wait for the log catcher to get the meta information
        etime = time.time() + 10.0
        while log_catcher.is_alive() and not log_catcher.header and time.time() < etime:
            time.sleep(0.01)

        # Check whether we have the information
        if not log_catcher.header:
            err2 = log_catcher.get_text(0.2)
            fmt = "Could not load meta information\n=== stderr ===\n{}"
            raise IOError(fmt.format(err2))
        elif "No such file or directory" in log_catcher.header:
            raise IOError("{} not found! Wrong path?".format(path))

        meta = parse_ffmpeg_header(log_catcher.header)
        yield meta

        # ----- Read frames

        width, height = meta["size"]
        framesize_bits = width * height * bits_per_pixel
        framesize_bytes = framesize_bits / 8
        assert (
            framesize_bytes.is_integer()
        ), "incorrect bits_per_pixel, framesize in bytes must be an int"
        framesize_bytes = int(framesize_bytes)
        framenr = 0

        while True:
            framenr += 1
            try:
                bb = bytes()
                while len(bb) < framesize_bytes:
                    extra_bytes = process.stdout.read(framesize_bytes - len(bb))
                    if not extra_bytes:
                        if len(bb) == 0:
                            return
                        else:
                            raise RuntimeError(
                                "End of file reached before full frame could be read."
                            )
                    bb += extra_bytes
                yield bb
            except Exception as err:
                err1 = str(err)
                err2 = log_catcher.get_text(0.4)
                fmt = "Could not read frame {}:\n{}\n=== stderr ===\n{}"
                raise RuntimeError(fmt.format(framenr, err1, err2))

    except GeneratorExit:
        # Note that GeneratorExit does not inherit from Exception but BaseException
        pass

    except Exception:
        # Normal exceptions fall through
        raise

    except BaseException:
        # Detect KeyboardInterrupt / SystemExit: don't wait for ffmpeg to quit
        stop_policy = "kill"
        raise

    finally:
        # Stop the LogCatcher thread, which reads from stderr.
        log_catcher.stop_me()

        # Make sure that ffmpeg is terminated.
        if process.poll() is None:
            # Ask ffmpeg to quit
            try:
                # I read somewhere that modern ffmpeg on Linux prefers a
                # "ctrl-c", but tests so far suggests sending q is more robust.
                # > p.send_signal(signal.SIGINT)
                # Sending q via communicate works, but can hang (see #17)
                # > p.communicate(b"q")
                # So let's do similar to what communicate does, but without
                # reading stdout (which may block). It looks like only closing
                # stdout is enough (tried Windows+Linux), but let's play safe.
                # Found that writing to stdin can cause "Invalid argument" on
                # Windows # and "Broken Pipe" on Unix.
                # p.stdin.write(b"q")  # commented out in v0.4.1
                process.stdout.close()
                process.stdin.close()
                # p.stderr.close() -> not here, the log_catcher closes it
            except Exception as err:  # pragma: no cover
                logger.warning("Error while attempting stop ffmpeg (r): " + str(err))

            if stop_policy == "timeout":
                # Wait until timeout, produce a warning and kill if it still exists
                try:
                    etime = time.time() + 1.5
                    while time.time() < etime and process.poll() is None:
                        time.sleep(0.01)
                finally:
                    if process.poll() is None:  # pragma: no cover
                        logger.warning("We had to kill ffmpeg to stop it.")
                        process.kill()

            else:  # stop_policy == "kill"
                # Just kill it
                process.kill()


def write_frames(
    path,
    size,
    pix_fmt_in="rgb24",
    pix_fmt_out="yuv420p",
    fps=16,
    quality=5,
    bitrate=None,
    codec=None,
    macro_block_size=16,
    ffmpeg_log_level="warning",
    ffmpeg_timeout=None,
    input_params=None,
    output_params=None,
    audio_path=None,
    audio_codec=None,
):
    """
    Create a generator to write frames (bytes objects) into a video file.

    The frames are written by using the generator's `send()` method. Frames
    can be anything that can be written to a file. Typically these are
    bytes objects, but c-contiguous Numpy arrays also work.

    Example:

        gen = write_frames(path, size)
        gen.send(None)  # seed the generator
        for frame in frames:
            gen.send(frame)
        gen.close()  # don't forget this

    Parameters:
        path (str): the filename to write to.
        size (tuple): the width and height of the frames.
        pix_fmt_in (str): the pixel format of incoming frames.
            E.g. "gray", "gray8a", "rgb24", or "rgba". Default "rgb24".
        pix_fmt_out (str): the pixel format to store frames. Default yuv420p".
        fps (float): The frames per second. Default 16.
        quality (float): A measure for quality between 0 and 10. Default 5.
            Ignored if bitrate is given.
        bitrate (str): The bitrate, e.g. "192k". The defaults are pretty good.
        codec (str): The codec. Default "libx264" for .mp4 (if available from
            the ffmpeg executable) or "msmpeg4" for .wmv.
        macro_block_size (int): You probably want to align the size of frames
            to this value to avoid image resizing. Default 16. Can be set
            to 1 to avoid block alignment, though this is not recommended.
        ffmpeg_log_level (str): The ffmpeg logging level. Default "warning".
        ffmpeg_timeout (float): Timeout in seconds to wait for ffmpeg process
            to finish. Value of 0 or None will wait forever (default). The time that
            ffmpeg needs depends on CPU speed, compression, and frame size.
        input_params (list): Additional ffmpeg input command line parameters.
        output_params (list): Additional ffmpeg output command line parameters.
        audio_path (str): A input file path for encoding with an audio stream.
            Default None, no audio.
        audio_codec (str): The audio codec to use if audio_path is provided.
            "copy" will try to use audio_path's audio codec without re-encoding.
            Default None, but some formats must have certain codecs specified.
    """

    # ----- Input args

    if isinstance(path, pathlib.PurePath):
        path = str(path)
    if not isinstance(path, str):
        raise TypeError("Video path must be a string or pathlib.Path.")

    # The pix_fmt_out yuv420p is the best for the outpur to work in
    # QuickTime and most other players. These players only support
    # the YUV planar color space with 4:2:0 chroma subsampling for
    # H.264 video. Otherwise, depending on the source, ffmpeg may
    # output to a pixel format that may be incompatible with these
    # players. See https://trac.ffmpeg.org/wiki/Encode/H.264#Encodingfordumbplayers

    pix_fmt_in = pix_fmt_in or "rgb24"
    pix_fmt_out = pix_fmt_out or "yuv420p"
    fps = fps or 16
    # bitrate, codec, macro_block_size can all be None or ...
    macro_block_size = macro_block_size or 16
    ffmpeg_log_level = ffmpeg_log_level or "warning"
    input_params = input_params or []
    output_params = output_params or []
    ffmpeg_timeout = ffmpeg_timeout or 0

    floatish = float, int
    if isinstance(size, (tuple, list)):
        assert len(size) == 2, "size must be a 2-tuple"
        assert isinstance(size[0], int) and isinstance(
            size[1], int
        ), "size must be ints"
        sizestr = "{:d}x{:d}".format(*size)
    # elif isinstance(size, str):
    #     assert "x" in size, "size as string must have format NxM"
    #     sizestr = size
    else:
        assert False, "size must be str or tuple"
    assert isinstance(pix_fmt_in, str), "pix_fmt_in must be str"
    assert isinstance(pix_fmt_out, str), "pix_fmt_out must be str"
    assert isinstance(fps, floatish), "fps must be float"
    if quality is not None:
        assert isinstance(quality, floatish), "quality must be float"
        assert 1 <= quality <= 10, "quality must be between 1 and 10 inclusive"
    assert isinstance(macro_block_size, int), "macro_block_size must be int"
    assert isinstance(ffmpeg_log_level, str), "ffmpeg_log_level must be str"
    assert isinstance(ffmpeg_timeout, floatish), "ffmpeg_timeout must be float"
    assert isinstance(input_params, list), "input_params must be a list"
    assert isinstance(output_params, list), "output_params must be a list"

    # ----- Prepare

    # Get parameters
    if not codec:
        if path.lower().endswith(".wmv"):
            # This is a safer default codec on windows to get videos that
            # will play in powerpoint and other apps. H264 is not always
            # available on windows.
            codec = "msmpeg4"
        else:
            codec = get_first_available_h264_encoder()

    audio_params = ["-an"]
    if audio_path is not None and not path.lower().endswith(".gif"):
        audio_params = ["-i", audio_path]
        if audio_codec is not None:
            output_params += ["-acodec", audio_codec]
        output_params += ["-map", "0:v:0", "-map", "1:a:0"]

    # Get command
    cmd = [
        get_ffmpeg_exe(),
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-s",
        sizestr,
    ]
    cmd += ["-pix_fmt", pix_fmt_in, "-r", "{:.02f}".format(fps)] + input_params
    cmd += ["-i", "-"] + audio_params
    cmd += ["-vcodec", codec, "-pix_fmt", pix_fmt_out]

    # Add fixed bitrate or variable bitrate compression flags
    if bitrate is not None:
        cmd += ["-b:v", str(bitrate)]
    elif quality is not None:  # If None, then we don't add anything
        quality = 1 - quality / 10.0
        if codec == "libx264":
            # crf ranges 0 to 51, 51 being worst.
            quality = int(quality * 51)
            cmd += ["-crf", str(quality)]  # for h264
        else:  # Many codecs accept q:v
            # q:v range can vary, 1-31, 31 being worst
            # But q:v does not always have the same range.
            # May need a way to find range for any codec.
            quality = int(quality * 30) + 1
            cmd += ["-qscale:v", str(quality)]  # for others

    # Note, for most codecs, the image dimensions must be divisible by
    # 16 the default for the macro_block_size is 16. Check if image is
    # divisible, if not have ffmpeg upsize to nearest size and warn
    # user they should correct input image if this is not desired.
    if macro_block_size > 1:
        if size[0] % macro_block_size > 0 or size[1] % macro_block_size > 0:
            out_w = size[0]
            out_h = size[1]
            if size[0] % macro_block_size > 0:
                out_w += macro_block_size - (size[0] % macro_block_size)
            if size[1] % macro_block_size > 0:
                out_h += macro_block_size - (size[1] % macro_block_size)
            cmd += ["-vf", "scale={}:{}".format(out_w, out_h)]
            logger.warning(
                "IMAGEIO FFMPEG_WRITER WARNING: input image is not"
                " divisible by macro_block_size={}, resizing from {} "
                "to {} to ensure video compatibility with most codecs "
                "and players. To prevent resizing, make your input "
                "image divisible by the macro_block_size or set the "
                "macro_block_size to 1 (risking incompatibility).".format(
                    macro_block_size, size[:2], (out_w, out_h)
                )
            )

    # Rather than redirect stderr to a pipe, just set minimal
    # output from ffmpeg by default. That way if there are warnings
    # the user will see them.
    cmd += ["-v", ffmpeg_log_level]
    cmd += output_params
    cmd.append(path)
    cmd_str = " ".join(cmd)
    if any(
        [level in ffmpeg_log_level for level in ("info", "verbose", "debug", "trace")]
    ):
        logger.info("RUNNING FFMPEG COMMAND: " + cmd_str)

    # Launch process
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=None,
        **_popen_kwargs(prevent_sigint=True)
    )

    # Note that directing stderr to a pipe on windows will cause ffmpeg
    # to hang if the buffer is not periodically cleared using
    # StreamCatcher or other means.
    # Setting bufsize to 0 or a small value does not seem to have much effect
    # (tried on Windows and Linux). I suspect that ffmpeg buffers
    # multiple frames (before encoding in a batch).

    # Init policy by which to terminate ffmpeg. May be set to "kill" later.
    stop_policy = "timeout"
    if not ffmpeg_timeout:
        stop_policy = "wait"

    # ----- Write frames

    # Enter try block directly after opening the process.
    # We terminate ffmpeg in the finally clause.
    # Generators are automatically closed when they get deleted,
    # so the finally block is guaranteed to run.
    try:
        # Just keep going until the generator.close() is called (raises GeneratorExit).
        # This could also happen when the generator is deleted somehow.
        nframes = 0
        while True:
            # Get frame
            bb = yield

            # framesize = size[0] * size[1] * depth * bpp
            # assert isinstance(bb, bytes), "Frame must be send as bytes"
            # assert len(bb) == framesize, "Frame must have width*height*depth*bpp bytes"
            # Actually, we accept anything that can be written to file.
            # This e.g. allows writing numpy arrays without having to make a copy ...

            # Write
            try:
                p.stdin.write(bb)
            except Exception as err:
                # Show the command and stderr from pipe
                msg = (
                    "{0:}\n\nFFMPEG COMMAND:\n{1:}\n\nFFMPEG STDERR "
                    "OUTPUT:\n".format(err, cmd_str)
                )
                raise IOError(msg)

            nframes += 1

    except GeneratorExit:
        # Note that GeneratorExit does not inherit from Exception but BaseException
        # Detect premature closing
        if nframes == 0:
            logger.warning("No frames have been written; the written video is invalid.")

    except Exception:
        # Normal exceptions fall through
        raise

    except BaseException:
        # Detect KeyboardInterrupt / SystemExit: don't wait for ffmpeg to quit
        stop_policy = "kill"
        raise

    finally:
        # Make sure that ffmpeg is terminated.
        if p.poll() is None:
            # Tell ffmpeg that we're done
            try:
                p.stdin.close()
            except Exception as err:  # pragma: no cover
                logger.warning("Error while attempting stop ffmpeg (w): " + str(err))

            if stop_policy == "timeout":
                # Wait until timeout, produce a warning and kill if it still exists
                try:
                    etime = time.time() + ffmpeg_timeout
                    while (time.time() < etime) and p.poll() is None:
                        time.sleep(0.01)
                finally:
                    if p.poll() is None:  # pragma: no cover
                        logger.warning(
                            "We had to kill ffmpeg to stop it. "
                            + "Consider increasing ffmpeg_timeout, "
                            + "or setting it to zero (no timeout)."
                        )
                        p.kill()

            elif stop_policy == "wait":
                # Wait forever, kill if it if we're interrupted
                try:
                    while p.poll() is None:
                        time.sleep(0.01)
                finally:  # the above can raise e.g. by ctrl-c or systemexit
                    if p.poll() is None:  # pragma: no cover
                        p.kill()

            else:  #  stop_policy == "kill":
                # Just kill it
                p.kill()
        # Just to be safe, wrap in try/except
        try:
            p.stdout.close()
        except Exception:
            pass
