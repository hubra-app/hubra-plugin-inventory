# Inventory

## 2.1.0

- An item opens as its own page at /app/inventory/<id> instead of a side
  panel, like a member's page in Hubra: a header with its badges and key
  figures, a card of facts, links and the inductions. Edit and delete work
  from the page, and search results (Ctrl+K) and shared links open it
  directly; before, that address only showed "no item selected".
- Other plugins still add to an item through the `inventory.item` slot, now
  on the page.

## 2.0.0

Inventory is now a plugin instead of a part of Hubra. Clubs keep their
items, checkouts, inductions, module setting and roles: the tables, the API
and the permissions are the same as before.

- Items are found by the club app's search (Ctrl+K).
