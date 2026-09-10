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

from app.integrations.llm.travel_card import config
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
_IMAGE_COST = {"low": 0.011, "medium": 0.042, "high": 0.17}
_KRW = 1400


def _estimate_cost() -> tuple[float, int]:
    usd = _TEXT_COST_PER_CALL + _IMAGE_COST.get(config.IMAGE_QUALITY, 0.042)
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
        print(f"     {i:2}. {memo}  ({len(memo)}자)")


def run_one(path: Path, style: WritingStyle, args) -> bool:
    print()
    print("=" * 72)
    print(f"사진: {path.name}    말투: {STYLE_LABEL[style]}")
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

    print(f"\n[결과] {result.outcome.value}")
    if result.message:
        print(f"   안내 문구: {result.message}")

    if result.outcome is not CardOutcome.OK or result.png is None:
        return False

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{path.stem}-{style.value}.png"
    out.write_bytes(result.png)
    prompt_path = OUT_DIR / f"{path.stem}-{style.value}.prompt.txt"
    prompt_path.write_text(result.prompt, encoding="utf-8")
    print(f"   저장: {out}  ({len(result.png) // 1024}KB)")
    print(f"   프롬프트: {prompt_path}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="여행기록 카드 파이프라인 확인")
    parser.add_argument("photos", nargs="+", type=Path, help="사진 파일 경로")
    parser.add_argument("--pet", help="반려동물 이름 (강아지 일기에 필요)")
    parser.add_argument("--place", help="장소명")
    parser.add_argument("--place-desc", help="장소 설명 (선택)")
    parser.add_argument("--date", help="날짜 표기 (예: 2026.09.08)")
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
    print(f"예상 비용  카드 1장당 약 ${usd:.4f} (~{krw}원) · 총 {len(args.photos) * len(styles)}장")
    print("           ※ 어림값입니다. 실제 청구액은 OpenAI 대시보드에서 확인하세요.")

    made = 0
    for path in args.photos:
        for style in styles:
            if run_one(path, style, args):
                made += 1

    total_cards = len(args.photos) * len(styles)
    print()
    print("=" * 72)
    print(f"완료: {made}/{total_cards}장 생성")
    print(f"예상 총비용: 약 ${usd * total_cards:.3f} (~{krw * total_cards}원)")
    if made:
        print(f"\n결과를 눈으로 확인하세요 — {OUT_DIR}/")
        print("특히 볼 것:")
        print("  · 한글이 온전한 음절인가 (자음·모음이 홀로 떨어진 글자가 없는지)")
        print("  · 원본 사진이 그대로인가 (얼굴·색감이 바뀌지 않았는지)")
        print("  · 사진에 없는 것이 그려지지 않았는가 (특히 풍경 사진에 강아지)")
        print("  · 두 말투가 실제로 달라 보이는가")
    return 0 if made == total_cards else 1


if __name__ == "__main__":
    sys.exit(main())
