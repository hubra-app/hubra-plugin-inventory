"""Marshmallow schemas for InventoryItem and InventoryCheckout."""

import re

from marshmallow import EXCLUDE, RAISE, ValidationError, fields, validate

from hubra.core.extensions import ma
from .models import _CATEGORIES, InventoryItem

_STATUSES = [
    "available",
    "in_use",
    "maintenance",
    "broken",
    "archived",
    "checked_out",
    "pending",
    "lost",
    "retired",
]
_VISIBILITIES = ["private", "shared"]

# Links and documents end up as <a href> in the app: only web and mail
# addresses, never javascript: or data: (stored XSS against whoever opens
# the item). Browsers ignore control characters and spaces in a scheme, so
# those are dropped before looking at it.
_SAFE_SCHEMES = ("http", "https", "mailto")
_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")
_MAX_URL = 2000
_MAX_LIST = 50
_MAX_TEXT = 20000


def _check_url(value: str) -> None:
    if len(value) > _MAX_URL:
        raise ValidationError(f"URL longer than {_MAX_URL} characters")
    m = _SCHEME.match(re.sub(r"[\x00-\x20\x7f]", "", value))
    if m and m.group(1).lower() not in _SAFE_SCHEMES:
        raise ValidationError("Only http, https and mailto links are allowed")


class SafeUrl(fields.Str):
    """A link target: http(s), mailto or a path in the app."""

    def _deserialize(self, value, attr, data, **kwargs):
        value = super()._deserialize(value, attr, data, **kwargs).strip()
        _check_url(value)
        return value


class _LinkSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    label = fields.Str(load_default="", validate=validate.Length(max=200))
    url = SafeUrl(required=True)


class _DocumentSchema(ma.Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(load_default="", validate=validate.Length(max=200))
    url = SafeUrl(required=True)
    type = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=50))


def _links(**kw):
    return fields.List(
        fields.Nested(_LinkSchema), validate=validate.Length(max=_MAX_LIST), **kw
    )


def _documents(**kw):
    return fields.List(
        fields.Nested(_DocumentSchema), validate=validate.Length(max=_MAX_LIST), **kw
    )


_LONG = validate.Length(max=_MAX_TEXT)
_SHORT = validate.Length(max=255)


class InventoryItemSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = InventoryItem
        load_instance = True
        unknown = EXCLUDE
        # The guide belongs to the inventory.guides module (/guides API).
        exclude = ("instructed_members", "checkouts")

    cost = fields.Decimal(as_string=True, allow_none=True)
    purchase_cost = fields.Decimal(as_string=True, allow_none=True, dump_default=None)
    current_value = fields.Decimal(as_string=True, allow_none=True, dump_default=None)

    # Auto schemas leave foreign keys out; the club app needs these.
    owner_id = fields.Int(dump_only=True, allow_none=True)
    responsible_id = fields.Int(dump_only=True, allow_none=True)
    holder_id = fields.Int(dump_only=True, allow_none=True)
    holder_name = fields.Method("get_holder_name", dump_only=True)
    owner_name = fields.Method("get_owner_name", dump_only=True)
    responsible_name = fields.Method("get_responsible_name", dump_only=True)
    instructed_member_ids = fields.Method("get_instructed_ids", dump_only=True)
    instructed_member_names = fields.Method("get_instructed_names", dump_only=True)

    # M5 new fields
    purchase_date = fields.Date(allow_none=True, dump_default=None)
    location = fields.Str(allow_none=True, dump_default=None)
    serial_number = fields.Str(allow_none=True, dump_default=None)
    stock = fields.Int(allow_none=True, dump_default=None)
    min_stock = fields.Int(allow_none=True, dump_default=None)
    unit = fields.Str(allow_none=True, dump_default=None)
    low_stock = fields.Method("get_low_stock", dump_only=True)
    barcode_id = fields.Str(allow_none=True, dump_default=None)
    documents = fields.List(fields.Dict(), dump_default=list)
    image_url = fields.Str(allow_none=True, dump_default=None)
    notes = fields.Str(allow_none=True, dump_default=None)
    deleted_at = fields.DateTime(allow_none=True, dump_only=True, dump_default=None)

    def get_low_stock(self, obj):
        from .stock import is_low

        return is_low(obj)

    def get_owner_name(self, obj):
        return obj.owner.name if obj.owner else None

    def get_responsible_name(self, obj):
        return obj.responsible.name if obj.responsible else None

    def get_holder_name(self, obj):
        return obj.holder.name if obj.holder else None

    def get_instructed_ids(self, obj):
        return [m.id for m in (obj.instructed_members or [])]

    def get_instructed_names(self, obj):
        return [m.name for m in (obj.instructed_members or [])]


class InventoryItemCreateSchema(ma.Schema):
    class Meta:
        unknown = RAISE

    name = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    category = fields.Str(required=True, validate=validate.OneOf(_CATEGORIES))
    description = fields.Str(allow_none=True, load_default=None, validate=_LONG)
    owner_id = fields.Int(allow_none=True, load_default=None)
    responsible_id = fields.Int(allow_none=True, load_default=None)
    visibility = fields.Str(
        load_default="shared", validate=validate.OneOf(_VISIBILITIES)
    )
    # "checked_out" comes from a checkout only: an item created as out had
    # no checkout to check in and could never be made available again.
    status = fields.Str(
        load_default="available",
        validate=validate.OneOf([s for s in _STATUSES if s != "checked_out"]),
    )
    cost = fields.Decimal(allow_none=True, load_default=None)
    links = _links(load_default=list)
    instruction_required = fields.Bool(load_default=False)
    purchase_date = fields.Date(allow_none=True, load_default=None)
    purchase_cost = fields.Decimal(allow_none=True, load_default=None)
    current_value = fields.Decimal(allow_none=True, load_default=None)
    location = fields.Str(allow_none=True, load_default=None, validate=_SHORT)
    serial_number = fields.Str(allow_none=True, load_default=None, validate=_SHORT)
    stock = fields.Int(allow_none=True, load_default=None, validate=validate.Range(min=-99999, max=999999))
    min_stock = fields.Int(allow_none=True, load_default=None, validate=validate.Range(min=0, max=999999))
    unit = fields.Str(allow_none=True, load_default=None, validate=validate.Length(max=30))
    barcode_id = fields.Str(allow_none=True, load_default=None, validate=_SHORT)
    documents = _documents(load_default=list)
    image_url = SafeUrl(allow_none=True, load_default=None, validate=validate.Length(max=500))
    notes = fields.Str(allow_none=True, load_default=None, validate=_LONG)


class InventoryItemUpdateSchema(ma.Schema):
    """PATCH — all fields optional."""

    class Meta:
        unknown = RAISE

    name = fields.Str(validate=validate.Length(min=1, max=255))
    category = fields.Str(validate=validate.OneOf(_CATEGORIES))
    description = fields.Str(allow_none=True, validate=_LONG)
    owner_id = fields.Int(allow_none=True)
    responsible_id = fields.Int(allow_none=True)
    visibility = fields.Str(validate=validate.OneOf(_VISIBILITIES))
    status = fields.Str(validate=validate.OneOf(_STATUSES))
    cost = fields.Decimal(allow_none=True)
    links = _links()
    instruction_required = fields.Bool()
    purchase_date = fields.Date(allow_none=True)
    purchase_cost = fields.Decimal(allow_none=True)
    current_value = fields.Decimal(allow_none=True)
    location = fields.Str(allow_none=True, validate=_SHORT)
    serial_number = fields.Str(allow_none=True, validate=_SHORT)
    stock = fields.Int(allow_none=True, validate=validate.Range(min=-99999, max=999999))
    min_stock = fields.Int(allow_none=True, validate=validate.Range(min=0, max=999999))
    unit = fields.Str(allow_none=True, validate=validate.Length(max=30))
    barcode_id = fields.Str(allow_none=True, validate=_SHORT)
    documents = _documents()
    image_url = SafeUrl(allow_none=True, validate=validate.Length(max=500))
    notes = fields.Str(allow_none=True, validate=_LONG)


class InventoryCheckoutSchema(ma.Schema):
    """Schema for checkout records."""

    class Meta:
        unknown = EXCLUDE

    id = fields.Int(dump_only=True)
    item_id = fields.Int(dump_only=True)
    member_id = fields.Int(dump_only=True)
    member_name = fields.Method("get_member_name", dump_only=True)
    checked_out_at = fields.DateTime(dump_only=True)
    expected_return_at = fields.DateTime(allow_none=True, dump_default=None)
    returned_at = fields.DateTime(allow_none=True, dump_only=True, dump_default=None)
    condition_notes = fields.Str(allow_none=True, dump_default=None)

    def get_member_name(self, obj):
        return obj.member.name if obj.member else None


class CheckoutCreateSchema(ma.Schema):
    """Schema for checking out an item."""

    class Meta:
        unknown = RAISE

    member_id = fields.Int(required=True)
    expected_return_at = fields.DateTime(allow_none=True, load_default=None)
    condition_notes = fields.Str(allow_none=True, load_default=None, validate=_LONG)
