"""챗봇 답변 생성.

질문을 받아 **우리 DB 에서 장소를 찾고**, 그 결과로 답변 문장을 만든다.

## 부르는 쪽은 OpenAI 를 몰라도 된다

엔드포인트는 `generate_answer()` 하나만 부르고 `Answer` 를 받는다. 벤더를 바꾸거나
스트리밍으로 옮길 때 **이 파일 안만 고치면 된다** — `travel_log_image.py` 와 같은
방식이다.

## 흐름

```
질문
 ↓ ① OpenAI 에 질문 + 도구 설명을 보냄
 ↓ ② "search_places(지역=애월, 카테고리=cafe) 불러줘" 라고 답이 옴
 ↓ ③ 우리가 DB 를 찾아 장소 5곳을 돌려줌
 ↓ ④ 그 장소들로 답변 문장이 옴
답변
```

②③이 여러 번 돌 수 있다(조건을 바꿔 다시 찾는 경우). `MAX_TOOL_ROUNDS` 로 막는다 —
막지 않으면 모델이 검색만 반복하다 요금만 쓴다.

## 지어내지 못하게 하는 장치가 둘이다

1. 시스템 프롬프트에 "도구가 찾아준 장소만 말하라"고 적는다(`prompts/system.py`)
2. **답변에 이름이 등장한 장소만** `referenced_place_ids` 로 남긴다 — 지도에 핀을
   찍는 것은 이 목록이라, 지어낸 이름은 애초에 핀이 될 수 없다(설계 결정 C4)
"""

import json
import uuid
from dataclasses import dataclass, field

from openai import APITimeoutError, OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.enums import MessageRole, PetPolicyType, PlaceEnvironment
from app.rag.prompts.system import build_system_prompt
from app.rag.retrieval.place_search import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    PlaceHit,
    PlaceSort,
    UnknownVocabularyError,
    search_places,
)
from app.rag.vocabulary import CATEGORIES, REGIONS, TAGS

#: 도구 호출을 몇 번까지 허용할지. 설계 결정 B7 — 조건을 완화해 다시 찾는 것까지다.
MAX_TOOL_ROUNDS = 3

#: 대화 맥락으로 함께 보낼 지난 메시지 수(10턴 = 20개). 설계 결정 C2.
#: 상한이 없으면 대화가 길수록 비싸지고, 언젠가 모델 입력 한도를 넘어 에러만 뱉는다.
HISTORY_LIMIT = 20

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search_places",
        "description": (
            "제주의 반려동물 동반 장소를 조건으로 찾는다. "
            "장소를 추천하기 전에 반드시 이 도구로 찾아야 한다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "region": {
                    "type": "string",
                    "enum": list(REGIONS),
                    "description": "관광권역. 사용자가 방위로 물으면 시스템 안내의 표로 옮긴다.",
                },
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "pet_policy": {
                    "type": "array",
                    "items": {"type": "string", "enum": [p.value for p in PetPolicyType]},
                    "description": (
                        "생략하면 동반 불가인 곳만 빠지고 나머지는 모두 나온다. "
                        "'실내까지 들어갈 수 있는' 처럼 분명할 때만 지정한다."
                    ),
                },
                "environment": {
                    "type": "string",
                    "enum": [e.value for e in PlaceEnvironment],
                    "description": "실내/실외. 비 오는 날 질문 등에 쓴다.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "enum": list(TAGS)},
                    "description": "분위기 질문을 옮겨 담는 자리. 여러 개면 전부 가진 곳만 나온다.",
                },
                "sort": {"type": "string", "enum": [s.value for s in PlaceSort]},
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT},
            },
            "additionalProperties": False,
        },
    },
}


class ChatGenerationError(RuntimeError):
    """답변을 만들지 못했다. 부르는 쪽이 `llm_failed` 로 내려준다."""


class ChatTimeoutError(ChatGenerationError):
    """모델이 제때 답하지 않았다. 부르는 쪽이 `llm_timeout` 으로 내려준다."""


@dataclass(frozen=True)
class Answer:
    """엔드포인트가 그대로 저장하면 되는 답변."""

    content: str
    model_name: str
    referenced_place_ids: list[uuid.UUID] = field(default_factory=list)


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise ChatGenerationError("OPENAI_API_KEY 가 설정되지 않았습니다")
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.chat_timeout_seconds,
        max_retries=0,  # 서버가 몰래 재시도하지 않는다(설계 결정 E4).
    )


def _describe(hit: PlaceHit) -> dict:
    """장소 하나를 모델에게 보여줄 모양으로. 설계 결정 B6.

    `place_id` 를 함께 준다. 모델이 답변에 쓰지는 않지만, 어떤 장소를 봤는지
    우리가 대조할 수 있어야 한다.
    """
    described = {
        "place_id": str(hit.place_id),
        "name": hit.name,
        "category": hit.category,
        "region": hit.region,
        "pet_policy": hit.pet_policy_type.value,
    }
    if hit.rating is not None:
        described["rating"] = hit.rating
        described["review_count"] = hit.review_count
    if hit.description:
        described["description"] = hit.description
    return described


def _run_search(db: Session, raw_arguments: str) -> tuple[str, list[PlaceHit]]:
    """모델이 넘긴 인자로 검색한다. 결과를 모델에게 돌려줄 문자열로 만든다."""
    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return "검색 조건을 읽지 못했습니다. 다시 시도하세요.", []

    try:
        hits = search_places(
            db,
            region=arguments.get("region"),
            category=arguments.get("category"),
            pet_policy=[PetPolicyType(p) for p in arguments.get("pet_policy") or []] or None,
            environment=(
                PlaceEnvironment(arguments["environment"])
                if arguments.get("environment")
                else None
            ),
            tags=arguments.get("tags"),
            sort=PlaceSort(arguments.get("sort") or PlaceSort.RATING),
            limit=int(arguments.get("limit") or DEFAULT_LIMIT),
        )
    except UnknownVocabularyError as error:
        # 조용히 0건을 주면 모델이 "그런 곳이 없다"고 답한다. 실제로는 값을
        # 잘못 고른 것이라, 무엇이 틀렸는지 알려주고 다시 고르게 한다.
        return str(error), []
    except (ValueError, TypeError) as error:
        return f"검색 조건이 잘못됐습니다: {error}", []

    if not hits:
        return "조건에 맞는 장소가 없습니다.", []
    return json.dumps([_describe(hit) for hit in hits], ensure_ascii=False), hits


def _mentioned(content: str, seen: dict[uuid.UUID, PlaceHit]) -> list[uuid.UUID]:
    """답변에 **이름이 등장한** 장소만 고른다. 설계 결정 C4.

    검색은 다섯 곳을 가져와도 답변이 세 곳만 말했다면 지도 핀도 세 개여야 한다.
    모델에게 "어느 걸 언급했니"라고 다시 묻지 않는다 — 요금이 한 번 더 들고,
    이름 대조로 충분하다.
    """
    return [place_id for place_id, hit in seen.items() if hit.name in content]


def generate_answer(db: Session, history: list[dict], question: str) -> Answer:
    """질문 하나에 대한 답변을 만든다.

    `history` 는 오래된 순으로 정렬된 `{"role", "content"}` 목록이다.
    `HISTORY_LIMIT` 개까지만 쓴다.
    """
    client = _client()
    messages: list[dict] = [
        {"role": "system", "content": build_system_prompt()},
        *history[-HISTORY_LIMIT:],
        {"role": "user", "content": question},
    ]

    #: 이번 답변을 만들며 모델이 본 장소. 이름 대조에 쓴다.
    seen: dict[uuid.UUID, PlaceHit] = {}

    try:
        for _round in range(MAX_TOOL_ROUNDS):
            completion = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=[SEARCH_TOOL],
            )
            choice = completion.choices[0].message

            if not choice.tool_calls:
                content = (choice.content or "").strip()
                if not content:
                    raise ChatGenerationError("빈 답변을 받았습니다")
                return Answer(
                    content=content,
                    model_name=completion.model,
                    referenced_place_ids=_mentioned(content, seen),
                )

            messages.append(choice.model_dump(exclude_none=True))
            for call in choice.tool_calls:
                result, hits = _run_search(db, call.function.arguments)
                seen.update({hit.place_id: hit for hit in hits})
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )
    except APITimeoutError as error:
        raise ChatTimeoutError("답변 생성이 시간을 초과했습니다") from error
    except ChatGenerationError:
        raise
    except Exception as error:  # noqa: BLE001 - 벤더 예외를 우리 것으로 감싼다
        raise ChatGenerationError(f"답변 생성에 실패했습니다: {error}") from error

    # 도구만 계속 부르고 답을 안 한 경우. 여기까지 오면 모델이 헤매는 중이다.
    raise ChatGenerationError("검색만 반복하고 답변을 만들지 못했습니다")


def to_history(role: MessageRole, content: str) -> dict:
    """DB 의 메시지를 모델에게 보낼 모양으로. `system` 은 우리가 따로 넣으므로 제외한다."""
    return {"role": role.value, "content": content}
