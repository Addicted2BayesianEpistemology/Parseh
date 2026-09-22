"""deckroutes — the exercise decks over HTTP, mounted at /exercises.

The same routes answer in both servers: inside Parseh (../../serve.py hands
it every /exercises/... request) and beside the studio when the studio runs
on its own (server.py does the same).  So this module must NOT import
server.py: serve.py loads that file under another module name, and a second
import would make a second, unconfigured copy of the studio.  What it needs
from the studio arrives instead through two calls server.py makes when it
loads -- set_studio_base (where the studio's static files and pages are) and
set_shutdown (what the Stop button runs) -- and one serve.py makes, since
only Parseh has books and videos: set_notes_resolver (which notes library a
notes page's address stands for, so "+ Deck" works in a note too).

The handler `h` given to dispatch offers only what both servers' handlers
share: h.query, h._body(), h._json_body(), h.send_bytes, h.send_json,
h.send_html, h.send_file, and in Parseh possibly h._spool -- a temp file
holding a body too large to keep in memory (an imported deck).

The work is decks.py's; this is the translation to and from HTTP: its errors
become statuses (NotFound 404, Conflict 409 with its kind, DeckError 400),
and every JSON answer carries "ok".
"""
import json
import re
import traceback
from pathlib import Path

import htmlgen          # first: it puts exlex/ (mdparser, texgen) and lib/ on sys.path
import audiofile
import decks
import languages
import store

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"

BASE = "/exercises"
# where the studio is mounted: "/studio" in Parseh, "" on its own
STUDIO = ""
_SHUTDOWN = {"fn": None}
_NOTES = {"fn": None}

# a client that goes away mid-answer is ordinary traffic: the server above
# decides what to do with it, never a 500 here
GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, TimeoutError)

# \x00 and \x01 are htmlgen's internal sentinels: a preview of unsaved text
# is rendered without going through the store, so it is cleaned here
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def set_studio_base(base):
    global STUDIO
    STUDIO = (base or "").rstrip("/")


def set_shutdown(fn):
    """The callable POST /api/shutdown runs with the handler (the studio's
    own api_shutdown, which stops whichever server is running)."""
    _SHUTDOWN["fn"] = fn


def set_notes_resolver(fn):
    """`fn(prefix) -> Path | None`: the notes library a notes mount serves,
    for its URL prefix (/books/<folder>/<slug>/notes, /youtube/v/<id>/notes),
    or None for a prefix that is no such mount.  serve.py registers it; the
    studio run alone has no notes and registers none.  Gives back the one
    it replaces."""
    was = _NOTES["fn"]
    _NOTES["fn"] = fn
    return was


def notes_library(prefix):
    """The notes directory behind a notes page's prefix, or None.

    The prefix comes from a request body, so it is checked the way the deck
    store checks the origin it keeps (a path on this server), and only then
    handed to the resolver -- which knows the shelves."""
    fn = _NOTES["fn"]
    if fn is None or not decks._source_ok(prefix):
        return None
    try:
        found = fn(prefix)
    except (OSError, ValueError):
        return None
    return Path(found) if found else None


def notes_source_ok(prefix):
    """Whether a copy from the notes under this prefix would be accepted:
    a note's page offers "+ Deck" only then."""
    return notes_library(prefix) is not None


# ---------------------------------------------------------------- templating

# THE INTERFACE, BROWSER OR MOBILE (docs/mobile.md), on <html data-mode>
# before anything is drawn -- the one thing these pages need of lib/parseh.js,
# which they do not load.  Read as parseh.js reads it: the value stored under
# `parseh_mode` first, the cookie of the same name when there is none,
# browser when there is neither.  Every page of the decks carries both of its
# layouts and static/mobile.css shows one; decks.js keeps the switch.
MODE_SCRIPT = (
    "<script>(function(){var m=null;"
    "try{m=localStorage.getItem('parseh_mode')}catch(e){}"
    "if(m!=='browser'&&m!=='mobile'){"
    "var c=/(?:^|;\\s*)parseh_mode=(browser|mobile)(?:;|$)/.exec(document.cookie||'');"
    "m=c?c[1]:'browser'}"
    "document.documentElement.setAttribute('data-mode',m)})();</script>")

# The switch between the two, for the mobile layout's bar: the hub's own two
# buttons (lib/mobile.py's mode_switch writes the same markup, and
# tests/test_mobile_mode.py holds the two together), wired here by decks.js.
MODE_SWITCH = (
    '<span class="parseh-mode" role="group" aria-label="interface">'
    '<button type="button" data-parseh-mode="browser" aria-pressed="true" '
    'title="the browser interface: every page, with everything that edits">'
    'Browser</button>'
    '<button type="button" data-parseh-mode="mobile" aria-pressed="false" '
    'title="the mobile interface: pages made for a phone, to read and to study, '
    'with nothing on them that edits">Mobile</button></span>')

# The tags that make a page part of the mobile interface installed as an app
# (docs/mobile.md): the manifest, the icons, the bars' colour.  The same tags
# lib/mobile.py's app_head writes (tests/test_mobile_pages.py holds the two
# together), for the pages here, which are the studio's and do not import it.
APP_HEAD = (
    '<link rel="manifest" href="/manifest.webmanifest">\n'
    '<link rel="apple-touch-icon" href="/lib/icons/apple-touch-icon.png">\n'
    '<meta name="theme-color" content="#f3eff1" media="(prefers-color-scheme: light)">\n'
    '<meta name="theme-color" content="#171214" media="(prefers-color-scheme: dark)">\n'
    '<meta name="mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-title" content="Parseh">\n'
    '<meta name="apple-mobile-web-app-status-bar-style" content="default">')


def render_template(name, mapping):
    """templates/<name> with {{BASE}}, {{STUDIO}}, {{MODE_SCRIPT}},
    {{MODE_SWITCH}}, {{APP_HEAD}} and the mapping filled in.

    One pass over the template, not one str.replace per key: a deck name
    that happens to contain "{{STUDIO}}" is the learner's text and stays as
    typed.  Values arrive escaped by the caller."""
    tpl = (TEMPLATES / name).read_text(encoding="utf-8")
    values = {"BASE": BASE, "STUDIO": STUDIO, "MODE_SCRIPT": MODE_SCRIPT,
              "MODE_SWITCH": MODE_SWITCH, "APP_HEAD": APP_HEAD}
    values.update(mapping)
    return _PLACEHOLDER_RE.sub(lambda m: values.get(m.group(1), m.group(0)), tpl)


def json_for_script(obj):
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")


def _not_found_page(h):
    # the studio's own 404 page, whose stylesheet and library link are the
    # studio's: its {{BASE}} is the studio's base, not this mount's
    h.send_html(render_template("404.html", {"BASE": STUDIO}), 404)


def _page_mapping(title, counts=None):
    return {"TITLE": htmlgen.esc(title),
            "LANGS_JSON": json_for_script(languages.chips(counts))}


def _deck_mapping(title, deck):
    L = languages.get(deck["lang"])
    m = _page_mapping(title)
    m.update({"DECK_JSON": json_for_script(deck),
              "LANG_JSON": json_for_script(L.as_json()),
              "TARGET": L.code,
              "TARGET_NAME": htmlgen.esc(L.name),
              "TARGET_DIR": L.dir})
    return m


# ---------------------------------------------------------------- small helpers

def _q1(h, key, default=""):
    return (h.query or {}).get(key, [default])[0]


def _flag(h, key, default=True):
    value = _q1(h, key, None)
    if value is None:
        return default
    return value.strip().lower() not in ("0", "false", "no", "off", "")


def _obj(h):
    """The JSON body as an object; DeckError for anything else.

    Parsed here from h._body(), not through h._json_body(): Parseh's handler
    answers a body it cannot use (empty, not JSON, not an object) by itself
    and gives back None, and a route that went on from there would write a
    second answer into the keep-alive connection -- read by the browser's
    next request as its own."""
    raw = h._body() or b""
    if not raw.strip():
        return {}
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError:
        raise decks.DeckError("bad JSON body: it is not UTF-8")
    try:
        body = json.loads(text)             # JSONDecodeError -> 400 in dispatch
    except RecursionError:
        raise decks.DeckError("bad JSON body: nested too deeply")
    if not isinstance(body, dict):
        raise decks.DeckError("the body must be a JSON object")
    return body


def _skip_ids(values):
    """Item ids to leave out of the queue, from `a,b` strings or a list."""
    if isinstance(values, str):
        values = [values]
    out = []
    for v in values if isinstance(values, list) else []:
        for part in (v.split(",") if isinstance(v, str) else []):
            part = part.strip()
            if decks.ITEM_RE.fullmatch(part) and part not in out:
                out.append(part)
    return out


def _lang_of(folder):
    # deck_dir has already refused anything that is not a registry folder
    return languages.by_folder(folder).code


def _asset_base(folder, slug):
    return BASE + "/media/%s/%s/" % (folder, slug)


def _render(folder, slug, item, preview):
    return decks.render_item({"lang": _lang_of(folder)}, item, _asset_base(folder, slug),
                             preview=preview, docs=store.doc_index())


# ---------------------------------------------------------------- pages

def page_decks(h):
    counts = {}
    for deck in decks.list_decks():
        counts[deck["lang"]] = counts.get(deck["lang"], 0) + 1
    m = _page_mapping("Exercises", counts)
    m["LANG_CHIPS"] = languages.chips_html(counts)
    h.send_html(render_template("decks.html", m))


def _page_deck_summary(h, folder, slug):
    try:
        return decks.get_deck(folder, slug)
    except decks.NotFound:
        _not_found_page(h)
        return None


def page_deck(h, folder, slug):
    deck = _page_deck_summary(h, folder, slug)
    if deck is not None:
        h.send_html(render_template("deck.html", _deck_mapping(deck["name"], deck)))


def page_study(h, folder, slug):
    deck = _page_deck_summary(h, folder, slug)
    if deck is not None:
        h.send_html(render_template("study.html",
                                    _deck_mapping("Study: " + deck["name"], deck)))


def page_cram(h, folder, slug):
    deck = _page_deck_summary(h, folder, slug)
    if deck is not None:
        h.send_html(render_template("cram.html",
                                    _deck_mapping("Cram: " + deck["name"], deck)))


def serve_image(h, folder, slug, name):
    # image_file validates the name (no traversal: it must be a picture name)
    # and builds a PDF's missing .pdf.svg twin before looking
    h.send_file(decks.image_file(folder, slug, name))


def serve_audio(h, folder, slug, name):
    # audio_file validates the name (a recording's, so no traversal); both
    # servers' send_file answer a Range request with the bytes it asks for,
    # which is what lets a card's player seek
    h.send_file(decks.audio_file(folder, slug, name))


# ---------------------------------------------------------------- decks

def api_decks_list(h):
    h.send_json({"ok": True, "decks": decks.list_decks(_q1(h, "lang") or None)})


def api_decks_create(h):
    body = _obj(h)
    h.send_json({"ok": True, "deck": decks.create_deck(body.get("name"), body.get("lang"))}, 201)


def api_deck_get(h, folder, slug):
    deck = decks.get_deck(folder, slug)
    h.send_json({"ok": True, "deck": deck, "items": decks.list_items(folder, slug)})


def api_deck_update(h, folder, slug):
    body = _obj(h)
    deck = decks.update_deck(folder, slug, name=body.get("name"), settings=body.get("settings"))
    h.send_json({"ok": True, "deck": deck})


def api_deck_delete(h, folder, slug):
    decks.delete_deck(folder, slug)
    h.send_json({"ok": True})


# ---------------------------------------------------------------- exercises

def api_item_add(h, folder, slug):
    """One exercise into the deck: the deck page's form, and the card
    sheets of the book reader and the video player, which say where the
    card was made (`origin`: decks._clean_origin keeps what it can link)."""
    body = _obj(h)
    item = decks.add_item(folder, slug, body.get("markdown"), origin=body.get("origin"),
                          force=body.get("force") is True, tags=body.get("tags"))
    # beside the item, as the copy answers them: a picture or a recording
    # the exercise names and the deck does not have, even from the clip
    # tray (the page says so, the item is saved)
    h.send_json({"ok": True, "item": item, "warnings": item.get("warnings") or []}, 201)


def api_item_get(h, folder, slug, item_id):
    item = decks.get_item(folder, slug, item_id)
    h.send_json({"ok": True, "item": item, "html": _render(folder, slug, item, preview=True)})


def api_item_update(h, folder, slug, item_id):
    body = _obj(h)
    item = decks.update_item(folder, slug, item_id, body.get("markdown"))
    h.send_json({"ok": True, "item": item, "warnings": item.get("warnings") or []})


def api_item_delete(h, folder, slug, item_id):
    decks.delete_item(folder, slug, item_id)
    h.send_json({"ok": True})


def api_item_duplicate(h, folder, slug, item_id):
    h.send_json({"ok": True, "item": decks.duplicate_item(folder, slug, item_id)}, 201)


def api_items_bulk(h, folder, slug):
    body = _obj(h)
    action = body.get("action")
    ids = body.get("ids")
    if action in ("copy", "move"):
        target = body.get("target")
        if not isinstance(target, dict):
            raise decks.DeckError("choose a destination deck")
        out = decks.transfer_items(folder, slug, ids, target.get("folder"),
                                   target.get("slug"), move=action == "move")
        h.send_json({"ok": True, "count": len(out["ids"]), "ids": out["ids"],
                     "warnings": out["warnings"]})
    else:
        count = decks.bulk_items(folder, slug, ids, action, body.get("tag"))
        h.send_json({"ok": True, "count": count})


def api_cram(h, folder, slug):
    items = decks.cram_items(folder, slug, _obj(h).get("ids"))
    h.send_json({"ok": True, "cards": [
        {"item": item, "html": _render(folder, slug, item, preview=False)}
        for item in items]})


def api_copy(h, folder, slug):
    """An exercise of a studio document into the deck (the "+ Deck" button).

    `source`, when given, is the prefix of the notes page the exercise sits
    on (a note beside a book or a video): the document is then read from
    that notes library, and a prefix that names none is refused before
    anything else is looked at."""
    body = _obj(h)
    source = body.get("source")
    library = None
    if source is not None and source != "":        # "" is the studio's own page
        library = notes_library(source)
        if library is None:
            raise decks.DeckError("those notes are not on this shelf")
    else:
        source = None
    doc_id = body.get("doc_id")
    if not isinstance(doc_id, str) or not store.ID_RE.match(doc_id):
        raise KeyError(doc_id)                  # -> 404 "document not found"
    subtype = body.get("subtype")
    if not isinstance(subtype, str):
        raise decks.DeckError("subtype must be the exercise's type")
    updated = body.get("updated")
    if updated is not None and not isinstance(updated, str):
        raise decks.DeckError("updated must be the document's timestamp")
    out = decks.copy_from_doc(folder, slug, doc_id, body.get("ordinal"), subtype, updated,
                              force=body.get("force") is True,
                              library=library, source=source)
    h.send_json({"ok": True, "item": out["item"], "warnings": out["warnings"],
                 "deck": decks.get_deck(folder, slug)}, 201)


def api_item_to_doc(h, folder, slug, item_id):
    """One exercise of the deck back into a studio document (the editor's
    "Load from a deck…"): the markdown to put in at the cursor, with its
    pictures and recordings copied into that document first.

    `source` is the notes prefix, as it is for api_copy, and means the same
    thing: the document is the one in that notes library, not the studio's."""
    body = _obj(h)
    source = body.get("source")
    library = None
    if source is not None and source != "":        # "" is the studio's own page
        library = notes_library(source)
        if library is None:
            raise decks.DeckError("those notes are not on this shelf")
    doc_id = body.get("doc_id")
    if not isinstance(doc_id, str) or not store.ID_RE.match(doc_id):
        raise KeyError(doc_id)                  # -> 404 "document not found"
    out = decks.copy_to_doc(folder, slug, item_id, doc_id, library=library)
    h.send_json({"ok": True, "markdown": out["markdown"],
                 "footnotes": out["footnotes"], "warnings": out["warnings"]})


def api_preview(h, folder, slug):
    """The exercise form's solved preview of unsaved markdown; `item` names
    the exercise being edited, whose footnotes the preview carries."""
    body = _obj(h)
    markdown = body.get("markdown")
    if not isinstance(markdown, str):
        raise decks.DeckError("markdown must be text")
    if not decks._text_ok(markdown):                 # a lone surrogate, as saving refuses it
        raise decks.DeckError("the exercise must be text")
    if len(markdown.encode("utf-8", "replace")) > decks.MAX_MARKDOWN:
        raise decks.DeckError("the exercise is larger than %d KB" % (decks.MAX_MARKDOWN // 1024))
    item_id = body.get("item")
    if item_id:
        footnotes = decks.get_item(folder, slug, item_id)["footnotes"]
    else:
        decks.get_deck(folder, slug)            # 404 for a deck that is not there
        footnotes = ""
    draft = {"markdown": _CTRL_RE.sub("", markdown), "footnotes": footnotes}
    # what the exercise names from the clip tray is not the deck's until it
    # is saved (decks.add_item brings it in): until then it plays from the tray
    html = decks.render_item({"lang": _lang_of(folder)}, draft,
                             decks.preview_assets(folder, slug, _asset_base(folder, slug)),
                             preview=True, docs=store.doc_index())
    h.send_json({"ok": True, "html": html})


# ---------------------------------------------------------------- studying

def _next(folder, slug, skip):
    """/next's answer (without "ok"): the card to study now, rendered as the
    learner sees it -- unsolved -- with the four interval labels."""
    card = decks.next_card(folder, slug, skip=skip)
    out = {"done": card["done"], "item": card["item"], "html": None,
           "intervals": card["intervals"], "counts": card["counts"],
           "next_due": card["next_due"]}
    if card["item"] is not None:
        out["html"] = _render(folder, slug, card["item"], preview=False)
    return out


def api_next(h, folder, slug):
    out = _next(folder, slug, _skip_ids(h.query.get("skip") or []))
    h.send_json(dict(out, ok=True))


def api_review(h, folder, slug):
    """Schedule one answer, and answer with the card that comes next.

    `reps` is the exercise's reps as the page showed it: an answer to a
    state the exercise has already left (another tab, a retry after a lost
    reply) is a 409 "reviewed", and nothing is written.  Once the answer is
    written, nothing that follows may turn it into a failure: the page would
    say it was not saved, and a second press would schedule it twice.  So a
    `next` that cannot be built is null (the page then asks /next itself)."""
    body = _obj(h)
    # the exercises skipped this session stay skipped: the study page may
    # name them here as on /next, in the body or the query
    skip = _skip_ids((h.query.get("skip") or []) + _skip_ids(body.get("skip") or []))
    decks.review(folder, slug, body.get("item"), body.get("rating"), body.get("result"),
                 reps=body.get("reps"))
    try:
        nxt = _next(folder, slug, skip)
    except GONE:
        raise
    except Exception:
        traceback.print_exc()
        nxt = None
    h.send_json({"ok": True, "next": nxt})


# ---------------------------------------------------------------- files

def api_export(h, folder, slug):
    data, name = decks.export_zip(folder, slug, _flag(h, "scheduling", True))
    h.send_bytes(data, "application/zip", 200,
                 {"Content-Disposition": 'attachment; filename="%s"' % name})


def api_image_upload(h, folder, slug):
    """A picture for the deck's flashcards, as the raw body; ?name=cat.png.

    The body is looked at before the deck: what is not a picture is refused
    without touching exercises/.  decks.add_image checks it again, names it
    and writes it; the answer is the path a picture field takes."""
    raw = h._body() or b""
    if not raw:
        raise decks.DeckError("the upload is empty: send the picture as the body")
    if store._img_kind(bytes(raw)) is None:
        raise decks.DeckError("only PNG, JPEG, SVG and PDF pictures can be added")
    name = decks.add_image(folder, slug, _q1(h, "name", "img") or "img", bytes(raw))
    h.send_json({"ok": True, "name": name, "path": "images/" + name,
                 "url": _asset_base(folder, slug) + "images/" + name}, 201)


def api_audio_upload(h, folder, slug):
    """A recording for the deck's cards, as the raw body; ?name=word.mp3.

    As a picture's upload: the body is looked at before the deck, so what is
    not a recording is refused without touching exercises/; decks.add_audio
    checks it again, names it and writes it."""
    raw = h._body() or b""
    if not raw:
        raise decks.DeckError("the upload is empty: send the recording as the body")
    if len(raw) > audiofile.MAX_BYTES:
        raise decks.DeckError("the recording is larger than %d MB" % (audiofile.MAX_BYTES // 2 ** 20))
    name = _q1(h, "name", "audio") or "audio"
    if audiofile.kind(bytes(raw[:4096]), name) is None:
        raise decks.DeckError("only %s recordings can be added" % audiofile.HUMAN)
    name = decks.add_audio(folder, slug, name, bytes(raw))
    h.send_json({"ok": True, "name": name, "path": "audio/" + name,
                 "url": _asset_base(folder, slug) + "audio/" + name}, 201)


def api_import(h):
    """A deck export as the raw body; ?scheduling=1|0&mode=new|replace|copy."""
    spool = getattr(h, "_spool", None)
    source = spool if spool else h._body()
    if not source:
        raise decks.DeckError("nothing to import: send the deck's zip as the body")
    out = decks.import_zip(source, scheduling=_flag(h, "scheduling", True),
                           mode=_q1(h, "mode", "new") or "new")
    h.send_json(dict(out, ok=True))


def api_backup(h):
    """Every deck on the shelf as one zip -- the studio's Backup, for the
    exercises.  A plain GET, so the button is a link and the browser saves
    it the way it saves any download."""
    data, name = decks.backup_zip()
    h.send_bytes(data, "application/zip", 200,
                 {"Content-Disposition": 'attachment; filename="%s"' % name})


def api_restore(h):
    """A backup put back: the zip the Backup button gives, as the body.

    ?replace=1 overwrites a deck that is already here; without it such a
    deck is kept and named in the answer, so a restore never quietly eats
    work that is newer than the backup.  The body is spooled to disk by the
    hub (serve.py's UPLOAD_ROUTES) for a shelf of any size, and read from
    there; the studio on its own still has its 32 MB body cap.
    """
    spool = getattr(h, "_spool", None)
    source = spool if spool else h._body()
    if not source:
        raise decks.DeckError("nothing to restore: send the backup zip as the body")
    out = decks.restore_zip(source, replace=_q1(h, "replace", "") == "1")
    h.send_json(dict(out, ok=True), 201)


def api_shutdown(h):
    fn = _SHUTDOWN["fn"]
    if fn is None:
        return h.send_json({"ok": False, "error": "this server cannot be stopped from here"}, 404)
    return fn(h)


# ---------------------------------------------------------------- routing

F = r"([a-z]+)"
S = r"([a-z0-9][a-z0-9-]*)"
I = r"([0-9a-f]{12})"

ROUTES = [
    ("GET",    r"^/$",                                        page_decks),
    ("GET",    r"^/deck/%s/%s/?$" % (F, S),                    page_deck),
    ("GET",    r"^/deck/%s/%s/study$" % (F, S),                page_study),
    ("GET",    r"^/deck/%s/%s/cram$" % (F, S),                 page_cram),
    ("GET",    r"^/media/%s/%s/images/([A-Za-z0-9._-]+)$" % (F, S), serve_image),
    ("GET",    r"^/media/%s/%s/audio/([A-Za-z0-9._-]+)$" % (F, S), serve_audio),
    ("GET",    r"^/api/decks$",                               api_decks_list),
    ("POST",   r"^/api/decks$",                               api_decks_create),
    ("GET",    r"^/api/decks/%s/%s$" % (F, S),                 api_deck_get),
    ("PATCH",  r"^/api/decks/%s/%s$" % (F, S),                 api_deck_update),
    ("DELETE", r"^/api/decks/%s/%s$" % (F, S),                 api_deck_delete),
    ("POST",   r"^/api/decks/%s/%s/items$" % (F, S),           api_item_add),
    ("GET",    r"^/api/decks/%s/%s/items/%s$" % (F, S, I),     api_item_get),
    ("PUT",    r"^/api/decks/%s/%s/items/%s$" % (F, S, I),     api_item_update),
    ("DELETE", r"^/api/decks/%s/%s/items/%s$" % (F, S, I),     api_item_delete),
    ("POST",   r"^/api/decks/%s/%s/items/%s/duplicate$" % (F, S, I), api_item_duplicate),
    ("POST",   r"^/api/decks/%s/%s/items/bulk$" % (F, S),     api_items_bulk),
    ("POST",   r"^/api/decks/%s/%s/items/%s/to-doc$" % (F, S, I),    api_item_to_doc),
    ("POST",   r"^/api/decks/%s/%s/images$" % (F, S),          api_image_upload),
    ("POST",   r"^/api/decks/%s/%s/audio$" % (F, S),           api_audio_upload),
    ("POST",   r"^/api/decks/%s/%s/copy$" % (F, S),            api_copy),
    ("POST",   r"^/api/decks/%s/%s/preview$" % (F, S),         api_preview),
    ("GET",    r"^/api/decks/%s/%s/next$" % (F, S),            api_next),
    ("POST",   r"^/api/decks/%s/%s/cram$" % (F, S),            api_cram),
    ("POST",   r"^/api/decks/%s/%s/review$" % (F, S),          api_review),
    ("GET",    r"^/api/decks/%s/%s/export$" % (F, S),          api_export),
    ("POST",   r"^/api/import$",                              api_import),
    ("GET",    r"^/api/backup$",                              api_backup),
    ("POST",   r"^/api/restore$",                             api_restore),
    ("POST",   r"^/api/shutdown$",                            api_shutdown),
]


def dispatch(h, method, sub):
    """Answer one request; `sub` is the path with BASE taken off."""
    sub = sub or "/"
    for m, pattern, fn in ROUTES:
        if m != method:
            continue
        match = re.fullmatch(pattern, sub)
        if not match:
            continue
        try:
            return fn(h, *match.groups())
        # the subclasses first: a Conflict and a NotFound are DeckErrors too
        except decks.Conflict as e:
            return h.send_json({"ok": False, "error": str(e), "conflict": e.kind}, 409)
        except decks.NotFound as e:
            return h.send_json({"ok": False, "error": str(e) or "not found"}, 404)
        except decks.DeckError as e:
            return h.send_json({"ok": False, "error": str(e)}, 400)
        except KeyError:
            return h.send_json({"ok": False, "error": "document not found"}, 404)
        except json.JSONDecodeError:
            return h.send_json({"ok": False, "error": "bad JSON body"}, 400)
        except store.StoreError as e:
            return h.send_json({"ok": False, "error": str(e)}, 400)
        except GONE:
            raise
        except Exception as e:          # surface it, and still answer
            traceback.print_exc()
            return h.send_json({"ok": False, "error": "%s: %s" % (type(e).__name__, e)}, 500)
    if method == "GET":
        return _not_found_page(h)
    return h.send_json({"ok": False, "error": "no such endpoint"}, 404)
