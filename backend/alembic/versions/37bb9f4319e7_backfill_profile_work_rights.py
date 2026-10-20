"""backfill profile work rights

Revision ID: 37bb9f4319e7
Revises: a138acf143ff
Create Date: 2026-10-20 18:00:15.768197

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37bb9f4319e7'
down_revision: Union[str, Sequence[str], None] = 'a138acf143ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight table stub: migrations must not import app models, which keep changing.
profiles = sa.table("candidate_profiles", sa.column("id", sa.Integer), sa.column("data", sa.JSON))


def _rewrite(add: bool) -> None:
    conn = op.get_bind()
    for row in conn.execute(sa.select(profiles.c.id, profiles.c.data)).all():
        data = dict(row.data)
        if add:
            data.setdefault("work_rights", None)
        else:
            data.pop("work_rights", None)
        conn.execute(profiles.update().where(profiles.c.id == row.id).values(data=data))


def upgrade() -> None:
    """Add a null work_rights to profiles stored before the field existed."""
    _rewrite(add=True)


def downgrade() -> None:
    """Drop the work_rights key."""
    _rewrite(add=False)
