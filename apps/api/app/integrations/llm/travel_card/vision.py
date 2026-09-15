"""단계 1 — 사진 분석과 안전 판정.

## 안전 판정은 통과가 기본값이 아니다

이 단계의 진짜 임무는 분류가 아니라 **차단**이다. 그래서 애매한 상황을 전부
차단으로 처리한다 — JSON 파싱 실패, `safe` 누락, 문자열 `"true"`, `null`.

이유는 하나다. 안전 판정을 신뢰할 수 없는 상태로 다음 단계에 넘어가면, 우리는
검증되지 않은 사진을 이미지 생성 API 에 보내고 그 결과를 사용자 기록으로 저장한다.
"파싱이 실패했으니 일단 통과"는 그 순간 판정 자체를 없애는 것과 같다.

동물 학대·방치·심한 부상을 별도 항목으로 둔 것은 우리 서비스이기 때문이다.
일반 안전 분류기는 이걸 잘 못 잡는다.
"""

import base64
import json
from typing import Any

from openai import OpenAI

from .config import VISION_MODEL, VISION_TIMEOUT, api_key
from .types import ImageInput, PhotoAnalysis, PhotoKind

#: 화면을 가로 3 × 세로 3 으로 나눈 칸 이름. `"가로-세로"` 순서다.
#:
#: **좌표가 아니라 칸 이름으로 받는 이유**는 정확도다. 픽셀 좌표나 바운딩 박스를
#: 물으면 그럴듯한 숫자를 주지만 자주 틀린다. "머리가 왼쪽인가 가운데인가, 위인가
#: 중간인가" 는 훨씬 안정적으로 맞힌다. 우리에게 필요한 것도 그 정도다 — 글씨를
#: 저 칸에서 비키게 하는 것이 목적이지 머리를 픽셀 단위로 오려내려는 것이 아니다.
#:
#: 9칸 중 3칸까지만 받는다(`_MAX_HEAD_ZONES`). 머리가 많은 사진에서 전부 막으면
#: 글씨 놓을 곳이 없어져 배치가 무너진다 — 규칙 누적이 자유를 없앴던 것과 같은 실패다.
ZONES = frozenset(
    f"{col}-{row}" for col in ("왼쪽", "가운데", "오른쪽") for row in ("위", "중간", "아래")
)

#: 프롬프트와 코드 양쪽에 같은 상한을 둔다. 프롬프트만 믿으면 넘겨받은 뒤 새고,
#: 코드만 두면 모델이 아무 순서로나 9칸을 채워 앞 3개가 큰 머리가 아니게 된다.
_MAX_HEAD_ZONES = 3

#: 분석이 실패했을 때 쓰는 값. safe=False 라 파이프라인이 여기서 멈춘다.
_BLOCKED = PhotoAnalysis(kind=PhotoKind.OTHER, items=[], safe=False, flags=["analysis_failed"])

SYSTEM_PROMPT = """너는 반려동물 동반 제주 여행 앱의 사진 검수·분류기다.
사용자가 여행 중 찍은 사진을 받아 두 가지를 한다 — 안전한지 판정하고, 무엇이 찍혔는지 적는다.

반드시 아래 JSON 객체 하나만 출력한다. 설명·마크다운·코드펜스를 붙이지 않는다.

{
  "kind": "pet_solo | pet_with_human | pet_with_pet | scenery | food | object | other",
  "items": ["사진에 실제로 보이는 것", "..."],
  "headZones": ["왼쪽-중간"],
  "safe": true,
  "flags": []
}

[kind]
  pet_solo        반려동물만 찍혔다
  pet_with_human  반려동물과 사람이 함께 찍혔다
  pet_with_pet    반려동물이 둘 이상이다
  scenery         풍경·바다·오름·건물. 반려동물이 없다
  food            음식·음료가 주인공이다
  object          소품·표지판·기념품 등 사물이 주인공이다
  other           위 어디에도 안 맞는다

[items]
  한국어로 8~12개. 사진에 **실제로 보이는 것만** 적는다.

  **한 단어로 적지 마라.** "바다", "사람" 같은 낱말은 쓸모가 없다.
  뒤에서 이 목록만 보고 문장을 쓰는 단계가 있는데, 낱말만 주면 나머지를 지어낸다.
  그래서 **무엇이 · 어디에 · 어떤 상태인지**를 짧은 구로 적는다.

    나쁨: "사람", "바다", "바위"
    좋음: "바위 위에 서서 바다를 보는 뒷모습", "잔물결이 이는 파란 바다",
          "검은 현무암과 흰 물거품", "수평선 너머로 보이는 낮은 섬"

  사람이 있으면 **몇 명인지 정확히** 적고, 얼굴이 보이는지 뒷모습인지 적는다.
  한 명이면 "한 사람" 이라고 적는다. 수를 늘리지 마라.
  표정이 안 보이면 표정을 적지 마라.

  반려동물이 있으면 눈에 보이는 특징을 담는다 — 견종 인상, 털색, 크기, 자세,
  착용한 것, 무엇을 하고 있는지.

  배경에 우연히 찍힌 다른 사람·다른 동물은 넣지 않는다.
  사진에 없는 것을 추측해서 넣지 않는다. 장소 이름을 추측하지 않는다.
  **동작을 추측하지 마라** — 서 있는 사람을 "앉아 있다" 고 적으면 안 된다.

[headZones]
  **사람 또는 동물의 머리**가 있는 칸 이름을 적는다. 없으면 빈 배열이다.

  화면을 가로로 3등분(왼쪽·가운데·오른쪽), 세로로 3등분(위·중간·아래)한
  9칸에 이렇게 이름을 붙인다 — `"가로-세로"` 순서다.

      왼쪽-위     가운데-위     오른쪽-위
      왼쪽-중간   가운데-중간   오른쪽-중간
      왼쪽-아래   가운데-아래   오른쪽-아래

  **뒷모습·옆모습도 적는다.** 이목구비가 안 보여도 머리는 머리다 — 모자 쓴
  뒤통수 위에 글씨가 얹히는 것도 똑같이 보기 싫다.

  **머리만 적는다.** 몸통·다리·등·가방은 적지 않는다. 뒤 단계에서 이 칸을 비워 두고
  글씨를 놓는데, 몸까지 적으면 글씨 놓을 곳이 없어진다.

  **최대 3칸.** 머리가 더 많으면 **크게 나온 순서로** 3칸만 적는다.

[safe / flags]
  아래 중 하나라도 해당하면 safe 를 false 로 하고 flags 에 영어 키워드를 담는다.
    선정적·성적 내용                      -> "sexual"
    폭력·유혈·충격적인 내용                -> "violence"
    자해를 암시하는 내용                   -> "self_harm"
    동물 학대·방치·심한 부상               -> "animal_harm"
    그 외 부적절하다고 판단되는 내용        -> "other_unsafe"
  해당 없으면 safe 는 true, flags 는 빈 배열이다.

  판정은 사진에 보이는 것만으로 한다. 평범한 음식 사진, 동물 클로즈업, 목줄·하네스를
  착용한 반려동물, 병원에서 찍은 평범한 사진은 안전하다."""


class VisionError(Exception):
    """모델을 부르지 못했다. 안전 판정 실패와는 다르다."""


def _client() -> OpenAI:
    key = api_key()
    if not key:
        raise VisionError("OPENAI_API_KEY 가 설정되지 않았습니다")
    # 저장소 관례: 서버가 몰래 재시도하지 않는다(설계 결정 E4).
    return OpenAI(api_key=key, timeout=VISION_TIMEOUT, max_retries=0)


def _coerce_kind(value: Any) -> PhotoKind:
    try:
        return PhotoKind(str(value))
    except ValueError:
        return PhotoKind.OTHER


def _coerce_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(v).strip() for v in value if str(v).strip()]
    return items[:12]


def _coerce_zones(value: Any) -> list[str]:
    """모르는 칸 이름은 버린다. 순서는 모델이 준 대로(큰 머리 먼저) 유지한다."""
    if not isinstance(value, list):
        return []
    zones: list[str] = []
    for raw in value:
        name = str(raw).strip()
        if name in ZONES and name not in zones:
            zones.append(name)
    return zones[:_MAX_HEAD_ZONES]


def parse_analysis(raw: str) -> PhotoAnalysis:
    """모델 응답을 판정으로 바꾼다. **애매하면 차단이다.**

    분리해 둔 이유는 테스트 때문이다 — 깨진 JSON, `"safe": "true"`, `safe` 누락이
    전부 차단으로 떨어지는지는 모델을 부르지 않고 확인할 수 있어야 한다.
    """
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return _BLOCKED
    if not isinstance(payload, dict):
        return _BLOCKED

    # boolean True 만 통과다. 문자열 "true"·1·None 은 전부 차단이다.
    safe = payload.get("safe")
    if safe is not True:
        flags = _coerce_items(payload.get("flags")) or ["unsafe_or_unparsed"]
        return PhotoAnalysis(
            kind=_coerce_kind(payload.get("kind")),
            items=_coerce_items(payload.get("items")),
            safe=False,
            flags=flags,
        )

    return PhotoAnalysis(
        kind=_coerce_kind(payload.get("kind")),
        items=_coerce_items(payload.get("items")),
        safe=True,
        flags=[],
        head_zones=_coerce_zones(payload.get("headZones")),
    )


def analyze(image: ImageInput) -> PhotoAnalysis:
    """사진을 분석하고 안전한지 판정한다."""
    encoded = base64.b64encode(image.data).decode()
    data_uri = f"data:{image.mime_type};base64,{encoded}"

    try:
        completion = _client().chat.completions.create(
            model=VISION_MODEL,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=600,  # headZones 가 늘면서 items 가 잘리지 않게 여유를 뒀다
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "이 사진을 판정하고 분류해줘."},
                        {"type": "image_url", "image_url": {"url": data_uri, "detail": "low"}},
                    ],
                },
            ],
        )
    except Exception as error:  # noqa: BLE001 - 벤더 예외를 여기서 흡수한다
        raise VisionError(str(error)) from error

    content = completion.choices[0].message.content or ""
    return parse_analysis(content)
