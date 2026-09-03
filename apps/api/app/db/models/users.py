"""User, pet, and default travel preference models."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import (
    AuthProvider,
    ConsentType,
    PetSize,
    PetSpecies,
    TransportType,
    TripPace,
    db_enum,
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("auth_provider", "provider_user_id"),
        # local(이메일) 계정은 password_hash 가 반드시 있어야 한다. 소셜 계정은 NULL 허용.
        # 마이그레이션은 NOT VALID 로 추가하고, 데이터 정리 후 별도 마이그레이션에서 VALIDATE.
        CheckConstraint(
            "auth_provider <> 'local' OR password_hash IS NOT NULL",
            name="local_requires_password",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    auth_provider: Mapped[AuthProvider] = mapped_column(
        db_enum(AuthProvider, "auth_provider"), nullable=False, server_default="local"
    )
    provider_user_id: Mapped[str | None] = mapped_column(String(255))
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    inquiry_answer_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    marketing_notification_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    #: 비밀번호를 마지막으로 바꾼 시각. **이 시각 이전에 발급된 access·refresh
    #: 토큰은 전부 무효**로 본다(app/api/dependencies.py · auth.refresh).
    #: NULL 이면 한 번도 바꾼 적이 없다는 뜻이라 아무 토큰도 무효화하지 않는다.
    #: 계정을 털린 사람이 비밀번호를 바꿔도 refresh token 수명(14일) 동안
    #: 공격자가 로그인 상태를 그대로 유지하는 구멍을 막는다.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserConsent(Base):
    """약관 동의 이력.

    한 행을 고쳐 쓰지 않고 동의·철회가 있을 때마다 새 행을 쌓는다.
    마케팅 동의는 켜고 끌 수 있고 약관은 개정될 수 있어서, 덮어쓰면
    "그 시점에 어떤 버전에 동의했는지"가 사라져 분쟁 시 증빙이 되지 않는다.

    현재 동의 상태는 (user_id, consent_type)별 created_at 이 가장 큰 행이다.
    """

    __tablename__ = "user_consents"
    __table_args__ = (
        Index("ix_user_consents_user_type_created", "user_id", "consent_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    consent_type: Mapped[ConsentType] = mapped_column(
        db_enum(ConsentType, "consent_type"), nullable=False
    )
    #: 동의는 True, 철회는 False.
    is_agreed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    #: 동의한 약관 문서의 버전. 문서가 없는 age_14_or_over 는 비어 있다.
    document_version: Mapped[str | None] = mapped_column(String(50))
    #: 동의하거나 철회한 시각.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Pet(Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint("weight_kg IS NULL OR weight_kg >= 0", name="weight_nonnegative"),
        CheckConstraint(
            "(species = 'other' AND species_detail IS NOT NULL "
            "AND btrim(species_detail) <> '') "
            "OR (species <> 'other' AND species_detail IS NULL)",
            name="species_detail_consistency",
        ),
        Index(
            "uq_pets_user_primary_active",
            "user_id",
            unique=True,
            postgresql_where=text("is_primary = true AND deleted_at IS NULL"),
        ),
        Index("ix_pets_user_active", "user_id", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    species: Mapped[PetSpecies] = mapped_column(db_enum(PetSpecies, "pet_species"), nullable=False)
    species_detail: Mapped[str | None] = mapped_column(String(50))
    breed: Mapped[str | None] = mapped_column(String(100))
    size: Mapped[PetSize | None] = mapped_column(db_enum(PetSize, "pet_size"))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    birth_date: Mapped[date | None] = mapped_column(Date)
    image_url: Mapped[str | None] = mapped_column(Text)
    health_notes: Mapped[str | None] = mapped_column(Text)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserTravelPreference(Base):
    __tablename__ = "user_travel_preferences"
    __table_args__ = (
        CheckConstraint(
            "preferred_duration_days IS NULL OR preferred_duration_days >= 1",
            name="duration_positive",
        ),
        CheckConstraint("companion_count >= 1", name="companion_count_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    default_pace: Mapped[TripPace | None] = mapped_column(db_enum(TripPace, "trip_pace"))
    default_transport: Mapped[TransportType | None] = mapped_column(
        db_enum(TransportType, "transport_type")
    )
    departure_location: Mapped[str | None] = mapped_column(String(100))
    preferred_duration_days: Mapped[int | None] = mapped_column(Integer)
    companion_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    preferred_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserSocialAccount(Base):
    """소셜 로그인 수단 연결 (docs/api/auth.md 소셜 절).

    `users.auth_provider` 컬럼은 하나라 "이메일 계정 + 카카오 연동" 같은 다중 수단을
    표현할 수 없어 이 연결 테이블이 필요하다. `users.auth_provider`·`provider_user_id`
    는 "최초 가입 수단" 기록으로 의미를 고정하고, 로그인 판정은 여기의
    `(provider, provider_user_id)` UNIQUE 로 한다.
    """

    __tablename__ = "user_social_accounts"
    __table_args__ = (
        # local 은 소셜 수단이 아니다 — 이 테이블에 들어오면 안 된다.
        CheckConstraint("provider <> 'local'", name="social_provider_not_local"),
        UniqueConstraint("provider", "provider_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[AuthProvider] = mapped_column(
        db_enum(AuthProvider, "auth_provider"), nullable=False
    )
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PasswordResetCode(Base):
    """비밀번호 재설정 인증 코드 (docs/api/auth.md 비밀번호 재설정 절).

    ## 왜 테이블이 필요한가

    코드를 서버가 기억하지 않으려면 그 흔적을 토큰에 실어 앱에 들려보내야 하는데,
    JWT 페이로드는 **서명일 뿐 암호화가 아니라 누구나 열어볼 수 있다**. 6자리는
    100만 조합뿐이라 토큰을 가로챈 쪽이 오프라인에서 즉시 맞춰볼 수 있다.
    그래서 코드는 서버에만 두고, 앱에는 아무 단서도 주지 않는다.

    ## 컬럼이 각각 막는 것

    - `code_hash` — DB 가 유출돼도 코드가 평문으로 새지 않게 argon2 해시로 둔다.
    - `expires_at` — 메일함이 나중에 털려도 지난 코드는 못 쓰게 한다.
    - `attempt_count` — 무차별 대입 차단. 상한을 넘으면 그 코드는 죽는다.
    - `used_at` — 한 번 쓴 코드의 재사용 차단. 새 코드를 발급할 때 이전 것들도
      여기에 시각을 찍어 함께 폐기한다(살아 있는 코드는 항상 최대 하나).
    """

    __tablename__ = "password_reset_codes"
    __table_args__ = (
        # "이 사용자의 살아 있는 코드"와 "최근 1시간 발급 수"를 둘 다 이 인덱스로 찾는다.
        Index("ix_password_reset_codes_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PasswordResetRequest(Base):
    """비밀번호 재설정 **요청** 발송 기록 (docs/api/auth.md 비밀번호 재설정 절).

    ## 왜 코드 테이블과 따로 있나

    발송 상한("시간당 몇 통")은 코드 발급 여부와 **무관**하게 걸려야 한다. 소셜
    계정은 코드를 발급하지 않고 안내 메일만 나가는데, 코드 행으로만 세면 소셜
    발송은 셀 근거가 없어 상한을 통째로 우회당한다(안내 메일 무제한 = 발신 도메인
    평판 손상). 그래서 "요청이 한 번 있었다 = 메일 한 통 나갔다"를 이 테이블에
    로컬·소셜 공통으로 한 행씩 남기고, 시간당 발송 상한은 이 행 수로 센다.

    코드 자체(해시·시도횟수·만료·사용여부)는 그대로 `password_reset_codes` 가
    관리한다. 이 테이블은 오직 "발송 빈도"만 센다.
    """

    __tablename__ = "password_reset_requests"
    __table_args__ = (
        # "최근 1시간 이 사용자에게 몇 통 나갔나"를 이 인덱스로 센다.
        Index("ix_password_reset_requests_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
