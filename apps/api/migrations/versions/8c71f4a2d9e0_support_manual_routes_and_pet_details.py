"""support manual routes and pet species details

Revision ID: 8c71f4a2d9e0
Revises: 5eead3cb186c
Create Date: 2026-08-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c71f4a2d9e0"
down_revision: str | Sequence[str] | None = "5eead3cb186c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


route_creation_type = postgresql.ENUM(
    "recommended",
    "manual",
    name="route_creation_type",
    create_type=False,
)


def upgrade() -> None:
    op.add_column("pets", sa.Column("species_detail", sa.String(length=50), nullable=True))
    op.execute(
        "UPDATE pets SET species_detail = '미입력' "
        "WHERE species = 'other' AND (species_detail IS NULL OR btrim(species_detail) = '')"
    )
    op.create_check_constraint(
        op.f("ck_pets_species_detail_consistency"),
        "pets",
        "(species = 'other' AND species_detail IS NOT NULL AND btrim(species_detail) <> '') "
        "OR (species <> 'other' AND species_detail IS NULL)",
    )

    route_creation_type.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "routes",
        sa.Column(
            "creation_type",
            route_creation_type,
            server_default="recommended",
            nullable=False,
        ),
    )
    op.alter_column("routes", "creation_type", server_default=None)
    op.alter_column("routes", "route_request_id", existing_type=sa.UUID(), nullable=True)
    op.create_check_constraint(
        op.f("ck_routes_creation_type_request_consistency"),
        "routes",
        "(creation_type = 'recommended' AND route_request_id IS NOT NULL) "
        "OR (creation_type = 'manual' AND route_request_id IS NULL)",
    )

    op.create_table(
        "route_pets",
        sa.Column("route_id", sa.UUID(), nullable=False),
        sa.Column("pet_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["pet_id"],
            ["pets.id"],
            name=op.f("fk_route_pets_pet_id_pets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["route_id"],
            ["routes.id"],
            name=op.f("fk_route_pets_route_id_routes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("route_id", "pet_id", name=op.f("pk_route_pets")),
    )
    op.execute(
        """
        INSERT INTO route_pets (route_id, pet_id)
        SELECT routes.id, route_request_pets.pet_id
        FROM routes
        JOIN route_request_pets
          ON route_request_pets.route_request_id = routes.route_request_id
        ON CONFLICT (route_id, pet_id) DO NOTHING
        """
    )

    op.drop_column("places", "weather_sensitivity")
    op.drop_column("places", "crowd_level")
    op.drop_column("places", "activity_level")


def downgrade() -> None:
    op.add_column("places", sa.Column("activity_level", sa.SmallInteger(), nullable=True))
    op.add_column("places", sa.Column("crowd_level", sa.SmallInteger(), nullable=True))
    op.add_column("places", sa.Column("weather_sensitivity", sa.SmallInteger(), nullable=True))
    op.create_check_constraint(
        op.f("ck_places_activity_level_range"),
        "places",
        "activity_level IS NULL OR activity_level BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        op.f("ck_places_crowd_level_range"),
        "places",
        "crowd_level IS NULL OR crowd_level BETWEEN 1 AND 5",
    )
    op.create_check_constraint(
        op.f("ck_places_weather_sensitivity_range"),
        "places",
        "weather_sensitivity IS NULL OR weather_sensitivity BETWEEN 1 AND 5",
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM routes WHERE creation_type = 'manual') THEN
                RAISE EXCEPTION
                    'Cannot downgrade while manual routes exist; export or remove them first';
            END IF;
        END
        $$
        """
    )
    op.drop_table("route_pets")
    op.drop_constraint(
        op.f("ck_routes_creation_type_request_consistency"), "routes", type_="check"
    )
    op.alter_column("routes", "route_request_id", existing_type=sa.UUID(), nullable=False)
    op.drop_column("routes", "creation_type")
    route_creation_type.drop(op.get_bind(), checkfirst=True)

    op.drop_constraint(op.f("ck_pets_species_detail_consistency"), "pets", type_="check")
    op.drop_column("pets", "species_detail")
