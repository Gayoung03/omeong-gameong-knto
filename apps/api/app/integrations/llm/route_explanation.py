"""규칙으로 짠 루트 결과 요약 → 여행 전체 설명 한 문단(LLM 1회).

`request_intent.py`·`route_edit.py` 와 같은 패턴의 별도 모듈 — 챗봇과 프롬프트·호출
경로를 공유하지 않는다. 추천 생성 중 **여행당 1회만** 부르고, 장소별로는 부르지 않는다.

설계 결정(route-redesign Phase 6):
- 입력은 **규칙 결과 요약뿐**이다(일수·장소 수·이동수단·속도·반려동물 메모·날씨 반영·
  미확정 슬롯 수). `request_text` 원문은 넣지 않는다 — 개인 서사가 설명으로 새지 않게.
- 폴링 3분 예산 안에서 짧게 자르고(기본 10초), 실패·미설정은 조용히 None 을 돌려
  호출부가 템플릿으로 폴백한다. 추천 생성 자체는 항상 진행된다.
"""

import logging
from dataclasses import dataclass, field

from openai import APITimeoutError, OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TripExplanationInput:
    """설명 프롬프트에 넣는 규칙 결과 요약. 값은 이미 사람이 읽는 형태(한글)다."""

    day_count: int
    place_count: int
    unfilled_count: int
    pace_label: str
    transport_label: str
    pet_notes: tuple[str, ...] = field(default_factory=tuple)
    weather_note: str | None = None


def _user_prompt(summary: TripExplanationInput) -> str:
    pets = ", ".join(summary.pet_notes) if summary.pet_notes else "정보 없음"
    unfilled = (
        f"{summary.unfilled_count}곳 (직접 확인이 필요한 슬롯이 있음)"
        if summary.unfilled_count > 0
        else "없음"
    )
    return (
        "다음은 규칙으로 짠 반려동물 동반 제주 여행 요약입니다. 이 사실만으로 안내 문단을 쓰세요.\n"
        f"- 일정: {summary.day_count}일, 방문 장소 {summary.place_count}곳\n"
        f"- 이동수단: {summary.transport_label}, 여행 속도: {summary.pace_label}\n"
        f"- 반려동물: {pets}\n"
        f"- 날씨 반영: {summary.weather_note or '특이사항 없음'}\n"
        f"- 아직 확정 못한 슬롯: {unfilled}"
    )


def generate_trip_explanation(summary: TripExplanationInput) -> str | None:
    """여행 전체 설명 한 문단. 실패·키 미설정은 None — 호출부가 템플릿으로 폴백한다."""
    if not settings.openai_api_key:
        return None

    try:
        client = OpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.route_explanation_timeout_seconds,
            max_retries=0,
        )
        completion = client.chat.completions.create(
            model=settings.route_explanation_model,
            temperature=0.4,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "너는 반려동물 동반 제주 여행 일정을 한 문단으로 따뜻하게 요약하는 "
                        "안내자다. 주어진 요약 사실만 쓰고 새로운 장소·수치를 지어내지 않는다. "
                        "2~3문장, 존댓말, 한 문단으로만 답한다."
                    ),
                },
                {"role": "user", "content": _user_prompt(summary)},
            ],
        )
        # 응답 파싱도 try 안에서 한다 — 빈 choices 로 인한 IndexError 가 새어 나가면
        # "실패는 항상 None" 계약이 깨진다.
        content = completion.choices[0].message.content
    except APITimeoutError:
        logger.warning("여행 설명 생성 시간 초과")
        return None
    except Exception as error:
        logger.warning("여행 설명 생성 실패: %s", type(error).__name__)
        return None

    return content.strip() if content and content.strip() else None
