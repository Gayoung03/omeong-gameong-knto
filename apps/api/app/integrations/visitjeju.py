"""비짓제주 관광정보 Open API 클라이언트."""

from dataclasses import dataclass

import httpx

from app.core.config import settings

SEARCH_URL = "https://api.visitjeju.net/vsjApi/contents/searchList"
DETAIL_URL = "https://www.visitjeju.net/kr/detail/view?contentsid={}"
REQUEST_TIMEOUT_SECONDS = 20.0


class VisitJejuAPIError(RuntimeError):
    """키를 노출하지 않는 비짓제주 조회 오류."""


@dataclass(frozen=True)
class VisitJejuContent:
    content_id: str
    title: str
    category: str
    introduction: str
    tags: tuple[str, ...]
    address: str | None
    image_url: str
    source_url: str

    @property
    def searchable_text(self) -> str:
        return " ".join((self.title, self.category, self.introduction, *self.tags)).lower()


def _text(value: object) -> str:
    return str(value or "").replace("\ufeff", "").strip()


def _nested_label(value: object) -> str:
    if isinstance(value, dict):
        return _text(value.get("label") or value.get("value"))
    return _text(value)


def _image_url(item: dict) -> str:
    photo = item.get("repPhoto") or item.get("repphoto") or {}
    if isinstance(photo, list):
        photo = photo[0] if photo else {}
    if isinstance(photo, dict):
        nested = photo.get("photoid")
        if isinstance(nested, dict):
            photo = nested
        return _text(photo.get("imgpath") or photo.get("thumbnailpath"))
    return ""


def parse_contents(payload: object) -> tuple[list[VisitJejuContent], int]:
    """문서의 top-level 응답과 일부 운영 응답의 result 래핑을 모두 읽는다."""
    if not isinstance(payload, dict):
        raise VisitJejuAPIError("비짓제주 API 응답 형식이 올바르지 않습니다")
    container = payload.get("result") if isinstance(payload.get("result"), dict) else payload
    code = container.get("resultCode") or payload.get("result")
    if code not in (None, "00", 0, 200, "200", "success"):
        message = _text(container.get("resultMessage") or payload.get("resultMessage"))
        raise VisitJejuAPIError(f"비짓제주 API 오류: {message or code}")
    raw_items = container.get("items") or []
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("item") or []
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    if not isinstance(raw_items, list):
        raise VisitJejuAPIError("비짓제주 API 콘텐츠 목록이 올바르지 않습니다")

    contents: list[VisitJejuContent] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        content_id = _text(item.get("contentsid") or item.get("contentsId"))
        title = _text(item.get("title"))
        image_url = _image_url(item)
        if not content_id or not title or not image_url:
            continue
        raw_tags = _text(item.get("alltag") or item.get("tag")).split(",")
        tags = tuple(part.strip() for part in raw_tags if part.strip())
        contents.append(
            VisitJejuContent(
                content_id=content_id,
                title=title,
                category=_nested_label(item.get("contentscd")) or "제주 여행",
                introduction=_text(item.get("introduction")),
                tags=tags,
                address=_text(item.get("roadaddress") or item.get("address")) or None,
                image_url=image_url,
                source_url=DETAIL_URL.format(content_id),
            )
        )
    page_count = int(container.get("pageCount") or payload.get("pageCount") or 1)
    return contents, max(1, page_count)


def fetch_all_contents(
    *, client: httpx.Client | None = None, max_pages: int = 100
) -> list[VisitJejuContent]:
    if not settings.visitjeju_api_key:
        raise VisitJejuAPIError("VISITJEJU_API_KEY가 설정되지 않았습니다")

    def fetch(http: httpx.Client) -> list[VisitJejuContent]:
        result: list[VisitJejuContent] = []
        page_count = 1
        page = 1
        while page <= min(page_count, max_pages):
            response = http.get(
                SEARCH_URL,
                params={"apiKey": settings.visitjeju_api_key, "locale": "kr", "page": page},
                headers={
                    "Accept": "application/json",
                    "User-Agent": "OmeongGameong/1.0 (editorial sync)",
                },
            )
            response.raise_for_status()
            if "json" not in response.headers.get("content-type", "").lower():
                raise VisitJejuAPIError("비짓제주 API가 JSON 대신 차단 페이지를 반환했습니다")
            items, discovered_pages = parse_contents(response.json())
            page_count = min(discovered_pages, max_pages)
            result.extend(items)
            page += 1
        return result

    try:
        if client is not None:
            return fetch(client)
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as owned_client:
            return fetch(owned_client)
    except VisitJejuAPIError:
        raise
    except httpx.HTTPStatusError as error:
        raise VisitJejuAPIError(
            f"비짓제주 API 요청이 거절됐습니다({error.response.status_code})"
        ) from None
    except (httpx.HTTPError, TypeError, ValueError):
        raise VisitJejuAPIError("비짓제주 관광정보 조회에 실패했습니다") from None
