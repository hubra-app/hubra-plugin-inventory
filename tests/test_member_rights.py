"""What the member rights at "view" (checkout, checkin, instruct_self) allow:
oneself only. Lending to others, taking back others' loans and inducting
stay with the owner, the responsible person or an inventory manager."""

import pytest

from tests.settings.test_settings_kv import _login, _make_role_and_member

BASE = "/api/v1/inventory"
_MEMBER = [
    "inventory.items.read",
    "inventory.items.checkout",
    "inventory.items.checkin",
    "inventory.items.instruct_self",
]


@pytest.fixture
def people(client, app, db, seeded_db):
    app.test_cli_runner().invoke(args=["sync-permissions"])
    tier = seeded_db["tier"]
    anna = _make_role_and_member(db, tier, name="Anna", permission_keys=_MEMBER)
    ben = _make_role_and_member(db, tier, name="Ben", permission_keys=_MEMBER)
    mgr = _make_role_and_member(
        db, tier, name="Mara", permission_keys=[*_MEMBER, "inventory.items.update"]
    )
    loc = _make_role_and_member(
        db, tier, name="Leo",
        permission_keys=["inventory.items.read", "inventory.items.update.location"],
    )
    _login(client, "admin@test.ch")
    club = client.post(f"{BASE}/", json={"name": "Drill", "category": "Tool"}).get_json()
    bens = client.post(
        f"{BASE}/",
        json={"name": "Trailer", "category": "Item", "owner_id": ben.id, "visibility": "private"},
    ).get_json()
    machine = client.post(
        f"{BASE}/", json={"name": "Laser", "category": "Tool", "instruction_required": True}
    ).get_json()
    return {"anna": anna, "ben": ben, "mgr": mgr, "loc": loc,
            "club": club["id"], "bens": bens["id"], "machine": machine["id"]}


def _as(client, name):
    _login(client, f"{name}@test.ch")


def test_member_checks_out_to_themselves_only(client, people):
    url = f"{BASE}/{people['club']}/checkout"
    _as(client, "anna")
    r = client.post(url, json={"member_id": people["ben"].id})
    assert r.status_code == 403 and r.get_json()["error"] == "LEND_NOT_ALLOWED"
    assert client.post(url, json={"member_id": people["anna"].id}).status_code == 201


def test_manager_lends_to_others(client, people):
    _as(client, "mara")
    r = client.post(f"{BASE}/{people['club']}/checkout", json={"member_id": people["ben"].id})
    assert r.status_code == 201


def test_a_persons_item_is_lent_by_them(client, people):
    url = f"{BASE}/{people['bens']}/checkout"
    for who, member in (("anna", "anna"), ("mara", "mgr")):
        _as(client, who)
        r = client.post(url, json={"member_id": people[member].id})
        assert r.status_code == 403, who
    _as(client, "ben")
    assert client.post(url, json={"member_id": people["anna"].id}).status_code == 201


def test_checkin_own_loan_only(client, people):
    _as(client, "anna")
    client.post(f"{BASE}/{people['club']}/checkout", json={"member_id": people["anna"].id})
    _as(client, "ben")
    r = client.post(f"{BASE}/{people['club']}/checkin", json={})
    assert r.status_code == 403 and r.get_json()["error"] == "CHECKIN_NOT_ALLOWED"
    _as(client, "anna")
    assert client.post(f"{BASE}/{people['club']}/checkin", json={}).status_code == 200


def test_self_induction_off_by_default(client, app, people):
    url = f"{BASE}/{people['machine']}/instructions/self"
    _as(client, "anna")
    r = client.post(url)
    assert r.status_code == 403 and r.get_json()["error"] == "SELF_INDUCTION_OFF"
    assert client.get(f"{BASE}/{people['machine']}").get_json()["self_induction"] is False
    # and so the induction can't be skipped to borrow the machine
    r = client.post(f"{BASE}/{people['machine']}/checkout", json={"member_id": people["anna"].id})
    assert r.status_code == 409


def test_self_induction_when_the_club_allows_it(client, app, people, monkeypatch):
    import hubra.core.modules as modules

    real = modules.get_config
    monkeypatch.setattr(
        modules, "get_config",
        lambda code, *a, **k: {**real(code, *a, **k), "self_induction": True}
        if code == "inventory" else real(code, *a, **k),
    )
    _as(client, "anna")
    assert client.post(f"{BASE}/{people['machine']}/instructions/self").status_code == 204


def test_field_rights_change_only_their_fields(client, people):
    _as(client, "leo")
    r = client.patch(
        f"{BASE}/{people['club']}", json={"location": "Shelf 3", "name": "Renamed"}
    )
    assert r.status_code == 200
    body = r.get_json()
    assert body["location"] == "Shelf 3" and body["name"] == "Drill"
