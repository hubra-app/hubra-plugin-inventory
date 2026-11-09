"""Inventory: tools, machines, items and materials, checkouts and inductions.

Was built into Hubra up to 0.x as the module "inventory"; the module code,
the tables, the API path and the permissions (inventory.items.*) stay the
same, so clubs keep their items, their switch and their roles, and the
plugins built on it (keys, guides) keep working.
"""

from hubra.core.contracts import (
    WidgetField,
    action_contract,
    event_contract,
    query_contract,
    widget_contract,
)
from hubra.core.modules import Blueprint, Module, NavItem, SettingField

_C = "hubra_inventory.contracts"

module = Module(
    code="inventory",
    name="Inventory",
    description="Tools, machines and materials, checkouts and inductions",
    default_enabled=False,
    depends_on=("members",),
    blueprints=(
        Blueprint(
            "hubra_inventory.routes",
            "inventory_bp",
            "/api/v1/inventory",
        ),
    ),
    settings=(
        SettingField(
            "checkout_max_days",
            "int",
            default=14,
            label="Longest checkout (days)",
            description="Default due date for new checkouts",
        ),
        SettingField(
            "require_induction",
            "bool",
            default=True,
            label="Only inducted members can check out",
            description="Applies to items marked as needing instruction",
        ),
        SettingField(
            "block_when_overdue",
            "bool",
            default=False,
            label="Block checkouts while an invoice is overdue",
            description="More than 7 days past due; needs the Finance module",
        ),
    ),
    nav=(
        NavItem(
            "/app/inventory",
            "shell.nav.inventory",
            "package",
            section="operations",
            order=5,
            perms=("inventory.items.read",),
        ),
    ),
    tables=("inventory_items", "inventory_checkouts", "item_instructions"),
    # What other plugins and the dashboards may use (Hubra docs/contracts.md).
    provides=(
        query_contract(
            "inventory.items.get",
            f"{_C}:get_items",
            input=f"{_C}:ItemsIn",
            output=f"{_C}:Item",
            perm="inventory.items.read",
            description="Items by id (deleted ones left out)",
        ),
        query_contract(
            "inventory.items.list",
            f"{_C}:list_items",
            input=f"{_C}:ListIn",
            output=f"{_C}:Item",
            perm="inventory.items.read",
            description="Items by name, optionally matching a search",
        ),
        action_contract(
            "inventory.items.lend",
            f"{_C}:lend_item",
            input=f"{_C}:LendIn",
            output=f"{_C}:Item",
            perm="inventory.items.create_own",
            description="Record a member's own thing as lent to the club",
        ),
        event_contract(
            "inventory.item.deleted",
            f"{_C}:ItemDeleted",
            description="An item was deleted",
        ),
        widget_contract(
            "inventory.checked_out",
            f"{_C}:checked_out",
            label="inventory.widget.checkedOut",
            description="inventory.widget.checkedOutHint",
            size="m",
            view="list",
            perm="inventory.items.read",
            fields=(WidgetField("count", "inventory.widget.count", "number", 5),),
        ),
        widget_contract(
            "inventory.overdue",
            f"{_C}:overdue",
            label="inventory.widget.overdue",
            description="inventory.widget.overdueHint",
            size="s",
            view="stat",
            perm="inventory.items.read",
        ),
    ),
    permissions=(("inventory.items.create_own", "Add own inventory items"),),
    field_permissions=(
        ("inventory", "items", "name", "Item name"),
        ("inventory", "items", "description", "Description"),
        ("inventory", "items", "location", "Location"),
        ("inventory", "items", "status", "Status"),
        ("inventory", "items", "owner_id", "Owner"),
        ("inventory", "items", "responsible_id", "Responsible person"),
    ),
)
