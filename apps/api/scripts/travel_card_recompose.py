"""합성 단계만 다시 돌린다 — **이미지 모델을 부르지 않는다.**

마스크 눈금(`card_render` 의 `_POP_MIN` 등)을 손볼 때 쓴다. `travel_card_smoke` 로
한 번 돌리면 `...-생성원판.png` 가 같이 저장되는데, 그 원판과 원본 사진만 있으면
합성은 몇 초 만에 공짜로 다시 할 수 있다. 눈금 하나 바꾸자고 카드값을 또 낼 이유가 없다.

    uv run python -m scripts.travel_card_recompose \
        ~/사진/털봉_샘플_01.jpg \
        tmp/travel-cards/털봉_샘플_01-dog_diary-생성원판.png

`--mask` 를 붙이면 마스크 자체도 흑백 PNG 로 떨어뜨린다. 결과가 이상할 때
"무엇을 손글씨로 쳤는가" 를 눈으로 보는 것이 제일 빠르다.
"""

import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageOps

from app.integrations.llm.travel_card import card_render
from app.integrations.llm.travel_card.types import ImageInput


def main() -> int:
    parser = argparse.ArgumentParser(description="합성 단계만 다시 실행 (API 호출 없음)")
    parser.add_argument("photo", type=Path, help="원본 사진")
    parser.add_argument("generated", type=Path, help="합성 전 생성 원판 PNG")
    parser.add_argument("-o", "--out", type=Path, help="저장 경로 (기본: 원판 옆에 -재합성.png)")
    parser.add_argument("--mask", action="store_true", help="마스크도 흑백 PNG 로 저장")
    parser.add_argument(
        "--plate", action="store_true", help="검은 바탕 + 흰 손글씨 레이어를 넘긴 경우"
    )
    args = parser.parse_args()

    for path in (args.photo, args.generated):
        if not path.is_file():
            print(f"파일이 없습니다: {path}")
            return 1

    data = args.photo.read_bytes()
    with Image.open(io.BytesIO(data)) as probe:
        width, height = ImageOps.exif_transpose(probe).size
    original = ImageInput(data=data, mime_type="image/jpeg", width=width, height=height)

    out = args.out or args.generated.with_name(f"{args.generated.stem}-재합성.png")
    merge = card_render.compose_from_plate if args.plate else card_render.compose
    out.write_bytes(merge(original, args.generated.read_bytes()))
    print(f"저장: {out}")

    if args.mask and args.plate:
        print("레이어 모드는 마스크가 곧 레이어 자체입니다 — 원판을 그대로 보세요.")
    elif args.mask:
        mask_path = out.with_name(f"{out.stem}-마스크.png")
        card_render.save_mask(original, args.generated.read_bytes(), mask_path)
        print(f"마스크: {mask_path}   (흰 곳이 손글씨로 친 자리다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
