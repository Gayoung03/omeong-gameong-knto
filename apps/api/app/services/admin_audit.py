"""관리자 감사 로그 공용 헬퍼.

여행 이야기·문의·공지가 각자 자기 도메인 테이블에 이력을 쓴다. `changes` 는
JSONB 라 저장 전에 Enum·datetime 을 JSON 이 담을 수 있는 값으로 바꿔야 한다.
"""

from datetime import datetime
from enum import Enum


def json_value(value: object) -> object:
    """Enum·datetime·중첩 컨테이너를 JSON 으로 저장 가능한 값으로 바꾼다."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    return value
