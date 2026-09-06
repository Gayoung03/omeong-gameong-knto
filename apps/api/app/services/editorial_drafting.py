"""공식 관광정보에서 매일 바뀌는 제주 여행 이야기 초안을 만든다."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from openai import OpenAI

from app.core.config import settings
from app.db.models.enums import EditorialStoryKind
from app.integrations.visitjeju import VisitJejuContent


@dataclass(frozen=True)
class StoryCandidate:
    kind: EditorialStoryKind
    category: str
    display_order: int
    source: VisitJejuContent


@dataclass(frozen=True)
class StoryDraft:
    card_title: str
    title: str
    summary: str
    sections: list[dict]
    tips: list[str]
    tags: list[str]
    model: str


SLOTS = (
    (EditorialStoryKind.EVENT, "행사·특별 개방", ("축제", "행사", "특별", "개방", "예약")),
    (EditorialStoryKind.WEATHER, "오늘 날씨 추천", ()),
    (EditorialStoryKind.STORY, "제주 여행 이야기", ("제주", "여행", "산책", "바다", "숲")),
    (EditorialStoryKind.GUIDE, "제주 자연유산", ("세계유산", "자연유산", "유네스코", "오름")),
)

WEATHER_KEYWORDS = {
    "rainy": ("실내", "박물관", "미술관", "전시", "카페"),
    "snowy": ("실내", "박물관", "미술관", "전시", "카페"),
    "windy": ("실내", "박물관", "미술관", "전시"),
    "sunny": ("산책", "해변", "오름", "숲", "공원"),
    "partly_cloudy": ("산책", "오름", "숲", "공원"),
    "cloudy": ("산책", "박물관", "숲", "카페"),
}


def _daily_rank(content_id: str, day: date) -> str:
    return hashlib.sha256(f"{day.isoformat()}:{content_id}".encode()).hexdigest()


def _json_list(value: object) -> list:
    """일부 모델이 도구 인자를 JSON 문자열로 감싸도 배열로 복구한다."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return [value]
    return value if isinstance(value, list) else []


def select_daily_candidates(
    contents: list[VisitJejuContent], *, day: date, weather_condition: str
) -> list[StoryCandidate]:
    """공식 이미지가 있는 서로 다른 콘텐츠 네 건을 날짜별로 고른다."""
    available = [item for item in contents if item.image_url and item.introduction]
    used: set[str] = set()
    selected: list[StoryCandidate] = []
    for order, (kind, category, base_keywords) in enumerate(SLOTS):
        keywords = (
            WEATHER_KEYWORDS.get(weather_condition, WEATHER_KEYWORDS["cloudy"])
            if kind == EditorialStoryKind.WEATHER
            else base_keywords
        )
        ranked = sorted(
            (item for item in available if item.content_id not in used),
            key=lambda item: (
                -sum(keyword.lower() in item.searchable_text for keyword in keywords),
                _daily_rank(item.content_id, day),
            ),
        )
        if not ranked:
            break
        chosen = ranked[0]
        used.add(chosen.content_id)
        selected.append(StoryCandidate(kind, category, order, chosen))
    return selected


def _draft_tool() -> dict:
    section = {
        "type": "object",
        "properties": {
            "heading": {"type": "string"},
            "paragraphs": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["heading", "paragraphs"],
        "additionalProperties": False,
    }
    return {
        "type": "function",
        "function": {
            "name": "write_editorial_story",
            "description": "제공된 공식 사실만으로 제주 여행 이야기 초안을 작성한다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "card_title": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "sections": {"type": "array", "items": section},
                    "tips": {"type": "array", "items": {"type": "string"}},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["card_title", "title", "summary", "sections", "tips", "tags"],
                "additionalProperties": False,
            },
        },
    }


def create_story_draft(candidate: StoryCandidate, *, weather_summary: str | None) -> StoryDraft:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다")
    source = candidate.source
    facts = {
        "card_type": candidate.kind.value,
        "source_title": source.title,
        "source_category": source.category,
        "source_introduction": source.introduction,
        "source_tags": source.tags,
        "source_address": source.address,
        "weather": weather_summary if candidate.kind == EditorialStoryKind.WEATHER else None,
    }
    model = settings.editorial_openai_model or settings.openai_model
    completion = OpenAI(
        api_key=settings.openai_api_key,
        timeout=30,
        max_retries=1,
    ).chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "너는 제주 반려동물 여행 서비스 오멍가멍의 에디터다. 입력된 공식 사실만 "
                    "사용하고 날짜, 운영시간, 반려동물 허용 여부를 추측하지 않는다. 원문 문장을 "
                    "복사하지 말고 짧게 새로 쓴다. 제목·도입·마무리 중 최대 두 곳에만 '했다개', "
                    "'좋다멍' 같은 말투를 자연스럽게 쓴다. 주소·수치·주의사항에는 캐릭터 말투를 "
                    "쓰지 않는다. 본문은 2개 섹션, 팁은 2~3개, 태그는 3~5개로 작성한다. "
                    "반려동물 동반 여부가 입력에 없으면 반드시 방문 전 확인하라고 쓴다."
                ),
            },
            {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
        ],
        tools=[_draft_tool()],
        tool_choice={"type": "function", "function": {"name": "write_editorial_story"}},
    )
    calls = completion.choices[0].message.tool_calls
    if not calls:
        raise RuntimeError("제주 여행 이야기 초안을 생성하지 못했습니다")
    data = json.loads(calls[0].function.arguments)
    sections = []
    for raw_section in _json_list(data.get("sections"))[:3]:
        if isinstance(raw_section, str):
            try:
                raw_section = json.loads(raw_section)
            except json.JSONDecodeError:
                continue
        if not isinstance(raw_section, dict):
            continue
        paragraphs = _json_list(raw_section.get("paragraphs"))[:3]
        if raw_section.get("heading") and paragraphs:
            sections.append(
                {
                    "id": f"section-{len(sections) + 1}",
                    "heading": str(raw_section["heading"])[:120],
                    "paragraphs": [str(value)[:1000] for value in paragraphs],
                }
            )
    if not sections:
        raise RuntimeError("생성된 초안에 본문이 없습니다")
    return StoryDraft(
        card_title=str(data["card_title"])[:160],
        title=str(data["title"])[:200],
        summary=str(data["summary"])[:500],
        sections=sections,
        tips=[str(value)[:300] for value in _json_list(data.get("tips"))[:3]],
        tags=[str(value).lstrip("#")[:50] for value in _json_list(data.get("tags"))[:5]],
        model=model,
    )
