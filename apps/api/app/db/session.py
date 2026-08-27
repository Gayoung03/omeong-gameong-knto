"""PostgreSQL session configuration."""

from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager

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


#: 뒷작업이 "연결 하나 열어줘" 라고 부를 수 있는 것.
BackgroundSessionFactory = Callable[[], AbstractContextManager[Session]]


@contextmanager
def background_session() -> Generator[Session, None, None]:
    """BackgroundTasks 안에서 쓰는 DB 연결."""
    with SessionLocal() as session:
        yield session


def get_background_session() -> BackgroundSessionFactory:
    """뒷작업용 연결 공장. 엔드포인트가 의존성으로 받아 뒷작업에 넘긴다.

    요청용 연결(`get_db`)은 응답과 함께 닫히므로 BackgroundTasks 안에서 쓸 수
    없다. 그래서 새 연결이 필요하다.

    **의존성으로 만든 이유는 테스트다.** `SessionLocal` 을 곧장 부르면
    `settings.database_url` 로 붙는데, 그 값은 **공유 AWS RDS** 를 가리킬 수
    있다(tests/conftest.py 의 설명 참고). 갈아끼울 수 있게 해두지 않으면
    테스트가 팀 데이터를 건드린다.
    """
    return background_session
