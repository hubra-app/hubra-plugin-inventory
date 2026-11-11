"""Fixes from the security audit of 2026-11-11."""

from __future__ import annotations

import pytest

from hubra.core import contracts
from hubra.core.models.member import Member
from hubra_inventory.models import InventoryItem

BASE = "/api/v1/inventory"


def _create(client, auth_headers, **kw):
    return client.post(
        f"{BASE}/", json={"name": "Drill", "category": "Tool", **kw}, headers=auth_headers
    )


@pytest.mark.parametrize(
    "url",
    ["javascript:alert(1)", " JaVaScRiPt:alert(1)", "java\tscript:alert(1)", "data:text/html,x", "vbscript:x"],
)
def test_links_refuse_script_urls(client, auth_headers, seeded_db, url):
    resp = _create(client, auth_headers, links=[{"label": "x", "url": url}])
    assert resp.status_code == 400
    resp = _create(client, auth_headers, documents=[{"name": "x", "url": url}])
    assert resp.status_code == 400
    resp = _create(client, auth_headers, image_url=url)
    assert resp.status_code == 400


def test_links_keep_web_mail_and_app_addresses(client, auth_headers, seeded_db):
    links = [
        {"label": "Shop", "url": "https://example.ch/x"},
        {"label": "Mail", "url": "mailto:a@b.ch"},
        {"label": "Guide", "url": "/app/guides/1"},
        {"label": "", "url": ""},
    ]
    resp = _create(client, auth_headers, links=links)
    assert resp.status_code == 201, resp.get_json()
    assert [l["url"] for l in resp.get_json()["links"]] == [l["url"] for l in links]

    item_id = resp.get_json()["id"]
    resp = client.patch(
        f"{BASE}/{item_id}",
        json={"links": [{"label": "x", "url": "javascript:alert(1)"}]},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_too_many_links_and_long_fields(client, auth_headers, seeded_db):
    many = [{"label": "x", "url": "https://a.ch"}] * 51
    assert _create(client, auth_headers, links=many).status_code == 400
    assert _create(client, auth_headers, location="x" * 256).status_code == 400


def test_new_item_cannot_start_checked_out(client, auth_headers, seeded_db):
    assert _create(client, auth_headers, status="checked_out").status_code == 400


def test_unknown_owner_is_404_not_500(client, auth_headers, seeded_db):
    resp = _create(client, auth_headers, owner_id=999999)
    assert resp.status_code == 404
    item_id = _create(client, auth_headers).get_json()["id"]
    resp = client.patch(
        f"{BASE}/{item_id}", json={"responsible_id": 999999}, headers=auth_headers
    )
    assert resp.status_code == 404


def _person_item(db, owner_id):
    item = InventoryItem(
        name="Trailer", category="Item", status="available",
        owner_id=owner_id, visibility="private",
    )
    db.session.add(item)
    db.session.commit()
    return item


def _ctx(actor=None, system=False):
    return contracts.CallContext(
        tenant_id=None, name="t", caller="test", actor=actor, system=system
    )


def _other_member(db, seeded_db):
    from hubra.core.models.user import User

    user = User(email="other@inv.ch", first_name="O", last_name="Ther")
    user.set_password("pw")
    db.session.add(user)
    db.session.flush()
    m = Member(user_id=user.id, status="active")
    m.tier_id = seeded_db["tier"].id
    db.session.add(m)
    db.session.commit()
    return m


def test_delete_action_keeps_a_persons_item(app, db, seeded_db):
    from hubra_inventory.contracts import DeleteIn, delete_item

    owner = seeded_db["admin"]
    other = _other_member(db, seeded_db)
    item = _person_item(db, owner.id)

    # Someone else, even naming the owner as actor_id, is refused.
    with pytest.raises(contracts.Refused):
        delete_item(_ctx(other), DeleteIn(item_id=item.id, actor_id=owner.id))
    assert db.session.get(InventoryItem, item.id) is not None

    # The owner may, and so may the system (an add-on's own check).
    assert delete_item(_ctx(owner), DeleteIn(item_id=item.id)).deleted is True
    item2 = _person_item(db, owner.id)
    assert delete_item(_ctx(system=True), DeleteIn(item_id=item2.id)).deleted is True


def test_actor_id_only_counts_for_the_system(app, db, seeded_db):
    from hubra_inventory.contracts import _actor_id

    me = seeded_db["admin"]
    assert _actor_id(_ctx(me), me.id + 1) == me.id
    assert _actor_id(_ctx(system=True), 42) == 42


def test_stock_adjust_reads_the_current_count(app, db, client, auth_headers, seeded_db):
    item_id = _create(client, auth_headers, stock=10).get_json()["id"]
    item = db.session.get(InventoryItem, item_id)
    # Another request took 3 meanwhile; this session still holds 10.
    db.session.execute(
        InventoryItem.__table__.update().where(InventoryItem.id == item_id).values(stock=7)
    )
    from hubra_inventory.stock import adjust_stock

    assert item.stock == 10
    adjust_stock(item, -1, None)
    assert item.stock == 6
