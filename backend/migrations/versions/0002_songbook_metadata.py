"""Songbook metadata and chord-diagram selection (#89).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All new columns are nullable or have a server default, so existing
    # songbooks keep working without a data migration.
    op.add_column(
        "songbooks", sa.Column("author", sa.String(length=256), nullable=True)
    )
    op.add_column("songbooks", sa.Column("date", sa.Date(), nullable=True))
    op.add_column("songbooks", sa.Column("genre", sa.String(length=128), nullable=True))
    op.add_column(
        "songbooks", sa.Column("difficulty", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "songbooks",
        sa.Column(
            "chord_diagrams",
            sa.String(length=16),
            server_default="none",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("songbooks", "chord_diagrams")
    op.drop_column("songbooks", "difficulty")
    op.drop_column("songbooks", "genre")
    op.drop_column("songbooks", "date")
    op.drop_column("songbooks", "author")
