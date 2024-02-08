import requests
from typing import List
from termcolor import colored

def search_for_stock_videos(query: str, api_key: str, it: int, min_dur: int) -> List[str]:
    """
    Searches for stock videos based on a query.

    Args:
        query (str): The query to search for.
        api_key (str): The API key to use.
        it (int): The number of videos to retrieve.
        min_dur (int): The minimum duration of the video in seconds.

    Returns:
        List[str]: A list of stock video URLs.
    """
    try:
        # Build headers
        headers = {"Authorization": api_key}

        # Build URL
        qurl = f"https://api.pexels.com/videos/search?query={query}&per_page={it}"

        # Send the request
        r = requests.get(qurl, headers=headers)
        r.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the response
        response = r.json()

        # Parse each video
        video_urls = []
        for video in response.get("videos", []):
            if video.get("duration", 0) >= min_dur:
                best_video = max(video.get("video_files", []), key=lambda x: x.get("width", 0) * x.get("height", 0))
                if best_video:
                    video_urls.append(best_video["link"])

        # Let the user know
        print(colored(f"\t=> \"{query}\" found {len(video_urls)} videos", "cyan"))

        return video_urls

    except requests.exceptions.HTTPError as http_err:
        print(colored(f"HTTP error occurred: {http_err}", "red"))
    except requests.exceptions.RequestException as req_err:
        print(colored(f"Request error occurred: {req_err}", "red"))
    except Exception as err:
        print(colored(f"An error occurred: {err}", "red"))
