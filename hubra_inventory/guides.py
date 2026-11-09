"""The usage guide of an item: /api/v1/inventory/<item_id>/guide.

Markdown and/or a link to a manual or video, one per item (``ItemGuide``).
Reading it takes the right to read the item, writing it the right to change
the item, so the item's owner and responsible person may too.

An item can name the qualification it takes. Qualifications is its own
plugin: its kinds and who holds them come from its queries
(``qualifications.kinds.list``, ``qualifications.member.holds``), never from
its tables or code. Without it the guide just shows no qualification. The
qualification is shown, not enforced: inductions still decide who may check
an item out.
"""

from __future__ import annotations

from flask import jsonify, request

from hubra.core.auth.helpers import get_current_member
from hubra.core.contracts import SYSTEM, ActionFailed, ActionUnavailable, query
from hubra.core.errors import api_error, raise_error
from hubra.core.extensions import db
from hubra.core.permissions import member_has_permission, permission_required
from hubra.core.utils import log_audit

from .models import InventoryItem, ItemGuide
from .routes import inventory_bp
from .services import item_access

MAX_GUIDE = 100_000
KINDS = "qualifications.kinds.list"
HOLDS = "qualifications.member.holds"


def _ask(name: str, **data) -> list[dict] | None:
    """Ask Qualifications; ``None`` when it isn't there or is switched off."""
    try:
        # The guide checks its own rights; managing qualifications isn't needed.
        return query(name, actor=SYSTEM, **data)
    except (ActionUnavailable, ActionFailed):
        return None


def _qualification(kind_id: int | None) -> dict | None:
    """The qualification the item takes, and whether the viewer holds it."""
    if not kind_id:
        return None
    kinds = _ask(KINDS, ids=[kind_id])
    if not kinds:
        return None
    member = get_current_member()
    mine = None
    if member is not None:
        held = _ask(HOLDS, member_id=member.id, kind_ids=[kind_id]) or []
        mine = next((h.get("state") for h in held if h["kind_id"] == kind_id), None)
    return {"id": kind_id, "name": kinds[0]["name"], "mine": mine}


def _live_item(item_id: int) -> InventoryItem:
    item = db.session.get(InventoryItem, item_id)
    if item is None or item.deleted_at is not None:
        raise_error(404, "NOT_FOUND", f"Inventory item {item_id} not found")
    return item  # type: ignore[return-value]


def _may_edit(item: InventoryItem) -> bool:
    """The same rule as saving: the club right, or the item's owner or
    responsible person."""
    member = get_current_member()
    if member is None:
        return False
    if member_has_permission(member, "inventory.items.update"):
        return True
    return bool(item_access("update")(member, item_id=item.id))


def _to_dict(item: InventoryItem, guide: ItemGuide | None) -> dict:
    return {
        "itemId": item.id,
        "itemName": item.name,
        "guide": (guide.guide if guide else None) or "",
        "guideUrl": guide.guide_url if guide else None,
        "instructionRequired": bool(item.instruction_required),
        "canEdit": _may_edit(item),
        "qualification": _qualification(guide.qualification_kind_id if guide else None),
    }


@inventory_bp.get("/<int:item_id>/guide")
@permission_required("items", "read", "View inventory", allow=item_access("read"))
def get_guide(item_id: int):
    item = _live_item(item_id)
    return jsonify(_to_dict(item, db.session.get(ItemGuide, item.id))), 200


@inventory_bp.get("/guide-qualifications")
@permission_required("items", "read", "View inventory")
def guide_qualifications():
    """The qualifications an item can take (empty without Qualifications)."""
    kinds = _ask(KINDS) or []
    return jsonify([{"id": k["id"], "name": k["name"]} for k in kinds]), 200


def _check(body: dict):
    """An error response for a bad body, or ``None``."""
    guide = body.get("guide")
    url = body.get("guide_url")
    if guide is not None and not isinstance(guide, str):
        return api_error("VALIDATION_ERROR", "guide must be text", 400)
    if guide and len(guide) > MAX_GUIDE:
        return api_error("VALIDATION_ERROR", "guide is too long", 400)
    if url:
        if not isinstance(url, str) or not url.startswith("https://"):
            return api_error(
                "VALIDATION_ERROR", "guide_url must start with https://", 400
            )
        if len(url) > 500:
            return api_error("VALIDATION_ERROR", "guide_url is too long", 400)
    qid = body.get("qualification_id")
    if qid is not None:
        # Only the club's own kinds are offered, never self-service ones.
        known = (
            isinstance(qid, int)
            and not isinstance(qid, bool)
            and bool(_ask(KINDS, ids=[qid]))
        )
        if not known:
            return api_error(
                "VALIDATION_ERROR",
                "qualification_id must be one of the club's qualifications",
                400,
            )
    return None


@inventory_bp.put("/<int:item_id>/guide")
@permission_required(
    "items", "update", "Update inventory items", allow=item_access("update")
)
def save_guide(item_id: int):
    body = request.get_json(silent=True) or {}
    error = _check(body)
    if error is not None:
        return error
    item = _live_item(item_id)
    row = db.session.get(ItemGuide, item.id)
    if row is None:
        row = ItemGuide(item_id=item.id)
        db.session.add(row)
    if "guide" in body:
        row.guide = (body.get("guide") or "").strip() or None
    if "guide_url" in body:
        row.guide_url = (body.get("guide_url") or "").strip() or None
    if "qualification_id" in body:
        row.qualification_kind_id = body.get("qualification_id")
    member = get_current_member()
    log_audit(
        member.id if member else None,
        "update_guide",
        "InventoryItem",
        item.id,
        item.name,
    )
    db.session.commit()
    return jsonify(_to_dict(item, row)), 200
