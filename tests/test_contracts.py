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


def _two_members(db, seeded_db):
    from hubra.core.models.user import User

    out = []
    for email in ("anna@test.ch", "ben@test.ch"):
        user = User(email=email, first_name="Test", last_name="Member")
        user.set_password("password123")
        db.session.add(user)
        db.session.flush()
        m = Member(user_id=user.id, status="active", tier_id=seeded_db["tier"].id)
        db.session.add(m)
        db.session.flush()
        out.append(m)
    db.session.commit()
    return out


def test_lending_to_the_club(app, db, seeded_db):
    """A member's own thing they lend to the club becomes an item that
    stays theirs (Community moves its old "lends" entries over with this)."""
    anna, other = _two_members(db, seeded_db)
    got = contracts.call(
        "inventory.items.lend",
        member_id=anna.id,
        name="Car trailer",
        description="  1.5 t, needs a tow bar  ",
        actor=contracts.SYSTEM,
    )
    assert got["lent_by"] == anna.id and got["category"] == "Item"
    row = db.session.get(InventoryItem, got["id"])
    assert (row.owner_id, row.visibility, row.status) == (anna.id, "private", "available")
    assert row.description == "1.5 t, needs a tow bar"
    # Club items are not lent by anyone.
    club = InventoryItem(name="Drill", category="Tool", status="available")
    db.session.add(club)
    db.session.commit()
    assert contracts.query("inventory.items.get", ids=[club.id],
                           actor=contracts.SYSTEM)[0]["lent_by"] is None

    with pytest.raises(contracts.Refused):
        contracts.call("inventory.items.lend", member_id=999999, name="x",
                       actor=contracts.SYSTEM)


def test_members_lend_only_their_own_things(app, db, seeded_db, monkeypatch):
    anna, other = _two_members(db, seeded_db)
    monkeypatch.setattr("hubra.core.permissions.member_has_permission",
                        lambda member, perm: True)
    with pytest.raises(contracts.Refused):
        contracts.call("inventory.items.lend", member_id=other.id, name="Beamer",
                       actor=anna)
    got = contracts.call("inventory.items.lend", member_id=anna.id, name="Beamer",
                         actor=anna)
    assert got["lent_by"] == anna.id
