"""공통 이미지 업로드 API."""

import uuid
from datetime import datetime
from functools import lru_cache
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.api.dependencies import CurrentUser
from app.core.config import settings
from app.schemas.upload import UploadResponse

router = APIRouter(prefix="/uploads")

MAX_FILE_SIZE = 10 * 1024 * 1024
KST = ZoneInfo("Asia/Seoul")
UploadPurpose = Literal["review", "travel_log", "inquiry", "profile", "pet", "place"]


def _detect_image(data: bytes) -> tuple[str, str] | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", "png"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


@lru_cache
def _get_s3_client() -> Any:
    return boto3.client("s3", region_name=settings.aws_region)


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_image(
    file: Annotated[UploadFile, File()],
    purpose: Annotated[UploadPurpose, Form()],
    current_user: CurrentUser,
) -> UploadResponse:
    """이미지 한 장을 S3에 저장하고 CloudFront 주소를 반환한다."""
    del current_user  # 인증은 필요하지만 소유자 정보는 객체 경로에 노출하지 않는다.

    if not settings.s3_bucket_name or not settings.s3_public_base_url:
        raise HTTPException(status_code=500, detail="이미지 저장소가 설정되지 않았습니다")

    data = file.file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="이미지는 10MB 이하만 업로드할 수 있습니다")

    detected = _detect_image(data)
    if detected is None:
        raise HTTPException(status_code=415, detail="JPEG, PNG, WebP 이미지만 업로드할 수 있습니다")
    content_type, extension = detected

    now = datetime.now(KST)
    prefix = purpose.replace("_", "-")
    object_key = f"{prefix}/{now:%Y/%m}/{uuid.uuid4()}.{extension}"

    try:
        _get_s3_client().put_object(
            Bucket=settings.s3_bucket_name,
            Key=object_key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )
    except (BotoCoreError, ClientError) as error:
        raise HTTPException(status_code=500, detail="이미지를 저장하지 못했습니다") from error

    return UploadResponse(
        file_url=f"{settings.s3_public_base_url.rstrip('/')}/{object_key}",
        content_type=content_type,
        size_bytes=len(data),
    )
