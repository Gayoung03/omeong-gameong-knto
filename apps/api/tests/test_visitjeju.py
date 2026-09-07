import httpx
import pytest

from app.core.config import settings
from app.integrations.visitjeju import (
    VisitJejuAPIError,
    fetch_all_contents,
    fetch_content_detail,
    parse_contents,
)


def _item(content_id: str, *, title: str = "성산일출봉") -> dict:
    return {
        "contentsid": content_id,
        "contentscd": {"value": "c1", "label": "관광지"},
        "title": title,
        "roadaddress": "제주 서귀포시 성산읍 일출로 284-12",
        "alltag": "세계유산,오름,산책",
        "introduction": "바다 위에 솟은 제주 세계자연유산",
        "repPhoto": {
            "imgpath": "https://api.cdn.visitjeju.net/photomng/imgpath/photo.webp",
            "thumbnailpath": "https://api.cdn.visitjeju.net/photomng/thumbnailpath/photo.webp",
        },
    }


def test_parse_contents_reads_official_image_and_source_url() -> None:
    items, page_count = parse_contents(
        {"result": "00", "pageCount": 2, "items": [_item("CONT_1")]}
    )

    assert page_count == 2
    assert items[0].content_id == "CONT_1"
    assert items[0].category == "관광지"
    assert items[0].tags == ("세계유산", "오름", "산책")
    assert items[0].image_url.startswith("https://api.cdn.visitjeju.net/")
    assert items[0].source_url.endswith("contentsid=CONT_1")


def test_parse_contents_reads_live_nested_photo_shape() -> None:
    item = _item("CONT_LIVE")
    item["repPhoto"] = {
        "descseo": "대표사진",
        "photoid": {
            "photoid": 123,
            "imgpath": "https://api.cdn.visitjeju.net/live.webp",
            "thumbnailpath": "https://api.cdn.visitjeju.net/live-thumb.webp",
        },
    }

    items, _ = parse_contents({"result": 200, "pageCount": 1, "items": [item]})

    assert items[0].image_url == "https://api.cdn.visitjeju.net/live.webp"


def test_fetch_all_contents_follows_documented_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "visitjeju_api_key", "secret-key")

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        return httpx.Response(
            200,
            json={"result": "00", "pageCount": 2, "items": [_item(f"CONT_{page}")]},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        items = fetch_all_contents(client=client)

    assert [item.content_id for item in items] == ["CONT_1", "CONT_2"]


def test_html_block_page_becomes_explicit_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "visitjeju_api_key", "secret-key")
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                text="blocked",
                headers={"content-type": "text/html"},
            )
        )
    )

    with client, pytest.raises(VisitJejuAPIError, match="차단 페이지"):
        fetch_all_contents(client=client)


def test_fetch_content_detail_reads_body_and_gallery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "visitjeju_api_key", "secret-key")
    content, _ = parse_contents({"result": "00", "items": [_item("CONT_1")]})

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/contents/read"):
            return httpx.Response(
                200,
                json={
                    "result": "200",
                    "item": {
                        "photo": [
                            {
                                "photoid": {
                                    "imgpath": "https://api.cdn.visitjeju.net/gallery.webp"
                                }
                            }
                        ]
                    },
                },
            )
        return httpx.Response(
            200,
            text=(
                '<section class="detail_contents"><h5>상세정보</h5>'
                '<p>원문의 긴 첫 번째 문단입니다.</p>'
                '<img src="//api.cdn.visitjeju.net/body.webp">'
                "</section>"
            ),
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        detail = fetch_content_detail(content[0], client=client)

    assert detail.body == "원문의 긴 첫 번째 문단입니다."
    assert detail.image_urls == (
        content[0].image_url,
        "https://api.cdn.visitjeju.net/body.webp",
        "https://api.cdn.visitjeju.net/gallery.webp",
    )
