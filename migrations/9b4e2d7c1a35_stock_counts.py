"""inventory_items.stock, min_stock and unit

Stock counts for consumables (the Strichliste's drinks and snacks), with a
reorder level.

Revision ID: 9b4e2d7c1a35
Revises: 6c2f9a4d1e83
Create Date: 2026-11-10 12:00:00

"""

from alembic import op
import sqlalchemy as sa

from hubra.core.plugins.ops import columns

revision = "9b4e2d7c1a35"
down_revision = "6c2f9a4d1e83"
branch_labels = None
depends_on = None


def upgrade():
    have = columns("inventory_items")
    with op.batch_alter_table("inventory_items", schema=None) as batch_op:
        if "stock" not in have:
            batch_op.add_column(sa.Column("stock", sa.Integer(), nullable=True))
        if "min_stock" not in have:
            batch_op.add_column(sa.Column("min_stock", sa.Integer(), nullable=True))
        if "unit" not in have:
            batch_op.add_column(sa.Column("unit", sa.String(length=30), nullable=True))


def downgrade():
    with op.batch_alter_table("inventory_items", schema=None) as batch_op:
        batch_op.drop_column("unit")
        batch_op.drop_column("min_stock")
        batch_op.drop_column("stock")
