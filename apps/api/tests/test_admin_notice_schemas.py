"""관리자 공지 스키마 검증 (순수 Pydantic)."""

import pytest
from pydantic import ValidationError

from app.schemas.admin_notice import AdminNoticeCreate, AdminNoticeUpdate


def test_create_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        AdminNoticeCreate.model_validate({"title": "   ", "content": "본문"})


def test_update_rejects_explicit_null_required() -> None:
    with pytest.raises(ValidationError, match="null"):
        AdminNoticeUpdate.model_validate({"title": None})
    with pytest.raises(ValidationError, match="null"):
        AdminNoticeUpdate.model_validate({"isActive": None})


def test_update_partial_is_allowed() -> None:
    parsed = AdminNoticeUpdate.model_validate({"isPinned": True})
    assert parsed.model_dump(exclude_unset=True) == {"is_pinned": True}


def test_update_strips_title() -> None:
    parsed = AdminNoticeUpdate.model_validate({"title": "  제목  "})
    assert parsed.title == "제목"
