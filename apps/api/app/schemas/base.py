"""API 스키마 공통 베이스.

모든 요청·응답 스키마는 이 클래스를 상속한다.
설정을 여기 한 곳에 모아두면 스키마마다 복붙할 일이 없고, 하나만 빠뜨려
그 스키마만 다르게 동작하는 사고를 막는다.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class APISchema(BaseModel):
    """오멍가멍 API가 주고받는 데이터의 부모 클래스."""

    model_config = ConfigDict(
        # 파이썬은 snake_case, API 응답은 camelCase (docs/api/README.md 6장).
        # start_at -> startAt 처럼 나갈 때만 바뀐다.
        alias_generator=to_camel,
        # 파이썬 코드에서는 안쪽 이름(start_at)으로도 만들 수 있게 한다.
        populate_by_name=True,
        # SQLAlchemy 모델은 딕셔너리가 아니라 객체다.
        # "대괄호 말고 점으로 꺼내도 된다"는 허락.
        from_attributes=True,
    )
