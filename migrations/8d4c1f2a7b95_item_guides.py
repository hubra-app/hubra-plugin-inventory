"""inventory_item_guides: the usage guide per item

Until Inventory 2.4 the guides were the Guides plugin's (``item_guides``),
which is now Qualifications. When that table exists, its rows are copied
here once (items that have a guide here already keep theirs). Guides 2.0
keeps its table for now, so the copy works in either update order.

Revision ID: 8d4c1f2a7b95
Revises: 6c2f9a4d1e83
Create Date: 2026-11-09 16:00:00

"""

from alembic import op
import sqlalchemy as sa

from hubra.core.plugins.ops import has_table

revision = "8d4c1f2a7b95"
down_revision = "6c2f9a4d1e83"
branch_labels = None
depends_on = None


def upgrade():
    if not has_table("inventory_item_guides"):
        op.create_table(
            "inventory_item_guides",
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("guide", sa.Text(), nullable=True),
            sa.Column("guide_url", sa.String(length=500), nullable=True),
            sa.Column("qualification_kind_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["item_id"], ["inventory_items.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("item_id"),
        )
    if has_table("item_guides"):
        op.execute(
            sa.text(
                "INSERT INTO inventory_item_guides"
                " (item_id, guide, guide_url, qualification_kind_id, updated_at)"
                " SELECT g.item_id, g.guide, g.guide_url, g.qualification_id,"
                " COALESCE(g.updated_at, CURRENT_TIMESTAMP) FROM item_guides g"
                " JOIN inventory_items i ON i.id = g.item_id"
                " WHERE NOT EXISTS (SELECT 1 FROM inventory_item_guides x"
                " WHERE x.item_id = g.item_id)"
            )
        )


def downgrade():
    op.drop_table("inventory_item_guides")
