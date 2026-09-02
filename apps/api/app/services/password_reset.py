"""비밀번호 재설정 — 코드 발급·검증 (docs/api/auth.md 비밀번호 재설정 절).

엔드포인트는 요청을 받고 응답을 만들 뿐이고, "누구에게 코드를 줄지"와
"이 코드가 맞는지"의 판단은 전부 여기 모여 있다.

## 이 파일이 막고 있는 것들

| 구멍 | 대응 |
| --- | --- |
| 가입 여부가 응답으로 새는 것 | 판단을 여기서 하고 **엔드포인트에는 결과를 알려주지 않는다** |
| 무차별 대입(6자리=100만) | `attempt_count` 상한. 넘으면 코드 폐기 |
| 메일함 폭탄 | 1시간 발급 수 상한 |
| 소셜 계정에 없던 비밀번호가 생기는 것 | `local` 이 아니면 발급하지 않고 안내 메일만 |
| 코드 재사용 | `used_at` + 새 코드 발급 시 이전 것 일괄 폐기 |
| 동시 요청으로 한 코드가 두 번 통과 | 검증 시 행 잠금(`with_for_update`) |
"""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from enum import Enum

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.models import PasswordResetCode, User
from app.db.models.enums import AuthProvider
from app.services.email import send_email

logger = logging.getLogger(__name__)

#: 코드 자릿수. 바꾸려면 앱 입력 칸(maxLength)도 같이 바꿔야 한다.
CODE_DIGITS = 6


class ConfirmResult(Enum):
    """`confirm_reset` 의 결과. 엔드포인트가 이 값만 보고 응답을 고른다."""

    OK = "ok"
    #: 코드가 없거나·만료됐거나·이미 썼거나·틀렸다. **넷을 구분하지 않는다** —
    #: 어느 쪽인지 알려주면 유효한 코드를 찾는 데 힌트가 된다.
    INVALID = "invalid"
    #: 시도 횟수를 넘겨 코드가 죽었다. 이건 알려줘야 사용자가 재발급을 누른다.
    TOO_MANY_ATTEMPTS = "too_many_attempts"


def _generate_code() -> str:
    """`secrets` 로 6자리를 만든다(`random` 은 예측 가능해 인증에 쓰면 안 된다)."""
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def _find_local_user(db: Session, email: str, *, lock: bool = False) -> User | None:
    """이 이메일로 비밀번호를 바꿀 수 있는 살아 있는 계정. 없으면 None.

    `lock=True` 는 사용자 행을 트랜잭션이 끝날 때까지 잠근다(발급 경로 전용).
    시간당 상한이 "세고 → 넣는" 두 단계라, 잠그지 않으면 동시에 들어온 요청들이
    **모두 같은 숫자를 읽고 모두 통과한다** — 상한을 100 번 요청으로 우회할 수
    있어 메일 폭탄을 막지 못한다. 잠금은 삽입 직후 커밋까지 몇 밀리초만 잡는다.
    """
    statement = select(User).where(User.email == email, User.deleted_at.is_(None))
    if lock:
        statement = statement.with_for_update()
    return db.scalar(statement)


def _recent_request_count(db: Session, user: User) -> int:
    since = datetime.now(UTC) - timedelta(hours=1)
    return (
        db.scalar(
            select(func.count(PasswordResetCode.id)).where(
                PasswordResetCode.user_id == user.id,
                PasswordResetCode.created_at >= since,
            )
        )
        or 0
    )


def _expire_outstanding(db: Session, user: User, now: datetime) -> None:
    """이 사용자의 아직 안 쓴 코드를 전부 폐기한다.

    코드를 새로 받으면 이전 것은 죽어야 한다. 안 그러면 한 시간 상한만큼(5개)
    동시에 살아 있어서 맞춰볼 수 있는 조합이 그만큼 늘어난다.
    """
    db.execute(
        update(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id, PasswordResetCode.used_at.is_(None))
        .values(used_at=now)
    )


def request_reset(db: Session, email: str) -> None:
    """재설정 코드를 발급하고 메일을 보낸다.

    **아무것도 돌려주지 않는다.** 가입 여부·소셜 여부·상한 초과가 응답에 드러나면
    남의 가입 여부를 알아내는 통로가 되기 때문이다. 엔드포인트는 결과와 무관하게
    같은 응답을 준다.
    """
    user = _find_local_user(db, email, lock=True)
    if user is None:
        logger.info("비밀번호 재설정 요청 — 해당 계정 없음(응답은 동일)")
        return

    # 소셜 계정에는 코드를 주지 않는다. 비밀번호를 만들어 주면 **원래 없던
    # 로그인 경로가 새로 생기는** 것이라, 메일함만 뚫려도 계정이 넘어간다.
    # 대신 진짜 주인에게 도움이 되도록 안내 메일은 보낸다.
    if user.auth_provider != AuthProvider.LOCAL or user.password_hash is None:
        send_email(email, *_social_guide_mail(user.auth_provider))
        return

    if _recent_request_count(db, user) >= settings.password_reset_hourly_limit:
        # 상한을 넘겨도 사용자에게는 티 내지 않는다(위 주석과 같은 이유).
        logger.warning("비밀번호 재설정 요청 시간당 상한 초과 — user_id=%s", user.id)
        return

    now = datetime.now(UTC)
    code = _generate_code()
    _expire_outstanding(db, user, now)
    db.add(
        PasswordResetCode(
            user_id=user.id,
            code_hash=hash_password(code),
            expires_at=now + timedelta(minutes=settings.password_reset_code_ttl_minutes),
        )
    )
    db.commit()
    send_email(email, *_code_mail(code))


def confirm_reset(db: Session, email: str, code: str, new_password: str) -> ConfirmResult:
    """코드를 확인하고 맞으면 비밀번호를 바꾼다."""
    user = _find_local_user(db, email)
    if user is None or user.auth_provider != AuthProvider.LOCAL:
        return ConfirmResult.INVALID

    now = datetime.now(UTC)
    # 살아 있는 코드는 설계상 최대 하나지만, 동시에 두 요청이 같은 행을 집으면
    # 둘 다 통과할 수 있다. 행을 잠가 한 번에 하나만 검사하게 한다.
    entry = db.scalar(
        select(PasswordResetCode)
        .where(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.used_at.is_(None),
            PasswordResetCode.expires_at > now,
        )
        .order_by(PasswordResetCode.created_at.desc())
        .with_for_update()
    )
    if entry is None:
        return ConfirmResult.INVALID

    if entry.attempt_count >= settings.password_reset_max_attempts:
        entry.used_at = now
        db.commit()
        return ConfirmResult.TOO_MANY_ATTEMPTS

    # **먼저 세고 커밋한다.** 틀렸을 때 예외로 빠져나가면 증가분까지 롤백돼서
    # 시도 횟수 제한이 통째로 무력해진다 — 그러면 6자리는 그냥 뚫린다.
    entry.attempt_count += 1
    db.commit()

    if not verify_password(code, entry.code_hash):
        return ConfirmResult.INVALID

    # 위 커밋에서 행 잠금이 풀렸으므로 그 사이 다른 요청이 같은 코드를 썼을 수
    # 있다. `used_at IS NULL` 을 조건에 걸어 **바꾼 행이 있을 때만** 통과시킨다
    # (읽고 나서 쓰면 둘 다 성공한다).
    consumed = db.execute(
        update(PasswordResetCode)
        .where(PasswordResetCode.id == entry.id, PasswordResetCode.used_at.is_(None))
        .values(used_at=now)
    )
    if consumed.rowcount == 0:
        return ConfirmResult.INVALID

    user.password_hash = hash_password(new_password)
    # 이 시각 이전에 발급된 토큰을 전부 무효로 만든다 — 계정을 털린 사람이
    # 비밀번호를 바꿔도 공격자가 refresh token 으로 14일 더 버티는 것을 막는다.
    user.password_changed_at = now
    db.commit()
    return ConfirmResult.OK


# ---------------------------------------------------------------------------
# 메일 문구 — 본문에 링크를 넣지 않는다(피싱 훈련이 되지 않도록 코드만 읽게 한다)
# ---------------------------------------------------------------------------


def _code_mail(code: str) -> tuple[str, str]:
    minutes = settings.password_reset_code_ttl_minutes
    return (
        "[오멍가멍] 비밀번호 재설정 인증번호",
        f"인증번호는 {code} 입니다.\n"
        f"{minutes}분 안에 앱에 입력해 주세요.\n\n"
        "본인이 요청한 것이 아니라면 이 메일을 무시하셔도 됩니다. "
        "비밀번호는 바뀌지 않습니다.",
    )


def _social_guide_mail(provider: AuthProvider) -> tuple[str, str]:
    label = {AuthProvider.KAKAO: "카카오", AuthProvider.GOOGLE: "구글"}.get(provider, "소셜 계정")
    return (
        "[오멍가멍] 로그인 방법 안내",
        f"이 이메일은 {label} 계정으로 가입되어 있어 비밀번호가 없습니다.\n"
        f"로그인 화면에서 {label}(으)로 로그인해 주세요.\n\n"
        "본인이 요청한 것이 아니라면 이 메일을 무시하셔도 됩니다.",
    )
