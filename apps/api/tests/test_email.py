"""메일 발송(SMTP) — 실제 서버 없이 확인할 수 있는 부분.

여기서 막는 사고는 전부 "설정은 맞는데 메일이 안 간다"류다. 원인이 화면 어디에도
안 보여서 사람이 몇 시간을 태우는 종류라, 코드로 고정해 둔다.
"""

import logging
import smtplib
from email import message_from_string
from email.header import decode_header, make_header

import pytest

from app.core.config import settings
from app.services import email as email_module


class FakeSMTP:
    """smtplib 대역. 보낸 내용과 로그인 인자를 그대로 붙잡아 둔다."""

    instances: list["FakeSMTP"] = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.context = context
        self.login_args: tuple[str, str] | None = None
        self.messages: list = []
        self.started_tls = False
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def starttls(self, context=None):
        self.started_tls = True

    def login(self, username, password):
        self.login_args = (username, password)

    def send_message(self, message):
        self.messages.append(message)


@pytest.fixture
def smtp(monkeypatch):
    """SMTP 설정을 채우고 smtplib 를 대역으로 바꾼다."""
    FakeSMTP.instances = []
    monkeypatch.setattr(settings, "smtp_host", "smtp.naver.com")
    monkeypatch.setattr(settings, "smtp_port", 465)
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    monkeypatch.setattr(settings, "smtp_username", "someone@naver.com")
    monkeypatch.setattr(settings, "smtp_password", "app-password")
    monkeypatch.setattr(settings, "smtp_from_email", "")
    monkeypatch.setattr(settings, "smtp_from_name", "오멍가멍")
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTP)
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def test_설정이_비어있으면_SMTP에_접속하지_않는다(monkeypatch) -> None:
    """팀원 로컬·CI 에는 메일 계정이 없다. 거기서 접속을 시도하면 요청이 느려진다."""
    monkeypatch.setattr(settings, "smtp_host", "")
    monkeypatch.setattr(settings, "smtp_username", "")
    monkeypatch.setattr(settings, "smtp_password", "")

    def 접속하면_실패(*args, **kwargs):
        raise AssertionError("설정이 없는데 SMTP 에 접속했다")

    monkeypatch.setattr(smtplib, "SMTP_SSL", 접속하면_실패)
    monkeypatch.setattr(smtplib, "SMTP", 접속하면_실패)

    email_module.send_email("someone@example.com", "제목", "본문")


def test_설정이_있으면_실제로_보낸다(smtp) -> None:
    email_module.send_email("받는사람@example.com", "인증번호", "123456")

    (client,) = smtp.instances
    assert client.host == "smtp.naver.com"
    assert client.port == 465
    (sent,) = client.messages
    assert sent["To"] == "받는사람@example.com"
    assert "123456" in sent.get_content()


def test_타임아웃_없이_접속하지_않는다(smtp) -> None:
    """기본값은 무제한이다. 메일 서버가 응답하지 않으면 백그라운드 스레드가 잡힌 채로 남는다."""
    email_module.send_email("someone@example.com", "제목", "본문")

    (client,) = smtp.instances
    assert client.timeout == settings.smtp_timeout_seconds
    assert client.timeout > 0


def test_앱_비밀번호의_공백은_제거된다(smtp, monkeypatch) -> None:
    """Gmail 은 앱 비밀번호를 네 글자씩 띄워 보여준다. 보이는 대로 붙여넣어도 되어야 한다."""
    monkeypatch.setattr(settings, "smtp_password", "abcd efgh ijkl mnop")

    email_module.send_email("someone@example.com", "제목", "본문")

    (client,) = smtp.instances
    assert client.login_args == ("someone@naver.com", "abcdefghijklmnop")


def test_발신자_이름이_한글이어도_깨지지_않는다(smtp) -> None:
    email_module.send_email("someone@example.com", "제목", "본문")

    (client,) = smtp.instances
    (sent,) = client.messages
    # 헤더는 ASCII(RFC 2047)로 인코딩돼 나간다. 읽는 쪽에서 되돌렸을 때
    # 원래 이름이어야 메일함에 "오멍가멍" 으로 보인다.
    parsed = message_from_string(sent.as_string())
    보이는_발신자 = str(make_header(decode_header(parsed["From"])))
    assert "오멍가멍" in 보이는_발신자
    assert "someone@naver.com" in 보이는_발신자


def test_From_주소를_따로_지정하면_그것을_쓴다(smtp, monkeypatch) -> None:
    monkeypatch.setattr(settings, "smtp_from_email", "noreply@omeong.example")

    email_module.send_email("someone@example.com", "제목", "본문")

    (client,) = smtp.instances
    (sent,) = client.messages
    assert "noreply@omeong.example" in str(sent["From"])
    # 로그인은 여전히 계정 아이디로 한다.
    assert client.login_args[0] == "someone@naver.com"


def test_제목에_개행이_섞여도_헤더가_쪼개지지_않는다(smtp) -> None:
    """헤더는 줄 단위라, 개행을 그대로 흘리면 뒤에 임의의 헤더를 붙일 수 있다."""
    email_module.send_email("someone@example.com", "제목\r\nBcc: 남의주소@example.com", "본문")

    (client,) = smtp.instances
    (sent,) = client.messages
    assert sent["Bcc"] is None
    assert "\n" not in str(sent["Subject"])


def test_587_이면_STARTTLS_로_올린다(smtp, monkeypatch) -> None:
    """465 는 접속부터 SSL, 587 은 접속 후 암호화로 올린다. 섞이면 인증 전에 끊긴다."""
    monkeypatch.setattr(settings, "smtp_use_ssl", False)
    monkeypatch.setattr(settings, "smtp_port", 587)

    email_module.send_email("someone@example.com", "제목", "본문")

    (client,) = smtp.instances
    assert client.started_tls is True


def test_실제_발송이_켜지면_로컬이어도_로그에_코드가_남지_않는다(
    smtp, monkeypatch, caplog
) -> None:
    """스텁일 때만 터미널에 코드를 찍는다. 진짜 메일이 나가는데 로그에도 남을 이유가 없다."""
    monkeypatch.setattr(settings, "environment", "local")

    with caplog.at_level(logging.DEBUG, logger=email_module.__name__):
        email_module.send_email("someone@example.com", "인증번호", "인증번호는 123456 입니다")

    assert "123456" not in caplog.text


def test_인증_실패는_예외로_새어나가지_않는다(smtp, monkeypatch) -> None:
    """앱 비밀번호가 틀려도 응답이 달라지면 안 된다 — 가입 여부를 알아내는 단서가 된다."""

    def 인증_실패(self, username, password):
        raise smtplib.SMTPAuthenticationError(535, b"auth failed")

    monkeypatch.setattr(FakeSMTP, "login", 인증_실패)

    email_module.send_email("someone@example.com", "제목", "본문")  # 예외 없음
