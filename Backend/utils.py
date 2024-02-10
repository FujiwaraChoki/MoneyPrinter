import os
import json
import random
import logging
import zipfile
import requests

from termcolor import colored

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
        if not os.path.exists(path):
            os.mkdir(path)
            logger.info(f"Created directory: {path}")

        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            os.remove(file_path)
            logger.info(f"Removed file: {file_path}")

        logger.info(colored(f"Cleaned {path} directory", "green"))
    except Exception as e:
        logger.error(f"Error occurred while cleaning directory {path}: {str(e)}")

def fetch_songs(zip_url: str) -> None:
    """
    Downloads songs into songs/ directory to use with geneated videos.

    Args:
        zip_url (str): The URL to the zip file containing the songs.

    Returns:
        None
    """
    try:
        logger.info(colored(f" => Fetching songs...", "magenta"))

        files_dir = "../Songs"
        if not os.path.exists(files_dir):
            os.mkdir(files_dir)
            logger.info(colored(f"Created directory: {files_dir}", "green"))

        # Download songs
        response = requests.get(zip_url)

        # Save the zip file
        with open("../Songs/songs.zip", "wb") as file:
            file.write(response.content)

        # Unzip the file
        with zipfile.ZipFile("../Songs/songs.zip", "r") as file:
            file.extractall("../Songs")

        # Remove the zip file
        os.remove("../Songs/songs.zip")

        logger.info(colored(" => Downloaded Songs to ../Songs.", "green"))

    except Exception as e:
        logger.error(colored(f"Error occurred while fetching songs: {str(e)}", "red"))

def choose_random_song() -> str:
    """
    Chooses a random song from the songs/ directory.

    Returns:
        str: The path to the chosen song.
    """
    try:
        songs = os.listdir("../Songs")
        song = random.choice(songs)
        logger.info(colored(f"Chose song: {song}", "green"))
        return f"../Songs/{song}"
    except Exception as e:
        logger.error(colored(f"Error occurred while choosing random song: {str(e)}", "red"))
