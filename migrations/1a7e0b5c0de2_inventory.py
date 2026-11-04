"""inventory_items, inventory_checkouts, item_instructions

Databases that ran Hubra before Inventory became a plugin have the tables
already (Hubra's revisions e5a32bbb8ef5 and a1b2c3d4e5f6); they are kept as
they are, items and all.

Revision ID: 1a7e0b5c0de2
Revises:
Create Date: 2026-11-02 15:00:00

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from hubra.core.plugins.ops import has_table

revision = "1a7e0b5c0de2"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    if not has_table("inventory_items"):
        op.create_table(
            "inventory_items",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("owner_id", sa.Integer(), nullable=True),
            sa.Column("responsible_id", sa.Integer(), nullable=True),
            sa.Column("visibility", sa.String(length=20), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("cost", sa.Numeric(precision=10, scale=2), nullable=True),
            sa.Column(
                "links", sa.JSON(), server_default=sa.text("'[]'"), nullable=False
            ),
            sa.Column("instruction_required", sa.Boolean(), nullable=False),
            sa.Column("purchase_date", sa.Date(), nullable=True),
            sa.Column(
                "purchase_cost", sa.Numeric(precision=10, scale=2), nullable=True
            ),
            sa.Column(
                "current_value", sa.Numeric(precision=10, scale=2), nullable=True
            ),
            sa.Column("location", sa.String(length=255), nullable=True),
            sa.Column("serial_number", sa.String(length=255), nullable=True),
            sa.Column("barcode_id", sa.String(length=255), nullable=True),
            sa.Column(
                "documents",
                postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
                nullable=True,
            ),
            sa.Column("image_url", sa.String(length=500), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["owner_id"], ["members.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(
                ["responsible_id"], ["members.id"], ondelete="SET NULL"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_table("inventory_checkouts"):
        op.create_table(
            "inventory_checkouts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expected_return_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("condition_notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(
                ["item_id"], ["inventory_items.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    if not has_table("item_instructions"):
        op.create_table(
            "item_instructions",
            sa.Column("item_id", sa.Integer(), nullable=False),
            sa.Column("member_id", sa.Integer(), nullable=False),
            sa.Column("instructed_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["item_id"], ["inventory_items.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["member_id"], ["members.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("item_id", "member_id"),
        )


def downgrade():
    op.drop_table("item_instructions")
    op.drop_table("inventory_checkouts")
    op.drop_table("inventory_items")
