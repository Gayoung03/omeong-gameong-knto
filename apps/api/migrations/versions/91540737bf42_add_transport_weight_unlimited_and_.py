"""add transport weight unlimited and cabin conditions

Revision ID: 91540737bf42
Revises: 16d96164ba8a
Create Date: 2026-08-31 16:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "91540737bf42"
down_revision: str | Sequence[str] | None = "16d96164ba8a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# transport_pet_rules "무게 제한 없음" 명시 + 조건부 사실(ai-io-column-design 7.4·8.1).
# NULL(미확인)과 "제한 없음"을 구분해 "무게 무제한" 오답을 막는다. 가산적 ADD COLUMN.
def upgrade() -> None:
    op.add_column(
        "transport_pet_rules", sa.Column("cabin_weight_unlimited", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "transport_pet_rules", sa.Column("cargo_weight_unlimited", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "transport_pet_rules", sa.Column("cabin_conditions", sa.String(length=200), nullable=True)
    )
    # 무게 무제한과 무게 상한은 동시에 참일 수 없다.
    op.create_check_constraint(
        op.f("ck_transport_pet_rules_cabin_weight_unlimited_excl"),
        "transport_pet_rules",
        "cabin_weight_unlimited IS NOT TRUE OR cabin_max_weight_kg IS NULL",
    )
    op.create_check_constraint(
        op.f("ck_transport_pet_rules_cargo_weight_unlimited_excl"),
        "transport_pet_rules",
        "cargo_weight_unlimited IS NOT TRUE OR cargo_max_weight_kg IS NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_transport_pet_rules_cargo_weight_unlimited_excl"),
        "transport_pet_rules",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_transport_pet_rules_cabin_weight_unlimited_excl"),
        "transport_pet_rules",
        type_="check",
    )
    op.drop_column("transport_pet_rules", "cabin_conditions")
    op.drop_column("transport_pet_rules", "cargo_weight_unlimited")
    op.drop_column("transport_pet_rules", "cabin_weight_unlimited")
