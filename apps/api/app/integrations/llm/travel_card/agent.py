"""네 단계를 순서대로 부르는 진입점.

부르는 쪽은 `build_card()` 하나만 알면 된다. 예외를 던지지 않고 `CardResult` 를
돌려준다 — 프론트가 `outcome` 하나로 갈라 처리할 수 있게 하려는 것이다.

## 안내 문구는 사진을 탓하지 않는다

안전 판정과 생성 거부는 **음식·동물 클로즈업에서 오탐이 잦다.** 멀쩡한 사진을 올린
사용자가 "부적절한 사진입니다" 를 보면 기분이 상하고, 무엇보다 우리가 틀렸을 때
사용자를 탓한 것이 된다. 그래서 문구를 "이 사진으로는 못 만들었어요, 다른 사진으로
해보시겠어요" 쪽으로 쓴다.
"""

import time
from collections.abc import Callable

from . import caption, image_edit, prompts, vision
from .image_io import UnreadableImage, load_image
from .types import CardOutcome, CardResult, WritingStyle

_MESSAGES = {
    CardOutcome.BLOCKED_INPUT: (
        "이 사진으로는 카드를 만들기 어려웠어요. 다른 사진으로 해보시겠어요?"
    ),
    CardOutcome.UNREADABLE_IMAGE: (
        "사진을 읽지 못했어요. JPG 나 PNG 로 다시 올려 주시겠어요?"
    ),
    CardOutcome.BLOCKED_OUTPUT: (
        "이 사진으로는 카드를 만들기 어려웠어요. 다른 사진으로 해보시겠어요?"
    ),
    CardOutcome.FAILED: "카드를 만들지 못했어요. 잠시 후 다시 시도해 주세요.",
}


def _timed[T](timings: dict[str, float], name: str, call: Callable[[], T]) -> T:
    started = time.perf_counter()
    try:
        return call()
    finally:
        timings[name] = round(time.perf_counter() - started, 2)


def build_card(
    data: bytes,
    style: WritingStyle,
    *,
    pet_name: str | None = None,
    place_name: str | None = None,
    place_description: str | None = None,
    date_text: str | None = None,
) -> CardResult:
    """사진 바이트 하나로 카드 PNG 를 만든다."""
    timings: dict[str, float] = {}

    # --- 0. 파일 읽기 -----------------------------------------------------
    try:
        image = load_image(data)
    except UnreadableImage as error:
        return CardResult(
            outcome=CardOutcome.UNREADABLE_IMAGE,
            message=f"{_MESSAGES[CardOutcome.UNREADABLE_IMAGE]} ({error})",
            timings=timings,
        )

    # --- 1. 사진 분석 + 안전 판정 ----------------------------------------
    try:
        analysis = _timed(timings, "vision", lambda: vision.analyze(image))
    except vision.VisionError as error:
        return CardResult(
            outcome=CardOutcome.FAILED,
            message=f"{_MESSAGES[CardOutcome.FAILED]} ({error})",
            timings=timings,
        )

    # 여기서 멈추는 것이 이 파이프라인의 존재 이유 중 하나다.
    if not analysis.safe:
        return CardResult(
            outcome=CardOutcome.BLOCKED_INPUT,
            message=_MESSAGES[CardOutcome.BLOCKED_INPUT],
            analysis=analysis,
            timings=timings,
        )

    # --- 2. 메모 생성 -----------------------------------------------------
    try:
        text = _timed(
            timings,
            "caption",
            lambda: caption.generate(
                analysis,
                style,
                pet_name=pet_name,
                place_name=place_name,
                place_description=place_description,
            ),
        )
    except caption.CaptionError as error:
        return CardResult(
            outcome=CardOutcome.FAILED,
            message=f"{_MESSAGES[CardOutcome.FAILED]} ({error})",
            analysis=analysis,
            timings=timings,
        )

    # --- 3. 프롬프트 조립 (호출 없음) -------------------------------------
    prompt = prompts.build(
        analysis.kind, style, text, place_name=place_name, date_text=date_text
    )

    # --- 4. 이미지 편집 ---------------------------------------------------
    try:
        png = _timed(timings, "image_edit", lambda: image_edit.edit(image, prompt))
    except image_edit.ImageRefused:
        return CardResult(
            outcome=CardOutcome.BLOCKED_OUTPUT,
            message=_MESSAGES[CardOutcome.BLOCKED_OUTPUT],
            analysis=analysis,
            title=text.title,
            memos=text.memos,
            prompt=prompt,
            timings=timings,
        )
    except image_edit.ImageEditError as error:
        return CardResult(
            outcome=CardOutcome.FAILED,
            message=f"{_MESSAGES[CardOutcome.FAILED]} ({error})",
            analysis=analysis,
            title=text.title,
            memos=text.memos,
            prompt=prompt,
            timings=timings,
        )

    return CardResult(
        outcome=CardOutcome.OK,
        png=png,
        analysis=analysis,
        title=text.title,
        memos=text.memos,
        prompt=prompt,
        timings=timings,
    )
