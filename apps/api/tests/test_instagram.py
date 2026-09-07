from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import settings
from app.integrations.instagram import fetch_recent_posts, parse_posts


def test_parse_posts_sorts_latest_and_reads_carousel_images() -> None:
    posts = parse_posts(
        {
            "data": [
                {
                    "id": "old",
                    "caption": "오래된 글",
                    "media_type": "IMAGE",
                    "media_url": "https://cdn.example/old.jpg",
                    "permalink": "https://instagram.com/p/old",
                    "timestamp": "2026-01-01T00:00:00+0000",
                },
                {
                    "id": "new",
                    "caption": "제주 산책 #제주 #반려견 #제주",
                    "media_type": "CAROUSEL_ALBUM",
                    "media_url": "https://cdn.example/cover.jpg",
                    "permalink": "https://instagram.com/p/new",
                    "timestamp": "2026-09-01T00:00:00Z",
                    "username": "omeong",
                    "children": {
                        "data": [
                            {
                                "media_type": "IMAGE",
                                "media_url": "https://cdn.example/second.jpg",
                            },
                            {
                                "media_type": "VIDEO",
                                "thumbnail_url": "https://cdn.example/video.jpg",
                            },
                        ]
                    },
                },
            ]
        }
    )

    assert [post.media_id for post in posts] == ["new", "old"]
    assert posts[0].timestamp == datetime(2026, 9, 1, tzinfo=UTC)
    assert posts[0].hashtags == ("제주", "반려견")
    assert posts[0].image_urls == (
        "https://cdn.example/cover.jpg",
        "https://cdn.example/second.jpg",
        "https://cdn.example/video.jpg",
    )


def test_fetch_recent_posts_sends_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "instagram_user_id", "123")
    monkeypatch.setattr(settings, "instagram_access_token", "secret-token")
    monkeypatch.setattr(settings, "instagram_graph_api_version", "v25.0")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret-token"
        assert request.url.path == "/v25.0/123/media"
        assert "children" in request.url.params["fields"]
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "post-1",
                        "media_type": "VIDEO",
                        "thumbnail_url": "https://cdn.example/reel.jpg",
                        "permalink": "https://instagram.com/reel/one",
                        "timestamp": "2026-09-01T00:00:00Z",
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        posts = fetch_recent_posts(client=client)

    assert posts[0].image_urls == ("https://cdn.example/reel.jpg",)
