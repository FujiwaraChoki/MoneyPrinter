import requests

from typing import List
from termcolor import colored

def search_for_stock_videos(query: str, api_key: str) -> List[str]:
    """
    Searches for stock videos based on a query.

    Args:
        query (str): The query to search for.
        api_key (str): The API key to use.

    Returns:
        List[str]: A list of stock videos.
    """
    
    # Build headers
    headers = {
        "Authorization": api_key
    }

    # Build URL
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=1"

    # Send the request
    r = requests.get(url, headers=headers)

    # Parse the response
    response = r.json()

    # Get first video url
    video_urls = response["videos"][0]["video_files"]
    video_url = ""

    # Loop through video urls
    for video in video_urls:
        # Check if video has a download link
        if ".com/external" in video["link"]:
            # Set video url
            video_url = video["link"]

    # Let user know
    print(colored(f"\t=>{video_url}", "light_cyan"))

    # Return the video url
    return video_url
