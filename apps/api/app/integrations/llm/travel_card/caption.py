"""단계 2 — 카드에 얹을 짧은 메모 만들기.

사진을 다시 보지 않는다. 단계 1이 뽑아둔 `kind`·`items` 와 장소 정보만으로 쓴다.
이미지 토큰을 두 번 낼 이유가 없고, 분석을 캐시해 두면 재생성이 이 단계부터 시작된다.

## 장소 이름을 도배하지 않는다

메모 여덟 줄에 장소명이 여섯 번 나오면 카드가 광고처럼 보인다. 장소는 **한 줄에만**,
그것도 토막이 아니라 문장으로 넣는다.

    나쁨: "협재 산책"          토막이라 말이 아니다
    좋음: "협재에서 보낸 오후"   문장이라 기록으로 읽힌다

사진이 장소와 동떨어져 있으면(하늘·발바닥·차 안) 사진 주제를 메인으로 두고
장소는 "협재 가는 길에" 처럼 한 줄로만 잇는다.

## 말투 두 종

`jeju_dialect` 는 여행하는 사람이 화자다. `dog_diary` 는 **반려동물이 화자**다 —
피사체가 아니라 화자라서, 사진에 안 찍혀 있어도 밖에서 지켜본 시점으로 쓴다.
그쪽이 오히려 재미있다(기다린 이야기, 못 먹은 이야기).
"""

import json
from typing import Any

from openai import OpenAI

from .config import CAPTION_MODEL, CAPTION_TIMEOUT, MAX_MEMOS, MIN_MEMOS, api_key
from .types import CardText, PhotoAnalysis, WritingStyle

_COMMON_RULES = f"""[재료는 itemsInPhoto 뿐이다 — 가장 중요]
- **itemsInPhoto 에 적힌 것만 근거로 쓴다.** 거기 없는 사물·행동·감정·표정을 지어내지 마라.
- 사람 수를 늘리지 마라. "한 사람" 이라고 적혀 있으면 "사람들" 이라고 쓰지 않는다.
- 동작을 바꾸지 마라. "서 있는" 을 "앉아 있었다" 로 쓰지 않는다.
- 표정이 items 에 없으면 표정을 쓰지 마라. "웃는" 을 임의로 붙이지 않는다.
- 재료가 모자라면 **메모를 적게 쓴다.** 지어내는 것보다 여덟 줄 대신 다섯 줄이 낫다.

[공통 규칙]
- 제목 1개 + 메모 {MIN_MEMOS}~{MAX_MEMOS}개.
- 제목은 그날을 한마디로 요약한다. 메모와 다른 종류의 글이다. 4~12자.
- 각 메모는 6~16자. 길면 이미지에서 글자가 깨진다.
- 다정한 일기체·혼잣말 톤. 완결된 말로 쓴다.
- 메모의 대부분은 사진 속 내용과 분위기로 채운다.
- 장소 이름은 **한 줄에만** 자연스럽게 넣는다. 도배하지 않는다.
- 장소 이름을 토막으로 쓰지 말고 문장으로 쓴다.
    나쁨: "협재 산책"        좋음: "협재에서 보낸 오후"
- 사진이 장소와 동떨어져 있으면(하늘·발바닥·차 안 등) 사진 주제를 메인으로 하고
  장소는 "협재 가는 길에" 처럼 한 줄로만 잇는다.
- 이모지는 한두 줄에만 살짝. 전부 붙이지 않는다.
- 사진에 없는 것을 지어내지 않는다. 장소·음식·동물·사람을 만들지 않는다.
- 사람의 외모·나이·체형·관계를 언급하지 않는다.
- 부정적·공격적인 표현을 쓰지 않는다.
- 반려동물의 건강·의료에 대한 단정을 넣지 않는다.
  ("아파 보여요", "살 빠졌네" 같은 말은 쓰지 않는다)
- 옛한글(아래아 ㅏ 형태의 ᄒᆞ, ᄆᆞᆯ)을 쓰지 않는다. 현대 한글로만 쓴다.
- **어미를 끝까지 지킨다.** 지정된 말투의 어미로 모든 줄을 끝낸다.
  한 줄이라도 평범한 말투로 새면 카드 전체가 어색해진다."""

_JEJU_RULES = """[말투 — 제주 방언]
화자는 여행하는 사람 본인이다.
`~수다` `~우다` `~햄수과` `혼저` `폭싹` 정도의 상용 표현을 섞는다.
읽는 사람이 뜻을 알 수 있을 만큼만 쓴다. 과한 방언 남용 금지.
예) "바당이 오늘 참 곱나", "바람이 시원허우다", "폭싹 좋은 하루우다"
"""

_DOG_RULES = """[말투 — 강아지 일기]
화자는 반려동물 "{pet}" 이다. **피사체가 아니라 화자다.**
1인칭으로 쓴다. 어미는 `~댕` `~개` `~멍` 셋 중에서 쓴다. 이름을 한 번은 넣는다.
셋을 골고루 섞는다. 한 어미만 반복하면 단조롭다.

사진에 "{pet}" 이가 있으면 -> 자랑하듯 1인칭으로.
    예) "여기서 신나게 달렸댕", "귀가 날아갈 뻔했개", "모래가 발가락에 꼈멍"

사진에 없으면 -> **사진 밖에서 지켜본 시점**으로. 있는 척하지 않는다.
    예) 풍경 - "집사가 백 장은 찍었댕", "그늘에서 기다렸개", "바람 냄새 좋았멍"
        음식 - "냄새만 맡았댕", "한 입도 안 줬멍"
        사람 - "집사 웃는 거 오랜만이댕"
사진에 없을 때가 더 재미있다. 기다린 이야기, 못 먹은 이야기.

**모든 줄이 `~댕` `~개` `~멍` 중 하나로 끝나야 한다.**
"보이네", "찍네", "좋다" 같은 평범한 어미는 한 줄도 쓰지 않는다.
세 어미를 한 카드 안에서 섞어 쓴다 — 한 가지만 반복하면 기계가 쓴 것처럼 읽힌다.
"""


class CaptionError(Exception):
    """메모를 만들지 못했다."""


def _client() -> OpenAI:
    key = api_key()
    if not key:
        raise CaptionError("OPENAI_API_KEY 가 설정되지 않았습니다")
    return OpenAI(api_key=key, timeout=CAPTION_TIMEOUT, max_retries=0)


def build_system_prompt(style: WritingStyle, pet_name: str | None) -> str:
    if style is WritingStyle.DOG_DIARY:
        voice = _DOG_RULES.format(pet=pet_name or "우리 강아지")
    else:
        voice = _JEJU_RULES
    return (
        "너는 반려동물 동반 제주 여행 앱의 여행기록 문구 작가다.\n"
        "사진 분석 결과를 받아 사진 위에 손글씨로 얹을 짧은 메모를 쓴다.\n\n"
        f"{voice}\n{_COMMON_RULES}\n\n"
        "반드시 아래 JSON 객체 하나만 출력한다.\n"
        '{ "title": "...", "memos": ["...", "..."] }'
    )


def _coerce_memos(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("memos")
    if not isinstance(raw, list):
        return []
    memos: list[str] = []
    for value in raw:
        text = " ".join(str(value).split())
        # 너무 긴 줄은 버린다. 자르면 말이 끊겨 더 이상해진다.
        if text and len(text) <= 24:
            memos.append(text)
    return memos[:MAX_MEMOS]


def generate(
    analysis: PhotoAnalysis,
    style: WritingStyle,
    *,
    pet_name: str | None = None,
    place_name: str | None = None,
    place_description: str | None = None,
) -> CardText:
    """제목과 메모를 돌려준다. 재료가 모자라면 메모 수가 줄어든다."""
    context = {
        "photoKind": analysis.kind.value,
        "hasPet": analysis.kind.has_pet,
        "itemsInPhoto": analysis.items,
        "petName": pet_name,
        "placeName": place_name,
        "placeDescription": place_description,
    }

    try:
        completion = _client().chat.completions.create(
            model=CAPTION_MODEL,
            response_format={"type": "json_object"},
            temperature=0.8,  # 분석과 달리 여기는 다양해야 한다.
            max_tokens=700,
            messages=[
                {"role": "system", "content": build_system_prompt(style, pet_name)},
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
        )
    except Exception as error:  # noqa: BLE001
        raise CaptionError(str(error)) from error

    content = completion.choices[0].message.content or ""
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, TypeError) as error:
        raise CaptionError("메모 응답을 해석하지 못했습니다") from error

    memos = _coerce_memos(payload)
    if len(memos) < 3:
        raise CaptionError(f"메모가 너무 적습니다 ({len(memos)}개)")

    title = " ".join(str(payload.get("title") or "").split())
    if not title or len(title) > 20:
        # 제목이 없거나 길면 첫 메모를 올린다. 카드가 제목 없이 나가는 것보다 낫다.
        title = memos[0]
        memos = memos[1:]
    return CardText(title=title, memos=memos)
