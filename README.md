# Inventory

A [Hubra](https://hubra.club) plugin for a club's tools, machines and
materials: who owns and looks after each item, where it is, what it cost,
checkouts with due dates, and inductions for items that need one before
anyone may use them.

**Plugin id** `inventory` · **Package** `hubra_inventory` · **Module** `inventory` · **Works with** Hubra `>=0.2,<1` (the version without the built-in Inventory module)

## Moving from the built-in module

Inventory was part of Hubra itself until it moved out
([hubra-app/hubra#171](https://github.com/hubra-app/hubra/pull/171)). The
plugin keeps everything the same, so nothing has to be migrated by hand:

- the module code `inventory` and its setting (checkout days), so clubs that
  had it on keep it on;
- the tables `inventory_items`, `inventory_checkouts` and
  `item_instructions` with their rows;
- the API path `/api/v1/inventory`;
- the permissions `inventory.items.*`, the extra right
  `inventory.items.create_own` and the per-field update rights, so roles
  keep them;
- the club-app pages `/app/inventory` and `/app/inventory/<id>`.

The migration creates the tables only where they do not exist yet. Items
also show up in the club app's search (Ctrl+K).

[hubra-plugin-guides](https://github.com/hubra-app/hubra-plugin-guides)
links guides to items when both plugins are on.

## Layout

```
plugin.yaml              # id, version, Hubra range, package, modules
hubra_inventory/         # Module, models, schemas, service, routes
migrations/              # creates the three tables where they are missing
frontend/src/            # list, item page, forms, search, translations
tests/                   # runs with Hubra's pytest fixtures
```

## Develop

Clone into `plugins/inventory` of a Hubra checkout:

```
cd hubra/app/backend
pytest ../../plugins/inventory
cd ../frontend
npm run typecheck:plugins
npm run build:plugin -- ../../plugins/inventory
```

## Release

Bump `version` in `plugin.yaml`, add a `## <version>` section to
`CHANGELOG.md`, merge, then publish a GitHub release tagged `v<version>`.
The workflow tests, signs (after approval in the `plugin-signing`
environment) and attaches `inventory-<version>.zip`.
