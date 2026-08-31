"""챗봇 답변 생성.

질문을 받아 **우리 DB 에서 장소를 찾고**, 그 결과로 답변 문장을 만든다.

## 부르는 쪽은 OpenAI 를 몰라도 된다

엔드포인트는 `stream_answer()` 하나만 부르고 `AnswerDelta` 조각들과 마지막 `Answer` 를
받는다. 벤더를 바꿔도 **이 파일 안만 고치면 된다** — `travel_log_image.py` 와 같은 방식이다.

## 스트리밍과 도구 호출이 한 라운드 안에서 섞이지 않는다

OpenAI 응답은 `tool_calls` 가 있는 메시지에는 `content` 가 없고, `content` 가 있는
메시지에는 `tool_calls` 가 없다. 그래서 도구 라운드는 화면에 보이지 않게 조각을 모아서만
처리하고, **텍스트를 실제로 만드는 마지막 라운드만** 조각이 오는 대로 그 자리에서
내보낸다(`AnswerDelta`). `generate_answer()` 는 `stream_answer()` 를 끝까지 돌려 최종
`Answer` 만 받는 얇은 래퍼다 — 스트리밍이 필요 없는 곳(`scripts/chat_quality_check.py`)이
쓴다.

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
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from openai import APITimeoutError, OpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.enums import (
    CarrierType,
    GuideCategory,
    MessageRole,
    PetPolicyType,
    PlaceEnvironment,
)
from app.rag.prompts.system import build_system_prompt
from app.rag.retrieval.guide_search import (
    DEFAULT_GUIDE_LIMIT,
    MAX_GUIDE_LIMIT,
    GuideHit,
    TransportRuleHit,
    Verdict,
    search_guides,
    search_transport_rules,
)
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


GUIDE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_guides",
        "description": (
            "반려동물과 제주를 오갈 때 필요한 안내 글을 찾는다. "
            "준비물, 케이지, 제주 입도 절차, 렌터카, 항공사·여객선 이용 방법을 물으면 쓴다. "
            "무게나 요금처럼 숫자로 따지는 질문은 search_transport_rules 를 쓴다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [c.value for c in GuideCategory],
                    "description": "airline 항공사 / ferry 여객선 / preparation 준비물·절차",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "제목·본문에서 찾을 낱말. 하나라도 걸리면 나온다. "
                        "'케이지', '입마개', '예방접종' 처럼 짧게 넣는다."
                    ),
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_GUIDE_LIMIT},
            },
            "additionalProperties": False,
        },
    },
}

TRANSPORT_TOOL = {
    "type": "function",
    "function": {
        "name": "search_transport_rules",
        "description": (
            "항공사·여객선의 반려동물 운송 규정을 조회한다. "
            "기내 탑승 가능 여부, 무게 상한, 요금, 신청 기한을 물으면 반드시 이 도구를 쓴다. "
            "무게를 알면 pet_weight_kg 에 넣는다 — 가능/불가 판정이 함께 나온다."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "carrier_type": {
                    "type": "string",
                    "enum": [c.value for c in CarrierType],
                    "description": "airline 항공사 / ferry 여객선. 생략하면 둘 다.",
                },
                "carrier_name": {
                    "type": "string",
                    "description": (
                        "'대한항공' 처럼 회사 이름 일부. 생략하면 전부 나오므로 "
                        "비교하는 질문에는 생략한다."
                    ),
                },
                "pet_weight_kg": {
                    "type": "number",
                    "minimum": 0,
                    "description": "반려동물 무게(kg). 케이지를 포함한 무게가 기준이다.",
                },
            },
            "additionalProperties": False,
        },
    },
}

TOOLS = [SEARCH_TOOL, GUIDE_TOOL, TRANSPORT_TOOL]


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


def _date(value) -> str | None:
    """확인일은 날짜까지만 준다. 시·분은 답변에 쓸 일이 없다."""
    return value.date().isoformat() if value else None


def _describe_guide(hit: GuideHit) -> dict:
    """가이드 글 하나. 본문이 400~1100자로 짧아 통째로 준다.

    `sources` 와 `verified_at` 을 빼지 않는다 — 이걸 빼면 GPT 가 출처 없이
    단정하게 되고, 그러라고 만든 도구가 아니다(설계 결정 A6).
    """
    return {
        "title": hit.title,
        "category": hit.category.value,
        "body": hit.body,
        "sources": [
            {"name": name, "url": url} if url else {"name": name} for name, url in hit.sources
        ],
        "verified_at": _date(hit.verified_at),
    }


def _describe_rule(hit: TransportRuleHit) -> dict:
    """운송 규정 하나.

    **값이 없는 항목은 아예 넣지 않는다.** `null` 을 그대로 넘기면 GPT 가 그것을
    "없다 = 불가"로 읽는다. 우리가 모르는 것은 말하지 않는 편이 낫다(설계 결정 A7).

    다만 `cabin_allowed` 가 `False` 인 경우(불가라고 명시)는 반드시 남긴다 —
    빠지면 안 되는 곳이 후보로 올라온다.
    """
    described: dict = {
        "carrier_name": hit.carrier_name,
        "carrier_type": hit.carrier_type.value,
    }
    optional = {
        "route": hit.route,
        "cabin_allowed": hit.cabin_allowed,
        "cabin_max_weight_kg": (
            float(hit.cabin_max_weight_kg) if hit.cabin_max_weight_kg is not None else None
        ),
        # "무게 제한 없음" 명시값(S등급). 값이 있을 때만 넣는다 — NULL(미확인)은 넣지 않는다.
        "cabin_weight_unlimited": hit.cabin_weight_unlimited,
        "cabin_fee_krw": hit.cabin_fee_krw,
        "cargo_allowed": hit.cargo_allowed,
        "cargo_max_weight_kg": (
            float(hit.cargo_max_weight_kg) if hit.cargo_max_weight_kg is not None else None
        ),
        "cargo_weight_unlimited": hit.cargo_weight_unlimited,
        "cargo_fee_krw": hit.cargo_fee_krw,
        "same_day_request_allowed": hit.same_day_request_allowed,
        "request_deadline_hours": hit.request_deadline_hours,
        "pledge_required": hit.pledge_required,
        "duration_minutes": hit.duration_minutes,
        "notes": hit.notes,
        "source_url": hit.source_url,
        "verified_at": _date(hit.verified_at),
    }
    described.update({key: value for key, value in optional.items() if value is not None})

    # 조건부 사실("원칙 불가·예외 허용")은 cabin_allowed 와 **항상 쌍으로** 넣는다.
    # allowed=False 여도 conditions 가 있으면 "불가, 단 예외" 를 유도해야 한다(플랜 8.1).
    # allowed 가 NULL 이면 넣지 않는다(A7 — null 을 "불가"로 읽는 문제).
    if hit.cabin_conditions is not None:
        described["cabin_conditions"] = hit.cabin_conditions
        if hit.cabin_allowed is not None:
            described["cabin_allowed"] = hit.cabin_allowed

    # 판정은 무게를 넣어 불렀을 때만 붙는다. 숫자 비교를 모델에게 맡기지 않는다.
    if hit.cabin_verdict is not None:
        described["cabin_verdict"] = hit.cabin_verdict.value
    if hit.cargo_verdict is not None:
        described["cargo_verdict"] = hit.cargo_verdict.value
    return described


def _run_guide_search(db: Session, raw_arguments: str) -> str:
    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return "검색 조건을 읽지 못했습니다. 다시 시도하세요."

    try:
        hits = search_guides(
            db,
            category=(
                GuideCategory(arguments["category"]) if arguments.get("category") else None
            ),
            keywords=arguments.get("keywords"),
            limit=int(arguments.get("limit") or DEFAULT_GUIDE_LIMIT),
        )
    except (ValueError, TypeError) as error:
        return f"검색 조건이 잘못됐습니다: {error}"

    if not hits:
        return "해당하는 안내 글이 없습니다."
    return json.dumps([_describe_guide(hit) for hit in hits], ensure_ascii=False)


def _leg_phrase(
    kind: str,
    verdict: Verdict | None,
    max_weight: float | None,
    weight_unlimited: bool | None = None,
) -> str:
    """기내/위탁 한 쪽의 결론을 문장 조각으로.

    **왜 안 되는지를 반드시 담는다.** `이용 불가` 라고만 보냈더니 GPT 가
    "기내 탑승이 불가하다"로 옮겨 적었다 — 실제로는 기내는 되고 위탁이 없는
    항공사였다. 이유가 빠지면 모델이 채워 넣는다.
    """
    if verdict is Verdict.ALLOWED:
        # 상한 없이 가능한 경우는 "무게 제한 없음"을 명시해 "미확인"으로 오해되지 않게 한다.
        return f"{kind} 가능(무게 제한 없음)" if weight_unlimited is True else f"{kind} 가능"
    if verdict is Verdict.OVER_WEIGHT:
        limit = f"(상한 {max_weight:g}kg 초과)" if max_weight is not None else "(상한 초과)"
        return f"{kind} 불가{limit}"
    if verdict is Verdict.NOT_ALLOWED:
        # 규정상 불가. 위탁은 "제도 자체가 없다" 는 뜻이라 문구를 나눈다.
        return "위탁 제도 없음" if kind == "위탁" else f"{kind} 불가(규정상 불가)"
    if verdict is Verdict.WEIGHT_UNKNOWN:
        return f"{kind} 가능하나 무게 상한 미확인"
    return f"{kind} 가능 여부 미확인"


def _weight_conclusions(hits: list[TransportRuleHit]) -> list[dict]:
    """무게를 넣어 부른 경우, **회사마다 결론 문장을 통째로 만들어** 보낸다.

    모델에게 요약을 맡기지 않는다. 규정 7건을 그대로 주면
    "모두 화물칸에 실을 수 있다" 로 묶어버리고, 분류만 주면
    "기내 탑승이 불가하다" 로 뒤집어 적는 것을 화면에서 확인했다.
    프롬프트로 두 번 막았지만 새어나갔다 — **문장을 여기서 완성한다.**
    """
    conclusions = []
    for hit in hits:
        cabin = _leg_phrase(
            "기내",
            hit.cabin_verdict,
            float(hit.cabin_max_weight_kg) if hit.cabin_max_weight_kg is not None else None,
            hit.cabin_weight_unlimited,
        )
        cargo = _leg_phrase(
            "위탁",
            hit.cargo_verdict,
            float(hit.cargo_max_weight_kg) if hit.cargo_max_weight_kg is not None else None,
            hit.cargo_weight_unlimited,
        )
        text = f"{cabin}, {cargo}"
        blocked = {Verdict.OVER_WEIGHT, Verdict.NOT_ALLOWED}
        if hit.cabin_verdict in blocked and hit.cargo_verdict in blocked:
            text += " → 이 회사로는 이 무게로 갈 수 없음"
        conclusions.append(
            {
                "carrier": f"{hit.carrier_name}({hit.route})" if hit.route else hit.carrier_name,
                "결론": text,
            }
        )
    return conclusions


def _run_transport_search(db: Session, raw_arguments: str) -> str:
    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return "검색 조건을 읽지 못했습니다. 다시 시도하세요."

    try:
        weight = arguments.get("pet_weight_kg")
        hits = search_transport_rules(
            db,
            carrier_type=(
                CarrierType(arguments["carrier_type"]) if arguments.get("carrier_type") else None
            ),
            carrier_name=arguments.get("carrier_name"),
            pet_weight_kg=Decimal(str(weight)) if weight is not None else None,
        )
    except (ValueError, TypeError, InvalidOperation) as error:
        return f"검색 조건이 잘못됐습니다: {error}"

    if not hits:
        return "해당하는 운송사 규정이 없습니다."

    rules = [_describe_rule(hit) for hit in hits]
    if weight is None:
        return json.dumps(rules, ensure_ascii=False)
    return json.dumps(
        {"이 무게 기준 결론": _weight_conclusions(hits), "규정": rules}, ensure_ascii=False
    )


def _dispatch(db: Session, name: str, raw_arguments: str) -> tuple[str, list[PlaceHit]]:
    """모델이 부른 도구를 실행한다.

    장소 검색만 `PlaceHit` 을 함께 돌려준다 — 지도 핀을 찍는 것은 장소뿐이라
    나머지는 빈 목록이다.
    """
    if name == "search_places":
        return _run_search(db, raw_arguments)
    if name == "search_guides":
        return _run_guide_search(db, raw_arguments), []
    if name == "search_transport_rules":
        return _run_transport_search(db, raw_arguments), []
    return f"'{name}' 이라는 도구는 없습니다.", []


def _mentioned(content: str, seen: dict[uuid.UUID, PlaceHit]) -> list[uuid.UUID]:
    """답변에 **이름이 등장한** 장소만 고른다. 설계 결정 C4.

    검색은 다섯 곳을 가져와도 답변이 세 곳만 말했다면 지도 핀도 세 개여야 한다.
    모델에게 "어느 걸 언급했니"라고 다시 묻지 않는다 — 요금이 한 번 더 들고,
    이름 대조로 충분하다.
    """
    return [place_id for place_id, hit in seen.items() if hit.name in content]


@dataclass(frozen=True)
class AnswerDelta:
    """스트리밍 중 도착한 답변 조각. 엔드포인트가 그대로 SSE `delta` 이벤트로 내보낸다."""

    text: str


def stream_answer(
    db: Session, history: list[dict], question: str
) -> Iterator[AnswerDelta | Answer]:
    """질문 하나에 대한 답변을 스트리밍으로 만든다.

    `AnswerDelta` 를 여러 번 내보내다가 마지막에 `Answer` 를 한 번 내보내고 끝난다.
    도구 라운드는 조각을 모아서만 쓰고 내보내지 않는다 — 볼 것이 없어서다.

    `history` 는 오래된 순으로 정렬된 `{"role", "content"}` 목록이다.
    `HISTORY_LIMIT` 개까지만 쓴다.

    호출부가 중간에 순회를 멈추면(중지 버튼·연결 끊김) 이 제너레이터에
    `GeneratorExit` 이 던져진다. 열려 있는 OpenAI 스트림을 닫는 것 말고는 할 일이
    없다 — 저장은 호출부 몫이고, 여기까지 오면 아직 저장할 `Answer` 를 안 만든
    상태라 "중지하면 저장하지 않는다"가 자연히 지켜진다.
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
            stream = client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=TOOLS,
                stream=True,
            )
            content_parts: list[str] = []
            #: 인덱스별로 조각을 모은다 — `arguments` 는 여러 청크에 걸쳐 문자열로 쪼개져 온다.
            tool_calls: dict[int, dict] = {}
            model_name = settings.openai_model
            try:
                for chunk in stream:
                    if not chunk.choices:
                        continue
                    model_name = chunk.model or model_name
                    delta = chunk.choices[0].delta
                    if delta.tool_calls:
                        for piece in delta.tool_calls:
                            call = tool_calls.setdefault(
                                piece.index, {"id": None, "name": None, "arguments": ""}
                            )
                            if piece.id:
                                call["id"] = piece.id
                            if piece.function and piece.function.name:
                                call["name"] = piece.function.name
                            if piece.function and piece.function.arguments:
                                call["arguments"] += piece.function.arguments
                    elif delta.content:
                        content_parts.append(delta.content)
                        yield AnswerDelta(delta.content)
            finally:
                close = getattr(stream, "close", None)
                if close:
                    close()

            if tool_calls:
                messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": call["id"],
                                "type": "function",
                                "function": {
                                    "name": call["name"],
                                    "arguments": call["arguments"],
                                },
                            }
                            for call in tool_calls.values()
                        ],
                    }
                )
                for call in tool_calls.values():
                    result, hits = _dispatch(db, call["name"], call["arguments"])
                    seen.update({hit.place_id: hit for hit in hits})
                    messages.append(
                        {"role": "tool", "tool_call_id": call["id"], "content": result}
                    )
                continue

            content = "".join(content_parts).strip()
            if not content:
                raise ChatGenerationError("빈 답변을 받았습니다")
            yield Answer(
                content=content,
                model_name=model_name,
                referenced_place_ids=_mentioned(content, seen),
            )
            return
    except APITimeoutError as error:
        raise ChatTimeoutError("답변 생성이 시간을 초과했습니다") from error
    except ChatGenerationError:
        raise
    except Exception as error:  # noqa: BLE001 - 벤더 예외를 우리 것으로 감싼다
        raise ChatGenerationError(f"답변 생성에 실패했습니다: {error}") from error

    # 도구만 계속 부르고 답을 안 한 경우. 여기까지 오면 모델이 헤매는 중이다.
    raise ChatGenerationError("검색만 반복하고 답변을 만들지 못했습니다")


def generate_answer(db: Session, history: list[dict], question: str) -> Answer:
    """`stream_answer()` 를 끝까지 돌려 최종 `Answer` 만 받는다.

    스트리밍이 필요 없는 곳(`scripts/chat_quality_check.py`)이 쓴다.
    """
    for piece in stream_answer(db, history, question):
        if isinstance(piece, Answer):
            return piece
    raise ChatGenerationError("답변을 받지 못했습니다")


def to_history(role: MessageRole, content: str) -> dict:
    """DB 의 메시지를 모델에게 보낼 모양으로. `system` 은 우리가 따로 넣으므로 제외한다."""
    return {"role": role.value, "content": content}
