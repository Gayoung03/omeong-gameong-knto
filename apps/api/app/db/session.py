"""PostgreSQL session configuration."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    # DB에서 읽어오는 시각을 한국시간(+09:00)으로 돌려받는다.
    # 저장 방식은 그대로다 — timestamptz 는 "절대 시각"을 담고, 표기만 KST 로 통일한다.
    # UTC 로 내려가면 이른 아침 일정에서 날짜가 하루 밀리는 버그가 난다.
    connect_args={"options": "-c timezone=Asia/Seoul"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
