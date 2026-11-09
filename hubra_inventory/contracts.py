"""What Inventory offers other plugins and the dashboards (Hubra docs/contracts.md).

Other plugins read items through these queries instead of importing this
package or reading ``inventory_items``; they hear of a deleted item through
``inventory.item.deleted``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from hubra.core.contracts import Refused
from hubra.core.extensions import db
from hubra.core.models.member import Member

from .models import InventoryCheckout, InventoryItem

MAX_ITEMS = 500


class ItemsIn(BaseModel):
    ids: list[int] = Field(max_length=MAX_ITEMS)


class ListIn(BaseModel):
    search: str | None = None
    limit: int = Field(default=200, ge=1, le=MAX_ITEMS)


class Item(BaseModel):
    """An item as other plugins see it."""

    id: int
    name: str
    category: str
    status: str
    location: str | None = None
    instruction_required: bool = False
    # The member whose own thing this is when a member lends it to the club.
    lent_by: int | None = None


class LendIn(BaseModel):
    """A member's own thing they lend to the club (a trailer, a projector)."""

    member_id: int
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    category: str = "Item"


class ItemDeleted(BaseModel):
    item_id: int


def _item(row: InventoryItem) -> Item:
    return Item(
        id=row.id,
        name=row.name,
        category=row.category,
        status=row.status,
        location=row.location,
        instruction_required=bool(row.instruction_required),
        lent_by=row.owner_id if row.visibility == "private" else None,
    )


def _live():
    return select(InventoryItem).where(InventoryItem.deleted_at.is_(None))


def get_items(ctx, data: ItemsIn) -> list[Item]:
    """The items with these ids that still exist, in the order asked."""
    ids = list(dict.fromkeys(data.ids))
    if not ids:
        return []
    rows = db.session.scalars(_live().where(InventoryItem.id.in_(ids))).all()
    by_id = {r.id: r for r in rows}
    return [_item(by_id[i]) for i in ids if i in by_id]


def list_items(ctx, data: ListIn) -> list[Item]:
    """Items by name, optionally matching *search*."""
    query = _live()
    if data.search:
        query = query.where(InventoryItem.name.ilike(f"%{data.search.strip()}%"))
    rows = db.session.scalars(query.order_by(InventoryItem.name).limit(data.limit)).all()
    return [_item(r) for r in rows]


def lend_item(ctx, data: LendIn) -> Item:
    """Record a member's own thing as lent to the club: an item that
    belongs to that member (``visibility="private"``, owner the member).

    A member may only lend their own things; a job or plugin acting as
    the system may record it for anyone (moving old entries over)."""
    if not ctx.system and (ctx.actor is None or ctx.actor.id != data.member_id):
        raise Refused("Members can only lend their own things.", "NOT_YOUR_ITEM", 403)
    if data.category not in ("Tool", "Item", "Material"):
        raise Refused("Category must be Tool, Item or Material.", "VALIDATION_ERROR", 400)
    member = db.session.get(Member, data.member_id)
    if member is None or member.archived_at is not None:
        raise Refused("No such member.", "NOT_FOUND", 404)
    from .services import InventoryServiceItems

    row = InventoryServiceItems.create(
        {
            "name": data.name.strip(),
            "category": data.category,
            "description": (data.description or "").strip() or None,
            "owner_id": member.id,
            "visibility": "private",
        },
        None if ctx.system else ctx.actor.id,
    )
    return _item(row)


# ── Dashboard widgets ───────────────────────────────────────────────────────


def _open_checkouts():
    return (
        select(InventoryCheckout, InventoryItem)
        .join(InventoryItem, InventoryItem.id == InventoryCheckout.item_id)
        .where(InventoryCheckout.returned_at.is_(None))
        .where(InventoryItem.deleted_at.is_(None))
    )


def checked_out(ctx, config: dict) -> dict:
    """Items out right now, the ones due back first."""
    count = max(1, min(int(config.get("count") or 5), 20))
    rows = db.session.execute(
        _open_checkouts()
        .order_by(InventoryCheckout.expected_return_at.is_(None), InventoryCheckout.expected_return_at)
        .limit(count)
    ).all()
    total = db.session.scalar(
        select(func.count()).select_from(_open_checkouts().subquery())
    )
    items = []
    for checkout, item in rows:
        who = checkout.member.name if checkout.member else ""
        due = checkout.expected_return_at
        sub = f"{who} · {due:%d.%m.%Y}" if due else who
        items.append({"label": item.name, "sub": sub, "path": f"/app/inventory/{item.id}"})
    return {"items": items, "total": total}


def overdue(ctx, config: dict) -> dict:
    """How many checkouts are past their due date."""
    now = datetime.now(timezone.utc)
    n = db.session.scalar(
        select(func.count()).select_from(
            _open_checkouts()
            .where(InventoryCheckout.expected_return_at.is_not(None))
            .where(InventoryCheckout.expected_return_at < now)
            .subquery()
        )
    )
    return {"value": n or 0, "sub": None, "path": "/app/inventory"}
