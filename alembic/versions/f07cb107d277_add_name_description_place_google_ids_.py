"""add name description place_google_ids to travel_routes

Revision ID: f07cb107d277
Revises: 6c962760db57
Create Date: 2025-04-21 04:26:30.790717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f07cb107d277'
down_revision: Union[str, None] = '6c962760db57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        "travel_routes",
        sa.Column("name", sa.String(), nullable=True),
    )
    op.add_column(
        "travel_routes",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "travel_routes",
        sa.Column("place_google_ids",
                  postgresql.ARRAY(sa.String()),
                  nullable=False,
                  server_default="{}")
    )

def downgrade():
    op.drop_column("travel_routes", "place_google_ids")
    op.drop_column("travel_routes", "description")
    op.drop_column("travel_routes", "name")