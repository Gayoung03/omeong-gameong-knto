#!/usr/bin/env bash
#
# 프로덕션(또는 dev) 덤프 파일을 리허설 Postgres 에 복원한다.
#
#   infra/scripts/restore_rehearsal.sh <덤프_파일_경로>
#   DUMP=<경로> infra/scripts/restore_rehearsal.sh
#   make db-rehearsal-restore DUMP=<경로>
#
# - 덤프 획득은 이 스크립트 밖의 일이다. 프로덕션(Railway) 덤프는 권한 정책상
#   사용자가 직접 떠서(railway 등) 가져다준 파일을 입력으로 받는다.
# - 지원 형식: pg_dump 커스텀 포맷(-Fc, 권장) / 평문 .sql / 평문 .sql.gz.
# - 복원 전 리허설 DB 를 통째로 DROP·CREATE 하므로 기존 리허설 데이터는 사라진다.
#   (프로덕션·dev 원본에는 절대 손대지 않는다 — 대상은 로컬 리허설 컨테이너뿐.)
# - 복원 후 alembic_version 을 출력해 "어느 리비전의 덤프인지" 검증한다.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

DUMP="${1:-${DUMP:-}}"
if [ -z "$DUMP" ]; then
  echo "오류: 덤프 파일 경로가 필요합니다." >&2
  echo "사용법: $0 <덤프_파일_경로>   또는   make db-rehearsal-restore DUMP=<경로>" >&2
  exit 2
fi
if [ ! -f "$DUMP" ]; then
  echo "오류: 파일을 찾을 수 없습니다: $DUMP" >&2
  exit 2
fi

COMPOSE=(docker compose -f infra/docker-compose.rehearsal.yml)
SVC=postgres-rehearsal
PGDB="${REHEARSAL_PG_DB:-omeong}"
PGUSER="${REHEARSAL_PG_USER:-omeong}"

echo "▶ 리허설 Postgres 기동(없으면 생성)…"
"${COMPOSE[@]}" up -d --wait "$SVC"

# 컨테이너 안에서 psql/pg_restore 를 돌린다 → 이미지 버전과 복원 도구 버전이 항상 일치.
dexec() { "${COMPOSE[@]}" exec -T "$SVC" "$@"; }

echo "▶ 리허설 DB '$PGDB' 초기화(DROP·CREATE)…"
# 활성 커넥션을 끊고, 유지보수 DB(postgres)에 붙어 대상 DB 를 재생성한다.
dexec psql -v ON_ERROR_STOP=1 -U "$PGUSER" -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$PGDB' AND pid <> pg_backend_pid();" >/dev/null
dexec psql -v ON_ERROR_STOP=1 -U "$PGUSER" -d postgres -c "DROP DATABASE IF EXISTS \"$PGDB\";"
dexec psql -v ON_ERROR_STOP=1 -U "$PGUSER" -d postgres -c "CREATE DATABASE \"$PGDB\" OWNER \"$PGUSER\";"

# 형식 판별: 커스텀 포맷 덤프는 매직 바이트 "PGDMP" 로 시작한다.
magic="$(head -c 5 "$DUMP" 2>/dev/null || true)"
echo "▶ 복원 시작: $DUMP"
if [ "$magic" = "PGDMP" ]; then
  echo "   (형식: pg_dump 커스텀 포맷 → pg_restore)"
  # 소유자·권한 구문은 무시한다(리허설 롤이 원본과 다르므로). 대상 DB 로 직접 복원.
  "${COMPOSE[@]}" cp "$DUMP" "$SVC:/tmp/rehearsal.dump"
  set +e
  dexec pg_restore --no-owner --no-privileges -U "$PGUSER" -d "$PGDB" /tmp/rehearsal.dump
  rc=$?
  set -e
  dexec rm -f /tmp/rehearsal.dump || true
  # pg_restore 는 소유자/권한 관련 무해한 경고로 비0을 낼 수 있다. 데이터는 아래에서 검증.
  [ "$rc" -ne 0 ] && echo "   ⚠ pg_restore 종료코드 $rc (소유자/권한 경고일 수 있음 — 아래 검증으로 확인)"
else
  case "$DUMP" in
    *.gz) echo "   (형식: gzip 평문 SQL → zcat | psql)"
          zcat "$DUMP" | dexec psql -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$PGDB" ;;
    *)    echo "   (형식: 평문 SQL → psql)"
          dexec psql -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$PGDB" < "$DUMP" ;;
  esac
fi

echo "▶ 검증: alembic_version"
if dexec psql -tA -U "$PGUSER" -d "$PGDB" -c "SELECT to_regclass('public.alembic_version');" | grep -q alembic_version; then
  ver="$(dexec psql -tA -U "$PGUSER" -d "$PGDB" -c "SELECT version_num FROM alembic_version;")"
  echo "   ✅ 복원된 스키마 리비전(alembic_version): ${ver:-<빈 테이블>}"
else
  echo "   ⚠ alembic_version 테이블이 없습니다. 이 덤프에는 마이그레이션 이력이 없거나, 복원이 스키마까지 도달하지 못했습니다." >&2
  exit 1
fi

echo "▶ 참고: 테이블 수 = $(dexec psql -tA -U "$PGUSER" -d "$PGDB" -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")"
echo "완료. 다음 단계: make db-rehearsal-migrate 로 새 마이그레이션을 이 복원본 위에서 리허설하세요."
