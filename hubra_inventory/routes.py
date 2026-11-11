"""Inventory blueprint — CRUD for InventoryItem + instruction tracking."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from hubra.core.auth.helpers import get_current_member
from marshmallow import ValidationError
from hubra.core.permissions import (
    can_update,
    filter_updatable_fields,
    member_has_permission,
    member_is_admin,
    permission_required,
)
from hubra.core.errors import api_error, raise_error
from hubra.core.extensions import db
from hubra.core.models.member import Member
from .schemas import (
    InventoryItemCreateSchema,
    InventoryItemSchema,
    InventoryItemUpdateSchema,
    InventoryCheckoutSchema,
    CheckoutCreateSchema,
)
from .services import (
    InventoryService,
    InventoryServiceItems,
    checkin_access,
    checkout_access,
    item_access,
    item_history,
    item_relation,
)

inventory_bp = Blueprint("inventory_bp", __name__)

_item_schema = InventoryItemSchema()
_items_schema = InventoryItemSchema(many=True)
_create_schema = InventoryItemCreateSchema()
_update_schema = InventoryItemUpdateSchema()

# Object-level rights: the owner or responsible person of an item passes
# these routes without the club-wide right (see services.ITEM_ACTIONS).
_CREATE_OWN = "inventory.items.create_own"


def _by_object() -> bool:
    """True when the request passed as the item's owner or responsible
    person rather than through a role."""
    return g.get("permission_scope") == "object"


def _check_people(data: dict, item=None) -> None:
    """404 for an owner or responsible person who isn't a current member
    (a wrong id was a database error, 500). Unchanged values pass."""
    for field in ("owner_id", "responsible_id"):
        mid = data.get(field)
        if mid is None or (item is not None and getattr(item, field) == mid):
            continue
        person = db.session.get(Member, mid)
        if person is None or person.archived_at is not None:
            raise_error(404, "NOT_FOUND", f"Member {mid} not found")


_UPDATE = "inventory.items.update"
_MANAGE_INSTRUCTIONS = "inventory.items.manage_instructions"


def _relation(item, member) -> str | None:
    return item_relation(item.owner_id, item.responsible_id, member.id)


def _may_lend(item, member) -> bool:
    """Lend the item to someone else or take it back from them: the owner,
    the responsible person, or whoever manages the inventory. The checkout
    and check-in rights alone (every member at "view") are for oneself."""
    if _relation(item, member):
        return True
    if item.visibility == "private" and item.owner_id is not None:
        # A person's item is lent by them (or the person looking after it).
        return member_is_admin(member)
    return member_has_permission(member, _UPDATE)


def _may_create_own(member, **_):
    return "own" if member_has_permission(member, _CREATE_OWN) else None


# ── GET /inventory ────────────────────────────────────────────────────────────


@inventory_bp.get("/")
@permission_required("items", "read", "View inventory")
def list_items():
    args = request.args
    items = InventoryServiceItems.list(
        category=args.get("category", "").strip(),
        status=args.get("status", "").strip(),
        visibility=args.get("visibility", "").strip(),
    )
    return jsonify(_items_schema.dump(items)), 200


# ── GET /inventory/<id> ───────────────────────────────────────────────────────


@inventory_bp.get("/<int:item_id>")
@permission_required("items", "read", "View inventory", allow=item_access("read"))
def get_item(item_id: int):
    from hubra.core.modules import get_config

    item = InventoryService.get(item_id)
    out = _item_schema.dump(item)
    # Whether "Mark myself as inducted" is offered (the self_induction setting).
    out["self_induction"] = bool(get_config("inventory").get("self_induction"))
    return jsonify(out), 200


@inventory_bp.get("/<int:item_id>/history")
@permission_required("items", "read", "View inventory", allow=item_access("read"))
def get_item_history(item_id: int):
    """Checkouts and what add-ons recorded (Keys: handovers), newest first."""
    InventoryService.get(item_id)
    return jsonify(item_history(item_id)), 200


# ── POST /inventory ───────────────────────────────────────────────────────────


@inventory_bp.post("/")
@permission_required("items", "create", "Create inventory items", allow=_may_create_own)
def create_item():
    body = request.get_json(silent=True) or {}
    try:
        data = _create_schema.load(body)
    except ValidationError as exc:
        return api_error("VALIDATION_ERROR", str(exc.messages), 400)
    if _by_object():
        # With only "add own items", the item is always the member's own.
        data["owner_id"] = get_current_member().id
    _check_people(data)

    item = InventoryServiceItems.create(data, get_current_member().id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify(_item_schema.dump(item)), 201


# ── PATCH /inventory/<id> ─────────────────────────────────────────────────────


@inventory_bp.patch("/<int:item_id>")
@can_update(
    "items",
    "Update inventory items",
    allow=item_access("update"),
    allow_fields=frozenset(InventoryItemUpdateSchema().fields),
)
def update_item(item_id: int):
    item = InventoryService.get(item_id)

    body = request.get_json(silent=True) or {}
    try:
        data = _update_schema.load(body)
    except ValidationError as exc:
        return api_error("VALIDATION_ERROR", str(exc.messages), 400)
    # A role with only some field rights (inventory.items.update.location)
    # changes only those fields; the rest of the form is left as it is.
    data = filter_updatable_fields(data)
    if _by_object() and g.object_access != "owner":
        InventoryService.check_owner_fields(item, data)
    InventoryService.check_person_owned(item, get_current_member().id, data)
    _check_people(data, item)

    InventoryService.update(item, data, get_current_member().id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    db.session.refresh(item)
    item = InventoryService.get(item.id)
    return jsonify(_item_schema.dump(item)), 200


# ── POST /inventory/<id>/stock ────────────────────────────────────────────────


@inventory_bp.post("/<int:item_id>/stock")
@permission_required(
    "items", "update", "Update inventory items", allow=item_access("update")
)
def adjust_item_stock(item_id: int):
    """{delta, reason?}: add some (restocked) or take some of a counted item."""
    from .stock import adjust_stock

    item = InventoryService.get(item_id)
    body = request.get_json(silent=True) or {}
    delta = body.get("delta")
    if isinstance(delta, bool) or not isinstance(delta, int) or not -9999 <= delta <= 9999 or delta == 0:
        return api_error("VALIDATION_ERROR", "delta must be a whole number from -9999 to 9999, not 0", 400)
    if item.stock is None:
        return api_error("NOT_COUNTED", "This item has no stock count; set one first", 409)
    reason = body.get("reason")
    reason = str(reason).strip()[:200] if reason else None
    adjust_stock(item, delta, get_current_member().id, reason)
    db.session.commit()
    item = InventoryService.get(item.id)
    return jsonify(_item_schema.dump(item)), 200


# ── DELETE /inventory/<id> ────────────────────────────────────────────────────


@inventory_bp.delete("/<int:item_id>")
@permission_required(
    "items", "delete", "Delete inventory items", allow=item_access("delete")
)
def delete_item(item_id: int):
    InventoryService.check_person_owned(
        InventoryService.get(item_id), get_current_member().id
    )
    InventoryService.delete(item_id, get_current_member().id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return "", 204


# ── POST /inventory/<id>/instructions/<member_id> ─────────────────────────────


@inventory_bp.post("/<int:item_id>/instructions/<int:member_id>")
@permission_required(
    "items",
    "manage_instructions",
    "Manage item instructions",
    allow=item_access("manage_instructions"),
)
def add_instruction(item_id: int, member_id: int):
    item = InventoryService.get(item_id)

    member = db.session.get(Member, member_id)
    if member is None:
        raise_error(404, "NOT_FOUND", f"Member {member_id} not found")
        return

    InventoryService.add_instruction(item, member, get_current_member().id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return "", 204


# ── POST /inventory/<id>/checkout ────────────────────────────────────────────


@inventory_bp.post("/<int:item_id>/checkout")
@permission_required(
    "items", "checkout", "Check out inventory items", allow=checkout_access
)
def checkout_item(item_id: int):
    body = request.get_json(silent=True) or {}
    try:
        data = CheckoutCreateSchema().load(body)
    except ValidationError as exc:
        return api_error("VALIDATION_ERROR", str(exc.messages), 400)

    me = get_current_member()
    if not _by_object():
        item = InventoryService.get(item_id)
        if (data["member_id"] != me.id or item.visibility == "private") and not _may_lend(item, me):
            raise_error(
                403,
                "LEND_NOT_ALLOWED",
                "You can check out items to yourself; the owner, the responsible "
                "person or an inventory manager lends them to others",
            )

    checkout = InventoryService.checkout(
        item_id=item_id,
        member_id=data["member_id"],
        expected_return_at=data.get("expected_return_at"),
        condition_notes=data.get("condition_notes"),
        actor_id=get_current_member().id,
    )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify(InventoryCheckoutSchema().dump(checkout)), 201


# ── POST /inventory/<id>/checkin ─────────────────────────────────────────────


@inventory_bp.post("/<int:item_id>/checkin")
@permission_required(
    "items", "checkin", "Check in inventory items", allow=checkin_access
)
def checkin_item(item_id: int):
    body = request.get_json(silent=True) or {}
    condition_notes = body.get("condition_notes")
    if condition_notes is not None and (
        not isinstance(condition_notes, str) or len(condition_notes) > 20000
    ):
        return api_error("VALIDATION_ERROR", "condition_notes must be text (20000 characters at most)", 400)

    if not _by_object():
        me = get_current_member()
        item = InventoryService.get(item_id)
        if InventoryService.borrower(item_id) != me.id and not _may_lend(item, me):
            raise_error(
                403,
                "CHECKIN_NOT_ALLOWED",
                "You can check in what you borrowed; the owner, the responsible "
                "person or an inventory manager takes back the rest",
            )

    checkout = InventoryService.checkin(
        item_id=item_id,
        condition_notes=condition_notes,
        actor_id=get_current_member().id,
    )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify(InventoryCheckoutSchema().dump(checkout)), 200


# ── GET /inventory/overdue ───────────────────────────────────────────────────


@inventory_bp.get("/overdue")
@permission_required("items", "read", "View inventory")
def list_overdue():
    overdues = InventoryService.list_overdue()
    return jsonify(InventoryCheckoutSchema(many=True).dump(overdues)), 200


# ── DELETE /inventory/<id>/instructions/<member_id> ───────────────────────────


@inventory_bp.delete("/<int:item_id>/instructions/<int:member_id>")
@permission_required(
    "items",
    "manage_instructions",
    "Manage item instructions",
    allow=item_access("manage_instructions"),
)
def remove_instruction(item_id: int, member_id: int):
    InventoryService.remove_instruction(item_id, member_id, get_current_member().id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return "", 204


# ── POST /inventory/<id>/instructions/self ────────────────────────────────────


@inventory_bp.post("/<int:item_id>/instructions/self")
@permission_required("items", "instruct_self", "Add self-instruction for items")
def add_self_instruction(item_id: int):
    from hubra.core.modules import get_config

    member_id = get_current_member().id
    item = InventoryService.get(item_id)
    # An induction is someone checking that you can use the machine safely.
    # Confirming it yourself is off unless the club switches it on.
    if not get_config("inventory").get("self_induction") and not member_has_permission(
        get_current_member(), _MANAGE_INSTRUCTIONS
    ):
        raise_error(
            403,
            "SELF_INDUCTION_OFF",
            "Ask the owner, the responsible person or an inventory manager to induct you",
        )

    from hubra.core.models.member import Member as MemberModel

    member = db.session.get(MemberModel, member_id)
    if member is None:
        raise_error(404, "NOT_FOUND", f"Member {member_id} not found")
        return

    InventoryService.add_instruction(item, member, get_current_member().id)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return "", 204
