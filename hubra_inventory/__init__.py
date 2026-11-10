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
    # Access the standard roles get when a club first switches it on
    # (docs/roles.md in hubra-app/hubra).
    role_defaults={"member": "view", "board": "view", "secretary": "edit"},
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
    tables=(
        "inventory_items",
        "inventory_checkouts",
        "item_instructions",
        "inventory_item_history",
    ),
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
        event_contract(
            "inventory.item.saved",
            f"{_C}:ItemSaved",
            description="An item was added or changed",
        ),
        # For add-ons that keep a type of item of their own (Keys: "Key").
        action_contract(
            "inventory.items.save",
            f"{_C}:save_item",
            input=f"{_C}:SaveIn",
            output=f"{_C}:Item",
            perm="inventory.items.update",
            description="Add an item (no item_id) or change the fields given",
        ),
        # Stock of consumables (Kasse: the Strichliste takes from it).
        action_contract(
            "inventory.stock.adjust",
            f"{_C}:adjust",
            input=f"{_C}:StockIn",
            output=f"{_C}:Item",
            perm="inventory.items.update",
            description="Take some of a counted item (negative delta) or add some",
        ),
        event_contract(
            "inventory.stock.low",
            f"{_C}:StockLow",
            description="A counted item fell to its reorder level or below",
        ),
        action_contract(
            "inventory.items.history.add",
            f"{_C}:add_history",
            input=f"{_C}:HistoryIn",
            output=f"{_C}:HistoryRef",
            perm="inventory.items.update",
            description="Add an entry to an item's history (Keys: a handover)",
        ),
        action_contract(
            "inventory.items.delete",
            f"{_C}:delete_item",
            input=f"{_C}:DeleteIn",
            output=f"{_C}:Deleted",
            perm="inventory.items.delete",
            description="Delete an item; one already gone is fine",
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
            "inventory.low_stock",
            f"{_C}:low_stock",
            label="inventory.widget.lowStock",
            description="inventory.widget.lowStockHint",
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
