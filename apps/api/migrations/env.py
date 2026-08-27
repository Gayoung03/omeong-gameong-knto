from logging.config import fileConfig

from alembic import context

from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.base import Base

config = context.config
# configparser 는 값 안의 "%" 를 보간 문법으로 읽는다.
# 비밀번호에 URL 인코딩 문자(%21 등)가 있으면 여기서 ValueError 가 나므로 이스케이프한다.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from app.db.session import engine

    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
