"""Inventory tests that lived in Hubra's own suite before Inventory became a
plugin: permissions, bad input, and the module setting for due dates."""

from datetime import datetime, timezone

from hubra_inventory.models import InventoryItem
from hubra_inventory.services import InventoryService
from tests.settings.test_settings_kv import _login, _make_role_and_member

BASE = "/api/v1/inventory/"


def _as_member_with(client, db, seeded_db, name, keys):
    _make_role_and_member(db, seeded_db["tier"], name=name, permission_keys=keys)
    _login(client, f"{name}@test.ch")


def test_reading_needs_the_read_right(client, db, seeded_db):
    _as_member_with(client, db, seeded_db, "Rita", ["inventory.items.read"])
    assert client.get(BASE).status_code == 200
    _as_member_with(client, db, seeded_db, "Nora", ["members.members.read"])
    assert client.get(BASE).status_code == 403


def test_adding_needs_the_create_right(client, db, seeded_db):
    _as_member_with(client, db, seeded_db, "Rita", ["inventory.items.read"])
    item = {"name": "Hammer", "category": "Tool"}
    assert client.post(BASE, json=item).status_code == 403
    _as_member_with(client, db, seeded_db, "Carl", ["inventory.items.create"])
    assert client.post(BASE, json=item).status_code == 201


def test_system_permissions_list_the_inventory_keys(client, seeded_db, auth_headers):
    data = client.get("/api/v1/system/permissions", headers=auth_headers).get_json()
    keys = {e["key"] for e in data if "/inventory" in e["path"]}
    assert {"inventory.items.read", "inventory.items.create"} <= keys
    assert not keys & {"groups.groups.read", "events.events.read"}


def test_create_own_and_field_rights_come_from_the_plugin(app):
    try:  # Hubra moved these into hubra.core
        from hubra.core.fields import iter_field_perms
        from hubra.core.permissions import extra_permissions
    except ImportError:
        from hubra.api.fields import iter_field_perms
        from hubra.api.permissions import extra_permissions

    with app.app_context():
        extra = {p["key"]: p for p in extra_permissions()}
        fields = {p["key"] for p in iter_field_perms()}
    assert extra["inventory.items.create_own"]["blueprint"] == "inventory_bp"
    assert "inventory.items.update.owner_id" in fields


def test_checkout_without_member_is_a_400(client, auth_headers, db):
    item = InventoryItem(name="Bohrer", category="Tool")
    db.session.add(item)
    db.session.commit()
    resp = client.post(f"{BASE}{item.id}/checkout", json={}, headers=auth_headers)
    assert resp.status_code == 400


def test_checkin_notes_must_be_text(client, seeded_db, auth_headers):
    iid = client.post(BASE, json={"name": "Drill", "category": "Tool"}).get_json()["id"]
    member_id = seeded_db["admin"].id
    client.post(f"{BASE}{iid}/checkout", json={"member_id": member_id})
    resp = client.post(f"{BASE}{iid}/checkin", json={"condition_notes": {"x": 1}})
    assert resp.status_code == 400


def test_checkout_uses_module_setting_for_due_date(db, seeded_db):
    item = InventoryItem(name="Drill", category="Tool", status="available")
    db.session.add(item)
    db.session.commit()
    checkout = InventoryService.checkout(item.id, seeded_db["admin"].id)
    due = checkout.expected_return_at
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    assert 13 <= (due - datetime.now(timezone.utc)).days <= 14


def test_item_ids_the_app_reads_are_in_the_answer(client, db, auth_headers, seeded_db):
    admin_id = seeded_db["admin"].id
    db.session.add(
        InventoryItem(
            name="Bohrer", category="Tool", owner_id=admin_id, responsible_id=admin_id
        )
    )
    db.session.commit()
    body = client.get(BASE, headers=auth_headers).get_json()
    rows = body.get("data", body) if isinstance(body, dict) else body
    assert (rows[0]["owner_id"], rows[0]["responsible_id"]) == (admin_id, admin_id)


def test_deleting_a_member_clears_their_inventory_links(
    client, auth_headers, db, seeded_db
):
    """Club schemas have no foreign keys, so Hubra's member delete applies the
    ondelete rules the plugin's models declare: checkouts go, items stay."""
    from hubra.api.members.services import MemberService
    from hubra_inventory.models import InventoryCheckout

    from tests.helpers import add_member

    member_id = add_member(
        client, auth_headers, first_name="Gina", last_name="Gone", email="gone@test.ch"
    ).get_json()["id"]
    item = InventoryItem(name="Bohrer", category="Tool", responsible_id=member_id)
    db.session.add(item)
    db.session.flush()
    db.session.add(InventoryCheckout(item_id=item.id, member_id=member_id))
    db.session.commit()
    item_id = item.id
    client.post(f"/api/v1/members/{member_id}/archive", headers=auth_headers)

    MemberService.delete_permanent(member_id, seeded_db["admin"].id)

    assert (
        db.session.query(InventoryCheckout).filter_by(member_id=member_id).count() == 0
    )
    db.session.expire_all()
    assert db.session.get(InventoryItem, item_id).responsible_id is None
    db.session.rollback()
