# Inventory

## 2.5.0

- **Tighter member rights.** The rights members get at "view" (check out, check in, confirm induction) now cover only themselves: a member checks out to themselves and checks in what they borrowed. Lending to someone else or taking back someone else's loan is for the owner, the responsible person or whoever may edit inventory items. A person's own item is lent only by that person, the person looking after it, or an admin.
- **Self-induction is off by default.** New setting *Members may confirm their own induction* (`self_induction`). While it is off, "Mark myself as inducted" is gone and the API refuses it, so an item that needs an induction can't be borrowed without one. Clubs that used self-induction switch it on in the module settings.
- Field rights work on edits: a role with only some field rights (e.g. `inventory.items.update.location`) changes just those fields; before, it got 403.
- Security: links, documents and the image address take only http, https, mailto or an app path; a `javascript:` or `data:` link is refused, and one saved before shows as text. Lists hold at most 50 entries, short fields 255 characters.
- Security: two Strichliste takes at the same moment no longer lose one (the stock count is read under a row lock); check-in uses the same lock as checkout.
- Security: the action `inventory.items.delete` keeps a person's own item like the delete button does, and `actor_id` / `by_id` in the actions count only when the caller acts as the system, so the audit log names who really acted.
- A new item can't start as "checked out" (it could never be checked in), and an unknown owner or responsible person is a 404 instead of a server error.
- List filters (category, status, ownership, low stock) all sit in the Filter panel, with readable chip names; the card view pages and filters like the table.
- German: "Eigentümer:in" reads "Eigentümer/in", like the other gender forms in Hubra.
- **Serial number** in the item form (Seriennummer; Schlüsselnummer for a key, which stays in line with the key's number in Keys).
- **Stock counts** for consumables (new type *Verbrauchsmaterial*, or *Bestand zählen* on any item): stock, reorder level and unit. The item page shows the stock with *Auffüllen* / *Entnehmen*; the list shows it and filters *Knapp*. Every change leaves a line in the history.
- For other plugins: action `inventory.stock.adjust` (the Kasse plugin's Strichliste takes from stock with it), event `inventory.stock.low` (once when an item falls to its reorder level, for reordering later), and the dashboard widget *Knapper Bestand* (`inventory.low_stock`). Run `flask db upgrade` after updating.

## 2.4.0

- Gives the standard roles access when a club first switches it on (`role_defaults`, docs/roles.md in hubra-app/hubra): Mitglied Ansehen, Vorstand Ansehen, Aktuar/in Bearbeiten. Roles without access don't see it; their own data from it stays on their profile. Needs Hubra 0.2.5 or later.

## 2.3.1

2.3.0 was tagged but couldn't be signed, so it was never released. 2.3.1 is the same plugin, signed. What it brings:

- Lending to the club lives here now. An item that belongs to a member
  (*Belongs to: A member (lent to the club)*) is something that member lends
  to the club; the list says "Lent by Anna" and filters by *The club's own*
  / *Lent by members*. Members who may only add their own items get a "Lend
  something to the club" button, and their new item is theirs by default;
  `/app/inventory?lend=1` opens that form directly.
- New action `inventory.items.lend` (member, name, description): records a
  member's own thing as lent to the club. A member may only lend their own
  things; the system may record it for anyone. Community 1.2.0 uses it to
  move its old "lends" entries here. Items from the queries carry `lent_by`.

## 2.3.0

- Lending to the club lives here now. An item that belongs to a member
  (*Belongs to: A member (lent to the club)*) is something that member lends
  to the club; the list says "Lent by Anna" and filters by *The club's own*
  / *Lent by members*. Members who may only add their own items get a "Lend
  something to the club" button, and their new item is theirs by default;
  `/app/inventory?lend=1` opens that form directly.
- New action `inventory.items.lend` (member, name, description): records a
  member's own thing as lent to the club. A member may only lend their own
  things; the system may record it for anyone. Community 1.2.0 uses it to
  move its old "lends" entries here. Items from the queries carry `lent_by`.

## 2.2.0

- New item type **Key** (keys, cards and fobs). With the Keys add-on on,
  every key is an inventory item of this type: it shows in the inventory
  list and search with the other items, and its page shows who holds it,
  the handover buttons and its history (from Keys). A key has no induction
  and isn't checked out: Keys hands it out, and its status follows (handed
  out = in use, lost, retired). Checking a key out is refused
  (`KEY_HANDOVER`).
- Every item page has a **history**: checkouts and returns, and what an
  add-on recorded (for keys: handed out, taken back, lost, found, retired,
  with who and a note). New table `inventory_item_history`.
- **Held by**: who has an item an add-on handed out (for keys: the holder),
  on the item page, in the list and on the cards. New column
  `inventory_items.holder_id`.
- List views: besides table and cards, **By type** shows one section per
  type. With the type "Key" picked, the table shows number, status and who
  holds each key. `/app/inventory?type=Key` opens the list on keys.
- For add-ons that keep a type of item of their own: the actions
  `inventory.items.save` (add an item, or change the fields given, incl.
  `holder_id`), `inventory.items.delete` and `inventory.items.history.add`
  (an entry in the item's history), and the event `inventory.item.saved` when an
  item is added or changed, in Inventory or through the action.
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
