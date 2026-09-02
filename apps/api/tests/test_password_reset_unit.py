"""비밀번호 재설정 중 DB 없이 확인할 수 있는 부분 (CI 에는 DB 가 없다)."""

import logging

from app.core.config import settings
from app.services import email as email_module
from app.services.password_reset import CODE_DIGITS, _code_mail, _generate_code


def test_코드는_항상_여섯자리다() -> None:
    # 0 으로 시작하는 코드가 5자리로 줄어들면 앱 입력 칸과 어긋난다.
    for _ in range(200):
        code = _generate_code()
        assert len(code) == CODE_DIGITS
        assert code.isdigit()


def test_코드는_매번_같지_않다() -> None:
    # 예측 가능한 코드는 인증이 아니다.
    assert len({_generate_code() for _ in range(50)}) > 1


def test_코드_메일에_코드와_유효시간이_들어간다() -> None:
    subject, body = _code_mail("123456")
    assert "123456" in body
    assert str(settings.password_reset_code_ttl_minutes) in body
    assert "오멍가멍" in subject


def test_배포환경_로그에는_코드가_남지_않는다(monkeypatch, caplog) -> None:
    """서버 로그를 볼 수 있는 사람이 남의 계정 비밀번호를 바꿀 수 있으면 안 된다."""
    monkeypatch.setattr(settings, "environment", "production")
    with caplog.at_level(logging.DEBUG, logger=email_module.__name__):
        email_module.send_email("someone@test.local", "제목", "인증번호는 123456 입니다")

    assert "123456" not in caplog.text


def test_로컬_로그에는_코드가_보인다(monkeypatch, caplog) -> None:
    """개발 중에는 메일함 대신 터미널에서 코드를 봐야 한다."""
    monkeypatch.setattr(settings, "environment", "local")
    # WARNING 으로 남긴다 — 이 프로젝트는 로깅을 설정하지 않아 uvicorn 기본값
    # (root=WARNING)으로 돌고, info 로 적으면 터미널에 아무것도 찍히지 않는다.
    with caplog.at_level(logging.WARNING, logger=email_module.__name__):
        email_module.send_email("someone@test.local", "제목", "인증번호는 123456 입니다")

    assert "123456" in caplog.text


def test_발송이_실패해도_예외가_새어나가지_않는다(monkeypatch) -> None:
    """발송 실패가 응답에 드러나면 가입 여부를 알아내는 단서가 된다."""

    def 터짐(*args, **kwargs):
        raise RuntimeError("메일 서버 다운")

    monkeypatch.setattr(email_module, "_deliver", 터짐)
    email_module.send_email("someone@test.local", "제목", "본문")  # 예외 없음
