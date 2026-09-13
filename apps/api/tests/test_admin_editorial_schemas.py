import pytest
from pydantic import ValidationError

from app.schemas.admin_editorial import AdminEditorialStoryUpdate


def test_admin_update_rejects_explicit_null_for_required_field() -> None:
    with pytest.raises(ValidationError, match="필수 필드는 null"):
        AdminEditorialStoryUpdate.model_validate({"cardTitle": None})


def test_admin_update_rejects_unsafe_image_scheme() -> None:
    with pytest.raises(ValidationError, match=r"http\(s\) 절대 URL"):
        AdminEditorialStoryUpdate.model_validate({"heroImageUrl": "javascript:alert(1)"})


def test_admin_update_accepts_nullable_schedule_fields() -> None:
    payload = AdminEditorialStoryUpdate.model_validate(
        {"publishedAt": None, "expiresAt": None}
    )

    assert payload.model_dump(exclude_unset=True) == {
        "published_at": None,
        "expires_at": None,
    }
