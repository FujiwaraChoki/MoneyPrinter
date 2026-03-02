from pathlib import Path

import utils


def test_clean_dir_removes_existing_files_and_directories(tmp_path: Path):
    target_dir = tmp_path / "cleanup"
    nested_dir = target_dir / "nested"
    nested_dir.mkdir(parents=True)
    (target_dir / "root.txt").write_text("root")
    (nested_dir / "nested.txt").write_text("nested")

    utils.clean_dir(str(target_dir))

    assert target_dir.exists()
    assert list(target_dir.iterdir()) == []


def test_choose_random_song_returns_none_if_songs_dir_missing(
    monkeypatch, tmp_path: Path
):
    songs_dir = tmp_path / "Songs"
    monkeypatch.setattr(utils, "SONGS_DIR", songs_dir)

    assert utils.choose_random_song() is None


def test_choose_random_song_returns_selected_mp3(monkeypatch, tmp_path: Path):
    songs_dir = tmp_path / "Songs"
    songs_dir.mkdir()
    first_song = songs_dir / "a.mp3"
    second_song = songs_dir / "b.mp3"
    ignored_file = songs_dir / "notes.txt"
    first_song.write_text("a")
    second_song.write_text("b")
    ignored_file.write_text("ignore")

    monkeypatch.setattr(utils, "SONGS_DIR", songs_dir)
    monkeypatch.setattr(utils.random, "choice", lambda songs: songs[0])

    selected = utils.choose_random_song()

    assert selected == str(first_song)


def test_resolve_imagemagick_binary_prefers_configured_existing_path(
    monkeypatch, tmp_path: Path
):
    fake_binary = tmp_path / "magick"
    fake_binary.write_text("binary")
    monkeypatch.setenv("IMAGEMAGICK_BINARY", str(fake_binary))

    resolved = utils.resolve_imagemagick_binary()

    assert resolved == str(fake_binary.resolve())


def test_resolve_imagemagick_binary_falls_back_to_path_lookup(monkeypatch):
    monkeypatch.setenv("IMAGEMAGICK_BINARY", "")

    def fake_which(candidate: str):
        if candidate == "magick":
            return "/usr/local/bin/magick"
        return None

    monkeypatch.setattr(utils.shutil, "which", fake_which)

    resolved = utils.resolve_imagemagick_binary()

    assert resolved == "/usr/local/bin/magick"
