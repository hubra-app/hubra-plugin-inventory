"""What Inventory offers other plugins and the dashboards (Hubra docs/contracts.md).

Other plugins read items through these queries instead of importing this
package or reading ``inventory_items``; they hear of a deleted item through
``inventory.item.deleted``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from hubra.core.extensions import db

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
