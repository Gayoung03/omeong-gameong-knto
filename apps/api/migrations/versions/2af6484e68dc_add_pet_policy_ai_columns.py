"""add pet policy ai columns

Revision ID: 2af6484e68dc
Revises: 83e31e2be855
Create Date: 2026-08-31 01:50:15.530852
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2af6484e68dc"
down_revision: str | Sequence[str] | None = "83e31e2be855"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# place_pet_policies AI 입출력 컬럼 4종(ai-io-column-design 7.1·8.1).
# 전부 nullable — 3값 의미(True/False = 명시, NULL = 미확인) 보존. 가산적 ADD COLUMN 만.
def upgrade() -> None:
    op.add_column(
        "place_pet_policies", sa.Column("muzzle_required", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "place_pet_policies", sa.Column("food_area_allowed", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "place_pet_policies", sa.Column("max_pets_per_person", sa.SmallInteger(), nullable=True)
    )
    op.add_column(
        "place_pet_policies", sa.Column("caution_note", sa.String(length=150), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_place_pet_policies_max_pets_per_person_positive"),
        "place_pet_policies",
        "max_pets_per_person IS NULL OR max_pets_per_person >= 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_place_pet_policies_max_pets_per_person_positive"),
        "place_pet_policies",
        type_="check",
    )
    op.drop_column("place_pet_policies", "caution_note")
    op.drop_column("place_pet_policies", "max_pets_per_person")
    op.drop_column("place_pet_policies", "food_area_allowed")
    op.drop_column("place_pet_policies", "muzzle_required")
