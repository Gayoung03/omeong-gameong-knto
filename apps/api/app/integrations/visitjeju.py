"""비짓제주 관광정보 Open API 클라이언트."""

import re
from dataclasses import dataclass, replace
from html.parser import HTMLParser

import httpx

from app.core.config import settings

SEARCH_URL = "https://api.visitjeju.net/vsjApi/contents/searchList"
READ_URL = "https://api.visitjeju.net/vsjApi/contents/read"
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
    body: str = ""
    image_urls: tuple[str, ...] = ()

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


def _photo_urls(item: dict) -> list[str]:
    result: list[str] = []
    for photo in item.get("photo") or []:
        if not isinstance(photo, dict):
            continue
        nested = photo.get("photoid")
        if not isinstance(nested, dict):
            continue
        url = _text(nested.get("imgpath") or nested.get("thumbnailpath"))
        if url and url not in result:
            result.append(url)
    return result


class _DetailPageParser(HTMLParser):
    """상세 페이지의 본문 영역만 텍스트와 이미지로 읽는다."""

    def __init__(self) -> None:
        super().__init__()
        self.in_detail = False
        self.detail_section_depth = 0
        self.text: list[str] = []
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "section" and "detail_contents" in classes:
            self.in_detail = True
            self.detail_section_depth = 1
            return
        if not self.in_detail:
            return
        if tag == "section":
            self.detail_section_depth += 1
        if tag == "img":
            url = _text(attributes.get("src"))
            if url.startswith("//"):
                url = f"https:{url}"
            if url and url not in self.images:
                self.images.append(url)
        if tag in {"br", "div", "h1", "h2", "h3", "h4", "h5", "li", "p"}:
            self.text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_detail:
            return
        if tag in {"div", "h1", "h2", "h3", "h4", "h5", "li", "p"}:
            self.text.append("\n")
        if tag == "section":
            self.detail_section_depth -= 1
            if self.detail_section_depth == 0:
                self.in_detail = False

    def handle_data(self, data: str) -> None:
        if self.in_detail:
            self.text.append(data)

    def body(self) -> str:
        lines = [re.sub(r"\s+", " ", line).strip() for line in "".join(self.text).splitlines()]
        return "\n".join(
            line for line in lines if line and line not in {"상세정보", "펼치기 +"}
        )[:12_000]


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


def fetch_content_detail(
    content: VisitJejuContent, *, client: httpx.Client | None = None
) -> VisitJejuContent:
    """선택된 콘텐츠의 상세 본문과 사진을 보강한다."""

    def fetch(http: httpx.Client) -> VisitJejuContent:
        response = http.get(
            READ_URL,
            params={
                "apiKey": settings.visitjeju_api_key,
                "locale": "kr",
                "contentsid": content.content_id,
            },
            headers={"Accept": "application/json", "User-Agent": "OmeongGameong/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
        container = payload.get("result") if isinstance(payload.get("result"), dict) else payload
        if container.get("result") not in (None, "00", 0, 200, "200", "success"):
            raise VisitJejuAPIError("비짓제주 상세 API 오류")
        item = container.get("item") or {}

        page = http.get(content.source_url, headers={"User-Agent": "OmeongGameong/1.0"})
        page.raise_for_status()
        parser = _DetailPageParser()
        parser.feed(page.text)

        images = []
        for url in (content.image_url, *parser.images, *_photo_urls(item)):
            if url and url not in images:
                images.append(url)
        return replace(
            content,
            body=parser.body() or content.introduction,
            image_urls=tuple(images),
        )

    try:
        if client is not None:
            return fetch(client)
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as owned_client:
            return fetch(owned_client)
    except VisitJejuAPIError:
        raise
    except (httpx.HTTPError, TypeError, ValueError):
        raise VisitJejuAPIError("비짓제주 상세 관광정보 조회에 실패했습니다") from None
