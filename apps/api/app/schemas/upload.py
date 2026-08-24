"""이미지 업로드 API 스키마."""

from app.schemas.base import APISchema


class UploadResponse(APISchema):
    file_url: str
    content_type: str
    size_bytes: int
