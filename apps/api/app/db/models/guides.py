"""여행 가이드 콘텐츠 모델.

두 종류로 나뉜다.

- ``GuideDocument`` / ``GuideDocumentSource`` — 사람이 **읽는** 글과 그 근거
- ``TransportPetRule`` / ``TransportRestrictedBreed`` — 챗봇이 **질의하는** 값

마크다운 본문만으로는 "우리 애 12kg인데 어디 타요?" 에 답할 수 없어서 나눴다.
자세한 배경은 ``docs/planning/travel-guide-collection.md`` 참고.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import (
    BreedRestrictionScope,
    BreedRestrictionType,
    CarrierType,
    GuideCategory,
    db_enum,
)


class GuideDocument(Base):
    """가이드 글 한 편. 본문은 마크다운."""

    __tablename__ = "guide_documents"
    __table_args__ = (
        Index("ix_guide_documents_category", "category"),
        Index("ix_guide_documents_is_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[GuideCategory] = mapped_column(
        db_enum(GuideCategory, "guide_category"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class GuideDocumentSource(Base):
    """가이드 글의 근거 출처.

    항공사는 안내 페이지 하나면 되지만 행정 자료는 여러 건을 겹쳐야 근거가 선다.
    (제주도 반입 규정 문서는 출처가 3건이다.)
    """

    __tablename__ = "guide_document_sources"
    __table_args__ = (Index("ix_guide_document_sources_guide_document_id", "guide_document_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guide_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guide_documents.id", ondelete="CASCADE"), nullable=False
    )
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    source_note: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    display_order: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )


class TransportPetRule(Base):
    """항공사·선사별 반려동물 규정의 구조화된 값.

    ⚠️ boolean은 전부 nullable이다. 원문이 「불가」라고 밝힌 것과
    아무 언급이 없는 것을 구분해야 하기 때문.

    - ``True``  — 가능하다고 명시됨
    - ``False`` — **불가라고 명시됨**
    - ``None``  — **확인 안 됨** (챗봇은 "확인이 필요해요"로 답해야 한다)

    ``False`` 로 뭉개면 확인 안 된 항목이 불가로 바뀌어, 없는 규정을 만들어 답하게 된다.
    """

    __tablename__ = "transport_pet_rules"
    __table_args__ = (
        CheckConstraint(
            "cabin_max_weight_kg IS NULL OR cabin_max_weight_kg >= 0",
            name="cabin_max_weight_nonnegative",
        ),
        CheckConstraint(
            "cargo_max_weight_kg IS NULL OR cargo_max_weight_kg >= 0",
            name="cargo_max_weight_nonnegative",
        ),
        CheckConstraint(
            "cabin_fee_krw IS NULL OR cabin_fee_krw >= 0", name="cabin_fee_nonnegative"
        ),
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes > 0", name="duration_positive"
        ),
        Index("ix_transport_pet_rules_guide_document_id", "guide_document_id"),
        Index("ix_transport_pet_rules_carrier_type", "carrier_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guide_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("guide_documents.id", ondelete="CASCADE"), nullable=False
    )
    carrier_name: Mapped[str] = mapped_column(String(50), nullable=False)
    carrier_type: Mapped[CarrierType] = mapped_column(
        db_enum(CarrierType, "carrier_type"), nullable=False
    )
    route: Mapped[str | None] = mapped_column(String(50))

    # 기내 반입 — 무게는 케이지 포함 기준
    cabin_allowed: Mapped[bool | None] = mapped_column(Boolean)
    cabin_max_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    cabin_fee_krw: Mapped[int | None] = mapped_column(Integer)
    min_age_weeks_cabin: Mapped[int | None] = mapped_column(SmallInteger)
    max_pets_per_person_cabin: Mapped[int | None] = mapped_column(SmallInteger)
    max_pets_per_trip: Mapped[int | None] = mapped_column(SmallInteger)

    # 화물칸 위탁 — 여객선은 해당 없음
    cargo_allowed: Mapped[bool | None] = mapped_column(Boolean)
    cargo_max_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    cargo_fee_threshold_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    cargo_fee_light_krw: Mapped[int | None] = mapped_column(Integer)
    cargo_fee_heavy_krw: Mapped[int | None] = mapped_column(Integer)
    min_age_weeks_cargo: Mapped[int | None] = mapped_column(SmallInteger)

    # 절차
    pledge_required: Mapped[bool | None] = mapped_column(Boolean)
    online_checkin_allowed: Mapped[bool | None] = mapped_column(Boolean)
    same_day_request_allowed: Mapped[bool | None] = mapped_column(Boolean)
    request_deadline_hours: Mapped[int | None] = mapped_column(SmallInteger)
    airport_cage_price_krw: Mapped[int | None] = mapped_column(Integer)

    # 여객선용 — 항공기는 노선별로 갈려 넣지 않는다
    duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)

    notes: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class TransportRestrictedBreed(Base):
    """운송사별 제한 견종.

    ⚠️ 목록을 하나로 합치면 안 된다. 운송사마다 다르고
    (대한항공 8종 / 아시아나 12종 / 진에어 10종 / 제주항공 15종),
    도베르만처럼 한 곳에만 있는 견종이 있다.
    """

    __tablename__ = "transport_restricted_breeds"
    __table_args__ = (
        Index("ix_transport_restricted_breeds_rule_id", "transport_pet_rule_id"),
        Index("ix_transport_restricted_breeds_breed_name_ko", "breed_name_ko"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transport_pet_rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transport_pet_rules.id", ondelete="CASCADE"), nullable=False
    )
    breed_name_ko: Mapped[str] = mapped_column(String(100), nullable=False)
    breed_name_en: Mapped[str | None] = mapped_column(String(100))
    breed_aliases: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    restriction_type: Mapped[BreedRestrictionType] = mapped_column(
        db_enum(BreedRestrictionType, "breed_restriction_type"), nullable=False
    )
    applies_to: Mapped[BreedRestrictionScope] = mapped_column(
        db_enum(BreedRestrictionScope, "breed_restriction_scope"), nullable=False
    )
    is_example_only: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
