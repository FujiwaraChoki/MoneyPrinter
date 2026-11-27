import requests

from typing import List
from logstream import log

PEXELS_SEARCH_URL = "https://api.pexels.com/videos/search"
REQUEST_TIMEOUT_SECONDS = 30


def search_for_stock_videos(
    query: str, api_key: str, it: int, min_dur: int
) -> List[str]:
    """
    Searches for stock videos based on a query.

    Args:
        query (str): The query to search for.
        api_key (str): The API key to use.
        it (int): Maximum number of videos to inspect from Pexels.
        min_dur (int): Minimum video duration in seconds.

    Returns:
        List[str]: A list of stock video download URLs.
    """
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": it}

    video_urls: List[str] = []
    try:
        r = requests.get(
            PEXELS_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        r.raise_for_status()
        response = r.json()

        videos = response.get("videos") or []
        for video_item in videos[:it]:
            duration = video_item.get("duration") or 0
            if duration < min_dur:
                continue

            raw_urls = video_item.get("video_files") or []
            best_video_url = ""
            best_video_res = 0

            for video in raw_urls:
                link = video.get("link") or ""
                width = video.get("width") or 0
                height = video.get("height") or 0
                if ".com/video-files" in link:
                    resolution = width * height
                    if resolution > best_video_res:
                        best_video_url = link
                        best_video_res = resolution

            if best_video_url:
                video_urls.append(best_video_url)
    except Exception as e:
        log("[-] No Videos found.", "error")
        log(str(e), "error")

    log(f'\t=> "{query}" found {len(video_urls)} Videos', "info")

    return video_urls
