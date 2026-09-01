"""중복 장소 2쌍(협재해수욕장·한림공원) 머지 — 시드본 → 유입본 (ai-io-column-design 7.2·8.1).

seed_dev 가 이미 유입(수집)된 장소가 있는 DB(dev·프로덕션 RDS)에 돌면서, 같은 장소의
**시드 사본**을 하나 더 만들었다. 유입본을 정본으로 삼아 참조를 이관하고 시드본은
비활성(is_active=false)으로 내린다. 시드본을 하드 삭제하지 않는 것은 설계 결정이다.

- **정본(유입본)**: 이름이 같고 시드 UUID 가 아니며 external_refs 를 가진 활성 장소.
- **시드본(source)**: seed_dev SEED_PLACES 의 고정 UUID(협재 …0101 / 한림 …0103).

이관 규칙 (place_id FK 10곳):
- **보존(재지정 source→target)**: favorites·reviews·travel_logs·route_items·
  route_requests.departure_place_id·route_request_stays — 사용자·여행 데이터.
  복합 UNIQUE(favorites)는 target 에 이미 있는 조합을 피해 재지정 후 잔여 삭제.
- **폐기(시드본 것 삭제)**: place_external_refs·place_business_hours·place_pet_policies·
  place_tag_links — 장소 고유 속성은 유입본이 정본(8.1: 병합하면 이중 진실원본 재생산).
  시드본이 갖고 target 이 없는 사본이 있으면 로그로 경고한다(그런 행이 있으면 수동 확인).

성질: 시드본이 이미 비활성이면 건너뜀(멱등). **기본 dry-run**, `--apply` 로 반영.

실행:
    uv run python -m scripts.merge_duplicate_places            # dry-run
    uv run python -m scripts.merge_duplicate_places --apply    # 반영
"""

import sys
import uuid

from sqlalchemy import text

from app.db.session import SessionLocal

# (시드본 UUID, 장소 이름) — seed_dev.SEED_PLACES 의 고정 ID 와 일치.
PAIRS = [
    (uuid.UUID("00000000-0000-0000-0000-000000000101"), "협재해수욕장"),
    (uuid.UUID("00000000-0000-0000-0000-000000000103"), "한림공원"),
]

# 보존: (테이블, place_id 컬럼). route_requests 만 컬럼명이 다르다.
PRESERVE_SIMPLE = [
    ("reviews", "place_id"),
    ("travel_logs", "place_id"),
    ("route_items", "place_id"),
    ("route_requests", "departure_place_id"),
    ("route_request_stays", "place_id"),
]
# 폐기: 장소 하위 속성 테이블.
DISCARD_SUB = [
    "place_external_refs",
    "place_business_hours",
    "place_pet_policies",
    "place_tag_links",
]


def _resolve_target(db, source_id, name):
    """이름이 같고 시드본이 아니며 external_refs 를 가진 활성 장소(유입본)를 찾는다."""
    rows = db.execute(
        text(
            "SELECT p.id, (SELECT count(*) FROM place_external_refs r WHERE r.place_id=p.id) refs "
            "FROM places p WHERE p.name=:name AND p.id<>:sid AND p.is_active=true"
        ),
        {"name": name, "sid": str(source_id)},
    ).all()
    withrefs = [r for r in rows if r.refs > 0]
    if len(withrefs) == 1:
        return withrefs[0].id
    return None  # 0개 또는 모호(여러개) — 호출부에서 건너뛴다.


def _count(db, sql, params):
    return db.execute(text(sql), params).scalar() or 0


def main() -> None:
    apply = "--apply" in sys.argv[1:]
    with SessionLocal() as db:
        any_action = False
        for source_id, name in PAIRS:
            src = db.execute(
                text("SELECT id, is_active FROM places WHERE id=:id"), {"id": str(source_id)}
            ).first()
            if src is None:
                print(f"[{name}] 시드본({source_id}) 없음 — 건너뜀")
                continue
            if not src.is_active:
                print(f"[{name}] 시드본 이미 비활성 — 건너뜀(멱등)")
                continue
            target = _resolve_target(db, source_id, name)
            if target is None:
                print(f"[{name}] ⚠ 유입본(정본) 확정 실패(0개 또는 모호) — 건너뜀. 수동 확인 필요.")
                continue

            print(f"[{name}] 시드본 {source_id} → 유입본 {target}")
            p = {"src": str(source_id), "tgt": str(target)}

            for tbl, col in PRESERVE_SIMPLE:
                n = _count(db, f"SELECT count(*) FROM {tbl} WHERE {col}=:src", p)
                if n:
                    print(f"    보존 재지정 {tbl}.{col}: {n}건")
                    any_action = True
                    if apply:
                        db.execute(
                            text(f"UPDATE {tbl} SET {col}=:tgt WHERE {col}=:src"), p
                        )

            # favorites 복합 UNIQUE(user_id, place_id)
            fav = _count(db, "SELECT count(*) FROM favorites WHERE place_id=:src", p)
            if fav:
                print(f"    보존 재지정 favorites: {fav}건(중복 조합은 잔여 삭제)")
                any_action = True
                if apply:
                    db.execute(
                        text(
                            "UPDATE favorites SET place_id=:tgt WHERE place_id=:src AND user_id "
                            "NOT IN (SELECT user_id FROM favorites WHERE place_id=:tgt)"
                        ),
                        p,
                    )
                    db.execute(text("DELETE FROM favorites WHERE place_id=:src"), p)

            for tbl in DISCARD_SUB:
                n = _count(db, f"SELECT count(*) FROM {tbl} WHERE place_id=:src", p)
                if n:
                    tn = _count(db, f"SELECT count(*) FROM {tbl} WHERE place_id=:tgt", p)
                    if tn == 0:
                        print(f"    ⚠ {tbl}: 시드본 {n}건, 유입본 0건 — 폐기 전 수동 확인 권장")
                    else:
                        print(f"    폐기 {tbl}: 시드본 {n}건 삭제(유입본 {tn}건 유지)")
                    any_action = True
                    if apply:
                        db.execute(text(f"DELETE FROM {tbl} WHERE place_id=:src"), p)

            print("    시드본 is_active=false")
            any_action = True
            if apply:
                db.execute(
                    text("UPDATE places SET is_active=false WHERE id=:src"), p
                )

        if apply and any_action:
            db.commit()
            print("완료: 반영됨.")
        elif not apply and any_action:
            print("\n(DRY-RUN) 실제 반영하려면 --apply 를 붙여 다시 실행하세요.")
        else:
            print("바꿀 것이 없습니다(멱등).")


if __name__ == "__main__":
    main()
