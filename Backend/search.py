import requests
from typing import List
from termcolor import colored

def search_for_stock_videos(query: str, api_key: str, it: int, min_dur: int) -> List[str]:
    """
    Searches for stock videos based on a query.

    Args:
        query (str): The query to search for.
        api_key (str): The API key to use.

    Returns:
        List[str]: A list of stock videos.
    """
    try:
        # Build headers
        headers = {
            "Authorization": api_key
        }

        # Build URL
        qurl = f"https://api.pexels.com/videos/search?query={query}&per_page={it}"

        # Send the request
        r = requests.get(qurl, headers=headers)
        r.raise_for_status()  # Check for HTTP errors

        # Parse the response
        response = r.json()

        # Filter and extract video URLs
        video_url = [
            max(video.get("video_files", []), key=lambda x: x.get("width", 0) * x.get("height", 0), default={}).get("link", "")
            for video in response.get("videos", [])
            if video.get("duration", 0) >= min_dur
        ]

        # Let user know
        print(colored(f"\t=> \"{query}\" found {len(video_url)} Videos", "cyan"))

        # Return the video URLs
        return video_url

    except requests.exceptions.RequestException as e:
        print(colored("[-] Error occurred during API request:", "red"))
        print(colored(e, "red"))
    except Exception as e:
        print(colored("[-] An error occurred:", "red"))
        print(colored(e, "red"))
        return []
