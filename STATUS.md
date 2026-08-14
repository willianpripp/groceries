# STATUS

**Where it stands (2026-08-15):** v1 live and in use, built in one session
from the approved sketches. Add bar with the two-level store memory (item
first, category default second), store columns (desktop) / stacked sections
(phone), in-store mode with the elsewhere list and buy-here, usuals one-tap
restock, autocomplete from history, bought-today strip with un-buy, PWA
manifest + icons.

**Decided rules encoded:** buying at a different store is an exception and
never moves an item's home store; ADDING with an explicit store chip is the
deliberate act that does. Auto on an unknown item lands in "Anywhere".

**Owned by the homelab session** (explicit exception to one-session-per-repo,
Willian 2026-08-15). Plumbing (router, funnel, backups, probes) lives in the
homelab repo; this repo is only the app.

Not built yet, by choice: offline mode (service worker + queued check-offs);
waits for proven pain from in-store dead zones. Store management UI (add or
rename stores) is SQL-only for now.
