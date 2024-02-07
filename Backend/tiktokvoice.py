# author: GiorDior aka Giorgio
# date: 12.06.2023
# topic: TikTok-Voice-TTS
# version: 1.0
# credits: https://github.com/oscie57/tiktok-voice

# --- MODIFIED VERSION --- #

from playsound import playsound
from typing import List

import threading
import requests
import base64

VOICES = [
    # DISNEY VOICES
    "en_us_ghostface",  # Ghost Face
    "en_us_chewbacca",  # Chewbacca
    "en_us_c3po",  # C3PO
    "en_us_stitch",  # Stitch
    "en_us_stormtrooper",  # Stormtrooper
    "en_us_rocket",  # Rocket
    # ENGLISH VOICES
    "en_au_001",  # English AU - Female
    "en_au_002",  # English AU - Male
    "en_uk_001",  # English UK - Male 1
    "en_uk_003",  # English UK - Male 2
    "en_us_001",  # English US - Female (Int. 1)
    "en_us_002",  # English US - Female (Int. 2)
    "en_us_006",  # English US - Male 1
    "en_us_007",  # English US - Male 2
    "en_us_009",  # English US - Male 3
    "en_us_010",  # English US - Male 4
    # EUROPE VOICES
    "fr_001",  # French - Male 1
    "fr_002",  # French - Male 2
    "de_001",  # German - Female
    "de_002",  # German - Male
    "es_002",  # Spanish - Male
    # AMERICA VOICES
    "es_mx_002",  # Spanish MX - Male
    "br_001",  # Portuguese BR - Female 1
    "br_003",  # Portuguese BR - Female 2
    "br_004",  # Portuguese BR - Female 3
    "br_005",  # Portuguese BR - Male
    # ASIA VOICES
    "id_001",  # Indonesian - Female
    "jp_001",  # Japanese - Female 1
    "jp_003",  # Japanese - Female 2
    "jp_005",  # Japanese - Female 3
    "jp_006",  # Japanese - Male
    "kr_002",  # Korean - Male 1
    "kr_003",  # Korean - Female
    "kr_004",  # Korean - Male 2
    # SINGING VOICES
    "en_female_f08_salut_damour",  # Alto
    "en_male_m03_lobby",  # Tenor
    "en_female_f08_warmy_breeze",  # Warmy Breeze
    "en_male_m03_sunshine_soon",  # Sunshine Soon
    # OTHER
    "en_male_narration",  # narrator
    "en_male_funny",  # wacky
    "en_female_emotional",  # peaceful
]

ENDPOINTS = [
    "https://tiktok-tts.weilnet.workers.dev/api/generation",
    "https://tiktoktts.com/api/tiktok-tts",
]
current_endpoint = 0
# in one conversion, the text can have a maximum length of 300 characters
TEXT_BYTE_LIMIT = 300


# create a list by splitting a string, every element has n chars
def split_string(string: str, chunk_size: int) -> List[str]:
    """    Split the input string into chunks of specified size.

    Args:
        string (str): The input string to be split into chunks.
        chunk_size (int): The size of each chunk.

    Returns:
        List[str]: A list of strings, each representing a chunk of the input string.
    """

    words = string.split()
    result = []
    current_chunk = ""
    for word in words:
        if (
            len(current_chunk) + len(word) + 1 <= chunk_size
        ):  # Check if adding the word exceeds the chunk size
            current_chunk += f" {word}"
        else:
            if current_chunk:  # Append the current chunk if not empty
                result.append(current_chunk.strip())
            current_chunk = word
    if current_chunk:  # Append the last chunk if not empty
        result.append(current_chunk.strip())
    return result


# checking if the website that provides the service is available
def get_api_response() -> requests.Response:
    """    Get the API response from the specified endpoint.

    Returns:
        requests.Response: The response object from the API.

    Raises:
        This function may raise the following exceptions:
        requests.exceptions.RequestException: If an error occurs while fetching the API response.
    """

    url = f'{ENDPOINTS[current_endpoint].split("/a")[0]}'
    response = requests.get(url)
    return response


# saving the audio file
def save_audio_file(base64_data: str, filename: str = "output.mp3") -> None:
    """    Save the audio file from base64 encoded data to the specified filename.

    Args:
        base64_data (str): The base64 encoded audio data.
        filename (str?): The name of the output file. Defaults to "output.mp3".

    Returns:
        None

    Raises:
        TypeError: If base64_data is not a string.
        TypeError: If filename is not a string.
        ValueError: If the base64 encoded data is invalid.
    """

    audio_bytes = base64.b64decode(base64_data)
    with open(filename, "wb") as file:
        file.write(audio_bytes)


# send POST request to get the audio data
def generate_audio(text: str, voice: str) -> bytes:
    """    Send a POST request to get the audio data.

    Args:
        text (str): The text to be converted to audio.
        voice (str): The voice to be used for the audio.

    Returns:
        bytes: The audio data in bytes.

    Raises:
        This function may raise exceptions of the following types:
        requests.exceptions.RequestException: If a request error occurs.
    """

    url = f"{ENDPOINTS[current_endpoint]}"
    headers = {"Content-Type": "application/json"}
    data = {"text": text, "voice": voice}
    response = requests.post(url, headers=headers, json=data)
    return response.content


# creates an text to speech audio file
def tts(
    text: str,
    voice: str = "none",
    filename: str = "output.mp3",
    play_sound: bool = False,
) -> None:
    """    Create a text-to-speech audio file.

    Args:
        text (str): The text to be converted to speech.
        voice (str?): The voice to be used for speech synthesis. Defaults to "none".
        filename (str?): The name of the output audio file. Defaults to "output.mp3".
        play_sound (bool?): Flag to indicate whether to play the generated audio file. Defaults to False.

    Returns:
        None

    Raises:
        ValueError: If no voice is selected or the selected voice does not exist.
        ValueError: If the input text is empty.
        RuntimeError: If an error occurs while generating the audio.
    """

    # checking if the website is available
    global current_endpoint

    if get_api_response().status_code == 200:
        print("Service available!")
    else:
        current_endpoint = (current_endpoint + 1) % 2
        if get_api_response().status_code == 200:
            print("Service available!")
        else:
            print(
                "Service not available and probably temporarily rate limited, try again later..."
            )
            return

    # checking if arguments are valid
    if voice == "none":
        print("No voice has been selected")
        return

    if voice not in VOICES:
        print("Voice does not exist")
        return

    if not text:
        print("Insert a valid text")
        return

    # creating the audio file
    try:
        if len(text) < TEXT_BYTE_LIMIT:
            audio = generate_audio((text), voice)
            if current_endpoint == 0:
                audio_base64_data = str(audio).split('"')[5]
            else:
                audio_base64_data = str(audio).split('"')[3].split(",")[1]

            if audio_base64_data == "error":
                print("This voice is unavailable right now")
                return

        else:
            # Split longer text into smaller parts
            text_parts = split_string(text, 299)
            audio_base64_data = [None] * len(text_parts)

            # Define a thread function to generate audio for each text part
            def generate_audio_thread(text_part, index):
                """                Generate audio for each text part in a separate thread.

                Args:
                    text_part (str): The text part for which audio needs to be generated.
                    index (int): The index of the text part.

                Returns:
                    None

                Raises:
                    ValueError: If the provided text_part is empty or None.
                    TypeError: If the index is not an integer.
                """

                audio = generate_audio(text_part, voice)
                if current_endpoint == 0:
                    base64_data = str(audio).split('"')[5]
                else:
                    base64_data = str(audio).split('"')[3].split(",")[1]

                if audio_base64_data == "error":
                    print("This voice is unavailable right now")
                    return "error"

                audio_base64_data[index] = base64_data

            threads = []
            for index, text_part in enumerate(text_parts):
                # Create and start a new thread for each text part
                thread = threading.Thread(
                    target=generate_audio_thread, args=(text_part, index)
                )
                thread.start()
                threads.append(thread)

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Concatenate the base64 data in the correct order
            audio_base64_data = "".join(audio_base64_data)

        save_audio_file(audio_base64_data, filename)
        print(f"Audio file saved successfully as '{filename}'")
        if play_sound:
            playsound(filename)

    except Exception as e:
        print("Error occurred while generating audio:", e)
