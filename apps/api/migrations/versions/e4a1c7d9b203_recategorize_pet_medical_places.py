"""recategorize pet medical places

Revision ID: e4a1c7d9b203
Revises: b7e2f4a9c1d3
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e4a1c7d9b203"
down_revision: str | Sequence[str] | None = "b7e2f4a9c1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE places
        SET category = 'veterinary_hospital', updated_at = now()
        WHERE category = 'etc'
          AND category_detail IN ('동물병원', '동물약국')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE places
        SET category = 'etc', updated_at = now()
        WHERE category = 'veterinary_hospital'
          AND category_detail IN ('동물병원', '동물약국')
        """
    )
