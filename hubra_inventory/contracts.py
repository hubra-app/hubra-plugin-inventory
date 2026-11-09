"""What Inventory offers other plugins and the dashboards (Hubra docs/contracts.md).

Other plugins read items through these queries instead of importing this
package or reading ``inventory_items``; they hear of a new or changed item
through ``inventory.item.saved`` and of a deleted one through
``inventory.item.deleted``. An add-on that keeps its own type of item (the
Keys add-on and the type "Key") adds, changes and deletes those items with
the actions ``inventory.items.save`` and ``inventory.items.delete``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from hubra.core.contracts import Refused
from hubra.core.extensions import db

from .models import (
    _CATEGORIES,
    _STATUSES,
    InventoryCheckout,
    InventoryHistoryEntry,
    InventoryItem,
)

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
    serial_number: str | None = None
    holder_id: int | None = None


class ItemDeleted(BaseModel):
    item_id: int


class ItemSaved(BaseModel):
    """An item was added or changed, in Inventory or through an action."""

    item_id: int
    name: str
    category: str
    status: str
    serial_number: str | None = None


class SaveIn(BaseModel):
    """A new item (no ``item_id``) or the fields to change on one.

    Fields left out stay as they are. ``status`` can't move an item in or
    out of "checked_out": that is the checkout's.
    """

    item_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: Literal[_CATEGORIES] | None = None  # type: ignore[valid-type]
    status: Literal[_STATUSES] | None = None  # type: ignore[valid-type]
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    serial_number: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    # Who has it now (an add-on handing it out); null takes it back.
    holder_id: int | None = None
    actor_id: int | None = None


class HistoryIn(BaseModel):
    """One entry in an item's history. ``action`` is the add-on's word
    ("issue", "return", ...), shown as ``inventory.history.<action>``."""

    item_id: int
    action: str = Field(min_length=1, max_length=30, pattern=r"^[a-z_]+$")
    member_id: int | None = None
    by_id: int | None = None
    note: str | None = None
    # When it happened, for entries moved over from before; now if unset.
    at: datetime | None = None


class HistoryRef(BaseModel):
    id: int


class DeleteIn(BaseModel):
    item_id: int
    actor_id: int | None = None


class Deleted(BaseModel):
    deleted: bool


def _item(row: InventoryItem) -> Item:
    return Item(
        id=row.id,
        name=row.name,
        category=row.category,
        status=row.status,
        location=row.location,
        instruction_required=bool(row.instruction_required),
        serial_number=row.serial_number,
        holder_id=row.holder_id,
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


# ── Actions ─────────────────────────────────────────────────────────────────


def _actor_id(ctx, given: int | None) -> int | None:
    if given is not None:
        return given
    return ctx.actor.id if ctx.actor is not None else None


def save_item(ctx, data: SaveIn) -> Item:
    """Add an item, or change the fields given on an existing one."""
    from .services import InventoryService, InventoryServiceItems

    fields = data.model_dump(exclude={"item_id", "actor_id"}, exclude_unset=True)
    actor_id = _actor_id(ctx, data.actor_id)
    if fields.get("holder_id") is not None:
        from hubra.core.models.member import Member

        if db.session.get(Member, fields["holder_id"]) is None:
            raise Refused(f"Member {fields['holder_id']} not found", code="NOT_FOUND", status=404)
    if data.item_id is None:
        if not fields.get("name") or not fields.get("category"):
            raise Refused("A new item needs a name and a category", code="VALIDATION_ERROR", status=400)
        if fields.get("status") == "checked_out":
            raise Refused(
                "Use check out to lend an item", code="USE_CHECKOUT", status=409
            )
        return _item(InventoryServiceItems.create(fields, actor_id))
    row = db.session.get(InventoryItem, data.item_id)
    if row is None:
        raise Refused(f"Inventory item {data.item_id} not found", code="NOT_FOUND", status=404)
    if any(k in fields and fields[k] is None for k in ("name", "category", "status")):
        raise Refused("name, category and status can't be empty", code="VALIDATION_ERROR", status=400)
    InventoryService.update(row, fields, actor_id)
    db.session.flush()
    return _item(row)


def add_history(ctx, data: HistoryIn) -> HistoryRef:
    """Record what an add-on did with an item."""
    from hubra.core.models.member import Member

    if db.session.get(InventoryItem, data.item_id) is None:
        raise Refused(f"Inventory item {data.item_id} not found", code="NOT_FOUND", status=404)
    for mid in (data.member_id, data.by_id):
        if mid is not None and db.session.get(Member, mid) is None:
            raise Refused(f"Member {mid} not found", code="NOT_FOUND", status=404)
    entry = InventoryHistoryEntry(
        item_id=data.item_id,
        action=data.action,
        member_id=data.member_id,
        by_id=_actor_id(ctx, data.by_id),
        note=data.note,
    )
    if data.at is not None:
        entry.at = data.at
    db.session.add(entry)
    db.session.flush()
    return HistoryRef(id=entry.id)


def delete_item(ctx, data: DeleteIn) -> Deleted:
    """Delete an item; an item that is already gone is fine."""
    from .services import InventoryService

    if db.session.get(InventoryItem, data.item_id) is None:
        return Deleted(deleted=False)
    InventoryService.delete(data.item_id, _actor_id(ctx, data.actor_id))
    return Deleted(deleted=True)


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
