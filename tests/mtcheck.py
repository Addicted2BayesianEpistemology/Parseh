#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Does any of it actually reach a reader?  In a real browser.

    python3 tests/mtcheck.py              every pair installed under mt/
    python3 tests/mtcheck.py fa en        just that one
    python3 tests/mtcheck.py --panels     open a real book and a real video
    python3 tests/mtcheck.py --align      which words of a translation are the chunk's,
                                          and lib/getsyn.py's synonym table

WHY THIS IS NOT IN smoke.py.  The engine is WebAssembly and runs in a page,
so the only honest test of it needs a browser -- and a browser is not a thing
this toolbox otherwise depends on.  smoke.py checks everything about the
model that can be checked without one (that the glue is shared, that the
engine is asked to start, that the wasm is served as the type
`WebAssembly.instantiateStreaming` insists on); this runs the model.

It needs Playwright and a Chromium:

    pip install playwright && playwright install chromium

and a model, which `python3 lib/getmt.py fa en` fetches.  With neither it
says so and stops, rather than failing as though something were broken.

`--panels` is the other half, and the one that answers "does it reach a
reader": it parks the Persian fixture book and the Persian fixture video
where the server serves them, opens each in a browser, turns the switch on,
and looks at what the panel actually draws over an unglossed chunk -- the
dictionary's entries, the machine's reading of the sentence with this chunk's
share of it marked, the corpus's sentences, and the external-chatbot handoff. Then
it opens the gloss editor, opens the SOURCES SIDEBAR, and presses a button in
it: the same four have to be there in the same order, and pressing
`meaning ->` has to leave the sense in the meaning box and nothing at all in
the file.  It puts both fixtures back afterwards.  smoke.py checks that the
wiring is there; this checks that a person would see it.

And four things only a rectangle on a screen can answer.  WHERE THE SOURCES
OPEN: to the left of the fields, the window grown to hold them and still
wholly on the screen, and under the fields on a phone.  WHETHER THE THREE
BLOCKS ARE RULED APART, by a solid line and not a 1px dotted one.  WHETHER A
NOTE SAYS WHAT IT IS BEFORE IT IS CLICKED: a note is written into a seam of
each parked copy, its mark hovered, and the card has to come with the
note's text, go when the pointer leaves, and not stop the click from
opening the note.
And WHETHER A REAL VERB GOES IN AS A VERB: the server is asked, chunk by
chunk, until one comes back with a \\vb (a real dictionary, dict/fa.db, and
lib/verbs/fa.py), and pressing that hit's button has to leave a \\vb in the
book's vocabulary box and the verb's entry in the video's -- unsaved.
"""
import http.client
import io
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "lib"))
import getmt                                                  # noqa: E402
import languages                                              # noqa: E402

PORT = 8797
# One line per language, and one thing each is meant to show.  They are not a
# quality benchmark -- a 17 MB model is not going to read poetry -- but a
# translation that comes back empty, or in the wrong language, or identical to
# its input, is the engine being broken rather than the model being small.
SAMPLE = {
    "fa": "دوباره می‌سازمت، وطن",
    "it": "Mi manchi tanto.",
    "de": "Ich wohne seit drei Jahren in Hamburg.",
    "ja": "昼ご飯はもう食べました。",
    "ar": "أين المحطة من فضلك؟",
    "fr": "Je ne peux pas m'arrêter, je suis pressé.",
    "tr": "Yarın Roma'ya gidiyorum.",
    "hi": "मुझे तुम्हारी याद आती है।",
    "es": "Te echo mucho de menos.",
    "zh": "我昨天买了一本书。",
}


def check(ok, what, detail=""):
    print("  %-4s %s" % ("ok" if ok else "FAIL", what))
    if not ok and detail:
        print("       %s" % detail)
    return bool(ok)


def skip(what):
    """Something this machine cannot show -- no dictionary, a shelf already
    holding somebody's copy -- said by name and not counted as a failure."""
    print("  --   %s" % what)


# The window every page is opened in: a laptop's, and the size the sheet and
# the edit window were measured at when the sources moved to the left.
WIDE = {"width": 1280, "height": 800}
# ...and a phone's, where there is no room beside the fields at all.
NARROW = {"width": 390, "height": 844}


def _unwrite_one_voc(path):
    """Blank the first vocabulary line in a copy of a fixture.

    The panel is drawn only where nobody has written one, and the fixtures
    are fully glossed -- which is right for a fixture and useless here.
    """
    d = json.load(io.open(path, encoding="utf-8"))
    for seg in d.get("segments") or []:
        for ch in seg.get("chunks") or []:
            if ch.get("voc"):
                ch["voc"] = ""
                io.open(path, "w", encoding="utf-8").write(
                    json.dumps(d, ensure_ascii=False, indent=1))
                return True
    return False


# THE SOURCES SIDEBAR, driven the way a person drives it.  smoke.py can see
# that the code is there; only a browser can say whether pressing the button
# puts a sense in the box.  Each reader opens its editor its own way -- the
# book reader's pencil over the chunk under the pointer, the player's `edit`
# button in its cloud -- so the opening is per reader and everything after it
# is the same.
PEN_OPEN = """async (row) => {
    row.scrollIntoView({block: 'center'});
    await new Promise(r => setTimeout(r, 150));     // let the scroll land
    const pen = document.querySelector('#chpen');
    row.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
    if (pen.hidden) row.click();                   // no pointer to follow: a tap brings it
    await new Promise(r => setTimeout(r, 100));
    if (pen.hidden) return false;
    pen.click();
    await new Promise(r => setTimeout(r, 300));
    return !document.querySelector('#chbox').hidden;
}"""
OPEN_BOOK_EDITOR = """async () => {
    const rows = [...document.querySelectorAll('.pass.p2 .row')];
    const row = rows.find(e => !e.querySelector('.voc')) || rows[0];
    if (!row) return false;
    return await (%s)(row);
}""" % PEN_OPEN

OPEN_VIDEO_EDITOR = """async () => {
    const b = document.querySelector('#cloud .mkedit');
    if (!b) return false;
    b.click();
    await new Promise(r => setTimeout(r, 400));
    return !!document.querySelector('#cloud .eside');
}"""


# Where one element is on the screen, and the screen itself.
RECTS = """(sels) => {
    const out = {vw: document.documentElement.clientWidth || innerWidth,
                 vh: document.documentElement.clientHeight || innerHeight};
    for (const [k, s] of Object.entries(sels)) {
        const e = document.querySelector(s);
        const r = e ? e.getBoundingClientRect() : null;
        out[k] = r && r.width && r.height
            ? {l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height}
            : null;
    }
    return out;
}"""


def shape(page, what, door, parts):
    """The sources open TO THE LEFT and the window grows -- measured.

    They were a block above the fields inside the same sheet, so every entry
    they held pushed the box it was meant to fill below the fold.  `parts`
    names the sheet (the book's #chbox, the player's #cloud), the sources
    column and the fields column.  The sheet is measured with the sources
    shut, then open; it must be wider open, lie wholly inside the window, and
    have the sources to the left of the fields.  Returns the failures; the
    sources are left open.
    """
    bad = 0
    shut = page.evaluate("""async ([d, sels]) => {
        const b = document.querySelector(d);
        if (b && b.classList.contains('on')) {
            b.click(); await new Promise(r => setTimeout(r, 500)); }
        return (%s)(sels);
    }""" % RECTS, [door, {"sheet": parts["sheet"]}])
    page.evaluate("""async (d) => {
        const b = document.querySelector(d);
        if (b && !b.classList.contains('on')) b.click();
        await new Promise(r => setTimeout(r, 4000));
    }""", door)
    got = page.evaluate(RECTS, parts)
    sheet, side, main = got.get("sheet"), got.get("side"), got.get("main")
    if not check(sheet and side and main and side["r"] <= main["l"] + 1,
                 "%s's sources open to the LEFT of the fields (sources %s, "
                 "fields %s)" % (what, side and "%.0f..%.0f" % (side["l"], side["r"]),
                                 main and "%.0f..%.0f" % (main["l"], main["r"])),
                 repr(got)):
        bad += 1
    was_w = (shut.get("sheet") or {}).get("w") or 0
    if not check(sheet and sheet["w"] > was_w + 40,
                 "%s's window grows to hold them (%.0f -> %.0f px wide)"
                 % (what, was_w, (sheet or {}).get("w") or 0), repr(shut)):
        bad += 1
    if not check(sheet and sheet["l"] >= -1 and sheet["t"] >= -1
                 and sheet["r"] <= got["vw"] + 1 and sheet["b"] <= got["vh"] + 1,
                 "%s's grown window is wholly on the screen (%dx%d)"
                 % (what, got["vw"], got["vh"]), repr(sheet)):
        bad += 1
    return bad


def narrow(page, what, parts):
    """On a phone there is no room beside the fields: the sources go UNDER
    them.  The window is narrowed with the editor and the sources open, and
    put back afterwards."""
    bad = 0
    page.set_viewport_size(NARROW)
    page.wait_for_timeout(900)
    got = page.evaluate(RECTS, parts)
    side, main = got.get("side"), got.get("main")
    if not check(side and main and side["t"] >= main["b"] - 1,
                 "%s at %dx%d stacks the sources below the fields"
                 % (what, NARROW["width"], NARROW["height"]), repr(got)):
        bad += 1
    page.set_viewport_size(WIDE)
    page.wait_for_timeout(600)
    return bad


def dividers(page, what):
    """The dictionary, the machine's reading and the sentences somebody
    translated, ruled apart where a reader can see it.  The line between them
    was a 1px dotted --rule of 1.08:1 contrast, the same stroke that sat over
    each block's own source line, and the three read as one list."""
    bad = 0
    got = page.evaluate("""() => {
        const st = s => {
            const e = document.querySelector('#cloud ' + s);
            if (!e) return null;
            const c = getComputedStyle(e);
            return {style: c.borderTopStyle, width: parseFloat(c.borderTopWidth)};
        };
        return {dmt: st('.dmt'), dpairs: st('.dpairs'),
                ddict: !!document.querySelector('#cloud .dict .ddict')};
    }""")
    if not check(got["ddict"], "%s gives the dictionary's entries a block of their "
                               "own (.ddict)" % what):
        bad += 1
    for k, name in (("dmt", "the machine's reading"),
                    ("dpairs", "the sentences somebody translated")):
        st = got.get(k) or {}
        if not check(st.get("style") == "solid" and (st.get("width") or 0) >= 1.5,
                     "%s rules %s off with a solid line (%s %spx)"
                     % (what, name, st.get("style"), st.get("width")), repr(got)):
            bad += 1
    return bad


def sidebar(page, what, opener, door, body, field, parts):
    """Open the gloss editor, open the sidebar, and press a button in it.

    `door` is the button that opens the sidebar, `body` the column it fills,
    `field` the meaning box a source is meant to land in, `parts` the sheet
    and its two columns (see shape).  Returns the number of failures.
    """
    bad = 0
    if not check(page.evaluate(opener), "%s opens its gloss editor" % what):
        return 1
    if not check(page.locator(door).count() > 0,
                 "%s's gloss editor offers the sources" % what):
        return 1
    was = page.evaluate("""(f) => {
        const el = document.querySelector(f);
        return el ? el.value : null;
    }""", field)
    bad += shape(page, what, door, parts)
    heads = page.evaluate("""(b) => [...document.querySelectorAll(b + ' h4')]
                                    .map(e => e.textContent)""", body)
    if not check(len(heads) == 4,
                 "%s's sidebar holds its four source tools: %r" % (what, heads)):
        bad += 1
    order = " | ".join(heads).lower()
    if not check(order.find("dictionary") == 0
                 and 0 < order.find("machine") < order.find("translated")
                 < order.find("chatbot"),
                 "%s's sidebar keeps the panel's order: %r" % (what, heads)):
        bad += 1
    put = page.evaluate("""(b) => [...document.querySelectorAll(b + ' .sput button')]
                                   .map(e => e.textContent)""", body)
    if not check(len(put) > 0,
                 "%s's sidebar puts buttons on what it found (%d)"
                 % (what, len(put))):
        return bad + 1
    # press the first thing that offers to fill the meaning, and see the
    # meaning filled -- unsaved, in the form, which is the whole contract
    pressed = page.evaluate("""async (b) => {
        const btn = [...document.querySelectorAll(b + ' .sput button')]
                     .find(e => /meaning/i.test(e.textContent));
        if (!btn) return null;
        btn.click();
        await new Promise(r => setTimeout(r, 200));
        return btn.textContent;
    }""", body)
    if not check(pressed, "%s's sidebar offers to fill the meaning" % what):
        return bad + 1
    now = page.evaluate("""(f) => {
        const el = document.querySelector(f);
        return el ? el.value : null;
    }""", field)
    if not check(bool(now) and now != was,
                 "%s puts what was pressed (%s) into the meaning: %r"
                 % (what, pressed, (now or "")[:50])):
        bad += 1
    # and NOTHING went to the file: the page has asked nothing of the server
    saved = page.evaluate("""() => window.__mtcheck_saved || 0""")
    if not check(saved == 0,
                 "%s wrote nothing into the book: the box is unsaved" % what):
        bad += 1
    return bad + narrow(page, what, parts)


def post(path, body):
    """One JSON question to the server this run started, the way the page
    asks it -> the answer, or {} where there is none."""
    try:
        data = json.dumps(body).encode("utf-8")
        c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=60)
        c.request("POST", path, data, {"Content-Type": "application/json",
                                       "Content-Length": str(len(data))})
        return json.loads(c.getresponse().read().decode("utf-8"))
    except (OSError, ValueError):
        return {}


def note_peek(browser, what, url, notes, seams, marks, kind):
    """A note says what it is before it is clicked.

    One note is written through the notes route of the PARKED copy (never a
    book or a video somebody keeps: the caller asks only for its own copies)
    into the first seam the page draws, and the page is opened again to
    draw its mark.  Hovering the mark must bring the card up with the note's
    own text; leaving must take it away; and a click must still open the
    note, the card or no card.  Returns the failures.
    """
    bad = 0
    page = browser.new_page(viewport=WIDE)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.goto(url, wait_until="load")
    page.wait_for_timeout(2500)
    at = page.evaluate("""(s) => {
        const g = [...document.querySelectorAll(s)].find(e => e.dataset.at);
        return g ? g.dataset.at : '';
    }""", seams)
    j = post(notes + "/api/marks", {"side": "before", "kind": kind, "at": at,
                                    "target": "fa"}) if at else {}
    nid = (j.get("note") or {}).get("id") or ""
    if not check(bool(nid), "%s: a note is written into a seam of the parked copy"
                            % what, repr(j)[:200]):
        page.close()
        return bad + 1
    page.reload(wait_until="load")
    page.wait_for_timeout(2500)
    mark = page.locator(marks).first
    if not check(page.locator(marks).count() > 0, "%s draws the note's mark in "
                                                  "its seam" % what):
        page.close()
        return bad + 1
    mark.scroll_into_view_if_needed()
    page.wait_for_timeout(400)
    mark.hover()
    page.wait_for_timeout(900)
    card = page.evaluate("""() => {
        const p = document.querySelector('#ntpeek');
        if (!p) return null;
        return {shown: !p.hidden && getComputedStyle(p).display !== 'none',
                text: p.textContent, tags: [...p.querySelectorAll('*')]
                    .map(e => e.tagName.toLowerCase())};
    }""")
    if not check(card and card["shown"] and "Written by hand" in card["text"],
                 "%s: hovering the mark brings up the note's text before any "
                 "click: %r" % (what, ((card or {}).get("text") or "")[:70]), repr(card)):
        bad += 1
    if not check(card and set(card["tags"]) <= {"div"},
                 "%s: and the card holds text and nothing a note could have "
                 "smuggled in" % what, repr(card)):
        bad += 1
    page.mouse.move(4, WIDE["height"] - 4)
    page.wait_for_timeout(700)
    gone = page.evaluate("""() => {
        const p = document.querySelector('#ntpeek');
        return !p || p.hidden || getComputedStyle(p).display === 'none';
    }""")
    if not check(gone, "%s: leaving the mark takes the card away" % what):
        bad += 1
    mark.click()
    page.wait_for_timeout(900)
    opened = page.evaluate("""(id) => {
        const box = document.querySelector('#ntbox'),
              fr = document.querySelector('#ntframe');
        return !!box && !box.hidden && !!fr && (fr.getAttribute('src') || fr.src || '')
               .indexOf('/doc/' + encodeURIComponent(id)) >= 0;
    }""", nid)
    if not check(opened, "%s: and a click on the mark still opens the note" % what):
        bad += 1
    if errs:
        bad += 1
        check(False, "%s runs its notes without a page error" % what, errs[0][:110])
    page.close()
    return bad


# THE BOOK'S OWN QUESTION, asked of its own chunks from inside the page: the
# chunk as the reader holds it (SRC) and the sentence it sends with it
# (chunkCtx), until a hit comes back with a \vb.
BOOK_VERB = """async () => {
    for (let n = 0; n < SRC.length && n < 60; n++) {
        const fa = (SRC[n] || [])[1];
        if (!fa) continue;
        const r = await fetch('__lookup', {method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: fa, sentence: chunkCtx(n).sentence})});
        const j = await r.json();
        for (const w of (j.words || []))
            for (const h of (w.hits || []))
                if (h.vb && h.vb.tex) return {n: n, fa: fa, lemma: h.vb.lemma, tex: h.vb.tex};
    }
    return null;
}"""


def book_verb(browser, url):
    """A real verb, in the book: the chunk sheet's sources, a hit the server
    built a \\vb for, and its button.  Returns the failures."""
    what, bad = "the book reader", 0
    page = browser.new_page(viewport=WIDE)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(SAVE_HOOK)
    page.goto(url, wait_until="load")
    page.wait_for_timeout(2500)
    hit = page.evaluate(BOOK_VERB)
    if not hit:
        skip("%s: no chunk of the parked book comes back with a \\vb (is dict/fa.db "
             "installed?) -- the verb button is not pressed" % what)
        page.close()
        return 0
    opened = page.evaluate("""async (n) => {
        const row = document.querySelector('.pass.p2 .row[data-c="' + n + '"]');
        if (!row) return false;
        return await (%s)(row);
    }""" % PEN_OPEN, hit["n"])
    if not check(opened, "%s opens the chunk sheet on a verb chunk (%s)"
                         % (what, hit["fa"])):
        page.close()
        return 1
    got = page.evaluate("""async () => {
        const d = document.querySelector('#chsrc');
        if (d && !d.classList.contains('on')) d.click();
        let btn = null;
        for (let i = 0; i < 40 && !btn; i++) {
            await new Promise(r => setTimeout(r, 200));
            btn = [...document.querySelectorAll('#chsrcbody .sput button')]
                  .find(e => e.textContent.indexOf('\\\\vb') >= 0);
        }
        if (!btn) return null;
        const v = document.querySelector('#chvoc');
        v.value = '';
        v.dispatchEvent(new Event('input', {bubbles: true}));
        btn.click();
        await new Promise(r => setTimeout(r, 200));
        return {label: btn.textContent, value: v.value};
    }""")
    if not check(got and got["value"].startswith("\\vb{" + hit["lemma"] + "}"),
                 "%s: pressing %r on %s's hit puts a \\vb into the vocabulary: %r"
                 % (what, (got or {}).get("label"), hit["lemma"],
                    ((got or {}).get("value") or "")[:60]), repr(got)):
        bad += 1
    saved = page.evaluate("""() => window.__mtcheck_saved || 0""")
    if not check(saved == 0, "%s: and the \\vb is in the box, unsaved" % what):
        bad += 1
    if errs:
        bad += 1
        check(False, "%s runs the verb button without a page error" % what, errs[0][:110])
    page.close()
    return bad


def video_verb(browser, url, vid, ann):
    """A real verb, in the video: the phrase's edit window, its sources, the
    hit whose \\vb names the verb the phrase's word is a form of, and its
    button -- which puts the video's shape of it, `<word> <sound> (<lemma>
    ...)`.  Returns the failures."""
    what, bad = "the player", 0
    at = None
    d = json.load(io.open(ann, encoding="utf-8"))
    for si, sg in enumerate(d.get("segments") or []):
        for ci, ch in enumerate(sg.get("chunks") or []):
            if at or not ch.get("fa"):
                continue
            j = post("/youtube/api/lookup", {"video": vid, "text": ch["fa"],
                                             "sentence": sg.get("text") or ""})
            vbs = [h["vb"] for w in j.get("words") or [] for h in w.get("hits") or []
                   if h.get("vb")]
            # the first verb button is the first verb hit's: take a phrase
            # where that one is a form of its lemma, so its entry is hung on
            # the word -- `(<lemma> ...` -- and not the lemma's entry alone
            if vbs and "(%s " % vbs[0]["lemma"] in vbs[0]["here"]:
                at = (si, ci, ch["fa"], vbs[0]["lemma"])
    if not at:
        skip("%s: no phrase of the parked video comes back with a \\vb on a "
             "form of its verb (is dict/fa.db installed?) -- the verb button is "
             "not pressed" % what)
        return 0
    page = browser.new_page(viewport=WIDE)
    errs = []
    page.on("pageerror", lambda e: errs.append(str(e)))
    page.add_init_script(SAVE_HOOK)
    page.goto(url, wait_until="load")
    page.wait_for_timeout(3000)
    btn = page.locator("#dictmode")
    if btn.count() and "on" not in (btn.get_attribute("class") or ""):
        btn.click()
        page.wait_for_timeout(500)
    found = page.evaluate("""([si, ci]) => {
        const w = [...document.querySelectorAll('.w')].find(e =>
            e.dataset.j == ci && e.parentNode && e.parentNode.parentNode &&
            e.parentNode.parentNode.dataset.i == si);
        if (!w) return false;
        w.setAttribute('data-mtcheck', 'verb');
        w.scrollIntoView({block: 'center'});
        return true;
    }""", [at[0], at[1]])
    if not check(found, "%s shows the verb phrase %s" % (what, at[2])):
        page.close()
        return 1
    page.wait_for_timeout(500)
    page.locator('[data-mtcheck="verb"]').hover()
    page.wait_for_timeout(1500)
    if not check(page.evaluate(OPEN_VIDEO_EDITOR),
                 "%s opens the edit window on it" % what):
        page.close()
        return 1
    got = page.evaluate("""async () => {
        const d = document.querySelector('#cloud .esrc');
        if (d && !d.classList.contains('on')) d.click();
        let btn = null;
        for (let i = 0; i < 40 && !btn; i++) {
            await new Promise(r => setTimeout(r, 200));
            btn = [...document.querySelectorAll('#cloud .esrcbody .sput button')]
                  .find(e => /^add this verb/.test(e.title || ''));
        }
        if (!btn) return null;
        const v = document.querySelector("#cloud .ef[data-f='voc']");
        v.value = '';
        btn.click();
        await new Promise(r => setTimeout(r, 200));
        return {label: btn.textContent, value: v.value};
    }""")
    if not check(got and ("(%s " % at[3]) in got["value"],
                 "%s: pressing %r on %s's hit puts the verb's entry, hung on the "
                 "phrase's word, into the vocabulary: %r"
                 % (what, (got or {}).get("label"), at[3],
                    ((got or {}).get("value") or "")[:70]), repr(got)):
        bad += 1
    saved = page.evaluate("""() => window.__mtcheck_saved || 0""")
    if not check(saved == 0, "%s: and it is in the box, unsaved" % what):
        bad += 1
    if errs:
        bad += 1
        check(False, "%s runs the verb button without a page error" % what, errs[0][:110])
    page.close()
    return bad


# nothing the sidebar does may reach a file; counting the two save routes is
# how that is checked rather than asserted
SAVE_HOOK = """
    window.__mtcheck_saved = 0;
    const f = window.fetch;
    window.fetch = function (u) {
      const s = String((u && u.url) || u || '');
      if (/__edit\\/chunk|\\/youtube\\/api\\/edit/.test(s))
        window.__mtcheck_saved++;
      return f.apply(this, arguments);
    };"""


def panels(sync_playwright):
    """Open a real book and a real video, and see what the panel draws.

    The fixtures are copied rather than used in place, because the server
    serves `books/` and `youtube/videos/` and not `tests/fixtures/`.  One
    chunk of the video has its vocabulary line blanked in the COPY, because
    the panel appears only where nobody has written one -- the fixture is
    fully glossed, which is the right state for a fixture and the wrong one
    for this.
    """
    import shutil
    book_src = os.path.join(HERE, "fixtures", "books", "persian", "mini-fa")
    vid_src = os.path.join(HERE, "fixtures", "videos", "persian", "fA6bK2mQ8sT")
    book_at = os.path.join(ROOT, "books", "persian", "mtcheck-fa")
    vid_at = os.path.join(ROOT, "youtube", "videos", "persian", "fA6bK2mQ8sT")
    if not os.path.isdir(book_src) and not os.path.isdir(vid_src):
        print("mtcheck: no Persian fixtures here -- panels not checked.")
        return 0
    made, bad = [], 0
    # the shelf directory ships with a .gitkeep in it and must survive this;
    # only a directory THIS test created may be taken away again
    vid_dir = os.path.dirname(vid_at)
    made_dir = not os.path.isdir(vid_dir)
    if os.path.isdir(book_src) and not os.path.exists(book_at):
        shutil.copytree(book_src, book_at)
        made.append(book_at)
    if os.path.isdir(vid_src) and not os.path.exists(vid_at):
        shutil.copytree(vid_src, vid_at)
        made.append(vid_at)
        _unwrite_one_voc(os.path.join(vid_at, "annotations.json"))
    srv = subprocess.Popen([sys.executable, "serve.py", "--port", str(PORT),
                            "--local", "--http"], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(6)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for what, url, how in (
                    ("the book reader",
                     "http://127.0.0.1:%d/books/persian/mtcheck-fa/reader/" % PORT,
                     "click"),
                    ("the player",
                     "http://127.0.0.1:%d/youtube/v/fA6bK2mQ8sT" % PORT,
                     "hover")):
                page = b.new_page(viewport=WIDE)
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.add_init_script(SAVE_HOOK)
                page.goto(url, wait_until="load")
                page.wait_for_timeout(3000)
                btn = page.locator("#dictmode")
                if not btn.count() or btn.get_attribute("hidden") is not None:
                    bad += 0 if check(False,
                                      "%s shows the reading-help switch" % what) else 1
                    page.close()
                    continue
                check(True, "%s shows the switch: %s"
                      % (what, (btn.get_attribute("title") or "")[:60]))
                if "on" not in (btn.get_attribute("class") or ""):
                    btn.click()
                page.wait_for_timeout(700)
                # the book reader opens a cloud on a click, the player on hover
                if how == "click":
                    page.evaluate("""async () => {
                        const rows=[...document.querySelectorAll('.pass.p2 .row')]
                                    .filter(e=>!e.querySelector('.voc'));
                        if(rows.length) (rows[0].querySelector('.fa')||rows[0]).click();
                        await new Promise(r=>setTimeout(r,2500));
                    }""")
                else:
                    ws = page.locator(".w")
                    for i in range(min(ws.count(), 8)):
                        ws.nth(i).hover()
                        page.wait_for_timeout(2000)
                        if page.locator("#cloud .dict").count():
                            break
                for sel, name in ((".dict", "a panel"),
                                  (".dmt", "a machine's reading"),
                                  (".dpairs", "a sentence somebody translated")):
                    if not check(page.locator("#cloud " + sel).count() > 0,
                                 "%s draws %s over an unglossed chunk" % (what, name)):
                        bad += 1
                if not check(page.locator("#cloud .mtgo").count() == 0,
                             "%s asks for no button -- the reading is simply "
                             "there" % what):
                    bad += 1
                # the order a reader meets them in
                order = page.evaluate("""() => {
                    const c = document.querySelector('#cloud .dict');
                    return [...(c ? c.children : [])].map(e => e.className);
                }""")
                mt_at = next((i for i, c in enumerate(order) if "dmt" in c), -1)
                tat_at = next((i for i, c in enumerate(order) if "dpairs" in c), -1)
                if not check(0 <= mt_at < tat_at,
                             "%s draws the dictionary, then the model, then "
                             "the sentences somebody translated" % what,
                             repr(order)):
                    bad += 1
                bad += dividers(page, what)
                got = page.evaluate("""() => ({
                    out: (document.querySelector('#cloud .mtout')||{}).innerText || '',
                    here: (document.querySelector('#cloud .mthere')||{}).textContent || ''
                })""")
                if not check(bool(got["out"].strip()),
                             "%s reads the whole sentence: %r"
                             % (what, got["out"][:60])):
                    bad += 1
                if not check(bool(got["here"].strip()),
                             "%s marks which of its words are this chunk's: %r"
                             % (what, got["here"][:40])):
                    bad += 1
                if how == "click":
                    bad += sidebar(page, what, OPEN_BOOK_EDITOR, "#chsrc",
                                   "#chsrcbody", "#chen",
                                   {"sheet": "#chbox", "side": "#chside",
                                    "main": "#chbox .chmain"})
                else:
                    bad += sidebar(page, what, OPEN_VIDEO_EDITOR, "#cloud .esrc",
                                   "#cloud .esrcbody", "#cloud .ef[data-f='en']",
                                   {"sheet": "#cloud", "side": "#cloud .eside",
                                    "main": "#cloud .emain"})
                if errs:
                    bad += 1
                    check(False, "%s runs without a page error" % what, errs[0][:110])
                page.close()
            # THE NOTES AND THE VERB are asked only of copies this run made:
            # a note is written into the one it asks about, and a book or a
            # video already on the shelf is somebody's, not a test's
            book_url = "http://127.0.0.1:%d/books/persian/mtcheck-fa/reader/" % PORT
            vid_url = "http://127.0.0.1:%d/youtube/v/fA6bK2mQ8sT" % PORT
            if book_at in made:
                bad += note_peek(b, "the book reader", book_url,
                                 "/books/persian/mtcheck-fa/notes", ".gap",
                                 ".gap .mark", "sub")
                bad += book_verb(b, book_url)
            else:
                skip("books/persian/mtcheck-fa was there already: the book's note "
                     "preview and verb button are not tried on it")
            if vid_at in made:
                bad += note_peek(b, "the player", vid_url,
                                 "/youtube/v/fA6bK2mQ8sT/notes", "#segs .gap",
                                 "#segs .gap .mark", "cap")
                bad += video_verb(b, vid_url, "fA6bK2mQ8sT",
                                  os.path.join(vid_at, "annotations.json"))
            else:
                skip("youtube/videos/persian/fA6bK2mQ8sT was there already: the "
                     "player's note preview and verb button are not tried on it")
            b.close()
    finally:
        srv.terminate()
        for d in made:
            shutil.rmtree(d, ignore_errors=True)
        if made_dir:
            try:
                os.rmdir(vid_dir)
            except OSError:
                pass
    return bad


def aligner(sync_playwright):
    """Which words of the machine's sentence are the chunk's -- by MEANING.

    lib/mt.js's align used to prefer the part of the translation sitting
    where the chunk sits in its sentence, and to fall back on that place when
    no word matched.  Word order is what a translation changes, so the mark
    now comes from what the dictionary says the chunk's words mean, and from
    the chunk translated on its own; where nothing matches, nothing is
    marked.  tests/fixtures/align/cases.json holds real cases, frozen: the
    model's own sentence, the chunk's own translation and the dictionary's
    own answer, each with what the mark must (or must not) be.

    Needs no server, no model and no dictionary: only the page and mt.js.
    Measured on 393 fixture chunks with the human gloss as the reference
    (2026-09-10): Persian marks right 76% -> 84% and wrong 21% -> 4%;
    Chinese, Spanish and Italian wrong 10%, 4%, 0% -> 0%.
    """
    path = os.path.join(HERE, "fixtures", "align", "cases.json")
    cases = json.load(io.open(path, encoding="utf-8"))["cases"]
    bad = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto("about:blank")
        page.add_script_tag(path=os.path.join(ROOT, "lib", "mt.js"))
        for c in cases:
            got = page.evaluate("""c => {
                const s = ParsehMT.align(c.target, c.probe, c.words, 'en');
                return s && {text: s.text, why: ParsehMT.why(s),
                             marked: ParsehMT.marked(c.target, s)
                                       .filter(x => x.here).map(x => x.text)};
            }""", c)
            exp = c["expect"]
            text = (got or {}).get("text")
            ok = True
            if "text" in exp:
                ok = ok and text == exp["text"]
            if "contains" in exp:
                ok = ok and bool(text) and exp["contains"] in text
            for no in exp.get("not") or []:
                ok = ok and not (text and no in text)
            # the marked pieces, put back together, are the text the line names
            ok = ok and (got is None or " … ".join(got["marked"]) == text)
            if not check(ok, "[%s] %s: %r%s" % (c["lang"], c["why"], text,
                                                 (" -- " + got["why"]) if got and got["why"] else ""),
                         "expected %r in %r" % (exp, c["target"])):
                bad += 1
        # A NUMBER WHERE THE WORDS GO -- an old caller's place in the
        # sentence -- is ignored: it marks by the chunk's own translation or
        # not at all, never by the place
        got = page.evaluate("""() => {
            const s = ParsehMT.align('Did you feed the dog this morning?', 'this morning', 0.1);
            return s && s.text;
        }""")
        if not check(got == "morning?", "a number where the words go is not read as a place: %r"
                     % got):
            bad += 1
        if errs:
            bad += 1
            check(False, "the aligner runs without a page error", errs[0][:110])
        b.close()
    return bad


def synonyms(sync_playwright):
    """Weaker evidence than the word itself: lib/getsyn.py's table.

    A synonym match is scored below an exact or an inflected one (SYN_Q in
    lib/mt.js), so a chunk with a real word in the reading is never outvoted
    by a synonym found for a different word of it -- and it is admitted
    ALONE only from the word's own first dictionary sense, and only ever
    extends a mark that is already strong.  Both rules were forced by a
    garbled reading: "Lord of the Lord, the Lord of the Lord" (a repeated
    weak match joining itself, unbounded, before the first rule) and a
    second, unrelated dictionary hit lending its synonym to a word the
    chunk's real hit never meant (before the second).

    Needs `mt/synonyms.en.json` on disk (python3 lib/getsyn.py) and a real
    server -- fetching it by a relative URL from about:blank answers
    nothing, which is why this is not folded into `aligner` above.
    """
    if not os.path.isfile(os.path.join(ROOT, "mt", "synonyms.en.json")):
        print("mtcheck: no mt/synonyms.en.json here -- synonyms not checked.")
        print("  python3 lib/getsyn.py")
        return 0
    sys.path.insert(0, os.path.join(ROOT, "lib"))
    import getsyn
    bad = 0
    srv = subprocess.Popen([sys.executable, "serve.py", "--port", str(PORT),
                            "--local", "--http"], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(6)
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto("http://127.0.0.1:%d/settings/reading-help/" % PORT, wait_until="load")
            page.add_script_tag(url="/lib/mt.js")

            # --- THE TWO STEMMERS AGREE.  lib/getsyn.py ports lib/mt.js's
            # `stem` by hand, because the table has to be keyed the way a
            # live match looks a word up; this is the check that they never
            # drift apart, on the same word list the module docstrings of
            # both files point at.
            words = ("begin started starting starts liked likes liking dogs boxes "
                     "buzzes running stopped fallen fell rebuild rebuilt colour "
                     "colours coloured centre centres theatre realise realised "
                     "realising organise happiness goalless careful careless flies "
                     "fried tried cities parties boys toys grey gray happier "
                     "happiest women children mice geese went gone getting "
                     "children's dog's cat's don't can't").split()
            py = [getsyn.stem(w) for w in words]
            js = page.evaluate("ws => ws.map(w => ParsehMT._stem(w, true))", words)
            mismatch = [(w, p_, j) for w, p_, j in zip(words, py, js) if p_ != j]
            if not check(not mismatch,
                         "lib/getsyn.py's stem and lib/mt.js's agree on %d words"
                         % len(words), json.dumps(mismatch, ensure_ascii=False)):
                bad += 1

            # --- THE TABLE LOADS, on its own -- has() on a pair this
            # machine's mt/ actually carries starts the fetch (see lib/mt.js
            # synLoad); translate() is only ever the backstop.
            pairs = getmt.installed()
            pairs = [(a, g) for a, g in pairs if getmt.available(a, g)]
            if pairs:
                a, g = pairs[0]
                page.evaluate("([a, g]) => ParsehMT.has(a, g)", [a, g])
            else:
                page.evaluate("() => { try { ParsehMT.translate('en','en','x'); } "
                              "catch (e) {} }")
            page.wait_for_timeout(1500)
            n = page.evaluate("() => ParsehMT._syn && Object.keys(ParsehMT._syn).length")
            if not check(n and n > 1000,
                         "the synonym table loads on its own, without a "
                         "translation having been asked for first: %r entries" % n):
                bad += 1
            begin_syn = page.evaluate("() => ParsehMT._syn.begin")
            if not check(begin_syn and "start" in begin_syn,
                         "begin and start are in it, both ways",
                         json.dumps(begin_syn)):
                bad += 1

            # --- THE PAGE SOMEBODY WOULD ACTUALLY PRESS.  The reading help's
            # own get/rebuild/remove row for the table (Settings, TO-DO
            # §11.10), the same pattern as a dictionary's -- because the
            # resource this whole section tests is worth nothing to a reader
            # who never finds the button that fetches it.
            row = page.evaluate("() => (document.querySelector('[data-row=\"synonyms:\"]')"
                                "||{}).innerText || ''")
            if not check("Remove" in row and "Rebuild" in row and "Installed" in row,
                         "the reading help offers to remove and rebuild the table it "
                         "already found installed", repr(row[:120])):
                bad += 1

            # --- A REPEATED WEAK MATCH DOES NOT JOIN ITSELF.  A dictionary
            # hit whose only synonym for "master" is "lord", read against a
            # translation that says "lord" four times running (the shape a
            # garbled reading takes), must not chain the whole line into one
            # mark: at most a few short, separate ones.
            garbled = ("And the lord of the lord, the lord of the lord, the lord "
                      "of the lord, the lord of the lord.")
            words_hit = [{"word": "x", "hits": [{"headword": "x", "senses": ["master"]}]}]
            span = page.evaluate(
                "x => { const s = ParsehMT.align(x[0], x[1], x[2], 'en'); "
                "return s && {ranges: s.ranges.length, span: s.to - s.from, sure: s.sure}; }",
                [garbled, "the master", words_hit])
            if not check(span is None or span["ranges"] <= 3,
                         "a repeated synonym does not chain every repeat "
                         "into one mark (bounded to at most 3 places, not "
                         "one span swallowing the whole line)", json.dumps(span)):
                bad += 1

            # --- ONE HIT'S SYNONYM DOES NOT ANSWER FOR ANOTHER HIT'S WORD.
            # A word with two dictionary hits -- one meaning "village", a
            # second, unrelated one meaning "to populate" -- must not have
            # its "village" sense answered by "living", which is only the
            # SECOND hit's synonym: exactly the pueblo/poblar case measured
            # against real Tatoeba sentences.
            two_hit_words = [{"word": "x", "hits": [
                {"headword": "pueblo", "senses": ["town, village"]},
                {"headword": "poblar", "senses": ["to populate"]}]}]
            r = page.evaluate(
                "x => { const s = ParsehMT.align(x[0], x[1], x[2], 'en'); return s && s.text; }",
                ["there was a baker living in a small town.", "a small village", two_hit_words])
            if not check(r is None or "living" not in r,
                         "a second, unrelated hit's synonym is not enough on "
                         "its own to mark a word the chunk's real sense never "
                         "meant: %r" % r):
                bad += 1

            # --- AN EXACT MATCH OUTVOTES A COMPETING SYNONYM.  Two places
            # in the reading could be marked -- one is the word itself
            # (help), the other only a synonym of it (aid) -- and the word
            # itself is where the mark goes.
            r = page.evaluate(
                "x => { const s = ParsehMT.align(x[0], x[1], x[2], 'en'); return s && s.text; }",
                ["We asked for aid, and they helped us at once.", "help",
                 [{"word": "x", "hits": [{"headword": "x", "senses": ["help"]}]}]])
            if not check(r == "helped",
                         "the word itself (helped) wins over a synonym of it "
                         "(aid) standing earlier in the same line: %r" % r):
                bad += 1

            if errs:
                bad += 1
                check(False, "the synonym table runs without a page error", errs[0][:110])
            b.close()
    finally:
        srv.terminate()
    return bad


def main(argv):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("mtcheck: no Playwright here -- nothing was run.")
        print("  pip install playwright && playwright install chromium")
        return 0
    if "--align" in argv:
        bad = aligner(sync_playwright) + synonyms(sync_playwright)
        print("")
        print("align: %d failed" % bad)
        return 1 if bad else 0
    if "--panels" in argv:
        # the aligner's own cases first: they need nothing but the page
        bad = aligner(sync_playwright) + synonyms(sync_playwright) + panels(sync_playwright)
        print("")
        print("panels: %d failed" % bad)
        return 1 if bad else 0
    if not getmt.engine_ready():
        print("mtcheck: the engine is not here -- nothing was run.")
        print("  python3 lib/getmt.py --engine")
        return 0
    pairs = getmt.installed()
    if argv:
        pairs = [(argv[0], argv[1] if len(argv) > 1 else "en")]
    pairs = [(a, b) for a, b in pairs if getmt.available(a, b)]
    if not pairs:
        print("mtcheck: no model installed -- nothing was run.")
        print("  python3 lib/getmt.py fa en")
        return 0

    srv = subprocess.Popen([sys.executable, "serve.py", "--port", str(PORT),
                            "--local", "--http"], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(6)
    bad = 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            page.goto("http://127.0.0.1:%d/settings/reading-help/" % PORT, wait_until="load")
            ct = page.evaluate("""async () => {
                const r = await fetch('/mt/engine/bergamot-translator-worker.wasm',
                                      {method: 'HEAD'});
                return r.headers.get('content-type');
            }""")
            if not check(ct == "application/wasm",
                         "the engine is served as application/wasm", repr(ct)):
                bad += 1
            page.add_script_tag(url="/lib/mt.js")
            for a, g in pairs:
                text = SAMPLE.get(a)
                if not text:
                    print("  --   no sample sentence for %s; skipped" % a)
                    continue
                A = languages.get_or_default(a)
                t0 = time.time()
                out = page.evaluate(
                    """async ([from, to, text]) => {
                        try { return await ParsehMT.translate(from, to, text); }
                        catch (e) { return 'ERROR: ' + (e && e.message); }
                    }""", [a, g, text])
                took = time.time() - t0
                ok = (isinstance(out, str) and out.strip()
                      and not out.startswith("ERROR:")
                      and out.strip() != text.strip())
                # it must come back in the GLOSS language, which for a script
                # language means it must have stopped being in the source's
                if ok and A.chars is not None:
                    ok = not A.has_script(out)
                if not check(ok, "%s -> %s translates (%.1fs): %r"
                                 % (a, g, took, (out or "")[:70])):
                    bad += 1
            for e in errs[:3]:
                print("       page error: %s" % e[:120])
            b.close()
    finally:
        srv.terminate()
    print("")
    print("%d pair(s) checked, %d failed" % (len(pairs), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
