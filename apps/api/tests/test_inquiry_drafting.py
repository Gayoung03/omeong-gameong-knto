"""문의 답변 초안 생성 서비스."""

import json
import uuid
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.services import inquiry_drafting
from app.services.inquiry_drafting import INQUIRY_SUPPORT_PROMPT, InquiryDraft, draft_answer


class _FakeInquiry:
    def __init__(self, **kw: object) -> None:
        self.id = uuid.uuid4()
        self.category = kw.get("category", "pet")
        self.title = kw.get("title", "반려동물 프로필 사진이 안 바뀌어요")
        self.content = kw.get("content", "프로필 수정 화면에서 저장이 안 됩니다.")
        self.asker = SimpleNamespace(nickname=kw.get("nickname", "율무"))


def _fake_openai_factory(arguments: dict):
    class _FakeCompletions:
        def create(self, **_kw: object) -> object:
            message = SimpleNamespace(
                tool_calls=[
                    SimpleNamespace(
                        function=SimpleNamespace(arguments=json.dumps(arguments))
                    )
                ]
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class _FakeClient:
        def __init__(self, **_kw: object) -> None:
            self.chat = SimpleNamespace(completions=_FakeCompletions())

    return _FakeClient


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "")
    with pytest.raises(RuntimeError):
        draft_answer(db=None, inquiry=_FakeInquiry())  # type: ignore[arg-type]


def test_parses_tool_call_and_truncates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "inquiry_openai_model", "")
    monkeypatch.setattr(settings, "openai_model", "gpt-4o-mini")
    monkeypatch.setattr(inquiry_drafting, "_past_answers", lambda db, inq: [])
    monkeypatch.setattr(inquiry_drafting, "_guides", lambda db, inq: [])
    monkeypatch.setattr(
        inquiry_drafting,
        "OpenAI",
        _fake_openai_factory(
            {
                "reply": "확인해 보겠습니다. " + "가" * 5000,
                # 모델이 배열을 문자열로 감싸도 복구한다.
                "used_context": json.dumps(["프로필 가이드", "과거 답변"]),
                "needs_human_review": True,
            }
        ),
    )

    draft = draft_answer(db=None, inquiry=_FakeInquiry())  # type: ignore[arg-type]

    assert isinstance(draft, InquiryDraft)
    # 본문은 2000자로 잘리고, 인사말·맺음말이 붙는다.
    assert draft.reply.startswith("율무님, 안녕하세요.\n오멍가멍입니다.\n\n")
    assert draft.reply.endswith("\n\n감사합니다.\n오멍가멍 드림")
    assert "가" * 1980 in draft.reply
    assert draft.used_context == ["프로필 가이드", "과거 답변"]
    assert draft.needs_human_review is True
    assert draft.model == "gpt-4o-mini"


def test_empty_reply_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(inquiry_drafting, "_past_answers", lambda db, inq: [])
    monkeypatch.setattr(inquiry_drafting, "_guides", lambda db, inq: [])
    monkeypatch.setattr(
        inquiry_drafting,
        "OpenAI",
        _fake_openai_factory({"reply": "   ", "needs_human_review": False}),
    )

    with pytest.raises(RuntimeError):
        draft_answer(db=None, inquiry=_FakeInquiry())  # type: ignore[arg-type]


def test_keywords_use_category_seeds_and_tokens() -> None:
    keywords = inquiry_drafting._keywords(
        _FakeInquiry(category="pet", title="반려견 프로필 사진 오류", content="저장 실패")
    )
    assert "반려동물" in keywords  # 카테고리 시드
    assert "프로필" in keywords
    assert len(keywords) <= 8


def test_prompt_forbids_fabrication_and_greeting() -> None:
    assert "지어내지 않는다" in INQUIRY_SUPPORT_PROMPT
    assert "해요체" in INQUIRY_SUPPORT_PROMPT
    # 인사말·맺음말은 시스템이 붙이므로 모델이 쓰면 안 된다.
    assert "본문만" in INQUIRY_SUPPORT_PROMPT


def test_answer_template_has_greeting_body_gap_and_footer() -> None:
    from app.services.inquiries import answer_header, answer_template

    template = answer_template("율무")
    assert template.startswith("율무님, 안녕하세요.\n오멍가멍입니다.\n\n")
    assert template.endswith("\n\n감사합니다.\n오멍가멍 드림")
    # 닉네임이 비면 "고객" 으로 대체한다.
    assert answer_header("  ") == "고객님, 안녕하세요.\n오멍가멍입니다."
