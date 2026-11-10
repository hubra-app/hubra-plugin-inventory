"""Stock counts of consumables (drinks, snacks, chalk).

An item is counted once ``stock`` is set. Taking some (the Kasse plugin's
Strichliste through the action ``inventory.stock.adjust``) or counting by
hand changes it and leaves a line in the item's history. When the count
falls to ``min_stock`` or below, ``inventory.stock.low`` goes out once, so a
plugin can reorder; it goes out again only after the stock was back above.
"""

from __future__ import annotations

from hubra.core.modules import emit
from hubra.core.extensions import db

from .models import InventoryHistoryEntry, InventoryItem


def is_low(item: InventoryItem) -> bool:
    return (
        item.stock is not None
        and item.min_stock is not None
        and item.stock <= item.min_stock
    )


def _record(item: InventoryItem, action: str, note: str, actor_id, member_id=None) -> None:
    db.session.add(
        InventoryHistoryEntry(
            item_id=item.id,
            action=action,
            member_id=member_id,
            by_id=actor_id,
            note=note,
        )
    )


def _after(item: InventoryItem, was_low: bool) -> None:
    if is_low(item) and not was_low:
        emit(
            "inventory.stock.low",
            item_id=item.id,
            name=item.name,
            stock=item.stock,
            min_stock=item.min_stock,
            unit=item.unit,
        )


def adjust_stock(
    item: InventoryItem,
    delta: int,
    actor_id: int | None,
    reason: str | None = None,
    member_id: int | None = None,
) -> bool:
    """Add *delta* (negative: taken) to a counted item. False when the item
    isn't counted (``stock`` is None): nothing changes then."""
    if item.stock is None or delta == 0:
        return False
    was_low = is_low(item)
    item.stock += delta
    note = f"{delta:+d}" + (f" · {reason}" if reason else "")
    _record(item, "stock_taken" if delta < 0 else "stock_added", note, actor_id, member_id)
    _after(item, was_low)
    return True


def set_stock(item: InventoryItem, count: int | None, actor_id: int | None) -> None:
    """Set the count by hand (a stocktake); None stops counting."""
    was_low = is_low(item)
    before = item.stock
    item.stock = count
    if count is not None:
        note = f"{before} → {count}" if before is not None else str(count)
        _record(item, "stock_counted", note, actor_id)
    _after(item, was_low)
