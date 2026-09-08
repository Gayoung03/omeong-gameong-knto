"""가입된 계정의 관리자 권한을 부여하거나 회수한다.

예:
    cd apps/api
    uv run python -m scripts.manage_admin grant --email admin@example.com
    uv run python -m scripts.manage_admin revoke --email admin@example.com
"""

import argparse

from sqlalchemy import select

from app.core.config import settings
from app.db.models import User
from app.db.session import SessionLocal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="관리자 권한 관리")
    parser.add_argument("action", choices=("grant", "revoke"))
    parser.add_argument("--email", required=True, help="가입된 계정 이메일")
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="운영 DB 변경을 명시적으로 확인",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    if settings.environment == "production" and not args.confirm_production:
        raise SystemExit("운영에서는 --confirm-production을 함께 입력하세요.")

    email = args.email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None or user.deleted_at is not None:
            raise SystemExit(f"활성 계정을 찾을 수 없습니다: {email}")

        user.is_admin = args.action == "grant"
        db.commit()
        state = "부여" if user.is_admin else "회수"
        print(f"관리자 권한 {state} 완료: {email}")


if __name__ == "__main__":
    main()
