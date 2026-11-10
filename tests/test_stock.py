"""Stock counts of consumables: counting, taking, the low-stock event."""

from __future__ import annotations

import pytest

from hubra.core import contracts
from hubra_inventory.models import InventoryHistoryEntry, InventoryItem

BASE = "/api/v1/inventory"


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(
        "hubra_inventory.stock.emit", lambda event, **kw: out.append((event, kw))
    )
    return out


@pytest.fixture
def beer(db, seeded_db):
    row = InventoryItem(name="Bier", category="Consumable", status="available",
                        stock=10, min_stock=3, unit="Flaschen")
    db.session.add(row)
    db.session.commit()
    return row


def _history(db, item):
    return db.session.query(InventoryHistoryEntry).filter_by(item_id=item.id).all()


def test_taking_reduces_the_stock_and_warns_once(app, db, beer, sent):
    out = contracts.call("inventory.stock.adjust", item_id=beer.id, delta=-6,
                         reason="Strichliste", actor=contracts.SYSTEM)
    assert out["stock"] == 4 and out["low_stock"] is False
    assert sent == []
    contracts.call("inventory.stock.adjust", item_id=beer.id, delta=-1, actor=contracts.SYSTEM)
    contracts.call("inventory.stock.adjust", item_id=beer.id, delta=-1, actor=contracts.SYSTEM)
    assert [e for e, _ in sent] == ["inventory.stock.low"]
    assert sent[0][1] == {"item_id": beer.id, "name": "Bier", "stock": 3,
                          "min_stock": 3, "unit": "Flaschen"}
    # Restocked above the level, then low again: a second warning.
    contracts.call("inventory.stock.adjust", item_id=beer.id, delta=24, actor=contracts.SYSTEM)
    contracts.call("inventory.stock.adjust", item_id=beer.id, delta=-24, actor=contracts.SYSTEM)
    assert len(sent) == 2
    actions = [h.action for h in _history(db, beer)]
    assert actions.count("stock_taken") == 4 and actions.count("stock_added") == 1


def test_an_item_without_count_stays_as_it_is(app, db, seeded_db, sent):
    row = InventoryItem(name="Drill", category="Tool", status="available")
    db.session.add(row)
    db.session.commit()
    out = contracts.call("inventory.stock.adjust", item_id=row.id, delta=-1, actor=contracts.SYSTEM)
    assert out["stock"] is None and _history(db, row) == [] and sent == []
    with pytest.raises(contracts.Refused):
        contracts.call("inventory.stock.adjust", item_id=99999, delta=-1, actor=contracts.SYSTEM)


def test_low_stock_widget(app, db, beer):
    assert contracts.widget_data("inventory.low_stock", {}, actor=contracts.SYSTEM)["total"] == 0
    beer.stock = 2
    db.session.commit()
    out = contracts.widget_data("inventory.low_stock", {}, actor=contracts.SYSTEM)
    assert out["total"] == 1 and out["items"][0]["sub"] == "2 / 3 Flaschen"


def test_stock_route_and_counting_by_hand(client, db, auth_headers, beer):
    resp = client.post(f"{BASE}/{beer.id}/stock", json={"delta": 12, "reason": "Lieferung"},
                       headers=auth_headers)
    assert resp.status_code == 200 and resp.get_json()["stock"] == 22
    resp = client.patch(f"{BASE}/{beer.id}", json={"stock": 20}, headers=auth_headers)
    body = resp.get_json()
    assert (body["stock"], body["min_stock"], body["unit"], body["low_stock"]) == (
        20, 3, "Flaschen", False,
    )
    notes = [(h.action, h.note) for h in _history(db, beer)]
    assert ("stock_added", "+12 · Lieferung") in notes and ("stock_counted", "22 → 20") in notes
    resp = client.post(f"{BASE}/{beer.id}/stock", json={"delta": "x"}, headers=auth_headers)
    assert resp.status_code == 400


def test_stock_route_needs_a_count(client, db, auth_headers, seeded_db):
    made = client.post(BASE, json={"name": "Saw", "category": "Tool"}, headers=auth_headers)
    resp = client.post(f"{BASE}/{made.get_json()['id']}/stock", json={"delta": 1},
                       headers=auth_headers)
    assert resp.status_code == 409


def test_a_consumable_is_made_through_the_api(client, db, auth_headers, seeded_db):
    resp = client.post(
        BASE,
        json={"name": "Kreide", "category": "Consumable", "stock": 3, "min_stock": 5, "unit": "Pack"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["category"] == "Consumable"
    assert body["stock"] == 3 and body["low_stock"] is True
