"""What Inventory offers other plugins and the dashboards (contracts)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from hubra.core import contracts
from hubra.core.models.member import Member
from hubra_inventory.models import InventoryCheckout, InventoryItem


@pytest.fixture
def items(db, seeded_db):
    rows = [
        InventoryItem(name="Laser cutter", category="Tool", status="available",
                      location="Werkstatt", instruction_required=True),
        InventoryItem(name="Drill", category="Tool", status="available"),
        InventoryItem(name="Old saw", category="Tool", status="available",
                      deleted_at=datetime.now(timezone.utc)),
    ]
    db.session.add_all(rows)
    db.session.commit()
    return rows


def test_items_get_and_list(app, db, items):
    laser, drill, gone = items
    got = contracts.query("inventory.items.get", ids=[drill.id, gone.id, laser.id],
                          actor=contracts.SYSTEM)
    assert [i["name"] for i in got] == ["Drill", "Laser cutter"]
    assert got[1]["location"] == "Werkstatt" and got[1]["instruction_required"] is True
    listed = contracts.query("inventory.items.list", search="las", actor=contracts.SYSTEM)
    assert [i["id"] for i in listed] == [laser.id]


def test_items_need_the_right(app, db, items):
    with pytest.raises(contracts.ActionForbidden):
        contracts.query("inventory.items.get", ids=[items[0].id], actor=None)


def test_deleting_an_item_tells_the_others(app, db, items, monkeypatch):
    from hubra_inventory.services import InventoryService

    sent = []
    monkeypatch.setattr(
        "hubra_inventory.services.emit", lambda name, **kw: sent.append((name, kw))
    )
    InventoryService.delete(items[1].id, None)
    db.session.commit()
    assert sent == [("inventory.item.deleted", {"item_id": items[1].id})]


def test_the_deleted_event_has_a_contract(app, db):
    from hubra.core.contracts import registry

    offer = registry.get("inventory.item.deleted")
    assert offer is not None and offer.module_code == "inventory"


def test_widgets(app, db, items, seeded_db):
    member = db.session.query(Member).first()
    now = datetime.now(timezone.utc)
    db.session.add_all([
        InventoryCheckout(item_id=items[0].id, member_id=member.id,
                          expected_return_at=now - timedelta(days=1)),
        InventoryCheckout(item_id=items[1].id, member_id=member.id,
                          expected_return_at=now + timedelta(days=3)),
    ])
    db.session.commit()
    out = contracts.widget_data("inventory.checked_out", {"count": 1}, actor=contracts.SYSTEM)
    assert out["total"] == 2
    assert [i["label"] for i in out["items"]] == ["Laser cutter"]
    assert out["items"][0]["path"] == f"/app/inventory/{items[0].id}"
    stat = contracts.widget_data("inventory.overdue", {}, actor=contracts.SYSTEM)
    assert stat["value"] == 1
