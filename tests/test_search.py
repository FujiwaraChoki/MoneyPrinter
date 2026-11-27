import requests

import search


class _FakeResponse:
    def __init__(self, payload: dict, status_error: Exception | None = None):
        self._payload = payload
        self._status_error = status_error

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def json(self) -> dict:
        return self._payload


def test_search_resets_best_resolution_per_video(monkeypatch):
    payload = {
        "videos": [
            {
                "duration": 15,
                "video_files": [
                    {
                        "link": "https://videos.pexels.com/video-files/1/uhd.mp4",
                        "width": 3840,
                        "height": 2160,
                    },
                ],
            },
            {
                "duration": 12,
                "video_files": [
                    {
                        "link": "https://videos.pexels.com/video-files/2/sd.mp4",
                        "width": 640,
                        "height": 360,
                    },
                    {
                        "link": "https://videos.pexels.com/video-files/2/hd.mp4",
                        "width": 1920,
                        "height": 1080,
                    },
                ],
            },
            {
                "duration": 20,
                "video_files": [
                    {
                        "link": "https://videos.pexels.com/video-files/3/720p.mp4",
                        "width": 1280,
                        "height": 720,
                    },
                ],
            },
        ]
    }
    monkeypatch.setattr(
        search.requests, "get", lambda *args, **kwargs: _FakeResponse(payload)
    )

    urls = search.search_for_stock_videos("nature", "test-key", it=15, min_dur=10)

    assert urls == [
        "https://videos.pexels.com/video-files/1/uhd.mp4",
        "https://videos.pexels.com/video-files/2/hd.mp4",
        "https://videos.pexels.com/video-files/3/720p.mp4",
    ]


def test_search_handles_fewer_results_than_limit_without_error_log(monkeypatch):
    payload = {
        "videos": [
            {
                "duration": 15,
                "video_files": [
                    {
                        "link": "https://videos.pexels.com/video-files/10/hd.mp4",
                        "width": 1920,
                        "height": 1080,
                    }
                ],
            }
        ]
    }
    logged_levels: list[str] = []

    monkeypatch.setattr(
        search.requests, "get", lambda *args, **kwargs: _FakeResponse(payload)
    )
    monkeypatch.setattr(
        search, "log", lambda _msg, level="info": logged_levels.append(level)
    )

    urls = search.search_for_stock_videos("rare query", "test-key", it=15, min_dur=10)

    assert urls == ["https://videos.pexels.com/video-files/10/hd.mp4"]
    assert "error" not in logged_levels


def test_search_filters_duration_invalid_links_and_null_dimensions(monkeypatch):
    payload = {
        "videos": [
            {
                "duration": 5,
                "video_files": [
                    {
                        "link": "https://videos.pexels.com/video-files/short/hd.mp4",
                        "width": 1920,
                        "height": 1080,
                    }
                ],
            },
            {
                "duration": 14,
                "video_files": [
                    {
                        "link": "https://videos.pexels.com/video-files/null/hls.m3u8",
                        "width": None,
                        "height": None,
                    },
                    {
                        "link": "https://example.com/other/file.mp4",
                        "width": 3840,
                        "height": 2160,
                    },
                    {
                        "link": "https://videos.pexels.com/video-files/valid/hd.mp4",
                        "width": 1920,
                        "height": 1080,
                    },
                ],
            },
        ]
    }
    monkeypatch.setattr(
        search.requests, "get", lambda *args, **kwargs: _FakeResponse(payload)
    )

    urls = search.search_for_stock_videos("city", "test-key", it=5, min_dur=10)

    assert urls == ["https://videos.pexels.com/video-files/valid/hd.mp4"]


def test_search_uses_encoded_params_and_timeout(monkeypatch):
    captured: dict = {}

    def fake_get(url, *, headers=None, params=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["params"] = params
        captured["timeout"] = timeout
        return _FakeResponse({"videos": []})

    monkeypatch.setattr(search.requests, "get", fake_get)

    urls = search.search_for_stock_videos(
        "cats & dogs #1", "secret-key", it=15, min_dur=10
    )

    assert urls == []
    assert captured["url"] == search.PEXELS_SEARCH_URL
    assert captured["headers"] == {"Authorization": "secret-key"}
    assert captured["params"] == {"query": "cats & dogs #1", "per_page": 15}
    assert captured["timeout"] == search.REQUEST_TIMEOUT_SECONDS


def test_search_returns_empty_list_on_http_error(monkeypatch):
    logged_levels: list[str] = []

    monkeypatch.setattr(
        search.requests,
        "get",
        lambda *args, **kwargs: _FakeResponse(
            {}, status_error=requests.HTTPError("429 Too Many Requests")
        ),
    )
    monkeypatch.setattr(
        search, "log", lambda _msg, level="info": logged_levels.append(level)
    )

    urls = search.search_for_stock_videos("finance", "test-key", it=15, min_dur=10)

    assert urls == []
    assert "error" in logged_levels
