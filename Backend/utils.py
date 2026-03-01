import os
import sys
import random
import logging
import shutil

from pathlib import Path
from typing import Optional
from termcolor import colored


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
TEMP_DIR = PROJECT_ROOT / "temp"
SUBTITLES_DIR = PROJECT_ROOT / "subtitles"
SONGS_DIR = PROJECT_ROOT / "Songs"
FONTS_DIR = PROJECT_ROOT / "fonts"
ENV_FILE = PROJECT_ROOT / ".env"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_dir(path: str) -> None:
    """
    Removes every file in a directory.

    Args:
        path (str): Path to directory.

    Returns:
        None
    """
    try:
        directory = Path(path).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

        for entry in directory.iterdir():
            if entry.is_dir():
                shutil.rmtree(entry)
                logger.info(f"Removed directory: {entry}")
            else:
                entry.unlink(missing_ok=True)
                logger.info(f"Removed file: {entry}")

        logger.info(colored(f"Cleaned {directory} directory", "green"))
    except Exception as e:
        logger.error(f"Error occurred while cleaning directory {path}: {str(e)}")


def choose_random_song() -> Optional[str]:
    """
    Chooses a random MP3 from the Songs/ directory.

    Returns:
        str: The path to the chosen song, or None if no MP3 files found.
    """
    try:
        if not SONGS_DIR.exists():
            return None

        songs = [
            song
            for song in SONGS_DIR.iterdir()
            if song.is_file() and song.suffix.lower() == ".mp3"
        ]

        if not songs:
            return None

        song = random.choice(songs)
        logger.info(colored(f"Chose song: {song}", "green"))
        return str(song)
    except Exception as e:
        logger.error(
            colored(f"Error occurred while choosing random song: {str(e)}", "red")
        )


def resolve_imagemagick_binary() -> Optional[str]:
    """
    Resolves an ImageMagick executable path across Linux, macOS, and Windows.

    Returns:
        Optional[str]: Absolute executable path if found.
    """
    configured_binary = os.getenv("IMAGEMAGICK_BINARY", "").strip().strip('"')
    if configured_binary:
        expanded = Path(configured_binary).expanduser()
        if expanded.exists():
            return str(expanded.resolve())
        logger.warning(
            colored("Configured IMAGEMAGICK_BINARY was not found on disk.", "yellow")
        )

    candidate_names = [
        "magick",
        "magick.exe",
        "convert",
        "convert.exe",
    ]

    for candidate in candidate_names:
        found = shutil.which(candidate)
        if found:
            return found

    return None


def check_env_vars() -> None:
    """
    Checks if the necessary environment variables are set.

    Returns:
        None

    Raises:
        SystemExit: If any required environment variables are missing.
    """
    try:
        required_vars = ["PEXELS_API_KEY", "TIKTOK_SESSION_ID"]
        missing_vars = []
        for var in required_vars:
            value = os.getenv(var)
            if value is None or len(value) == 0:
                missing_vars.append(var)

        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            logger.error(
                colored(
                    f"The following environment variables are missing: {missing_vars_str}",
                    "red",
                )
            )
            logger.error(
                colored(
                    "Please consult 'docs/configuration.md' for setup instructions.",
                    "yellow",
                )
            )
            sys.exit(1)  # Aborts the program

        imagemagick_binary = resolve_imagemagick_binary()
        if not imagemagick_binary:
            logger.error(
                colored(
                    "IMAGEMAGICK_BINARY is not set and no ImageMagick executable was detected in PATH.",
                    "red",
                )
            )
            logger.error(
                colored(
                    "Set IMAGEMAGICK_BINARY in .env or install ImageMagick and add it to PATH.",
                    "yellow",
                )
            )
            sys.exit(1)

        os.environ["IMAGEMAGICK_BINARY"] = imagemagick_binary
    except Exception as e:
        logger.error(f"Error occurred while checking environment variables: {str(e)}")
        sys.exit(1)  # Aborts the program if an unexpected error occurs
