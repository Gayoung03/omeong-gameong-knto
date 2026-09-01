"""공지 등록과 알림 발송을 한 번에 실행한다.

사용법: uv run python scripts/publish_notice.py "제목" "내용" [--pinned]
"""

import argparse

from app.db.session import SessionLocal
from app.services.notices import publish_notice


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("title")
    parser.add_argument("content")
    parser.add_argument("--pinned", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        notice = publish_notice(db, title=args.title, content=args.content, is_pinned=args.pinned)
        notice_id = notice.id
    print(f"공지 등록 완료: {notice_id}")


if __name__ == "__main__":
    main()
