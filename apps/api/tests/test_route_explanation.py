"""여행 설명 LLM 모듈 (route_explanation).

OpenAI 를 대역으로 바꿔 "실패는 항상 None(호출부가 템플릿 폴백)" 계약을 고정한다.
실제 네트워크 호출은 하지 않는다.
"""

from types import SimpleNamespace

import pytest
from openai import APITimeoutError

from app.integrations.llm import route_explanation as rex
from app.integrations.llm.route_explanation import (
    TripExplanationInput,
    generate_trip_explanation,
)

SUMMARY = TripExplanationInput(
    day_count=2,
    place_count=5,
    unfilled_count=1,
    pace_label="여유로운",
    transport_label="렌터카",
    pet_notes=("1마리 동반", "차멀미 배려 동선"),
    weather_note=None,
)


def _completion(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class _FakeClient:
    """result 가 예외면 create 에서 던지고, 아니면 그대로 돌려준다."""

    def __init__(self, result: object) -> None:
        completions = SimpleNamespace(create=lambda **_kwargs: self._yield(result))
        self.chat = SimpleNamespace(completions=completions)

    @staticmethod
    def _yield(result: object) -> object:
        if isinstance(result, Exception):
            raise result
        return result


def _use_client(monkeypatch: pytest.MonkeyPatch, result: object) -> None:
    monkeypatch.setattr(rex.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(rex, "OpenAI", lambda **_kwargs: _FakeClient(result))


def test_정상_응답은_공백을_다듬어_반환한다(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_client(monkeypatch, _completion("  몽이랑 여유로운 제주 여행입니다.  "))
    assert generate_trip_explanation(SUMMARY) == "몽이랑 여유로운 제주 여행입니다."


def test_타임아웃은_None(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_client(monkeypatch, APITimeoutError(request=SimpleNamespace()))
    assert generate_trip_explanation(SUMMARY) is None


def test_일반_예외는_None(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_client(monkeypatch, RuntimeError("네트워크 불가"))
    assert generate_trip_explanation(SUMMARY) is None


@pytest.mark.parametrize("content", ["", "   ", None])
def test_빈_내용은_None(monkeypatch: pytest.MonkeyPatch, content: str | None) -> None:
    _use_client(monkeypatch, _completion(content))
    assert generate_trip_explanation(SUMMARY) is None


def test_빈_choices는_None(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_client(monkeypatch, SimpleNamespace(choices=[]))
    assert generate_trip_explanation(SUMMARY) is None


def test_키_미설정이면_클라이언트를_만들지_않고_None(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(rex.settings, "openai_api_key", "")

    def _boom(**_kwargs: object) -> object:
        raise AssertionError("키가 없으면 OpenAI 클라이언트를 만들면 안 된다")

    monkeypatch.setattr(rex, "OpenAI", _boom)
    assert generate_trip_explanation(SUMMARY) is None


def test_프롬프트는_요약_필드만_쓰고_request_text_자리가_없다() -> None:
    # request_text 원문이 설명으로 새지 않도록 입력 스키마에 자리 자체가 없어야 한다.
    assert "request_text" not in TripExplanationInput.__dataclass_fields__
    prompt = rex._user_prompt(SUMMARY)
    assert "여유로운" in prompt
    assert "렌터카" in prompt
    assert "차멀미 배려 동선" in prompt
    assert "5곳" in prompt
