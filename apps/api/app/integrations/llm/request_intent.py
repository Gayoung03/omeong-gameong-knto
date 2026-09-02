"""루트 요청 자유문(request_text)에서 선호 태그만 구조화한다 (ai-io-column-design 8.3-3).

`route_edit.py` 와 같은 패턴의 별도 모듈 — 챗봇과 프롬프트·호출 경로를 공유하지 않는다.
추출 대상은 **표준 태그 어휘로 제한된 preferred_tags 하나뿐**이다:

- `pace` 는 뽑지 않는다 — 요청 스키마상 pace 는 항상 명시 값이라 "미지정" 상태가 없고,
  추출값을 얹으면 사용자가 고른 값을 덮게 된다(계획 리뷰 확정).
- 자유 문자열 출력 필드를 두지 않는다 — 개인 서사가 구조화 컬럼·관찰로 흘러드는 것을
  스키마 수준에서 차단한다(§2.7: request_text 는 상(잠재) 등급).
- 원문은 로그에 남기지 않는다(길이만). 실패는 조용히 None — 추천 생성은 항상 진행된다.
"""

import json
import logging
from dataclasses import dataclass

from openai import APITimeoutError, OpenAI

from app.core.config import settings
from app.recommend.config.tags import STANDARD_TAG_SET, STANDARD_TAGS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestIntent:
    preferred_tags: tuple[str, ...]


def merge_preferred_tags(
    existing: list[str] | None, extracted: tuple[str, ...]
) -> frozenset[str]:
    """기존 선택 태그와 추출 태그의 합집합 — 기존 값은 절대 사라지지 않는다."""
    return frozenset([*(existing or []), *extracted])


def parse_intent_arguments(raw: str) -> RequestIntent:
    """tool 호출 인자 JSON → RequestIntent. 어휘 밖 값은 **버린다**(오류 아님).

    strict 스키마를 쓰더라도 모델·버전에 따라 보장이 흔들릴 수 있어 서버에서
    한 번 더 거른다(이중 방어). 순수 함수 — 단위 테스트 대상.
    """
    arguments = json.loads(raw)
    tags = arguments.get("preferred_tags") or []
    filtered = tuple(dict.fromkeys(tag for tag in tags if tag in STANDARD_TAG_SET))
    return RequestIntent(preferred_tags=filtered)


def _intent_tool() -> dict:
    return {
        "type": "function",
        "function": {
            "name": "extract_request_intent",
            "description": "여행 요청문에서 표준 선호 태그만 고른다. 없으면 빈 배열.",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "preferred_tags": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(STANDARD_TAGS)},
                    },
                },
                "required": ["preferred_tags"],
                "additionalProperties": False,
            },
        },
    }


def extract_request_intent(request_text: str) -> RequestIntent | None:
    """자유문 → 표준 태그. 실패(키 없음·타임아웃·형식 오류)는 None — 호출부는 무시하고 진행."""
    if not request_text or not request_text.strip():
        return None
    if not settings.openai_api_key:
        return None

    try:
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.request_intent_timeout_seconds,
            max_retries=0,
        )
        completion = client.chat.completions.create(
            model=settings.request_intent_model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 여행 요청문 해석기다. 문장에서 표준 태그에 해당하는 "
                        "선호만 고른다. 태그 어휘 밖의 내용은 무시하고, 확실하지 "
                        "않으면 빈 배열을 낸다. 새로운 값을 만들지 않는다."
                    ),
                },
                {"role": "user", "content": request_text},
            ],
            tools=[_intent_tool()],
            tool_choice={"type": "function", "function": {"name": "extract_request_intent"}},
        )
    except APITimeoutError:
        logger.warning("request_text 추출 시간 초과 (원문 %d자)", len(request_text))
        return None
    except Exception:
        logger.warning("request_text 추출 실패 (원문 %d자)", len(request_text))
        return None

    calls = completion.choices[0].message.tool_calls
    if not calls:
        return None
    try:
        return parse_intent_arguments(calls[0].function.arguments)
    except (json.JSONDecodeError, TypeError):
        logger.warning("request_text 추출 형식 오류 (원문 %d자)", len(request_text))
        return None