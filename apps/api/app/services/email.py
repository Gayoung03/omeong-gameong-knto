"""메일 발송 — 지금은 **로그로만 출력하는 스텁**이다.

## 왜 스텁인가

발신 도메인·SMTP 계정이 아직 없다(PR1 범위). 그런데 비밀번호 재설정 로직은
그것 없이도 전부 만들고 검증할 수 있어서, 발송 지점만 이 함수 하나로 좁혀 두고
본문을 로그 출력으로 채운다. 실제 전송이 준비되면 **`_deliver` 안쪽만** 바꾸면
되고 부르는 쪽은 손대지 않는다.

## 로그에 본문을 찍는 기준

`environment == "local"` 일 때만 제목·본문을 통째로 남긴다. 개발 중에는 메일함
대신 터미널에서 인증 코드를 봐야 하기 때문이다. **그 외 환경에서는 수신자와
제목만 남긴다** — 배포 로그에 인증 코드가 남으면 로그를 볼 수 있는 사람이
남의 계정 비밀번호를 바꿀 수 있다.

## 레벨이 왜 WARNING 인가

이 프로젝트는 로깅을 따로 설정하지 않아 uvicorn 기본값(root=WARNING)으로 돈다.
`logger.info` 로 적으면 **터미널에 아무것도 찍히지 않아** 개발 중에 인증 코드를
볼 방법이 없다. 그리고 어느 환경이든 "메일이 실제로 나가지 않았다"는 사실 자체가
경고할 일이라, 레벨과 의미가 어긋나지도 않는다. 실제 발송이 붙으면 성공 로그는
`info` 로 내려도 된다.
"""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailNotConfigured(RuntimeError):
    """실제 발송 수단이 아직 없다(스텁 단계)."""


def _deliver(to: str, subject: str, body: str) -> None:
    """실제 전송 지점. PR1 에서 SMTP 로 교체한다."""
    if settings.environment == "local":
        logger.warning(
            "[메일 스텁] to=%s subject=%s\n--- 본문 ---\n%s\n------------", to, subject, body
        )
        return
    # 배포 환경에서 여기 오면 메일이 실제로 나가지 않는다. 조용히 넘어가면
    # "보냈다고 하는데 안 온다" 로 한참 헤매므로 경고로 남긴다(본문은 남기지 않는다).
    logger.warning("[메일 미설정] 발송 수단이 없어 건너뜀 — to=%s subject=%s", to, subject)


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
