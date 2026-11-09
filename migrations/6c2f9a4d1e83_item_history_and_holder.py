"""inventory_items.holder_id and inventory_item_history

Who has an item an add-on handed out (Keys: who holds a key), and the item
history for what add-ons do with an item (Keys: the handovers).

Revision ID: 6c2f9a4d1e83
Revises: 1a7e0b5c0de2
Create Date: 2026-11-09 11:00:00

"""

from alembic import op
import sqlalchemy as sa

from hubra.core.plugins.ops import columns, has_table

revision = "6c2f9a4d1e83"
down_revision = "1a7e0b5c0de2"
branch_labels = None
depends_on = None


def upgrade():
    if "holder_id" not in columns("inventory_items"):
        with op.batch_alter_table("inventory_items", schema=None) as batch_op:
            batch_op.add_column(sa.Column("holder_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_inventory_items_holder_id_members",
                "members",
                ["holder_id"],
                ["id"],
                ondelete="SET NULL",
            )
    if not has_table("inventory_item_history"):
        op.create_table(
            "inventory_item_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=30), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=True),
            sa.Column("by_id", sa.Integer(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["item_id"], ["inventory_items.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["by_id"], ["members.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_inventory_item_history_item_id",
            "inventory_item_history",
            ["item_id"],
        )


def downgrade():
    op.drop_index("ix_inventory_item_history_item_id", "inventory_item_history")
    op.drop_table("inventory_item_history")
    with op.batch_alter_table("inventory_items", schema=None) as batch_op:
        batch_op.drop_constraint("fk_inventory_items_holder_id_members", type_="foreignkey")
        batch_op.drop_column("holder_id")
