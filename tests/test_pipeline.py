import pytest

import pipeline
import video


class _FakeAudioClip:
    def __init__(self, path: str, duration: float = 2.0):
        self.path = path
        self.duration = duration
        self.closed = False

    def write_audiofile(self, output_path: str) -> None:
        with open(output_path, "wb") as f:
            f.write(b"fake-audio")

    def close(self) -> None:
        self.closed = True


def test_parse_subtitles_position_defaults_and_validation():
    assert video._parse_subtitles_position(None) == ("center", "center")
    assert video._parse_subtitles_position("") == ("center", "center")
    assert video._parse_subtitles_position("  ") == ("center", "center")
    assert video._parse_subtitles_position("center,top") == ("center", "top")
    assert video._parse_subtitles_position(" left , bottom ") == ("left", "bottom")

    with pytest.raises(ValueError, match="Invalid subtitles_position"):
        video._parse_subtitles_position("center")

    with pytest.raises(ValueError, match="Invalid subtitles_position"):
        video._parse_subtitles_position("center,")


def test_pipeline_fails_fast_when_all_stock_video_downloads_fail(monkeypatch):
    tts_called = False
    subtitles_called = False

    monkeypatch.setattr(pipeline, "generate_script", lambda *_args: "First sentence.")
    monkeypatch.setattr(pipeline, "get_search_terms", lambda *_args: ["ocean"])
    monkeypatch.setattr(
        pipeline,
        "search_for_stock_videos",
        lambda *_args: ["https://videos.pexels.com/video-files/1/hd.mp4"],
    )

    def fail_download(_url: str) -> str:
        raise RuntimeError("network error")

    def fake_tts(*_args, **_kwargs):
        nonlocal tts_called
        tts_called = True

    def fake_subtitles(*_args, **_kwargs):
        nonlocal subtitles_called
        subtitles_called = True
        return "subs.srt"

    monkeypatch.setattr(pipeline, "save_video", fail_download)
    monkeypatch.setattr(pipeline, "tts", fake_tts)
    monkeypatch.setattr(pipeline, "generate_subtitles", fake_subtitles)

    with pytest.raises(RuntimeError, match="Could not download any stock videos."):
        pipeline.run_generation_pipeline(
            data={"videoSubject": "ocean"},
            is_cancelled=lambda: False,
            on_log=None,
        )

    assert tts_called is False
    assert subtitles_called is False


def test_pipeline_handles_minimal_payload_and_coerces_string_threads(
    monkeypatch, tmp_path
):
    temp_dir = tmp_path / "temp"
    project_root = tmp_path / "project"
    temp_dir.mkdir()
    project_root.mkdir()

    captured: dict = {}

    monkeypatch.setattr(pipeline, "TEMP_DIR", temp_dir)
    monkeypatch.setattr(pipeline, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(
        pipeline,
        "generate_script",
        lambda subject, paragraphs, model, voice, custom_prompt: (
            captured.update(
                {
                    "subject": subject,
                    "paragraphs": paragraphs,
                    "custom_prompt": custom_prompt,
                }
            )
            or "Hello world."
        ),
    )
    monkeypatch.setattr(pipeline, "get_search_terms", lambda *_args: ["sky"])
    monkeypatch.setattr(
        pipeline,
        "search_for_stock_videos",
        lambda *_args: ["https://videos.pexels.com/video-files/1/hd.mp4"],
    )
    monkeypatch.setattr(pipeline, "save_video", lambda _url: str(temp_dir / "clip.mp4"))
    monkeypatch.setattr(
        pipeline, "tts", lambda _text, _voice, filename: open(filename, "wb").close()
    )
    monkeypatch.setattr(pipeline, "AudioFileClip", _FakeAudioClip)
    monkeypatch.setattr(
        pipeline, "concatenate_audioclips", lambda clips: _FakeAudioClip("concat.mp3")
    )
    monkeypatch.setattr(
        pipeline, "generate_subtitles", lambda **_kwargs: str(temp_dir / "subs.srt")
    )

    def fake_combine(video_paths, duration, max_clip_dur, threads):
        captured["combine_threads"] = threads
        return str(temp_dir / "combined.mp4")

    def fake_generate_video(
        combined_path, tts_path, subtitles_path, threads, subtitles_position, text_color
    ):
        captured["render_threads"] = threads
        captured["subtitles_position"] = subtitles_position
        out = temp_dir / "output.mp4"
        out.write_bytes(b"rendered-video")
        return "output.mp4"

    monkeypatch.setattr(pipeline, "combine_videos", fake_combine)
    monkeypatch.setattr(pipeline, "generate_video", fake_generate_video)
    monkeypatch.setattr(
        pipeline, "generate_metadata", lambda *_args: ("Title", "Desc", ["tag"])
    )
    monkeypatch.setattr(pipeline.shutil, "which", lambda _name: None)

    result = pipeline.run_generation_pipeline(
        data={
            "videoSubject": "  sky  ",
            "threads": "4",
        },
        is_cancelled=lambda: False,
        on_log=None,
    )

    assert result == "output.mp4"
    assert (project_root / "output.mp4").read_bytes() == b"rendered-video"
    assert captured["subject"] == "sky"
    assert captured["paragraphs"] == 1
    assert captured["custom_prompt"] == ""
    assert captured["combine_threads"] == 4
    assert isinstance(captured["combine_threads"], int)
    assert captured["render_threads"] == 4
    assert isinstance(captured["render_threads"], int)
    assert captured["subtitles_position"] == "center,center"
