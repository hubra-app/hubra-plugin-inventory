"""Inventory: tools, machines, items and materials, checkouts and inductions.

Was built into Hubra up to 0.x as the module "inventory"; the module code,
the tables, the API path and the permissions (inventory.items.*) stay the
same, so clubs keep their items, their switch and their roles, and the
plugins built on it (keys, guides) keep working.
"""

from hubra.core.modules import Blueprint, Module, NavItem, SettingField

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
