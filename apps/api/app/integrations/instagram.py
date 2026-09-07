"""Instagram 프로페셔널 계정 게시물 조회 클라이언트."""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import settings

GRAPH_URL = "https://graph.instagram.com"
REQUEST_TIMEOUT_SECONDS = 20.0
MEDIA_FIELDS = (
    "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,username,"
    "children{media_type,media_url,thumbnail_url}"
)


class InstagramAPIError(RuntimeError):
    """토큰을 노출하지 않는 Instagram 조회 오류."""


@dataclass(frozen=True)
class InstagramPost:
    media_id: str
    caption: str
    media_type: str
    permalink: str
    timestamp: datetime
    username: str
    image_urls: tuple[str, ...]

    @property
    def hashtags(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(re.findall(r"(?<!\w)#([^\s#]+)", self.caption)))


def _text(value: object) -> str:
    return str(value or "").strip()


def _image_url(item: dict) -> str:
    if _text(item.get("media_type")) == "VIDEO":
        return _text(item.get("thumbnail_url"))
    return _text(item.get("media_url") or item.get("thumbnail_url"))


def _parse_timestamp(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(_text(value).replace("Z", "+00:00"))
    except ValueError:
        raise InstagramAPIError("Instagram 게시물 날짜 형식이 올바르지 않습니다") from None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def parse_posts(payload: object) -> list[InstagramPost]:
    if not isinstance(payload, dict):
        raise InstagramAPIError("Instagram API 응답 형식이 올바르지 않습니다")
    error = payload.get("error")
    if isinstance(error, dict):
        message = _text(error.get("message"))
        raise InstagramAPIError(f"Instagram API 오류: {message or '요청 실패'}")
    items = payload.get("data") or []
    if not isinstance(items, list):
        raise InstagramAPIError("Instagram 게시물 목록이 올바르지 않습니다")

    posts: list[InstagramPost] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        images = []
        hero = _image_url(item)
        if hero:
            images.append(hero)
        children = item.get("children") or {}
        if isinstance(children, dict):
            for child in children.get("data") or []:
                if not isinstance(child, dict):
                    continue
                image = _image_url(child)
                if image and image not in images:
                    images.append(image)
        media_id = _text(item.get("id"))
        permalink = _text(item.get("permalink"))
        if not media_id or not permalink or not images:
            continue
        posts.append(
            InstagramPost(
                media_id=media_id,
                caption=_text(item.get("caption")),
                media_type=_text(item.get("media_type")),
                permalink=permalink,
                timestamp=_parse_timestamp(item.get("timestamp")),
                username=_text(item.get("username")) or "instagram",
                image_urls=tuple(images),
            )
        )
    return sorted(posts, key=lambda post: post.timestamp, reverse=True)


def fetch_recent_posts(
    *, limit: int = 10, client: httpx.Client | None = None
) -> list[InstagramPost]:
    if not settings.instagram_user_id or not settings.instagram_access_token:
        raise InstagramAPIError(
            "INSTAGRAM_USER_ID와 INSTAGRAM_ACCESS_TOKEN을 모두 설정해야 합니다"
        )
    version = settings.instagram_graph_api_version.strip("/")
    url = f"{GRAPH_URL}/{version}/{settings.instagram_user_id}/media"

    def fetch(http: httpx.Client) -> list[InstagramPost]:
        response = http.get(
            url,
            params={"fields": MEDIA_FIELDS, "limit": max(1, min(limit, 100))},
            headers={"Authorization": f"Bearer {settings.instagram_access_token}"},
        )
        response.raise_for_status()
        return parse_posts(response.json())

    try:
        if client is not None:
            return fetch(client)
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as owned_client:
            return fetch(owned_client)
    except InstagramAPIError:
        raise
    except httpx.HTTPStatusError as error:
        raise InstagramAPIError(
            f"Instagram API 요청이 거절됐습니다({error.response.status_code})"
        ) from None
    except (httpx.HTTPError, TypeError, ValueError):
        raise InstagramAPIError("Instagram 게시물 조회에 실패했습니다") from None
