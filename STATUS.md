# STATUS

**Where it stands (2026-08-15, end of day):** live, in real use, already
reshaped by it: **live sync** between phones (4s change-fingerprint poll,
never mid-typing), **edit/remove panels** on rows (built by the calendar
session at Willian's direct ask, same home-store rules), **empty stores
vanish** from the board, **quantity defaults to 1** and always shows,
desktop layout fixed (tidy fixed-width columns), seven stores (Costco, Aldi,
Walmart, Kroger, Lidl, Farmers Market, Asian Market). v1 was built in one
session from the approved sketches. Add bar with the two-level store memory (item
first, category default second), store columns (desktop) / stacked sections
(phone), in-store mode with the elsewhere list and buy-here, usuals one-tap
restock, autocomplete from history, bought-today strip with un-buy, PWA
manifest + icons.

**Added later on 2026-08-15** (calendar session, Willian's ask, 9a8be16):
open entries can be edited and removed, not only bought. Pencil on each row
opens an inline panel (qty, note, store, Save, Remove with confirm). Remove
deletes only the open entry; item memory and bought history stay. A store
change in the panel moves the item's home, same rule as the add chips.
updated_at column feeds the live-sync fingerprint; the poller holds still
while a panel is open. Verified live at phone and desktop widths.

**Decided rules encoded:** buying at a different store is an exception and
never moves an item's home store; ADDING with an explicit store chip is the
deliberate act that does. Auto on an unknown item lands in "Anywhere".

**Owned by the homelab session** (explicit exception to one-session-per-repo,
Willian 2026-08-15). Plumbing (router, funnel, backups, probes) lives in the
homelab repo; this repo is only the app.

Not built yet, by choice: offline mode (service worker + queued check-offs);
waits for proven pain from in-store dead zones. Store management UI (add or
rename stores) is SQL-only for now.
