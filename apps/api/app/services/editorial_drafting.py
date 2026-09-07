"""공식 관광정보에서 매일 바뀌는 제주 여행 이야기 초안을 만든다."""

import hashlib
import json
import re
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
YEAR_PATTERN = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
EDITORIAL_SYSTEM_PROMPT = (
    "너는 제주 반려동물 여행 서비스 오멍가멍의 다정한 제주 안내견이다. 입력된 공식 "
    "사실만 사용하고 날짜, 운영시간, 반려동물 허용 여부를 추측하지 않는다. 원문 문장을 "
    "복사하지 말고 자연스럽게 요약한다. card_title과 title에는 source_title의 핵심 내용을 "
    "유지하면서 '~하개', '~해멍' 같은 강아지 말투를 자연스럽게 쓴다. 각 section의 "
    "heading도 해당 단락의 원래 내용을 유지하면서 짧고 자연스러운 강아지 말투로 쓴다. "
    "summary와 paragraphs는 독자에게 예의 있게 설명하는 부드러운 해요체 존댓말로 쓴다. "
    "tips는 혼디가 친구에게 알려주듯 반말 기반의 재치 있는 강아지 말투로 쓰되, 같은 "
    "종결 표현을 반복하지 말고 내용에 따라 다양하게 쓴다. 억지스러운 합성 어미나 "
    "'기억해두개' 같은 고정 문구를 모든 항목에 붙이지 않는다. 주소, 날짜, 수치와 "
    "주의사항은 정확하게 유지한다. 본문은 "
    "원문의 핵심을 충분히 살린 3개 섹션으로 요약하고, 각 섹션은 서로 다른 세부사항을 "
    "담은 2~3개 문단, 문단당 2~4문장으로 작성한다. 팁은 2~3개, 태그는 3~5개로 "
    "작성한다. 반려동물 동반 여부가 입력에 없으면 반드시 방문 전 확인해 달라고 안내한다."
)


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
    available = [
        item
        for item in contents
        if item.image_url
        and item.introduction
        and all(int(year) >= day.year for year in YEAR_PATTERN.findall(item.searchable_text))
    ]
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
            "heading": {
                "type": "string",
                "description": "단락 내용을 유지한 자연스러운 강아지 말투 소제목",
            },
            "paragraphs": {
                "type": "array",
                "items": {
                    "type": "string",
                    "description": "부드러운 해요체 존댓말 본문",
                },
                "minItems": 2,
                "maxItems": 3,
            },
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
                    "card_title": {
                        "type": "string",
                        "description": "원문 핵심을 유지한 자연스러운 강아지 말투 카드 제목",
                    },
                    "title": {
                        "type": "string",
                        "description": "원문 내용을 유지한 자연스러운 강아지 말투 제목",
                    },
                    "summary": {
                        "type": "string",
                        "description": "부드러운 해요체 존댓말 요약",
                    },
                    "sections": {
                        "type": "array",
                        "items": section,
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    "tips": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "표현을 반복하지 않는 자연스러운 강아지 반말 여행 팁",
                        },
                    },
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
        "source_body": source.body,
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
        temperature=0.5,
        messages=[
            {"role": "system", "content": EDITORIAL_SYSTEM_PROMPT},
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
    detail_images = [url for url in source.image_urls if url != source.image_url][:3]
    for section, image_url in zip(sections, detail_images, strict=False):
        section["image_url"] = image_url
        section["image_caption"] = f"{source.title} · 비짓제주 제공"
    return StoryDraft(
        card_title=str(data["card_title"])[:160],
        title=str(data["title"])[:200],
        summary=str(data["summary"])[:500],
        sections=sections,
        tips=[str(value)[:300] for value in _json_list(data.get("tips"))[:3]],
        tags=[str(value).lstrip("#")[:50] for value in _json_list(data.get("tags"))[:5]],
        model=model,
    )
