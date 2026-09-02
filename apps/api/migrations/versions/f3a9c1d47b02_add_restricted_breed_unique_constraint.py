"""add restricted breed unique constraint

Revision ID: f3a9c1d47b02
Revises: e8b2a91c4d7f

견종 적재 스크립트(seed_restricted_breeds)의 멱등을 DB 가 최종 방어한다 (계획 리뷰 반영).
키에 restriction_type 이 들어가는 이유: 같은 견종이 한 운송사에서 두 유형으로 제한될 수
있다 — 아시아나 원문은 마스티프를 맹견 목록과 단두종 목록 **양쪽에** 올려 두었다
(리허설 적재 실측). 현재 테이블은 0행이라 잠금·검증 부담이 없다.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f3a9c1d47b02"
down_revision: str | Sequence[str] | None = "e8b2a91c4d7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "uq_restricted_breed_per_rule"


def upgrade() -> None:
    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "transport_restricted_breeds",
        ["transport_pet_rule_id", "breed_name_ko", "restriction_type"],
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "transport_restricted_breeds", type_="unique")