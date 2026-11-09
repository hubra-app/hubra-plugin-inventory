# Inventory

A [Hubra](https://hubra.club) plugin for a club's tools, machines and
materials: who owns and looks after each item, where it is, what it cost,
checkouts with due dates, inductions for items that need one before
anyone may use them, and a usage guide per item.

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

## Guides

Each item can have a usage guide: Markdown (steps, safety rules, what to
check after use) and/or a link to a manual or video. The item page shows a
short preview; the guide has its own page, `/app/inventory/<id>/guide`, with
a table of contents, and `?edit=1` opens the editor. Whoever may change the
item (the right `inventory.items.update`, or its owner or responsible
person) may change its guide.

A guide can name the qualification the item takes, when the
[Qualifications plugin](https://github.com/hubra-app/hubra-plugin-guides) is
on. The guide then shows it and whether the reader holds it, through that
plugin's queries `qualifications.kinds.list` and
`qualifications.member.holds`. It is shown, not enforced: inductions still
decide who may check an item out.

Up to 2.3 the guides belonged to the Guides plugin; 2.4 copies them here
once (from `item_guides`, when that table exists).

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
`CHANGELOG.md` and merge. Then tag the merged commit on main and push the tag:

```sh
git switch main && git pull
git tag v<version> && git push origin v<version>
```

The workflow tests the plugin and builds its frontend, the `plugin-signing`
job signs it after your approval, and only then is the GitHub release
`v<version>` published, with `inventory-<version>.zip` and its `.sha256` attached. Files
listed in `.releaseignore` stay out of the zip. Releases are immutable, so a
published version never changes: fix a bad one with a new version.