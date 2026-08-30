#!/usr/bin/env bash
#
# 로컬 .env 의 DATABASE_URL(= dev DB)에서 pg_dump 로 덤프를 뜬다. 읽기 전용.
#
#   infra/scripts/dump_dev_db.sh [출력_경로]
#   make db-dump-dev
#
# - 이 스크립트는 dev DB 전용이다. 프로덕션(Railway)은 권한 정책상 자동화하지 않는다 —
#   프로덕션 덤프는 사용자가 직접 떠서 restore_rehearsal.sh 에 넘긴다.
# - pg_dump 는 조회만 하므로 원본 dev DB 를 변경하지 않는다.
# - 커스텀 포맷(-Fc)으로 저장 → restore_rehearsal.sh 가 pg_restore 로 복원.
# - 산출물은 infra/dumps/ 아래에 떨어지며 .gitignore 로 커밋에서 제외된다(데이터 유출 방지).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f .env ]; then
  echo "오류: 루트 .env 가 없습니다. DATABASE_URL 을 읽을 수 없습니다." >&2
  exit 2
fi

# .env 에서 DATABASE_URL 만 추출(값에 특수문자가 있어도 안전하게 라인 그대로).
RAW_URL="$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2-)"
if [ -z "$RAW_URL" ]; then
  echo "오류: .env 에 DATABASE_URL 이 없습니다." >&2
  exit 2
fi

# SQLAlchemy 드라이버 접두어(postgresql+psycopg)를 libpq 가 이해하는 postgresql 로 바꾼다.
LIBPQ_URL="${RAW_URL/postgresql+psycopg:\/\//postgresql://}"

DUMPS_DIR="infra/dumps"
mkdir -p "$DUMPS_DIR"
OUT="${1:-$DUMPS_DIR/dev-$(date +%Y%m%d-%H%M%S).dump}"
OUT_DIR="$(cd "$(dirname "$OUT")" && pwd)"
OUT_BASE="$(basename "$OUT")"

IMAGE="${REHEARSAL_PG_IMAGE:-pgvector/pgvector:pg18}"

# 호스트에 pg_dump 가 없어도 되도록 컨테이너로 실행한다.
# 기본 pg18 도구는 dev(RDS 16.14) 서버를 덤프하는 방향(신버전 도구→구버전 서버)이라 안전하다.
# dev 가 pg18 보다 신버전이 되면 그때 REHEARSAL_PG_IMAGE 로 맞춘다.
HOST_HINT="$(printf '%s' "$LIBPQ_URL" | sed -E 's#(://[^:/@]+:)[^@]+@#\1***@#')"
echo "▶ dev DB 덤프 시작(읽기 전용): $HOST_HINT"
echo "   → $OUT"

docker run --rm \
  -v "$OUT_DIR:/dumps" \
  "$IMAGE" \
  pg_dump -Fc --no-owner --no-privileges -d "$LIBPQ_URL" -f "/dumps/$OUT_BASE"

echo "완료: $OUT"
echo "다음 단계: make db-rehearsal-restore DUMP=$OUT"
