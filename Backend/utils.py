import os
import zipfile
import logging
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

def fetch_music(url: str) -> None:
    """
    Downloads music into songs/ directory to use with geneated videos.

    Args:
        url (str): URL to the ZIP File of the music.

    Returns:
        None
    """
    try:
        response = requests.get(url)
        with open("../Songs/songs.zip", "wb") as file:
            file.write(response.content)
        logger.info(colored(f"Downloaded ZIP from {url}.", "green"))

        # Unzip
        with zipfile.ZipFile("../Songs/songs.zip", "r") as zip_ref:
            zip_ref.extractall("../Songs")

        logger.info(colored(f"Unzipped songs.zip", "green"))

        # Remove the zip file
        os.remove("../Songs/songs.zip")
    except Exception as e:
        logger.error(f"Error occurred while fetching music: {str(e)}")
