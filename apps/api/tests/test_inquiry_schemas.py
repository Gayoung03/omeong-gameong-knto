"""문의 스키마 검증 (순수 Pydantic, DB 불필요)."""

import pytest
from pydantic import ValidationError

from app.schemas.admin_inquiry import AdminInquiryAnswerRequest
from app.schemas.inquiry import InquiryCreate, InquiryDetail


def _body(**overrides: object) -> dict:
    body = {"category": "pet", "title": "제목", "content": "내용"}
    body.update(overrides)
    return body


def test_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        InquiryCreate.model_validate(_body(category="계정"))


def test_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        InquiryCreate.model_validate(_body(title=""))


def test_rejects_too_long_title() -> None:
    with pytest.raises(ValidationError):
        InquiryCreate.model_validate(_body(title="가" * 201))


def test_rejects_more_than_five_images() -> None:
    with pytest.raises(ValidationError):
        InquiryCreate.model_validate(
            _body(imageUrls=[f"https://cdn.example.com/{i}.webp" for i in range(6)])
        )


def test_accepts_minimal_body() -> None:
    parsed = InquiryCreate.model_validate(_body())
    assert parsed.category == "pet"
    assert parsed.image_urls == []


def test_answer_request_rejects_blank() -> None:
    with pytest.raises(ValidationError):
        AdminInquiryAnswerRequest.model_validate({"answer": "   "})


def test_answer_request_strips() -> None:
    parsed = AdminInquiryAnswerRequest.model_validate({"answer": "  처리했어요.  "})
    assert parsed.answer == "처리했어요."


def test_detail_coerces_null_image_urls_to_list() -> None:
    parsed = InquiryDetail.model_validate(
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "category": "pet",
            "status": "pending",
            "title": "제목",
            "content": "내용",
            "image_urls": None,
            "answer": None,
            "created_at": "2026-09-01T10:00:00+09:00",
            "updated_at": "2026-09-01T10:00:00+09:00",
            "answered_at": None,
        }
    )
    assert parsed.image_urls == []
