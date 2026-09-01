"""transport_pet_rules 무게 무제한·조건부 사실 백필 (ai-io-column-design 7.4·8.1).

#4 마이그레이션으로 신설한 컬럼에 실데이터를 채운다. 리허설에서 검증한 값·해석이며,
근거는 각 행 notes 원문을 인용한다. 대상 행은 carrier_name 으로 명시한다.

대상·근거
- **한일고속페리** → `cabin_weight_unlimited = true`
  notes 원문: "무게 제한이 명시되어 있지 않아 대형견도 함께 갈 수 있다."
- **씨월드고속훼리(객실 등급 행)** → `cabin_weight_unlimited = true`
  notes 원문: "객실 등급이 무게로 갈린다 — 펫코노미 4kg 미만, 펫스탠다드룸·퀸메리…"
  해석: 무게는 **객실 등급만 가를 뿐 탑승 자체에 상한은 없다**(어떤 무게도 탑승 가능,
  등급만 달라짐). 설계 7.4의 "객실별 무게 등급은 텍스트 유지"와 정합 — 상한이 아니라 분류.
- **아리온제주(남해고속)** → `cabin_conditions = '원칙적으로 불가, 부득이한 경우 케이지 동반 허용'`
  notes 원문: "선사 안내상 애완견 동승이 원칙적으로 불가하다. 부득이한 경우에만 케이지…"
- **오션비스타제주 등은 제외** — notes 에 무게 관련 근거가 없어 미확인(NULL) 유지.
  근거 없는 무제한 주입은 과보정이라 하지 않는다.

성질
- 멱등: 이미 값이 있는 행(IS NOT NULL)은 건너뛴다.
- CHECK(`*_weight_unlimited IS NOT TRUE OR *_max_weight_kg IS NULL`) 때문에 unlimited 는
  `cabin_max_weight_kg IS NULL` 인 행만 대상(한일·씨월드 객실등급 행이 이에 해당).
- **기본 dry-run**(무엇을 바꿀지 출력만). `--apply` 로 실제 반영.

실행:
    uv run python -m scripts.backfill_transport_rules            # dry-run
    uv run python -m scripts.backfill_transport_rules --apply    # 반영
프로덕션(railway ssh): `.venv/bin/python -m scripts.backfill_transport_rules --apply`
"""

import sys

from sqlalchemy import select, update

from app.db.models import TransportPetRule
from app.db.session import SessionLocal

ARION_CONDITIONS = "원칙적으로 불가, 부득이한 경우 케이지 동반 허용"


def _rows_to_change(db):
    """(설명, 매칭 조건) → 실제로 바뀔 행 목록을 만든다."""
    plans = []

    # 한일: cabin 무게 무제한
    hanil = db.scalars(
        select(TransportPetRule).where(
            TransportPetRule.carrier_name == "한일고속페리",
            TransportPetRule.cabin_max_weight_kg.is_(None),
            TransportPetRule.cabin_weight_unlimited.is_(None),
        )
    ).all()
    for r in hanil:
        plans.append((r, "cabin_weight_unlimited", True))

    # 씨월드 객실등급 행: cabin 무게 무제한
    seaworld = db.scalars(
        select(TransportPetRule).where(
            TransportPetRule.carrier_name == "씨월드고속훼리",
            TransportPetRule.notes.like("%객실 등급이 무게로%"),
            TransportPetRule.cabin_max_weight_kg.is_(None),
            TransportPetRule.cabin_weight_unlimited.is_(None),
        )
    ).all()
    for r in seaworld:
        plans.append((r, "cabin_weight_unlimited", True))

    # 아리온: 조건부 사실
    arion = db.scalars(
        select(TransportPetRule).where(
            TransportPetRule.carrier_name == "아리온제주(남해고속)",
            TransportPetRule.cabin_conditions.is_(None),
        )
    ).all()
    for r in arion:
        plans.append((r, "cabin_conditions", ARION_CONDITIONS))

    return plans


def main() -> None:
    apply = "--apply" in sys.argv[1:]

    with SessionLocal() as db:
        plans = _rows_to_change(db)

        if not plans:
            print("바꿀 행이 없습니다(이미 백필됐거나 대상 행 부재). 멱등 종료.")
            return

        print(f"{'적용' if apply else 'DRY-RUN'}: {len(plans)}건")
        for row, col, val in plans:
            print(f"  {row.carrier_name} [{row.carrier_type.value}] {col} = {val!r}")

        if not apply:
            print("\n실제 반영하려면 --apply 를 붙여 다시 실행하세요.")
            return

        for row, col, val in plans:
            db.execute(
                update(TransportPetRule)
                .where(TransportPetRule.id == row.id)
                .values(**{col: val})
            )
        db.commit()
        print(f"완료: {len(plans)}건 반영.")


if __name__ == "__main__":
    main()
