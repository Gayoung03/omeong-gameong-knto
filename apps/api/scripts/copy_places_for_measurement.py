"""측정용 장소 데이터 로컬 복제 — 팀 RDS 에서 SELECT 만 읽어 로컬 DB 로 옮긴다.

시나리오 매트릭스 측정(`measure_scenarios`)은 장소 데이터가 있어야 의미가 있는데,
로컬 시드는 4곳뿐이다. 팀 RDS(1299곳)에서 **읽기 전용**으로 장소 계열 테이블만 떠서
로컬 측정 DB 로 복사한다. RDS 에는 아무것도 쓰지 않는다.

**대상(--target-url)은 로컬 호스트(localhost/127.0.0.1/::1)만 허용한다**(허용목록) — 실수로
RDS·실서비스에 쓰는 것을 막는다. 다만 Railway ssh·포트포워딩은 localhost 로도 붙을 수 있어
허용목록으로도 못 막으니 **로컬 compose DB 전용으로만 쓰고, 포워딩된 원격에는 쓰지 말 것.**
대상 테이블은 매번 비우고 다시 채운다(idempotent). 측정이 끝나면 로컬 DB 를 원상태로
되돌리려면 `--truncate-only` 로 다시 부른다.

    uv run python -m scripts.copy_places_for_measurement \
        [--source-url <RDS URL, 기본 .env DATABASE_URL>] \
        --target-url postgresql+psycopg://omeong:omeong@localhost:5432/omeong_test \
        [--truncate-only]
"""

from __future__ import annotations

import argparse

from sqlalchemy import MetaData, Table, create_engine, delete, insert, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import (
    Place,
    PlaceBusinessHour,
    PlacePetPolicy,
    PlaceTag,
    PlaceTagLink,
)

# 삽입 순서(FK 만족): 독립 테이블 먼저, 의존 테이블 나중.
COPY_ORDER = [PlaceTag, Place, PlacePetPolicy, PlaceBusinessHour, PlaceTagLink]
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def _require_local(url: str) -> None:
    if not any(host in url for host in LOCAL_HOSTS):
        raise SystemExit(
            f"거부: 대상(--target-url)이 로컬이 아닙니다({url!r}). 이 스크립트는 로컬 측정 DB "
            "에만 씁니다(RDS·실서비스 쓰기 금지)."
        )


def _truncate(target: Session) -> None:
    for model in reversed(COPY_ORDER):
        target.execute(delete(model.__table__))


def main() -> None:
    parser = argparse.ArgumentParser(description="측정용 장소 데이터 로컬 복제(RDS 읽기전용)")
    parser.add_argument("--source-url", default=settings.database_url, help="원본(기본 .env)")
    parser.add_argument("--target-url", required=True, help="대상(localhost 만 허용)")
    parser.add_argument(
        "--truncate-only", action="store_true", help="복사 없이 대상 장소 테이블만 비운다"
    )
    args = parser.parse_args()
    _require_local(args.target_url)

    target_engine = create_engine(args.target_url)
    with Session(target_engine) as target:
        _truncate(target)
        if args.truncate_only:
            target.commit()
            print("대상 장소 테이블을 비웠습니다.")
            return

        source_engine = create_engine(args.source_url)
        # 원본(RDS)이 코드 모델보다 마이그레이션이 뒤처져 있을 수 있어(재설계 DB 미적용)
        # 실제 존재하는 컬럼만 반영해 읽는다. 대상에만 있는 새 컬럼은 기본값·NULL 로 채워진다.
        source_meta = MetaData()
        with source_engine.connect() as source_conn:
            source_conn.execute(text("SET default_transaction_read_only = on"))
            for model in COPY_ORDER:
                source_table = Table(
                    model.__table__.name, source_meta, autoload_with=source_conn
                )
                rows = [dict(row._mapping) for row in source_conn.execute(select(source_table))]
                if rows:
                    target.execute(insert(model.__table__), rows)
                print(
                    f"{model.__table__.name}: {len(rows)}행 복사 "
                    f"(컬럼 {len(source_table.columns)})"
                )
        source_engine.dispose()
        target.commit()
    target_engine.dispose()
    print("완료 — 로컬 측정 DB 준비됨.")


if __name__ == "__main__":
    main()
