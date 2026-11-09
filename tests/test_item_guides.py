"""The usage guide per item (moved here from the Guides plugin in 2.4).

The qualification an item takes comes from the Qualifications plugin's
queries; these tests stand in for it by replacing ``guides._ask``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hubra_inventory import guides
from hubra_inventory.models import ItemGuide


@pytest.fixture
def item(client, auth_headers, db, seeded_db):
    resp = client.post(
        "/api/v1/inventory/",
        json={"name": "Laser cutter", "category": "Tool", "status": "available"},
    )
    assert resp.status_code == 201, resp.get_json()
    return SimpleNamespace(id=resp.get_json()["id"])


@pytest.fixture
def qualifications(monkeypatch):
    """Qualifications with one club kind, "Laser induction" (id 7), that the
    viewer holds until soon."""

    def ask(name, **data):
        if name == guides.KINDS:
            kinds = [{"id": 7, "name": "Laser induction", "valid_months": 24}]
            ids = data.get("ids")
            return [k for k in kinds if ids is None or k["id"] in ids]
        if name == guides.HOLDS:
            return [
                {"kind_id": k, "state": "soon", "expires_on": None}
                for k in data["kind_ids"]
                if k == 7
            ]
        raise AssertionError(name)

    monkeypatch.setattr(guides, "_ask", ask)


def test_save_and_read_guide(client, auth_headers, item):
    resp = client.put(
        f"/api/v1/inventory/{item.id}/guide",
        json={
            "guide": "# Safety\nWear goggles.",
            "guide_url": "https://drive.google.com/x",
        },
    )
    assert resp.status_code == 200, resp.get_json()
    got = client.get(f"/api/v1/inventory/{item.id}/guide").get_json()
    assert got["guide"].startswith("# Safety")
    assert got["guideUrl"] == "https://drive.google.com/x"
    assert got["qualification"] is None
    assert got["canEdit"] is True


def test_guide_url_must_be_https_and_short(client, auth_headers, item):
    put = lambda body: client.put(f"/api/v1/inventory/{item.id}/guide", json=body)  # noqa: E731
    assert put({"guide_url": "http://x"}).status_code == 400
    assert put({"guide_url": "https://example.org/" + "a" * 500}).status_code == 400


def test_a_deleted_or_unknown_item_has_no_guide(client, auth_headers, item):
    client.put(f"/api/v1/inventory/{item.id}/guide", json={"guide": "steps"})
    assert client.delete(f"/api/v1/inventory/{item.id}").status_code in (200, 204)
    assert client.get(f"/api/v1/inventory/{item.id}/guide").status_code == 404
    put = client.put(f"/api/v1/inventory/{item.id}/guide", json={"guide": "x"})
    assert put.status_code == 404
    assert client.get("/api/v1/inventory/99999/guide").status_code == 404


def test_the_item_api_does_not_carry_the_guide(client, auth_headers, item, db):
    db.session.add(ItemGuide(item_id=item.id, guide="secret steps"))
    db.session.commit()
    body = client.get(f"/api/v1/inventory/{item.id}").get_json()
    assert "secret steps" not in str(body)


def test_without_qualifications_no_qualification_can_be_named(
    client, auth_headers, item
):
    assert client.get("/api/v1/inventory/guide-qualifications").get_json() == []
    resp = client.put(
        f"/api/v1/inventory/{item.id}/guide", json={"qualification_id": 7}
    )
    assert resp.status_code == 400


def test_the_guide_names_the_qualification_and_whether_i_hold_it(
    client, auth_headers, item, qualifications
):
    kinds = client.get("/api/v1/inventory/guide-qualifications").get_json()
    assert kinds == [{"id": 7, "name": "Laser induction"}]
    bad = client.put(f"/api/v1/inventory/{item.id}/guide", json={"qualification_id": 8})
    assert bad.status_code == 400
    resp = client.put(
        f"/api/v1/inventory/{item.id}/guide",
        json={"guide": "steps", "qualification_id": 7},
    )
    assert resp.status_code == 200
    got = client.get(f"/api/v1/inventory/{item.id}/guide").get_json()
    assert got["qualification"] == {"id": 7, "name": "Laser induction", "mine": "soon"}
    cleared = client.put(
        f"/api/v1/inventory/{item.id}/guide", json={"qualification_id": None}
    )
    assert cleared.get_json()["qualification"] is None
