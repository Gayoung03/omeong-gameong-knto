"""시드 데모 계정(seed@omeong.local)의 비어 있는 password_hash 를 채운다.

`ck_users_local_requires_password`(local → password_hash NOT NULL)를 VALIDATE 하기 전에,
2026-08-22 시드가 남긴 위반 행 1건을 정리하는 용도다. dev RDS·프로덕션 모두에서 쓴다.

**안전장치**: 오직 시드 계정 UUID(DEV_USER_ID)만, 그것도 `password_hash IS NULL` 일 때만
UPDATE 한다. 실사용자 계정은 절대 건드리지 않는다(실사용자의 빈 비밀번호를 임의 해시로
채우는 것은 보안 사고이므로, 대상을 이 한 계정으로 못박는다).

실행:
    SEED_DEV_PASSWORD='<데모비밀번호>' uv run python -m scripts.patch_seed_password
프로덕션(railway ssh, 컨테이너 안):
    SEED_DEV_PASSWORD='<데모비밀번호>' .venv/bin/python -m scripts.patch_seed_password

DATABASE_URL 이 가리키는 DB 에 붙는다. 비밀번호는 프로세스 목록·셸 히스토리에 남으니
실행 후 히스토리를 정리한다. 멱등: 이미 해시가 있으면 0건 업데이트.
"""

import os

from sqlalchemy import update

from app.api.dependencies import DEV_USER_ID
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal

SEED_USER_EMAIL = "seed@omeong.local"


def main() -> None:
    password = os.environ.get("SEED_DEV_PASSWORD")
    if not password:
        raise SystemExit(
            "SEED_DEV_PASSWORD 를 설정하세요.\n"
            "예) SEED_DEV_PASSWORD='<데모비밀번호>' uv run python -m scripts.patch_seed_password"
        )

    with SessionLocal() as db:
        result = db.execute(
            update(User)
            .where(
                User.id == DEV_USER_ID,
                User.auth_provider == "local",
                User.password_hash.is_(None),
            )
            .values(password_hash=hash_password(password))
        )
        db.commit()
        count = result.rowcount

    if count:
        print(f"완료: 시드 계정({SEED_USER_EMAIL}) 비밀번호 해시를 채웠습니다 ({count}건).")
    else:
        print(
            "변경 없음 — 이미 해시가 있거나 대상 계정이 없습니다. "
            "위반 행 존재 여부는 아래 SQL 로 확인하세요:\n"
            "  SELECT count(*) FROM users WHERE auth_provider='local' AND password_hash IS NULL;"
        )


if __name__ == "__main__":
    main()
