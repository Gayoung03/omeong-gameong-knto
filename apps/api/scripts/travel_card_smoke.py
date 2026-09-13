"""여행기록 카드 파이프라인 확인용 스크립트.

DB·S3·API 를 거치지 않고 **로컬 사진 파일 -> 카드 PNG** 까지만 돌린다.
프롬프트를 눈으로 보고 고치기 위한 도구다.

    # 한 장, 두 말투 모두
    uv run python -m scripts.travel_card_smoke ~/사진/mongi.jpg \
        --pet 몽이 --place 협재해수욕장 --date 2026.09.08

    # 여러 장을 한 번에 (스펙의 완료 조건: 반려동물 단독/반려동물+사람/장소만/음식)
    uv run python -m scripts.travel_card_smoke a.jpg b.jpg c.jpg d.jpg --pet 몽이

    # 한 말투만
    uv run python -m scripts.travel_card_smoke a.jpg --style jeju_dialect

결과는 `tmp/travel-cards/` 아래에 저장된다(저장소 .gitignore 가 tmp/ 를 무시한다).
"""

import argparse
import sys
import time
from pathlib import Path

from app.integrations.llm.travel_card import card_render, config
from app.integrations.llm.travel_card.agent import build_card
from app.integrations.llm.travel_card.types import CardOutcome, WritingStyle

OUT_DIR = Path("tmp/travel-cards")

STYLE_LABEL = {
    WritingStyle.JEJU_DIALECT: "제주 방언",
    WritingStyle.DOG_DIARY: "강아지 일기",
}

#: 대략적인 단가(USD). **정확한 청구액이 아니다** — 콘솔에서 규모를 가늠하는 용도다.
#: 실제 금액은 OpenAI 대시보드에서 확인해야 한다.
_TEXT_COST_PER_CALL = 0.0004  # vision + caption 합쳐 대략
#: 모델마다 단가가 다르다. 품질만 보고 계산하면 mini 와 gpt-image-2 가 같은 값으로 나온다.
_IMAGE_COST = {
    "gpt-image-2": {"low": 0.012, "medium": 0.047, "high": 0.19},
    "gpt-image-1.5": {"low": 0.011, "medium": 0.042, "high": 0.17},
    "gpt-image-1-mini": {"low": 0.005, "medium": 0.016, "high": 0.052},
}
_KRW = 1400


def _estimate_cost() -> tuple[float, int]:
    table = _IMAGE_COST.get(config.IMAGE_MODEL, _IMAGE_COST["gpt-image-2"])
    usd = _TEXT_COST_PER_CALL + table.get(config.IMAGE_QUALITY, 0.047)
    return usd, round(usd * _KRW)


def _print_analysis(result) -> None:
    a = result.analysis
    if a is None:
        print("   분석: (없음)")
        return
    print(f"   분류(kind) : {a.kind.value}   반려동물 있음: {a.kind.has_pet}")
    print(f"   안전(safe) : {a.safe}" + (f"   flags={a.flags}" if a.flags else ""))
    print(f"   보이는 것  : {', '.join(a.items) if a.items else '(없음)'}")


def _print_memos(result) -> None:
    if result.title:
        print(f"   제목: {result.title}  ({len(result.title)}자)")
    if not result.memos:
        print("   메모: (없음)")
        return
    print(f"   메모 {len(result.memos)}개")
    for i, memo in enumerate(result.memos, 1):
        arrow = result.memo_targets[i - 1] if i <= len(result.memo_targets) else None
        mark = f"  → {arrow}" if arrow else "  (화살표 없음)"
        print(f"     {i:2}. {memo}  ({len(memo)}자){mark}")


def run_one(path: Path, style: WritingStyle, args, attempt: int = 1) -> bool:
    # 같은 사진을 두 배치로 돌려 나란히 볼 수 있게 파일 이름을 갈라 둔다.
    # 덮어쓰면 비교할 것이 남지 않는다.
    stem = f"{path.stem}-{style.value}-{'loose' if args.loose else 'strict'}"
    if args.repeat > 1:
        stem += f"-{attempt}"

    print()
    print("=" * 72)
    print(f"사진: {path.name}    말투: {STYLE_LABEL[style]}    배치: {stem.rsplit('-', 1)[-1]}")
    print("=" * 72)

    try:
        data = path.read_bytes()
    except OSError as error:
        print(f"   파일을 열지 못했습니다: {error}")
        return False

    started = time.perf_counter()
    result = build_card(
        data,
        style,
        pet_name=args.pet,
        place_name=args.place,
        place_description=args.place_desc,
        date_text=args.date,
        ink_plate=args.ink_plate,
        loose=args.loose,
    )
    total = time.perf_counter() - started

    print("\n[단계 1 — 사진 분석]")
    _print_analysis(result)
    print("\n[단계 2 — 메모]")
    _print_memos(result)

    print("\n[시간]")
    for name, seconds in result.timings.items():
        print(f"   {name:<12} {seconds:>6.2f}초")
    print(f"   {'합계':<11} {total:>6.2f}초")

    if result.source_size:
        print("\n[크기]")
        mark = "" if result.requested_size == result.generated_size else "   <- 요청과 다름!"
        print(f"   원본       {result.source_size}")
        print(f"   업로드     {result.upload_size}   (표준화 후)")
        print(f"   생성 요청  {result.requested_size}")
        print(f"   생성 결과  {result.generated_size}{mark}")
        print(f"   최종 카드  {result.result_size}   (원본 비율, 긴 변 {card_render.LONG_EDGE})")

    print(f"\n[결과] {result.outcome.value}")
    if result.message:
        print(f"   안내 문구: {result.message}")

    if result.outcome is not CardOutcome.OK or result.png is None:
        return False

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{stem}.png"
    out.write_bytes(result.png)
    prompt_path = OUT_DIR / f"{stem}.prompt.txt"
    prompt_path.write_text(result.prompt, encoding="utf-8")
    print(f"   저장: {out}  ({len(result.png) // 1024}KB)")
    print(f"   프롬프트: {prompt_path}")

    # 합성 전 원판도 남긴다. 마스크를 손볼 때 travel_card_recompose 로 **공짜로** 다시
    # 합성할 수 있다 — 이게 없으면 눈금 하나 바꿀 때마다 카드값이 다시 나간다.
    if result.generated_png:
        suffix = "레이어" if args.ink_plate else "생성원판"
        raw = OUT_DIR / f"{stem}-{suffix}.png"
        raw.write_bytes(result.generated_png)
        print(f"   생성 원판: {raw}  (합성 전)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="여행기록 카드 파이프라인 확인")
    parser.add_argument("photos", nargs="+", type=Path, help="사진 파일 경로")
    parser.add_argument("--pet", help="반려동물 이름 (강아지 일기에 필요)")
    parser.add_argument("--place", help="장소명")
    parser.add_argument("--place-desc", help="장소 설명 (선택)")
    parser.add_argument("--date", help="날짜 표기 (예: 2026.09.08)")
    parser.add_argument(
        "--ink-plate",
        action="store_true",
        help="사진 대신 '검은 바탕 + 흰 손글씨' 레이어를 받아 원본에 얹는다.",
    )
    parser.add_argument(
        "--loose",
        action="store_true",
        help="배치·화살표 지시를 09-10 의 짧은 세 줄로 되돌린다(비교용).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="같은 설정으로 몇 번 돌릴지. 모델이 확률적이라 한 장으로는 판단이 어렵다.",
    )
    parser.add_argument(
        "--style",
        choices=[s.value for s in WritingStyle],
        help="한 말투만 돌린다. 없으면 둘 다.",
    )
    args = parser.parse_args()

    if not config.api_key():
        print("OPENAI_API_KEY 가 없습니다. apps/api/.env 또는 루트 .env 를 확인하세요.")
        return 1

    styles = [WritingStyle(args.style)] if args.style else list(WritingStyle)
    if not args.pet and WritingStyle.DOG_DIARY in styles:
        print("주의: --pet 이 없으면 강아지 일기의 화자 이름이 비어 '우리 강아지'로 나갑니다.\n")

    usd, krw = _estimate_cost()
    print(f"모델  vision={config.VISION_MODEL}  caption={config.CAPTION_MODEL}")
    print(f"      image={config.IMAGE_MODEL}  quality={config.IMAGE_QUALITY}")
    if args.ink_plate:
        print("      손글씨 레이어 모드 — 검은 바탕에 흰 글씨만 받아 원본에 얹습니다.")
    print(f"      배치 지시  {'느슨(09-10)' if args.loose else '빡빡(현재)'}")
    if "mini" in config.IMAGE_MODEL:
        print("      ⚠️  mini 는 작은 글씨의 한글이 깨집니다(2026-09-10 실측). 확인용으로만.")
    planned = len(args.photos) * len(styles) * max(1, args.repeat)
    print(f"예상 비용  카드 1장당 약 ${usd:.4f} (~{krw}원) · 총 {planned}장 (~{krw * planned}원)")
    print("           ※ 어림값입니다. 실제 청구액은 OpenAI 대시보드에서 확인하세요.")

    made = 0
    for path in args.photos:
        for style in styles:
            for attempt in range(1, max(1, args.repeat) + 1):
                if run_one(path, style, args, attempt):
                    made += 1

    total_cards = len(args.photos) * len(styles) * max(1, args.repeat)
    print()
    print("=" * 72)
    print(f"완료: {made}/{total_cards}장 생성")
    print(f"예상 총비용: 약 ${usd * total_cards:.3f} (~{krw * total_cards}원)")
    if made:
        print(f"\n결과를 눈으로 확인하세요 — {OUT_DIR}/")
        print("특히 볼 것:")
        print("  · 한글이 온전한 음절인가 (자음·모음이 홀로 떨어진 글자가 없는지)")
        print("  · 원본 사진이 그대로인가 (얼굴이 원본과 한 픽셀도 다르지 않아야 한다)")
        print("  · 몸을 벗어난 흰 테두리(유령 외곽선)가 남아 있지 않은가")
        print("  · 사진에 없는 것이 그려지지 않았는가 (특히 풍경 사진에 강아지)")
        print("  · 두 말투가 실제로 달라 보이는가")
    return 0 if made == total_cards else 1


if __name__ == "__main__":
    sys.exit(main())
