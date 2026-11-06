# Inventory

## Unreleased

- Other plugins read items through Hubra's contracts instead of this
  plugin's code or tables: the queries `inventory.items.get` (by id) and
  `inventory.items.list` (by name, with a search), and the event
  `inventory.item.deleted`. Needs a Hubra with contracts (hubra#231).
- Two dashboard widgets: "Checked out" (what is out right now, due back
  first) and "Overdue checkouts" (a number tile). Members see them with the
  right to read inventory (needs hubra#234).
- plugin.yaml lists the areas it uses (`uses:`).

## 2.1.0

- An item opens as its own page at /app/inventory/<id> instead of a side
  panel, like a member's page in Hubra: a header with its badges and key
  figures, a card of facts, links and the inductions. Edit and delete work
  from the page, and search results (Ctrl+K) and shared links open it
  directly; before, that address only showed "no item selected".
- Other plugins still add to an item through the `inventory.item` slot, now
  on the page.

## 2.0.1

- The open item is in the URL, /app/inventory/<id>. Search hits and links
  to an item open its panel again (before, they showed an empty "Kein
  Gegenstand ausgewählt" page), and the browser's back button closes it.

## 2.0.0

Inventory is now a plugin instead of a part of Hubra. Clubs keep their
items, checkouts, inductions, module setting and roles: the tables, the API
and the permissions are the same as before.

- Items are found by the club app's search (Ctrl+K).
