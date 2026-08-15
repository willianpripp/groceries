# Groceries: the household's shared supermarket list, split by store.
#
# Sketched and decided with Willian 2026-08-15 (the artifact "Popcorn &
# Groceries: the sketches" holds the decisions):
#   - every item remembers its home store ("meat -> Costco"), pre-selected on
#     add; buying it elsewhere once is an exception and never moves the home
#   - all stores visible at once; in-store mode ("I'm at Aldi") puts that
#     store first and shows everything still pending elsewhere below it, so
#     the meat can be grabbed at Aldi when it is in front of you
#   - phone-first, but good on the desktop too (the standing rule)
#   - PWA: manifest + icons so "Add to Home Screen" makes it feel installed
#
# Same skeleton as the family calendar: FastAPI + psycopg pool + Jinja,
# gate.py deciding who needs a login (public visitors only), one SCHEMA
# string, no ORM, no build step.

import os
import time as systime
from datetime import date
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

import gate

DSN = os.environ.get("GRO_DSN", "postgresql://groceries:groceries@db:5432/groceries")

SCHEMA = """
create table if not exists stores (
    id serial primary key,
    name text not null unique,
    color text not null default '#93A0B0',
    pos int not null default 100
);

-- The memory. One row per thing this household ever buys; home_store is what
-- gets pre-selected next time, category is the fallback grouping.
create table if not exists items (
    id serial primary key,
    name text not null,
    name_norm text not null unique,
    category text not null default '',
    home_store int references stores(id),
    created_at timestamptz not null default now()
);

-- Category-level fallback: an unknown item in a known category starts at the
-- category's store. Learned when someone sets both on an item, never guessed.
create table if not exists category_defaults (
    category text primary key,
    store_id int not null references stores(id)
);

-- What is currently on the list (done_at null) and everything ever bought
-- (done_at set): history and autocomplete come from the same rows.
create table if not exists entries (
    id serial primary key,
    item_id int not null references items(id),
    qty text not null default '',
    note text not null default '',
    planned_store int references stores(id),
    added_by text not null default '',
    added_at timestamptz not null default now(),
    done_at timestamptz,
    bought_store int references stores(id)
);
create index if not exists entries_open on entries (done_at) where done_at is null;
"""

SEED_STORES = [("Costco", "#C94A4A", 10), ("Aldi", "#4A7BC9", 20),
               ("Walmart", "#3FA7C9", 30), ("Kroger", "#7B68C9", 40),
               ("Lidl", "#C9A54A", 50), ("Farmers Market", "#5FBF8F", 60),
               ("Asian Market", "#C97BB0", 70)]

pool = ConnectionPool(DSN, min_size=1, max_size=4, open=False)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    pool.open()
    with pool.connection() as conn:
        conn.execute(SCHEMA)
        for name, color, pos in SEED_STORES:
            conn.execute(
                "insert into stores (name, color, pos) values (%s, %s, %s)"
                " on conflict (name) do nothing", (name, color, pos))
    if not gate.configured():
        print("groceries: GATE_SECRET/GATE_USERS unset; public visitors are"
              " locked out until they are configured (tailnet/LAN unaffected)")


def q(sql, params=()):
    with pool.connection() as conn:
        conn.row_factory = dict_row
        cur = conn.execute(sql, params)
        return cur.fetchall() if cur.description else None


def q1(sql, params=()):
    rows = q(sql, params)
    return rows[0] if rows else None


# --- subpath awareness ----------------------------------------------------------
# On the LAN and tailnet this app is the whole site; on the public hostname it
# lives under /groceries behind the path router, which strips the prefix and
# says so in X-Forwarded-Prefix. Every URL the templates emit starts with
# `base` so both mounts work from one codebase.


def base_of(request: Request) -> str:
    return request.headers.get("x-forwarded-prefix", "").rstrip("/")


@app.middleware("http")
async def front_door(request: Request, call_next):
    """Same trust boundary as the calendar: tailnet and LAN pass untouched,
    public visitors need the shared session. style.css and the PWA files stay
    open so the login page and the installed icon work; /health stays open for
    the healthcheck and the homelab monitor."""
    path = request.url.path
    if (
        path in ("/login", "/health")
        or path in ("/static/style.css", "/static/manifest.webmanifest",
                    "/static/icon-192.png", "/static/icon-512.png")
        or gate.trusted(request)
        or gate.session_user(request)
    ):
        return await call_next(request)
    nxt = quote(path + (f"?{request.url.query}" if request.url.query else ""))
    return RedirectResponse(f"{base_of(request)}/login?next={nxt}", status_code=303)


@app.get("/health")
def health():
    q("select 1")
    return {"status": "ok"}


@app.get("/poke")
def poke():
    """A cheap change fingerprint for live sync between phones: the page
    polls this and reloads when it moves. Any add, check-off, un-buy or move
    changes it; reading never does."""
    r = q1("""select count(*) n,
                 coalesce(max(extract(epoch from added_at)), 0) a,
                 coalesce(max(extract(epoch from done_at)), 0) d,
                 coalesce(max(id), 0) m
              from entries""")
    return {"v": f"{r['n']}:{r['m']}:{int(r['a'])}:{int(r['d'])}"}


# --- the memory -----------------------------------------------------------------


def norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


def remember(name: str, store_id, category: str | None):
    """The write side of the two-level memory. Called on add: an explicit
    store on a known item MOVES its home (adding is deliberate); buying
    elsewhere in-store never calls this."""
    n = norm(name)
    item = q1("select * from items where name_norm = %s", (n,))
    if item is None:
        item = q1(
            "insert into items (name, name_norm, home_store, category)"
            " values (%s, %s, %s, %s) returning *",
            (name.strip(), n, store_id, category or ""))
    else:
        if store_id and store_id != item["home_store"]:
            q("update items set home_store = %s where id = %s", (store_id, item["id"]))
            item["home_store"] = store_id
        if category and category != item["category"]:
            q("update items set category = %s where id = %s", (category, item["id"]))
            item["category"] = category
    if item["category"] and item["home_store"]:
        q("insert into category_defaults (category, store_id) values (%s, %s)"
          " on conflict (category) do update set store_id = excluded.store_id",
          (item["category"], item["home_store"]))
    return item


def suggest_store(name: str) -> dict:
    """The read side: exact item first, then its category's default."""
    n = norm(name)
    item = q1("select * from items where name_norm = %s", (n,))
    if item and item["home_store"]:
        return {"store_id": item["home_store"], "why": "item",
                "category": item["category"]}
    if item and item["category"]:
        d = q1("select store_id from category_defaults where category = %s",
               (item["category"],))
        if d:
            return {"store_id": d["store_id"], "why": "category",
                    "category": item["category"]}
    return {"store_id": None, "why": "unknown", "category": item["category"] if item else ""}


@app.get("/suggest")
def suggest(name: str = ""):
    return JSONResponse(suggest_store(name))


# --- who is adding --------------------------------------------------------------
# Session user when there is one (public path); otherwise the device map,
# same format as the calendar's: GRO_DEVICES="100.x.y.z=Willian,..."


def who(request: Request) -> str:
    u = gate.session_user(request)
    if u:
        return u.capitalize()
    ip = gate.real_client(request)
    for pair in os.environ.get("GRO_DEVICES", "").split(","):
        if "=" in pair:
            addr, _, name = pair.partition("=")
            if addr.strip() == str(ip):
                return name.strip().capitalize()
    return ""


# --- pages ----------------------------------------------------------------------


def page_ctx(request: Request, at: int | None):
    stores = q("select * from stores order by pos, name")
    open_entries = q("""
        select e.id, e.qty, e.note, e.planned_store, e.added_by,
               i.name, i.category
        from entries e join items i on i.id = e.item_id
        where e.done_at is null
        order by e.added_at""")
    done_today = q("""
        select e.id, e.qty, e.planned_store, e.bought_store, i.name
        from entries e join items i on i.id = e.item_id
        where e.done_at::date = current_date
        order by e.done_at desc""")
    by_store: dict = {s["id"]: [] for s in stores}
    unsorted = []
    for e in open_entries:
        if e["planned_store"] in by_store:
            by_store[e["planned_store"]].append(e)
        else:
            unsorted.append(e)
    names = [r["name"] for r in q(
        "select i.name, count(e.id) c from items i"
        " left join entries e on e.item_id = i.id"
        " group by i.name order by c desc, i.name limit 200")]
    usuals = q("""
        select i.id, i.name from items i
        where (select count(*) from entries e where e.item_id = i.id
               and e.done_at > now() - interval '60 days') >= 3
        and not exists (select 1 from entries e where e.item_id = i.id
                        and e.done_at is null)
        order by i.name limit 12""")
    return {
        "request": request, "base": base_of(request),
        "stores": stores, "by_store": by_store, "unsorted": unsorted,
        "done_today": done_today, "at": at, "names": names, "usuals": usuals,
        "who": who(request),
        "open_count": len(open_entries),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    at = request.cookies.get("gro_at", "")
    at_id = int(at) if at.isdigit() else None
    return templates.TemplateResponse(request, "index.html", page_ctx(request, at_id))


@app.post("/add")
def add(request: Request, name: str = Form(""), store: str = Form("auto"),
        qty: str = Form(""), note: str = Form(""), category: str = Form("")):
    name = name.strip()
    if not name:
        return RedirectResponse(base_of(request) + "/", status_code=303)
    explicit = int(store) if store.isdigit() else None
    if explicit:
        item = remember(name, explicit, category or None)
        planned = explicit
    else:
        s = suggest_store(name)
        item = remember(name, None, category or None)
        planned = s["store_id"]
    q("insert into entries (item_id, qty, note, planned_store, added_by)"
      " values (%s, %s, %s, %s, %s)",
      (item["id"], qty.strip(), note.strip(), planned, who(request)))
    return RedirectResponse(base_of(request) + "/", status_code=303)


@app.post("/entries/{eid}/toggle")
def toggle(request: Request, eid: int, at: str = Form("")):
    e = q1("select * from entries where id = %s", (eid,))
    if e is None:
        return RedirectResponse(base_of(request) + "/", status_code=303)
    if e["done_at"] is None:
        bought = int(at) if at.isdigit() else e["planned_store"]
        q("update entries set done_at = now(), bought_store = %s where id = %s",
          (bought, eid))
    else:
        q("update entries set done_at = null, bought_store = null where id = %s",
          (eid,))
    return RedirectResponse(base_of(request) + "/", status_code=303)


@app.post("/entries/{eid}/store")
def move(request: Request, eid: int, store: int = Form(...)):
    """Reassign an open entry (and the item's home: moving it is deliberate)."""
    e = q1("select e.*, i.name from entries e join items i on i.id = e.item_id"
           " where e.id = %s", (eid,))
    if e:
        q("update entries set planned_store = %s where id = %s", (store, eid))
        remember(e["name"], store, None)
    return RedirectResponse(base_of(request) + "/", status_code=303)


@app.post("/at")
def set_at(request: Request, store: str = Form("")):
    """In-store mode, remembered per device."""
    resp = RedirectResponse(base_of(request) + "/", status_code=303)
    if store.isdigit():
        resp.set_cookie("gro_at", store, max_age=86400, samesite="lax", httponly=True)
    else:
        resp.delete_cookie("gro_at")
    return resp


@app.post("/usuals")
def add_usuals(request: Request):
    rows = q("""
        select i.id from items i
        where (select count(*) from entries e where e.item_id = i.id
               and e.done_at > now() - interval '60 days') >= 3
        and not exists (select 1 from entries e where e.item_id = i.id
                        and e.done_at is null)""")
    for r in rows:
        item = q1("select * from items where id = %s", (r["id"],))
        q("insert into entries (item_id, planned_store, added_by)"
          " values (%s, %s, %s)", (item["id"], item["home_store"], who(request)))
    return RedirectResponse(base_of(request) + "/", status_code=303)


# --- the front door (public visitors only; see gate.py) --------------------------


def _safe_next(n: str) -> str:
    return n if n.startswith("/") and not n.startswith("//") else "/"


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request, next: str = "/"):
    if gate.trusted(request) or gate.session_user(request):
        return RedirectResponse(base_of(request) + _safe_next(next), status_code=303)
    return templates.TemplateResponse(request, "login.html", {
        "request": request, "base": base_of(request),
        "next": _safe_next(next), "error": None, "configured": gate.configured()})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, who_: str = Form("", alias="who"),
                 password: str = Form(""), next: str = Form("/")):
    name = who_.strip().lower()
    if not gate.configured() or not gate.check_password(name, password):
        systime.sleep(1)
        return templates.TemplateResponse(request, "login.html", {
            "request": request, "base": base_of(request),
            "next": _safe_next(next), "configured": gate.configured(),
            "error": "Wrong name or password." if gate.configured() else None})
    resp = RedirectResponse(base_of(request) + _safe_next(next), status_code=303)
    # path=/ so the cookie covers the calendar and popcorn too: one login.
    resp.set_cookie(gate.COOKIE, gate.mint(name), max_age=gate.SESSION_DAYS * 86400,
                    httponly=True, samesite="lax", secure=True, path="/")
    return resp
