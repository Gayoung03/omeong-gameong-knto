"""S3 저장소 읽기·쓰기.

## 왜 새 파일인가

`api/v1/endpoints/uploads.py` 도 S3 에 올린다. 그쪽은 **앱이 보낸 파일**을 받는
창구라 `UploadFile`·`HTTPException` 이 함께 딸려 있다. 여기는 **서버가 만든
결과물**을 올리고 원본을 되읽는 자리이고, 부르는 곳이 요청 바깥(백그라운드
작업)이라 HTTP 예외를 던질 수 없다. 그래서 순수 함수로 따로 뒀다.

`uploads.py` 를 이 모듈 위로 옮기는 정리가 남아 있다. **이번 브랜치에서는 하지
않았다** — 팀원 작업 브랜치가 열려 있는 파일이라 지금 건드려 충돌을 만들 이유가 없다.

## 원본을 왜 URL 로 내려받지 않고 키로 읽는가

원본 사진 주소는 앱이 보낸 값이다. `schemas/validators.py` 가 호스트를 검증하지만,
그 주소로 서버가 HTTP 요청을 보내는 순간 **서버가 바깥으로 요청을 내보내는 통로**가
하나 생긴다. 공개 주소에서 키만 떼어 버킷에서 직접 읽으면 그 통로가 아예 없고,
CloudFront 를 비공개로 잠가도 계속 동작한다. 덤으로 한 홉이 줄어 빠르다.
"""

import logging
import uuid
from datetime import datetime
from functools import lru_cache
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

KST = ZoneInfo("Asia/Seoul")


class StorageError(RuntimeError):
    """저장소 읽기·쓰기 실패. 부르는 쪽이 사용자에게 보일 말을 정한다."""


def is_configured() -> bool:
    """버킷과 공개 주소가 둘 다 있어야 쓸 수 있다."""
    return bool(settings.s3_bucket_name and settings.s3_public_base_url)


@lru_cache
def _client() -> Any:
    return boto3.client("s3", region_name=settings.aws_region)


def object_key_from_public_url(url: str) -> str | None:
    """공개 주소에서 버킷 안의 키만 떼어낸다. 우리 주소가 아니면 None.

    **`startswith` 로 비교하지 않는다.** `https://<허용호스트>@evil.com/x` 가
    통과해 버린다(`schemas/validators.py` 의 같은 설명). 호스트는 파싱해서 비교한다.
    """
    if not is_configured():
        return None

    base = urlsplit(settings.s3_public_base_url)
    base_host = (base.hostname or "").lower()
    base_path = base.path.rstrip("/")
    if not base_host:
        return None

    parsed = urlsplit(url)
    if (parsed.hostname or "").lower() != base_host:
        return None
    if base_path and not parsed.path.startswith(f"{base_path}/"):
        return None

    key = parsed.path[len(base_path) :].lstrip("/")
    # 빈 키와 상위 경로 탈출은 여기서 끊는다. 키는 우리가 만든 모양만 받는다.
    if not key or ".." in key.split("/"):
        return None
    return key


def download(object_key: str, *, max_bytes: int) -> bytes:
    """버킷에서 객체 하나를 읽는다.

    `max_bytes` 를 넘으면 **읽다가 멈추고 예외**를 던진다. 전부 읽은 뒤 크기를
    재면 상한을 넘는 파일이 이미 메모리에 들어와 있다.
    """
    try:
        body = _client().get_object(Bucket=settings.s3_bucket_name, Key=object_key)["Body"]
        with body:
            data = body.read(max_bytes + 1)
    except (BotoCoreError, ClientError) as error:
        raise StorageError(f"원본을 읽지 못했습니다: {object_key}") from error

    if len(data) > max_bytes:
        raise StorageError(f"원본이 상한({max_bytes}바이트)을 넘습니다: {object_key}")
    if not data:
        raise StorageError(f"원본이 비어 있습니다: {object_key}")
    return data


def build_object_key(prefix: str, extension: str) -> str:
    """`uploads.py` 와 같은 모양으로 키를 만든다 — `<접두사>/<연/월>/<uuid>.<확장자>`."""
    now = datetime.now(KST)
    return f"{prefix}/{now:%Y/%m}/{uuid.uuid4()}.{extension}"


def upload(data: bytes, *, object_key: str, content_type: str) -> str:
    """객체를 올리고 공개 주소를 돌려준다.

    `immutable` 캐시를 붙이는 근거는 키에 uuid 가 들어가 **같은 키의 내용이 절대
    바뀌지 않는다**는 것이다. 재생성은 새 키로 올라간다.
    """
    try:
        _client().put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
    except (BotoCoreError, ClientError) as error:
        raise StorageError(f"결과물을 올리지 못했습니다: {object_key}") from error

    return f"{settings.s3_public_base_url.rstrip('/')}/{object_key}"
