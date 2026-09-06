from datetime import date

from app.db.models.enums import EditorialStoryKind
from app.integrations.visitjeju import VisitJejuContent
from app.services.editorial_drafting import select_daily_candidates


def _content(index: int, text: str) -> VisitJejuContent:
    return VisitJejuContent(
        content_id=f"CONT_{index}",
        title=text,
        category="관광지",
        introduction=f"{text} 공식 소개",
        tags=(text,),
        address="제주",
        image_url=f"https://api.cdn.visitjeju.net/{index}.webp",
        source_url=f"https://www.visitjeju.net/detail/{index}",
    )


def test_daily_candidates_fill_four_distinct_slots() -> None:
    contents = [
        _content(1, "특별 개방 행사"),
        _content(2, "실내 박물관"),
        _content(3, "제주 바다 산책"),
        _content(4, "유네스코 세계유산"),
        _content(5, "제주 숲"),
    ]

    selected = select_daily_candidates(
        contents, day=date(2026, 9, 6), weather_condition="rainy"
    )

    assert [item.kind for item in selected] == [
        EditorialStoryKind.EVENT,
        EditorialStoryKind.WEATHER,
        EditorialStoryKind.STORY,
        EditorialStoryKind.GUIDE,
    ]
    assert len({item.source.content_id for item in selected}) == 4
    assert selected[0].source.content_id == "CONT_1"
    assert selected[1].source.content_id == "CONT_2"
