#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""The mobile interface's pages that the server writes (docs/mobile.md).

    mobile.books_page()     /m/books/, the book shelf as a phone reads it
    mobile.install_page(t)  /m/install/, installing the mobile interface as an app
    mobile.offline_page()   /m/offline/, what the app shows when the server is away
    mobile.manifest()       /manifest.webmanifest, the app's description
    mobile.app_head()       the tags that make a page part of the app
    mobile.mode_switch()    the Browser | Mobile switch, for a page's bar

The mobile interface is a second set of pages made to be READ on a phone:
one column, targets a finger can hit, and nothing on them that edits.  Most
of them are a second layout of the page they stand for -- the hub, the
exercise decks, a book's reader -- and need nothing here.  The book library
is the exception: books/index.html is a static page (lib/make_index.py)
written when a book is built or put on the shelf, so a layout added to it
would reach nobody's library until the next build.  Its mobile version is a
page of its own instead, written on every request from the shelf itself,
and lib/parseh.js routes every link to /books/ there in the mobile mode.

WHAT THE SHELF SAYS.  What the browser library's card says about a book,
less everything that manages the shelf: no delete, no build, no bundle
coming in or going out.  A book whose reader has never been built has
nothing to open, and a phone cannot build it, so its card says so and is not
a link.  Everything that CAN be tapped goes to a reader, where the mobile
layer (lib/mobilereader.js) takes over.
"""
import html
import os
import sys

LIB = os.path.dirname(os.path.realpath(__file__))
if LIB not in sys.path:
    sys.path.insert(0, LIB)
import books as booklib                                      # noqa: E402
import languages                                             # noqa: E402
import make_index                                            # noqa: E402

APP_NAME = "Parseh"


def esc(s):
    return html.escape(s or "", quote=True)


# ---------------------------------------------------------------- the app
# PARSEH AS AN APP (docs/mobile.md).  A phone's browser installs a site as an
# app -- an icon on the home screen, opening on the whole screen with no
# address bar -- when the site describes itself (the manifest below, linked
# from every page by app_head()), has a service worker (lib/sw.js, served at
# /sw.js), and is served over https with a certificate the phone trusts
# (serve.py's authority, handed over by /m/install/).  The app is the MOBILE
# INTERFACE: it opens on the mobile hub, with the mode set to mobile.
ICONS = "/lib/icons/"
# the light palette's ground (lib/parseh.css --bg), which the app's splash
# screen and the pages start on; and the dark one's, for a phone set dark
LIGHT_BG, DARK_BG = "#f3eff1", "#171214"
ACCENT = "#be3455"


def manifest():
    """The app's description, as /manifest.webmanifest serves it."""
    return {
        "id": "/",
        "name": APP_NAME,
        "short_name": APP_NAME,
        "description": "Reading editions with their narration, videos with their "
                       "transcripts, and exercise decks: the mobile interface.",
        "lang": "en",
        "dir": "ltr",
        # the app opens on the mobile hub, in the mobile mode (parseh.js
        # takes ?mode= off the address once it has set it)
        "start_url": "/?mode=mobile",
        "scope": "/",
        # the whole screen, a phone's own bars and all, where the phone can
        # (Android); where it cannot, an app's window with no address bar
        "display": "fullscreen",
        "display_override": ["fullscreen", "standalone"],
        "orientation": "any",
        "background_color": LIGHT_BG,
        "theme_color": ACCENT,
        "icons": [
            {"src": ICONS + "parseh-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": ICONS + "parseh-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": ICONS + "parseh-maskable-512.png", "sizes": "512x512", "type": "image/png",
             "purpose": "maskable"},
        ],
    }


def app_head():
    """The tags that make a page part of the app: the manifest (which names
    the icons), the colour of the phone's bars, and Apple's own names for
    the same things (an iPhone reads these when it adds a page to its home
    screen).  Not a favicon: a page keeps its own.  Every page of the mobile
    interface carries them -- the hub, the shelf, the decks -- and
    lib/parseh.js adds them to a page that has none (every book's reader,
    built without them)."""
    return ('<link rel="manifest" href="/manifest.webmanifest">\n'
            '<link rel="apple-touch-icon" href="%(i)sapple-touch-icon.png">\n'
            '<meta name="theme-color" content="%(l)s" media="(prefers-color-scheme: light)">\n'
            '<meta name="theme-color" content="%(d)s" media="(prefers-color-scheme: dark)">\n'
            '<meta name="mobile-web-app-capable" content="yes">\n'
            '<meta name="apple-mobile-web-app-capable" content="yes">\n'
            '<meta name="apple-mobile-web-app-title" content="%(n)s">\n'
            '<meta name="apple-mobile-web-app-status-bar-style" content="default">'
            % {"i": ICONS, "l": LIGHT_BG, "d": DARK_BG, "n": APP_NAME})


def offline_page():
    """/m/offline/: what the app shows when the server cannot be reached --
    the computer asleep or off, the phone away from its network.  The
    service worker keeps it (lib/sw.js), so it is written to stand alone:
    no stylesheet, no script from anywhere, both palettes in itself."""
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(app)s is not reachable</title>
<style>
:root{color-scheme:light dark;--bg:%(l)s;--card:#fff;--ink:#241e21;--dim:#6b5d62;--accent:%(a)s;--fg:#fff}
@media (prefers-color-scheme:dark){:root{--bg:%(d)s;--card:#211a1d;--ink:#e6dade;--dim:#ac9ba1;
  --accent:#ee8aa3;--fg:#171214}}
html,body{margin:0;background:var(--bg);color:var(--ink);
  font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:480px;margin:0 auto;padding:max(12vh,24px) 20px 24px}
.glyph{display:inline-flex;align-items:center;justify-content:center;width:56px;height:56px;
  border-radius:50%%;background:var(--accent);color:var(--fg);font-size:28px;padding-bottom:6px;
  box-sizing:border-box}
h1{font-size:22px;line-height:1.3;margin:18px 0 8px}
p{margin:0 0 12px;color:var(--dim)}
button{font:inherit;font-size:17px;min-height:52px;width:100%%;margin-top:14px;border:0;
  border-radius:12px;background:var(--accent);color:var(--fg);cursor:pointer}
</style>
</head><body>
<main>
  <span class="glyph" lang="fa" aria-hidden="true">&#x67E;</span>
  <h1>%(app)s cannot be reached</h1>
  <p>%(app)s runs on your computer, and this phone cannot reach it now: the
  computer may be asleep or off, or the phone away from its network (and
  from Tailscale, if that is how it reaches it).</p>
  <p>Once the computer is on and %(app)s is started there, try again.</p>
  <button type="button" onclick="location.reload()">Try again</button>
</main>
</body></html>
""" % {"app": APP_NAME, "l": LIGHT_BG, "d": DARK_BG, "a": ACCENT}


def mode_switch():
    """The switch between the browser and the mobile interface, for a page's
    top bar: two buttons parseh.js wires (Parseh.mode), the one in force
    filled in.  Which one that is, the page learns from <html data-mode>
    before it paints; aria-pressed here is only where it starts."""
    return ('<span class="parseh-mode" role="group" aria-label="interface">'
            '<button type="button" data-parseh-mode="browser" aria-pressed="true" '
            'title="the browser interface: every page, with everything that edits">'
            'Browser</button>'
            '<button type="button" data-parseh-mode="mobile" aria-pressed="false" '
            'title="the mobile interface: pages made for a phone, to read and to study, '
            'with nothing on them that edits">Mobile</button></span>')


def bar(where):
    """The mobile layout's bar, as the hub's: the way home, where this is,
    the switch and the theme -- nothing that stops or administers anything.
    A .parseh-bar, so on a phone it slides away on the way down and comes
    back on the way up like every other bar (parseh.js, bars())."""
    return ('<div class="parseh-bar m-bar">\n'
            '  <a class="home" href="/"><span class="glyph" lang="fa">&#x67E;</span>'
            '<span class="word">%s</span></a>\n'
            '  <span class="m-where">%s</span>\n'
            '  <span class="sp"></span>\n'
            '  %s\n'
            '  <button type="button" data-parseh-theme title="theme">&#9680;</button>\n'
            '</div>' % (APP_NAME, esc(where), mode_switch()))


def reader_href(b):
    """A book's reader, by the hub's own absolute address (the page is only
    ever served, never opened off the disk)."""
    return "/books/%s/reader/" % b.rel_from_books()


def book_card(b):
    """One book on the mobile shelf: a link to its reader, or -- a book never
    built -- a card that says so and opens nothing."""
    st = make_index.stats(b)
    L = b.lang
    attrs = L.html_attrs()
    tags = []
    if b.meta.get("draft"):
        tags.append('<span class="tag on">draft</span>')
    if st.get("built"):
        n = len(st.get("chapters", []))
        tags.append('<span class="tag">%d chapter%s</span>' % (n, "" if n == 1 else "s"))
        if b.has_audio:
            timed, subs = st.get("timed", 0), st.get("subs", 0)
            tags.append('<span class="tag on">narrated &middot; %d/%d timed</span>'
                        % (timed, subs))
    else:
        tags.append('<span class="tag no">not built yet</span>')
    title = ('<div class="m-btitle"%s>%s</div>' % (attrs, esc(b.title))) if b.title else ""
    author = ('<div class="m-bby"%s>%s</div>' % (attrs, esc(b.author))) if b.author else ""
    latin = esc(b.title_latin or b.slug)
    if b.author_latin:
        latin += " <i>&mdash; %s</i>" % esc(b.author_latin)
    blurb = b.meta.get("blurb", "")
    inner = """  %s%s
  <div class="m-blat">%s</div>%s
  <div class="m-tags">%s</div>""" % (
        title, author, latin,
        ('\n  <div class="m-bblurb">%s</div>' % esc(blurb)) if blurb else "",
        "".join(tags))
    if not st.get("built"):
        # nothing to open: a phone does not build a book (docs/mobile.md)
        return ('<div class="m-book m-off" data-lang="%s">\n%s\n'
                '  <div class="m-bnote">Its reader has not been built yet: that is done in '
                'the browser interface, from the book&rsquo;s card in the library.</div>\n'
                '</div>' % (esc(L.code), inner))
    # data-subs: how many subparagraphs the reader has, which is what the
    # reading place it keeps (a subparagraph's index) is counted against
    return ('<a class="m-book" href="%s" data-lang="%s" data-subs="%d">\n%s\n</a>'
            % (esc(reader_href(b)), esc(L.code), int(st.get("subs", 0) or 0), inner))


def lang_head(L, n):
    """The heading over one language's books: its English name, its own
    name in its own face, how many."""
    return ('<h2 class="m-lhead" data-lang="%s"><span class="name">%s</span>'
            '<bdi class="native"%s>%s</bdi><span class="n">%d</span></h2>'
            % (esc(L.code), esc(L.name), L.html_attrs(), esc(L.native), n))


# THE READING PLACE, where the phone has one.  The reader keeps it in this
# browser's localStorage, under bk_pos: and its own address, as {i: the
# subparagraph's index} (lib/tex2html.py, save()); the library links a reader
# by reader/index.html and this page by reader/, so both addresses are asked.
# A card whose book has been read on here says how far, and links the address
# the place was kept under, so the reader opens at it.  Nothing is written.
READ_ON_JS = r"""<script>
(function () {
  var cards = document.querySelectorAll('a.m-book[data-subs]');
  for (var i = 0; i < cards.length; i++) {
    var a = cards[i], base = a.getAttribute('href'), subs = +a.getAttribute('data-subs') || 0;
    var at = null, where = base;
    [base, base + 'index.html'].forEach(function (p) {
      if (at !== null) return;
      try {
        var v = JSON.parse(localStorage.getItem('bk_pos:' + p) || 'null');
        if (v && typeof v.i === 'number' && v.i > 0) { at = v.i; where = p; }
      } catch (e) {}
    });
    if (at === null || !subs) continue;
    var pct = Math.max(1, Math.min(100, Math.round((at + 1) * 100 / subs)));
    var tag = document.createElement('span');
    tag.className = 'tag on m-readon';
    tag.textContent = 'read on · ' + pct + '%';
    var tags = a.querySelector('.m-tags');
    if (tags) tags.insertBefore(tag, tags.firstChild);
    a.style.setProperty('--m-read', pct + '%');
    a.classList.add('m-read');
    a.setAttribute('href', where);
  }
})();
</script>"""


# What this phone is doing about the app, said live on /m/install/: in the
# app already; a browser that installs nothing; a page not trusted (the
# service worker refused -- the certificate); ready, with the browser's own
# Install behind the button (parseh.js keeps it: Parseh.app).
INSTALL_JS = r"""<script>
(function () {
  var say = document.getElementById('m-appnow'), P = window.Parseh;
  function put(cls, text) { say.className = 'm-appnow ' + cls; say.textContent = text; }
  function look() {
    if (P && P.app && P.app.standalone()) {
      put('ok', 'This is the app: Parseh is installed on this phone, and open on its whole screen.');
      return;
    }
    if (!('serviceWorker' in navigator) || !window.isSecureContext) {
      put('no', location.protocol === 'http:' && !/^(localhost|127\.)/.test(location.hostname)
        ? 'This page came over plain http: a phone installs an app only from https.'
        : 'This browser cannot install a site as an app. On Android use Chrome; on an iPhone, Safari.');
      return;
    }
    put('wait', 'Asking this browser whether it can install Parseh…');
    navigator.serviceWorker.register('/sw.js').then(function () {
      if (P && P.app && P.app.canPrompt())
        put('ok', 'Ready: this phone trusts Parseh, and its browser can install it. Step 2.');
      else
        put('ok', 'This phone trusts Parseh. Install it as step 2 says: the browser has not offered ' +
                  'its own Install button on this page, or it has been used already.');
    }, function () {
      put('no', 'This phone does not trust Parseh’s certificate yet: step 1 first, then open this page again.');
    });
  }
  if (P && P.app) P.app.onChange(look);
  look();
})();
</script>"""


def install_page(tls):
    """/m/install/: how to install the mobile interface on this phone as an
    app.  `tls` says what the server speaks: "authority" (serve.py's own
    certificate, whose authority this page hands over), "own" (one put in
    .tls/ by hand, which a phone may trust already), or "http"."""
    if tls == "authority":
        cert = """  <section class="m-step">
    <h2><span class="m-n">1</span> This phone trusts Parseh</h2>
    <p>Parseh makes its own certificate, so a phone trusts it only once it has been told
    to &mdash; that is the warning a browser shows the first time. A browser tab goes on after
    the warning; an app does not. Tell this phone once, and it trusts every certificate
    Parseh makes from then on.</p>
    <a class="m-btn" href="/m/install/parseh-ca.crt">Download the certificate</a>
    <p class="m-how"><b>Android:</b> open <i>Settings</i> and search for <i>CA certificate</i>
    (it is under <i>Security</i>, <i>Encryption &amp; credentials</i>, <i>Install a
    certificate</i>); choose <i>CA certificate</i>, <i>Install anyway</i>, and pick
    <i>Parseh-CA.crt</i> from the downloads. Then close this tab and open Parseh again.</p>
    <p class="m-how"><b>iPhone, iPad:</b> allow the download; then in <i>Settings</i>, open
    <i>Profile Downloaded</i> and <i>Install</i> it; then <i>General</i>, <i>About</i>,
    <i>Certificate Trust Settings</i>, and turn on full trust for <i>Parseh local
    authority</i>.</p>
    <p class="m-small">It can vouch for this computer and nothing else: only for its own
    name, its local and Tailscale addresses. It is taken off the phone where it was put on,
    in the same settings.</p>
  </section>"""
    elif tls == "own":
        cert = """  <section class="m-step">
    <h2><span class="m-n">1</span> This phone trusts Parseh</h2>
    <p>This server speaks with a certificate that was put in place by hand, not one Parseh
    made. If it comes from an authority the phone already trusts &mdash; Tailscale&rsquo;s own
    certificates do, as do Let&rsquo;s Encrypt&rsquo;s &mdash; there is nothing to do here.
    The line at the top of this page says whether the phone trusts it.</p>
  </section>"""
    else:
        cert = """  <section class="m-step">
    <h2><span class="m-n">1</span> This phone trusts Parseh</h2>
    <p>Parseh is being served over plain http this time, and a phone installs an app only
    from https &mdash; the computer itself, at <i>localhost</i>, is the one exception.
    Started as it usually is, Parseh speaks https.</p>
  </section>"""
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(app)s as an app</title>
%(head)s
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/mobile.css">
<script src="/lib/parseh.js"></script>
</head><body class="m-page" data-mobile-page data-browser-page="/">
%(bar)s
<main class="m-main m-install">
  <p class="m-elsewhere">This page belongs to the mobile interface, and the browser
  interface is on: switching to it goes to <a href="/">the hub</a>.</p>
  <h1 class="m-h1">%(app)s as an app</h1>
  <p class="m-tagline">Installed, the mobile interface opens from an icon on the home
  screen, on the whole screen: no address bar over the page, no browser around it.</p>
  <p id="m-appnow" class="m-appnow wait" role="status" aria-live="polite">&nbsp;</p>
%(cert)s
  <section class="m-step">
    <h2><span class="m-n">2</span> Install it</h2>
    <button type="button" class="m-btn" data-parseh-install hidden>Install %(app)s</button>
    <p class="m-how"><b>Android, Chrome:</b> <i>Install %(app)s</i>, here, once the browser
    offers it (the button appears just above); or the browser&rsquo;s <i>&#8942;</i> menu,
    <i>Install app</i> (<i>Add to Home screen</i> in some versions).</p>
    <p class="m-how"><b>iPhone, iPad, Safari:</b> the <i>Share</i> button, then <i>Add to
    Home Screen</i>.</p>
    <p class="m-small">The app is this server: it opens wherever the computer running
    %(app)s can be reached &mdash; on its network, or anywhere over Tailscale &mdash; and
    says so when it cannot.</p>
  </section>
</main>
%(js)s
</body></html>
""" % {"app": APP_NAME, "head": app_head(), "bar": bar("As an app"), "cert": cert,
       "js": INSTALL_JS}


def books_page():
    """/m/books/: every book on the shelf, grouped by language in the
    registry's order under the chip row that filters them, as the library
    groups them."""
    bs = booklib.all_books()
    groups, counts = [], {}
    for L in languages.LANGS.values():
        mine = [b for b in bs if b.language == L.code]
        if not mine:
            continue
        counts[L.code] = len(mine)
        groups.append(lang_head(L, len(mine)))
        groups.extend(book_card(b) for b in mine)
    chips = languages.chips_html(counts, cls="parseh-langs m-langs",
                                 selector=".m-book[data-lang], .m-lhead")
    empty = "" if bs else (
        '<div class="m-empty"><p>No book is on the shelf yet.</p>'
        '<p>Books are added and built in the browser interface &mdash; the switch '
        'is at the top of this page.</p></div>')
    return """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Books &mdash; %(app)s</title>
%(head)s
<link rel="stylesheet" href="/lib/parseh.css">
<link rel="stylesheet" href="/lib/langs.css">
<link rel="stylesheet" href="/lib/mobile.css">
<script src="/lib/parseh.js"></script>
</head><body class="m-page" data-mobile-page data-browser-page="/books/">
%(bar)s
<main class="m-main">
  <p class="m-elsewhere">This is the book shelf of the mobile interface, and the
  browser interface is on: <a href="/books/">the library</a> is its page.</p>
  <h1 class="m-h1">Books</h1>
  <p class="m-tagline">Reading editions: the text in chunks, each with its gloss, the
  narration in step.</p>
%(chips)s
<div class="m-shelf">
%(groups)s</div>%(empty)s
</main>
%(readon)s
</body></html>
""" % {"app": APP_NAME, "head": app_head(), "bar": bar("Books"), "chips": chips,
       "groups": "\n".join(groups), "empty": empty, "readon": READ_ON_JS}


if __name__ == "__main__":
    sys.stdout.write(books_page())
