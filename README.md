# Groceries

The household's shared supermarket list, split by store, with a memory:
every item remembers where it is bought ("meat -> Costco") and gets
pre-selected there next time. In-store mode puts the store you are standing
in first and shows everything still pending elsewhere, so the meat can be
grabbed at Aldi when it is in front of you.

Decisions and sketches: the "Popcorn & Groceries" artifact + the homelab
repo's OBJECTIVES.md (2026-08-15). Same stack and conventions as
family-calendar: FastAPI + Postgres + Jinja, no ORM, no build step, gate.py
deciding who needs a login (public visitors only; tailnet and home LAN pass
free). The gate is BYTE-COMPATIBLE with the calendar's: same cookie, same
secret, so one login covers the household apps.

- Tailnet: https://home.example.ts.net:8449/
- Home LAN: http://192.0.2.251:3030/
- Public (login): https://home.example.ts.net:10000/groceries/
- PWA: open it on the phone, "Add to Home Screen", it installs like an app.

Deploy: `make deploy` (rsync to lab:/srv/lab/groceries + compose build).
The `.env` lives only on the host: GRO_DB_PASSWORD, GATE_SECRET, GATE_USERS
(the latter two carry the same values as the calendar's CAL_GATE_*).
Backups nightly 07:50 UTC by the homelab service_backup role; probed by
app_health every 2 minutes.
