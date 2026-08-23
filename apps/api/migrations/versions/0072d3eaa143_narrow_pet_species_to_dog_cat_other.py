"""narrow pet species to dog cat other

Revision ID: 0072d3eaa143
Revises: b1b19f24afe9
Create Date: 2026-08-22 18:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0072d3eaa143"
down_revision: str | Sequence[str] | None = "b1b19f24afe9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Postgres 는 enum 값을 지울 수 없어 새 타입을 만들어 컬럼을 옮긴 뒤 옛 타입을 버린다.
narrowed_species = postgresql.ENUM("dog", "cat", "other", name="pet_species_new")
widened_species = postgresql.ENUM(
    "dog", "cat", "rabbit", "bird", "other", name="pet_species_old"
)

SPECIES_DETAIL_CONSISTENCY = (
    "(species = 'other' AND species_detail IS NOT NULL "
    "AND btrim(species_detail) <> '') "
    "OR (species <> 'other' AND species_detail IS NULL)"
)


def upgrade() -> None:
    # CHECK 제약이 옛 타입을 참조하므로 먼저 떼어낸다.
    op.drop_constraint(op.f("ck_pets_species_detail_consistency"), "pets", type_="check")

    narrowed_species.create(op.get_bind(), checkfirst=True)

    # rabbit·bird 는 other 로 합치고, 사라지는 종 이름을 species_detail 에 남긴다.
    op.execute(
        """
        UPDATE pets
        SET species_detail = CASE species::text
            WHEN 'rabbit' THEN '토끼'
            WHEN 'bird' THEN '새'
            ELSE species_detail
        END
        WHERE species::text IN ('rabbit', 'bird')
        """
    )
    op.execute(
        """
        ALTER TABLE pets
        ALTER COLUMN species TYPE pet_species_new
        USING (
            CASE
                WHEN species::text IN ('rabbit', 'bird') THEN 'other'
                ELSE species::text
            END
        )::pet_species_new
        """
    )
    op.execute("DROP TYPE pet_species")
    op.execute("ALTER TYPE pet_species_new RENAME TO pet_species")

    op.create_check_constraint(
        op.f("ck_pets_species_detail_consistency"), "pets", SPECIES_DETAIL_CONSISTENCY
    )


def downgrade() -> None:
    # 되돌려도 other 로 합쳐진 rabbit·bird 는 복원되지 않는다. 선택지만 다시 넓힌다.
    op.drop_constraint(op.f("ck_pets_species_detail_consistency"), "pets", type_="check")

    widened_species.create(op.get_bind(), checkfirst=True)
    op.execute(
        "ALTER TABLE pets ALTER COLUMN species TYPE pet_species_old "
        "USING species::text::pet_species_old"
    )
    op.execute("DROP TYPE pet_species")
    op.execute("ALTER TYPE pet_species_old RENAME TO pet_species")

    op.create_check_constraint(
        op.f("ck_pets_species_detail_consistency"), "pets", SPECIES_DETAIL_CONSISTENCY
    )
