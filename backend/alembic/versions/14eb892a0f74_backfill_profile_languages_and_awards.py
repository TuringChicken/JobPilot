"""backfill profile languages and awards

Revision ID: 14eb892a0f74
Revises: a2e6a70386e0
Create Date: 2026-10-19 01:05:52.906927

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14eb892a0f74'
down_revision: Union[str, Sequence[str], None] = 'a2e6a70386e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight table stub: migrations must not import app models, which keep changing.
profiles = sa.table("candidate_profiles", sa.column("id", sa.Integer), sa.column("data", sa.JSON))
NEW_KEYS = ("languages", "awards")


def _rewrite(add: bool) -> None:
    conn = op.get_bind()
    for row in conn.execute(sa.select(profiles.c.id, profiles.c.data)).all():
        data = dict(row.data)
        for key in NEW_KEYS:
            if add:
                data.setdefault(key, [])
            else:
                data.pop(key, None)
        conn.execute(profiles.update().where(profiles.c.id == row.id).values(data=data))


def upgrade() -> None:
    """Add empty languages/awards lists to profiles stored before these fields existed."""
    _rewrite(add=True)


def downgrade() -> None:
    """Drop the languages/awards keys."""
    _rewrite(add=False)
