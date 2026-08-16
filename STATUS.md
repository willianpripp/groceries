# STATUS

A running record of what was built, what was decided, and what was
deliberately left out. Newest first.

**Made public (2026-08-15, night):** MIT licence, a documented
`.env.example`, invented demo data behind `make demo`, a README written for
somebody who has never seen this house, and every address moved out of the
code and into configuration (the home icon now reads `GRO_PORTAL_URL` and
simply is not drawn when there is nothing to point at). The compose file binds
loopback only; host-specific bindings belong in an ignored override file.

Building the demo data immediately exposed a layout bug that real use never
had: with names as short as "Milk" nothing ever competed for space, but
"Rotisserie chicken" plus a quantity plus a note shredded the name into one
letter per line, and the edit pencil fell outside the card. Three real causes,
all now fixed: `overflow-wrap: anywhere` let flexbox shrink a name to its
narrowest character, the note could not shrink or truncate, and the store
columns were a fixed 280px, which is narrower than the content needs. Grid
items also needed `min-width: 0` so a wide row can no longer stretch its
column past the viewport and give the phone a sideways scrollbar.

**Friction round 1 (2026-08-15):** a home icon in the header, linking back to
the portal that fronts the household's apps. It is prefix-aware: behind a path
router it points at that host's root, and on the app's own port it points at
`GRO_PORTAL_URL`, or is not drawn at all when there is no portal. The brand was
pinned to one line beside it, since a third header element made it wrap.
Verified at 390px and 1280px.

**Where it stood at the end of the build day (2026-08-15):** live, in real use,
and already reshaped by that use. **Live sync** between phones (a four second
change-fingerprint poll that never fires mid-typing), **edit and remove panels**
on rows rather than buy-only, **empty stores vanish** from the board,
**quantity defaults to 1** and always shows, a tidy fixed-width desktop layout,
and seven default stores (Costco, Aldi, Walmart, Kroger, Lidl, Farmers Market,
Asian Market).

v1 was built in one session from approved sketches: the add bar with the
two-level store memory (item first, category default second), store columns on
desktop and stacked sections on the phone, in-store mode with the elsewhere
list and buy-here, one-tap restock from usuals, autocomplete from history, the
bought-today strip with un-buy, and a PWA manifest with icons.

**Added the same day:** open entries can be edited and removed, not only
bought. A pencil on each row opens an inline panel (quantity, note, store,
Save, and Remove behind a confirm). Remove deletes only that open entry: the
item's memory and its history stay. Changing the store in that panel moves the
item's home, the same rule the add chips follow. An `updated_at` column feeds
the live-sync fingerprint, and the poller holds still while a panel is open.

**Decided rules, now encoded:** buying at a different store is an exception and
never moves an item's home store. Adding it with an explicit store chip is the
deliberate act that does. An automatic placement for an unknown item in an
unknown category lands in "Anywhere" rather than guessing.

**Not built, by choice:** offline mode (a service worker with queued
check-offs) waits for proven pain from real dead zones inside supermarkets, and
adding or renaming stores is SQL-only for now. Both are cheap to add once
somebody actually wants them, and neither is worth carrying before that.

The infrastructure this runs on (reverse proxy, backups, uptime probes) is not
in this repo. The app is only the app.
