import os
import uuid

import requests
import srt_equalizer
import assemblyai as aai

from typing import List
from pathlib import Path
from moviepy import (
    AudioFileClip,
    CompositeVideoClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from dotenv import load_dotenv
from logstream import log
from moviepy.video.tools.subtitles import SubtitlesClip
from utils import ENV_FILE, TEMP_DIR, SUBTITLES_DIR, FONTS_DIR

load_dotenv(ENV_FILE)

ASSEMBLY_AI_API_KEY = os.getenv("ASSEMBLY_AI_API_KEY")
FRAME_EPSILON = 1 / 120


def save_video(video_url: str, directory: str = str(TEMP_DIR)) -> str:
    """
    Saves a video from a given URL and returns the path to the video.

    Args:
        video_url (str): The URL of the video to save.
        directory (str): The path of the temporary directory to save the video to

    Returns:
        str: The path to the saved video.
    """
    destination = Path(directory).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    video_id = uuid.uuid4()
    video_path = destination / f"{video_id}.mp4"
    with open(video_path, "wb") as f:
        f.write(requests.get(video_url).content)

    return str(video_path)


def __generate_subtitles_assemblyai(audio_path: str, voice: str) -> str:
    """
    Generates subtitles from a given audio file and returns the path to the subtitles.

    Args:
        audio_path (str): The path to the audio file to generate subtitles from.

    Returns:
        str: The generated subtitles
    """

    language_mapping = {
        "br": "pt",
        "id": "en",  # AssemblyAI doesn't have Indonesian
        "jp": "ja",
        "kr": "ko",
    }

    if voice in language_mapping:
        lang_code = language_mapping[voice]
    else:
        lang_code = voice

    aai.settings.api_key = ASSEMBLY_AI_API_KEY
    config = aai.TranscriptionConfig(language_code=lang_code)
    transcriber = aai.Transcriber(config=config)
    transcript = transcriber.transcribe(audio_path)
    subtitles = transcript.export_subtitles_srt()

    return subtitles


def __generate_subtitles_locally(
    sentences: List[str], audio_clips: List[AudioFileClip]
) -> str:
    """
    Generates subtitles from a given audio file and returns the path to the subtitles.

    Args:
        sentences (List[str]): all the sentences said out loud in the audio clips
        audio_clips (List[AudioFileClip]): all the individual audio clips which will make up the final audio track
    Returns:
        str: The generated subtitles
    """

    def convert_to_srt_time_format(total_seconds: float) -> str:
        # Convert total seconds to the SRT time format: HH:MM:SS,mmm
        milliseconds_total = int(round(total_seconds * 1000))
        hours, remainder = divmod(milliseconds_total, 3_600_000)
        minutes, remainder = divmod(remainder, 60_000)
        seconds, milliseconds = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    start_time = 0
    subtitles = []

    for i, (sentence, audio_clip) in enumerate(zip(sentences, audio_clips), start=1):
        duration = audio_clip.duration
        end_time = start_time + duration

        # Format: subtitle index, start time --> end time, sentence
        subtitle_entry = f"{i}\n{convert_to_srt_time_format(start_time)} --> {convert_to_srt_time_format(end_time)}\n{sentence}\n"
        subtitles.append(subtitle_entry)

        start_time += duration  # Update start time for the next subtitle

    return "\n".join(subtitles)


def generate_subtitles(
    audio_path: str, sentences: List[str], audio_clips: List[AudioFileClip], voice: str
) -> str:
    """
    Generates subtitles from a given audio file and returns the path to the subtitles.

    Args:
        audio_path (str): The path to the audio file to generate subtitles from.
        sentences (List[str]): all the sentences said out loud in the audio clips
        audio_clips (List[AudioFileClip]): all the individual audio clips which will make up the final audio track

    Returns:
        str: The path to the generated subtitles.
    """

    def equalize_subtitles(srt_path: str, max_chars: int = 10) -> None:
        # Equalize subtitles
        srt_equalizer.equalize_srt_file(srt_path, srt_path, max_chars)

    # Save subtitles
    SUBTITLES_DIR.mkdir(parents=True, exist_ok=True)
    subtitles_path = SUBTITLES_DIR / f"{uuid.uuid4()}.srt"

    if ASSEMBLY_AI_API_KEY is not None and ASSEMBLY_AI_API_KEY != "":
        log("[+] Creating subtitles using AssemblyAI", "info")
        subtitles = __generate_subtitles_assemblyai(audio_path, voice)
    else:
        log("[+] Creating subtitles locally", "info")
        subtitles = __generate_subtitles_locally(sentences, audio_clips)
        # print(colored("[-] Local subtitle generation has been disabled for the time being.", "red"))
        # print(colored("[-] Exiting.", "red"))
        # sys.exit(1)

    with open(subtitles_path, "w", encoding="utf-8") as file:
        file.write(subtitles)

    # Equalize subtitles
    equalize_subtitles(str(subtitles_path))

    log("[+] Subtitles generated.", "success")

    return str(subtitles_path)


def combine_videos(
    video_paths: List[str], max_duration: int, max_clip_duration: int, threads: int
) -> str:
    """
    Combines a list of videos into one video and returns the path to the combined video.

    Args:
        video_paths (List): A list of paths to the videos to combine.
        max_duration (int): The maximum duration of the combined video.
        max_clip_duration (int): The maximum duration of each clip.
        threads (int): The number of threads to use for the video processing.

    Returns:
        str: The path to the combined video.
    """
    video_id = uuid.uuid4()
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    combined_video_path = TEMP_DIR / f"{video_id}.mp4"

    if not video_paths:
        raise ValueError("No source videos were provided for concatenation.")

    max_duration = float(max_duration)
    max_clip_duration = float(max_clip_duration)

    # Required duration of each clip
    req_dur = max_duration / len(video_paths)

    log("[+] Combining videos...", "info")
    log(f"[+] Each clip will be maximum {req_dur} seconds long.", "info")

    clips = []
    tot_dur = 0
    # Add downloaded clips over and over until the duration of the audio (max_duration) has been reached
    while tot_dur < (max_duration - FRAME_EPSILON):
        progressed = False
        for video_path in video_paths:
            remaining = max_duration - tot_dur
            if remaining <= FRAME_EPSILON:
                break

            clip = VideoFileClip(video_path)
            clip = clip.without_audio()
            max_safe_source_duration = clip.duration - FRAME_EPSILON
            if max_safe_source_duration <= 0:
                clip.close()
                continue

            target_duration = min(req_dur, max_clip_duration, remaining)
            target_duration = min(target_duration, max_safe_source_duration)

            if target_duration <= 0:
                clip.close()
                continue

            if target_duration < clip.duration:
                clip = clip.subclipped(0, target_duration)
            clip = clip.with_fps(30)

            # Not all videos are same size,
            # so we need to resize them
            if round((clip.w / clip.h), 4) < 0.5625:
                clip = clip.cropped(
                    width=clip.w,
                    height=round(clip.w / 0.5625),
                    x_center=clip.w / 2,
                    y_center=clip.h / 2,
                )
            else:
                clip = clip.cropped(
                    width=round(0.5625 * clip.h),
                    height=clip.h,
                    x_center=clip.w / 2,
                    y_center=clip.h / 2,
                )
            clip = clip.resized(new_size=(1080, 1920))

            clips.append(clip)
            tot_dur += clip.duration
            progressed = True

        if not progressed:
            raise RuntimeError("Could not reach target duration from source videos.")

    if not clips:
        raise RuntimeError("No valid clips were produced for concatenation.")

    final_clip = concatenate_videoclips(clips, method="compose")
    final_clip = final_clip.with_fps(30).with_duration(max_duration)
    try:
        final_clip.write_videofile(
            str(combined_video_path),
            threads=threads,
            fps=30,
            codec="libx264",
            preset="medium",
            audio=False,
        )
    finally:
        final_clip.close()
        for clip in clips:
            clip.close()

    return str(combined_video_path)


def generate_video(
    combined_video_path: str,
    tts_path: str,
    subtitles_path: str,
    threads: int,
    subtitles_position: str,
    text_color: str,
) -> str:
    """
    This function creates the final video, with subtitles and audio.

    Args:
        combined_video_path (str): The path to the combined video.
        tts_path (str): The path to the text-to-speech audio.
        subtitles_path (str): The path to the subtitles.
        threads (int): The number of threads to use for the video processing.
        subtitles_position (str): The position of the subtitles.

    Returns:
        str: The path to the final video.
    """
    # Make a generator that returns a TextClip when called with consecutive
    font_path = str((FONTS_DIR / "bold_font.ttf").resolve())
    generator = lambda txt: TextClip(
        font=font_path,
        text=txt,
        font_size=100,
        color=text_color,
        stroke_color="black",
        stroke_width=5,
    )

    # Split the subtitles position into horizontal and vertical
    horizontal_subtitles_position, vertical_subtitles_position = (
        subtitles_position.split(",")
    )

    # Burn the subtitles into the video
    subtitles = SubtitlesClip(subtitles_path, make_textclip=generator)
    subtitle_vertical_position = vertical_subtitles_position
    if vertical_subtitles_position == "top":
        subtitle_vertical_position = 80

    base_video = VideoFileClip(str(combined_video_path))
    audio = AudioFileClip(tts_path)
    target_duration = min(base_video.duration, audio.duration)

    result = CompositeVideoClip(
        [
            base_video.subclipped(0, target_duration),
            subtitles.with_position(
                (horizontal_subtitles_position, subtitle_vertical_position)
            ).with_duration(target_duration),
        ]
    )

    # Clamp audio/video to exactly the same duration to avoid end-frame overreads.
    result = result.with_audio(audio.subclipped(0, target_duration)).with_duration(
        target_duration
    )

    output_path = TEMP_DIR / "output.mp4"
    try:
        result.write_videofile(
            str(output_path),
            threads=threads or 2,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
        )
    finally:
        result.close()
        subtitles.close()
        audio.close()
        base_video.close()

    return "output.mp4"
