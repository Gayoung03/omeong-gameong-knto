"""메일 발송 — SMTP 로 실제 보내고, 설정이 없으면 로그로만 남긴다.

## 두 가지 모드

`SMTP_HOST`·`SMTP_USERNAME`·`SMTP_PASSWORD` 가 **모두** 채워져 있으면 실제로
보낸다. 하나라도 비어 있으면 예전처럼 로그 스텁으로 돈다.

설정이 없다고 기동을 막지 않는 이유가 있다. 팀원 로컬과 CI 에는 메일 계정을
나눠 주지 않는다(계정 하나를 여러 사람이 공유하면 앱 비밀번호가 그만큼 퍼진다).
막아버리면 메일과 아무 상관 없는 작업을 하는 사람의 서버가 안 뜬다.

## 로그에 본문을 찍는 기준

발송 수단이 **없고** `environment == "local"` 일 때만 제목·본문을 통째로 남긴다.
메일이 안 나가는 상태에서 개발하려면 터미널에서 인증 코드를 봐야 하기 때문이다.
**그 외에는 수신자와 제목만 남긴다** — 실제로 메일이 나가는 상황에서까지 코드를
로그에 남기면, 로그를 볼 수 있는 사람이 남의 계정 비밀번호를 바꿀 수 있다.

## 레벨이 왜 WARNING 인가

이 프로젝트는 로깅을 따로 설정하지 않아 uvicorn 기본값(root=WARNING)으로 돈다.
`logger.info` 로 적으면 터미널에 아무것도 찍히지 않아 스텁 모드에서 인증 코드를
볼 방법이 없다. 그리고 "메일이 실제로 나가지 않았다"는 사실 자체가 경고할 일이라
레벨과 의미가 어긋나지도 않는다. 실제 발송 성공은 `info` 로 남긴다.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    """실제로 보낼 수 있는 상태인가."""
    return bool(settings.smtp_host and settings.smtp_username and _password())


def _password() -> str:
    """앱 비밀번호에서 공백을 모두 걷어낸다.

    Gmail 은 앱 비밀번호를 `abcd efgh ijkl mnop` 처럼 네 글자씩 띄워서 보여주고,
    사람들은 보이는 대로 복사해 붙인다. 공백이 섞인 채로 로그인하면 인증 실패만
    나고 원인은 화면 어디에도 안 보인다. 앱 비밀번호에 공백이 들어가는 경우는
    없으니 전부 제거하는 편이 안전하다.
    """
    return "".join(settings.smtp_password.split())


def _sender() -> str:
    """From 주소. 대부분의 메일 서버는 로그인 계정과 다른 주소를 거절한다."""
    return settings.smtp_from_email or settings.smtp_username


def _one_line(value: str) -> str:
    """헤더에 들어갈 값에서 개행을 없앤다.

    메일 헤더는 줄 단위라, 값에 개행이 섞이면 그 뒤를 새 헤더로 읽는다. 수신자
    주소는 `EmailStr` 를 통과해 오지만, 발신자 이름·제목까지 설정과 코드에서
    오므로 들어가는 길목에서 한 번 더 막는다.
    """
    return value.replace("\r", " ").replace("\n", " ").strip()


def _build_message(to: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    # formataddr 이 한글 발신자 이름을 RFC 2047 로 인코딩한다. 직접 문자열을
    # 조립하면 메일함에 이름이 깨져 보인다.
    message["From"] = formataddr((_one_line(settings.smtp_from_name), _one_line(_sender())))
    message["To"] = _one_line(to)
    message["Subject"] = _one_line(subject)
    message.set_content(body)
    return message


def _send_smtp(message: EmailMessage) -> None:
    """SMTP 로 한 통 보낸다. 연결은 매번 새로 연다(발송량이 적다).

    타임아웃을 반드시 넘긴다 — 기본값은 무제한이라, 메일 서버가 응답하지 않으면
    백그라운드 스레드가 영영 잡혀 있게 된다.
    """
    context = ssl.create_default_context()
    timeout = settings.smtp_timeout_seconds

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=timeout, context=context
        ) as client:
            client.login(settings.smtp_username, _password())
            client.send_message(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=timeout) as client:
        client.starttls(context=context)
        client.login(settings.smtp_username, _password())
        client.send_message(message)


def _deliver(to: str, subject: str, body: str) -> None:
    """실제 전송 지점. 설정이 없으면 로그로 대신한다."""
    if not _is_configured():
        if settings.environment == "local":
            logger.warning(
                "[메일 스텁] to=%s subject=%s\n--- 본문 ---\n%s\n------------", to, subject, body
            )
            return
        # 배포 환경에서 여기 오면 메일이 실제로 나가지 않는다. 조용히 넘어가면
        # "보냈다고 하는데 안 온다" 로 한참 헤매므로 경고로 남긴다(본문은 남기지 않는다).
        logger.warning("[메일 미설정] 발송 수단이 없어 건너뜀 — to=%s subject=%s", to, subject)
        return

    _send_smtp(_build_message(to, subject, body))
    logger.info("메일 발송 — to=%s subject=%s", to, subject)


def send_email(to: str, subject: str, body: str) -> None:
    """메일 한 통을 보낸다. **예외를 밖으로 던지지 않는다.**

    호출하는 쪽(비밀번호 재설정 등)은 대부분 백그라운드 작업이라 여기서 터지면
    사용자에게 전달할 방법이 없고, 무엇보다 **메일 발송 성공 여부가 응답에
    드러나면 안 된다**(가입된 이메일인지 알아내는 단서가 된다). 실패는 로그로만
    남기고 삼킨다.
    """
    try:
        _deliver(to, subject, body)
    except Exception:  # noqa: BLE001 - 발송 실패가 호출자를 깨뜨리면 안 된다
        logger.exception("메일 발송 실패 — to=%s subject=%s", to, subject)
